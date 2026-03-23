# staff_pwa.py

import html
import logging
import json
import urllib.parse
from decimal import Decimal
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response, status, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, delete, and_, desc
from sqlalchemy.orm import joinedload, selectinload

# --- ДОБАВЛЕНЫ ИМПОРТЫ ДЛЯ ОТПРАВКИ ТЕЛЕГРАМ-УВЕДОМЛЕНИЙ ИЗ PWA ---
from urllib.parse import quote_plus
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
# -----------------------------------------------------------------

# Імпорт моделей і залежностей
from models import (
    Employee, Settings, Order, OrderStatus, Role, OrderItem, Table, 
    Category, Product, OrderStatusHistory, StaffNotification, BalanceHistory,
    OrderLog
)
# Імпорт моделей інвентаря
from inventory_models import Modifier, Supplier, InventoryDoc, InventoryDocItem, Warehouse, Ingredient

from dependencies import get_db_session
from auth_utils import verify_password, create_access_token, get_current_staff

# Імпорт шаблонів
from staff_templates import (
    STAFF_LOGIN_HTML, STAFF_DASHBOARD_HTML, 
    STAFF_TABLE_CARD, STAFF_ORDER_CARD
)

# Імпорт менеджерів сповіщень та каси
from notification_manager import (
    notify_all_parties_on_status_change, 
    notify_new_order_to_staff, 
    notify_station_completion,
    create_staff_notification
)
from cash_service import (
    link_order_to_shift, register_employee_debt, unregister_employee_debt,
    get_any_open_shift, open_new_shift, close_active_shift, 
    process_handover, add_shift_transaction, get_shift_statistics
)
# Імпорт сервісу інвентаря
from inventory_service import (
    deduct_products_by_tech_card, reverse_deduction, process_movement, 
    generate_cook_ticket, calculate_order_prime_cost
)
from websocket_manager import manager

# Налаштування роутера та логера
router = APIRouter(prefix="/staff", tags=["staff_pwa"])
logger = logging.getLogger(__name__)

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def check_edit_permissions(employee: Employee, order: Order) -> bool:
    """
    Перевіряє, чи має співробітник право редагувати склад замовлення.
    """
    # 1. Адмін/Оператор може все
    if employee.role.can_manage_orders:
        return True
    
    # 2. Офіціант може редагувати тільки СВОЇ замовлення
    if employee.role.can_serve_tables:
        # Якщо замовлення "in_house" і прийняте цим офіціантом
        if order.accepted_by_waiter_id == employee.id:
            return True
        # Якщо замовлення "in_house", ніким не прийняте (дозволяємо редагувати/приймати)
        if order.order_type == 'in_house' and order.accepted_by_waiter_id is None:
            return True
            
    # 3. Кур'єри, Кухарі, Бармени не можуть змінювати склад замовлення
    return False

async def fetch_db_modifiers(session: AsyncSession, items_list: list) -> dict:
    """
    Збирає всі ID модифікаторів зі списку та завантажує їх з БД.
    """
    all_mod_ids = set()
    for item in items_list:
        for mod in item.get('modifiers', []):
            if 'id' in mod:
                all_mod_ids.add(int(mod['id']))
    
    db_mods = {}
    if all_mod_ids:
        res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
        for m in res.scalars().all():
            db_mods[m.id] = m
    return db_mods

async def check_and_update_order_readiness(session: AsyncSession, order_id: int, bot):
    """
    Перевіряє готовність всіх страв у замовленні.
    Оновлює глобальний статус замовлення, якщо всі позиції готові.
    """
    order = await session.get(Order, order_id, options=[selectinload(Order.items).joinedload(OrderItem.product)])
    if not order: return

    # Перевіряємо глобальну готовність (всі айтеми готові)
    all_items_ready = all(i.is_ready for i in order.items)
    
    # Оновлюємо легасі прапори для сумісності
    kitchen_items = [i for i in order.items if i.preparation_area != 'bar']
    bar_items = [i for i in order.items if i.preparation_area == 'bar']
    
    updated = False
    
    if kitchen_items:
        new_k_done = all(i.is_ready for i in kitchen_items)
        if new_k_done != order.kitchen_done:
            order.kitchen_done = new_k_done
            updated = True
            if new_k_done:
                await notify_station_completion(bot, order, 'kitchen', session)

    if bar_items:
        new_b_done = all(i.is_ready for i in bar_items)
        if new_b_done != order.bar_done:
            order.bar_done = new_b_done
            updated = True
            if new_b_done:
                await notify_station_completion(bot, order, 'bar', session)

    # Якщо ВСЕ готово, змінюємо глобальний статус замовлення
    if all_items_ready:
        ready_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "Готовий до видачі").limit(1))
        
        # Змінюємо статус тільки якщо він ще не фінальний і не "Готов"
        if ready_status and order.status_id != ready_status.id and not order.status.is_completed_status:
            old_status = order.status.name if order.status else "Unknown"
            order.status_id = ready_status.id
            session.add(OrderStatusHistory(order_id=order.id, status_id=ready_status.id, actor_info="Система (Авто-готовність)"))
            
            # Сповіщаємо всіх про зміну статусу
            await notify_all_parties_on_status_change(
                order, old_status, "Система", bot, None, session
            )
            updated = True

    if updated:
        await session.commit()

# --- WEBSOCKET ДЛЯ ПЕРСОНАЛУ ---
@router.websocket("/ws")
async def staff_websocket(websocket: WebSocket):
    await manager.connect_staff(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_staff(websocket)

# --- АВТОРИЗАЦІЯ ---

@router.get("/", include_in_schema=False)
async def staff_root_redirect():
    """Перенаправлення з кореня на дашборд."""
    return RedirectResponse(url="/staff/dashboard")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Сторінка входу. Якщо є токен - редірект на дашборд."""
    token = request.cookies.get("staff_access_token")
    if token:
        return RedirectResponse(url="/staff/dashboard")
    return STAFF_LOGIN_HTML

@router.post("/login")
async def login_action(
    response: Response,
    phone: str = Form(...), 
    password: str = Form(...), 
    session: AsyncSession = Depends(get_db_session)
):
    """Обробка входу співробітника."""
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    result = await session.execute(
        select(Employee).where(Employee.phone_number.ilike(f"%{clean_phone}%"))
    )
    employee = result.scalars().first()

    if not employee:
        return RedirectResponse(url="/staff/login?error=1", status_code=303)
    
    # Проста перевірка пароля
    if not employee.password_hash:
        if password == "admin": pass 
        else: return RedirectResponse(url="/staff/login?error=1", status_code=303)
    elif not verify_password(password, employee.password_hash):
        return RedirectResponse(url="/staff/login?error=1", status_code=303)

    access_token_expires = timedelta(minutes=60 * 12)
    
    access_token = create_access_token(
        data={"sub": str(employee.id)},
        expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/staff/dashboard", status_code=303)
    response.set_cookie(
        key="staff_access_token", 
        value=access_token, 
        httponly=True, 
        max_age=60*60*12,
        samesite="lax"
    )
    return response

@router.get("/logout")
async def logout():
    """Вихід із системи."""
    response = RedirectResponse(url="/staff/login", status_code=303)
    response.delete_cookie("staff_access_token")
    return response

# --- ГОЛОВНА ПАНЕЛЬ (DASHBOARD) ---

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Відображення головної панелі співробітника."""
    try:
        employee = await get_current_staff(request, session)
    except HTTPException:
        response = RedirectResponse(url="/staff/login", status_code=303)
        response.delete_cookie("staff_access_token")
        return response

    settings = await session.get(Settings, 1) or Settings()
    
    if 'role' not in employee.__dict__:
        await session.refresh(employee, ['role'])

    shift_btn_class = "on" if employee.is_on_shift else "off"
    shift_btn_text = "🟢 На зміні" if employee.is_on_shift else "🔴 Почати зміну"

    # --- ГЕНЕРАЦІЯ ВКЛАДОК (TABS) СТРОГО ПО РОЛЯМ ---
    tabs_html = ""
    
    # Ролі (прапори)
    is_admin_operator = employee.role.can_manage_orders
    is_waiter = employee.role.can_serve_tables
    is_courier = employee.role.can_be_assigned
    is_kitchen = employee.role.can_receive_kitchen_orders
    is_bar = employee.role.can_receive_bar_orders

    # 1. ОПЕРАТОР / АДМІН
    if is_admin_operator:
        tabs_html += '<button class="nav-item active" onclick="switchTab(\'orders\')"><i class="fa-solid fa-list-check"></i> Замовлення</button>'
        tabs_html += '<button class="nav-item" onclick="switchTab(\'delivery_admin\')"><i class="fa-solid fa-truck-fast"></i> Доставка (Всі)</button>'
    
    # 2. ОФІЦІАНТ
    if is_waiter:
        if not is_admin_operator:
            tabs_html += '<button class="nav-item active" onclick="switchTab(\'orders\')"><i class="fa-solid fa-list-ul"></i> Мої замовлення</button>'
        tabs_html += '<button class="nav-item" onclick="switchTab(\'tables\')"><i class="fa-solid fa-chair"></i> Столи</button>'
        
    # 3. КУХНЯ / БАР (ОБЪЕДИНЕНО В PRODUCTION)
    if is_kitchen or is_bar:
        active_cls = "active" if not (is_admin_operator or is_waiter) else ""
        tabs_html += f'<button class="nav-item {active_cls}" onclick="switchTab(\'production\')"><i class="fa-solid fa-fire-burner"></i> Черга</button>'
    
    # 4. КУР'ЄР
    if is_courier and not is_admin_operator:
        active_cls = "active" if not (is_waiter or is_kitchen or is_bar) else ""
        tabs_html += f'<button class="nav-item {active_cls}" onclick="switchTab(\'delivery_courier\')"><i class="fa-solid fa-motorcycle"></i> Мої доставки</button>'
    
    # 5. ФІНАНСИ (Каса)
    if is_waiter or is_courier or is_admin_operator:
        tabs_html += '<button class="nav-item" onclick="switchTab(\'finance\')"><i class="fa-solid fa-wallet"></i> Каса</button>'

    # 6. КАСИР (АДМІН) - Нова вкладка
    if is_admin_operator:
        tabs_html += '<button class="nav-item" onclick="switchTab(\'cashier_control\')"><i class="fa-solid fa-cash-register"></i> Керування</button>'

    # Сповіщення (для всіх)
    tabs_html += '<button class="nav-item" onclick="switchTab(\'notifications\')" style="position:relative;"><i class="fa-solid fa-bell"></i> Інфо<span id="nav-notify-badge" class="notify-dot" style="display:none;"></span></button>'

    content = f"""
    <div class="dashboard-header">
        <div class="user-info">
            <h3>{html.escape(employee.full_name)}</h3>
            <span class="role-badge">{html.escape(employee.role.name)}</span>
        </div>
        <button onclick="toggleShift()" id="shift-btn" class="shift-btn {shift_btn_class}">{shift_btn_text}</button>
    </div>
    
    <div id="main-view">
        <div id="loading-indicator"><i class="fa-solid fa-spinner fa-spin"></i> Завантаження...</div>
        <div id="content-area"></div>
    </div>

    <div class="bottom-nav" id="bottom-nav">
        {tabs_html}
        <button class="nav-item" onclick="window.location.href='/staff/logout'"><i class="fa-solid fa-right-from-bracket"></i> Вихід</button>
    </div>
    """
    
    return STAFF_DASHBOARD_HTML.format(
        site_title=settings.site_title or "Staff App",
        content=content
    )

@router.get("/manifest.json")
async def get_manifest(session: AsyncSession = Depends(get_db_session)):
    settings = await session.get(Settings, 1) or Settings()
    return JSONResponse({
        "name": f"{settings.site_title} Staff",
        "short_name": "Staff",
        "start_url": "/staff/dashboard",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": settings.primary_color or "#333333",
        "icons": [
            {"src": "/static/favicons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/favicons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/favicons/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"}
        ]
    })

# --- API МЕТОДИ ДЛЯ JS ---

@router.post("/api/shift/toggle")
async def toggle_shift_api(session: AsyncSession = Depends(get_db_session), employee: Employee = Depends(get_current_staff)):
    employee.is_on_shift = not employee.is_on_shift
    await session.commit()
    return JSONResponse({"status": "ok", "is_on_shift": employee.is_on_shift})

@router.get("/api/notifications")
async def get_notifications_api(session: AsyncSession = Depends(get_db_session), employee: Employee = Depends(get_current_staff)):
    notifs = (await session.execute(
        select(StaffNotification)
        .where(StaffNotification.employee_id == employee.id)
        .order_by(StaffNotification.created_at.desc())
        .limit(20)
    )).scalars().all()
    
    unread_count = sum(1 for n in notifs if not n.is_read)
    
    data = []
    for n in notifs:
        data.append({
            "id": n.id, 
            "message": n.message, 
            "time": n.created_at.strftime("%d.%m %H:%M"), 
            "is_read": n.is_read
        })
        if not n.is_read: 
            n.is_read = True
    
    if unread_count > 0: 
        await session.commit()
        
    return JSONResponse({"unread_count": unread_count, "list": data})

@router.get("/api/data")
async def get_staff_data(
    view: str = "orders",
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """Основний метод отримання HTML-контенту для вкладок."""
    try:
        if not employee.is_on_shift:
            return JSONResponse({"html": "<div class='empty-state'><i class='fa-solid fa-power-off'></i>🔴 Ви не на зміні. <br>Натисніть кнопку зверху для початку роботи.</div>"})

        # --- Вкладка СТОЛИ ---
        if view == "tables" and employee.role.can_serve_tables:
            return await _render_tables_view(session, employee)

        # --- Вкладка ЗАМОВЛЕННЯ ---
        elif view == "orders":
            if employee.role.can_manage_orders:
                orders_data = await _get_general_orders(session, employee)
                return JSONResponse({"html": "".join([o["html"] for o in orders_data]) if orders_data else "<div class='empty-state'><i class='fa-regular fa-folder-open'></i>Активних замовлень немає.</div>"})
            elif employee.role.can_serve_tables:
                orders_html = await _get_waiter_orders_grouped(session, employee)
                return JSONResponse({"html": orders_html if orders_html else "<div class='empty-state'><i class='fa-solid fa-utensils'></i>Ваших активних замовлень немає.</div>"})
            else:
                return JSONResponse({"html": "<div class='empty-state'>Немає доступу до списку замовлень.</div>"})

        # --- Вкладка ФІНАНСИ (Каса) ---
        elif view == "finance":
            if employee.role.can_serve_tables or employee.role.can_be_assigned or employee.role.can_manage_orders:
                finance_html = await _get_finance_details(session, employee)
                return JSONResponse({"html": finance_html})
            else:
                return JSONResponse({"html": "<div class='empty-state'>Доступ заборонено.</div>"})

        # --- Вкладка ВИРОБНИЦТВО (Кухня/Бар) ---
        elif view == "production":
            if employee.role.can_receive_kitchen_orders or employee.role.can_receive_bar_orders:
                orders_data = await _get_production_orders(session, employee)
                return JSONResponse({"html": "".join([o["html"] for o in orders_data]) if orders_data else "<div class='empty-state'><i class='fa-solid fa-check-double'></i>Черга пуста. Всі страви готові.</div>"})
            else:
                return JSONResponse({"html": "<div class='empty-state'>У вас немає прав доступу до кухні/бару.</div>"})

        # --- Вкладка ДОСТАВКА (КУР'ЄР) ---
        elif view == "delivery_courier":
            if employee.role.can_be_assigned:
                orders_data = await _get_my_courier_orders(session, employee)
                return JSONResponse({"html": "".join([o["html"] for o in orders_data]) if orders_data else "<div class='empty-state'><i class='fa-solid fa-motorcycle'></i>Немає призначених замовлень.</div>"})
            else:
                return JSONResponse({"html": "<div class='empty-state'>Ви не кур'єр.</div>"})

        # --- Вкладка ДОСТАВКА (АДМІН) ---
        elif view == "delivery_admin":
            if employee.role.can_manage_orders:
                orders_data = await _get_all_delivery_orders_for_admin(session, employee)
                return JSONResponse({"html": "".join([o["html"] for o in orders_data]) if orders_data else "<div class='empty-state'><i class='fa-solid fa-truck'></i>Активних доставок немає.</div>"})
            else:
                return JSONResponse({"html": "<div class='empty-state'>Доступ заборонено.</div>"})
        
        # --- Вкладка КАСИР (УПРАВЛІННЯ) ---
        elif view == "cashier_control":
            if employee.role.can_manage_orders:
                cashier_html = await _get_cashier_dashboard_view(session, employee)
                return JSONResponse({"html": cashier_html})
            else:
                return JSONResponse({"html": "<div class='empty-state'>Доступ заборонено.</div>"})

        elif view == "notifications":
            return JSONResponse({"html": "<div id='notification-list-container' style='text-align:center; color:#999;'>Оновлення...</div>"})

        return JSONResponse({"html": ""})
        
    except Exception as e:
        logger.error(f"API Error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

# --- РЕНДЕРИНГ КОНТЕНТУ ---

async def _render_tables_view(session: AsyncSession, employee: Employee):
    tables = (await session.execute(
        select(Table)
        .where(Table.assigned_waiters.any(Employee.id == employee.id))
        .order_by(Table.name)
    )).scalars().all()
    
    if not tables: 
        return JSONResponse({"html": "<div class='empty-state'><i class='fa-solid fa-chair'></i>За вами не закріплено столиків.</div>"})
    
    html_content = "<div class='grid-container'>"
    for t in tables:
        final_ids = select(OrderStatus.id).where(or_(OrderStatus.is_completed_status==True, OrderStatus.is_cancelled_status==True))
        active_count = await session.scalar(
            select(func.count(Order.id)).where(Order.table_id == t.id, Order.status_id.not_in(final_ids))
        )
        
        badge_class = "alert" if active_count > 0 else "success"
        border_color = "#e74c3c" if active_count > 0 else "transparent"
        bg_color = "#fff"
        status_text = f"{active_count} активних" if active_count > 0 else "Вільний"
        
        html_content += STAFF_TABLE_CARD.format(
            id=t.id, 
            name_esc=html.escape(t.name), 
            badge_class=badge_class, 
            status_text=status_text, 
            border_color=border_color, 
            bg_color=bg_color
        )
    html_content += "</div>"
    return JSONResponse({"html": html_content})

async def _get_waiter_orders_grouped(session: AsyncSession, employee: Employee):
    final_ids = (await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))).scalars().all()
    
    tables_sub = select(Table.id).where(Table.assigned_waiters.any(Employee.id == employee.id))
    
    q = select(Order).options(
        joinedload(Order.status), joinedload(Order.table), joinedload(Order.accepted_by_waiter),
        selectinload(Order.items)
    ).where(
        Order.status_id.not_in(final_ids),
        or_(Order.accepted_by_waiter_id == employee.id, Order.table_id.in_(tables_sub))
    ).order_by(Order.table_id, Order.id.desc())

    orders = (await session.execute(q)).scalars().all()
    if not orders: return ""

    grouped_orders = {} 
    for o in orders:
        t_id = o.table_id if o.table_id else 0 
        if t_id not in grouped_orders:
            t_name = o.table.name if o.table else "Інше"
            grouped_orders[t_id] = {"name": t_name, "orders": [], "total": Decimal(0)}
        
        grouped_orders[t_id]["orders"].append(o)
        grouped_orders[t_id]["total"] += o.total_price

    html_out = ""
    for t_id, group in grouped_orders.items():
        html_out += f"""
        <div class='table-group-header' style="justify-content: space-between;">
            <span><i class='fa-solid fa-chair'></i> {html.escape(group['name'])}</span>
            <span class="badge warning" style="font-size:0.9em; color:#333;">Σ {group['total']:.2f} грн</span>
        </div>
        """

        for o in group['orders']:
            items_html_list = []
            for item in o.items:
                mods_str = ""
                if item.modifiers:
                    mods_names = [m['name'] for m in item.modifiers]
                    mods_str = f" <small style='color:#666;'>({', '.join(mods_names)})</small>"
                
                is_ready = item.is_ready
                icon = "✅" if is_ready else "⏳"
                style = "color:green; font-weight:bold;" if is_ready else "color:#555;"
                
                items_html_list.append(f"<li style='{style}'>{icon} {html.escape(item.product_name)}{mods_str} x{item.quantity}</li>")
            
            items_html = f"<ul style='margin:5px 0; padding-left:20px; font-size:0.9rem;'>{''.join(items_html_list)}</ul>"

            content = f"""
            <div class="info-row"><i class="fa-solid fa-clock"></i> {o.created_at.strftime('%H:%M')}</div>
            <div class="info-row"><i class="fa-solid fa-money-bill-wave"></i> <b>{o.total_price} грн</b></div>
            {items_html}
            """
            
            btns = ""
            if not o.accepted_by_waiter_id: 
                btns += f"<button class='action-btn' onclick=\"performAction('accept_order', {o.id})\">🙋 Прийняти</button>"
            else: 
                btns += f"<button class='action-btn secondary' onclick=\"openOrderEditModal({o.id})\">✏️ Деталі / Оплата</button>"
            
            status_parts = [o.status.name]
            if o.kitchen_done: status_parts.append("🍳Готово")
            if o.bar_done: status_parts.append("🍹Готово")
            
            badge_class = "success" if (o.kitchen_done or o.bar_done) else "info"
            color = "#27ae60" if (o.kitchen_done or o.bar_done) else "#333"

            html_out += STAFF_ORDER_CARD.format(
                id=o.id, 
                time=o.created_at.strftime('%H:%M'), 
                badge_class=badge_class, 
                status=" | ".join(status_parts), 
                content=content, 
                buttons=btns, 
                color=color
            )
        
    return html_out

async def _get_finance_details(session: AsyncSession, employee: Employee):
    current_debt = employee.cash_balance
    
    q = select(Order).options(joinedload(Order.table)).where(
        or_(
            Order.accepted_by_waiter_id == employee.id,
            Order.courier_id == employee.id
        ),
        Order.payment_method == 'cash',
        Order.is_cash_turned_in == False,
        Order.status.has(is_completed_status=True)
    ).order_by(Order.id.desc())
    
    orders = (await session.execute(q)).scalars().all()
    
    list_html = ""
    for o in orders:
        target = o.table.name if o.table else (o.address or "Самовивіз")
        list_html += f"""
        <div class="debt-item">
            <div>
                <div style="font-weight:bold;">#{o.id} - {html.escape(target)}</div>
                <div style="font-size:0.8rem; color:#777;">{o.created_at.strftime('%d.%m %H:%M')}</div>
            </div>
            <div style="font-weight:bold; color:#e74c3c;">{o.total_price} грн</div>
        </div>
        """
    
    if not list_html:
        list_html = "<div style='text-align:center; color:#999; padding:20px;'>Немає незакритих чеків</div>"

    color_class = "red-text" if current_debt > 0 else "green-text"
    
    return f"""
    <div class="finance-card">
        <div class="finance-header">Ваш баланс (Борг)</div>
        <div class="finance-amount {color_class}">{current_debt:.2f} грн</div>
        <div style="font-size:0.9rem; color:#666; margin-top:5px;">Готівка на руках</div>
    </div>
    
    <h4 style="margin: 20px 0 10px; padding-left: 5px;">Деталізація (Не здані в касу):</h4>
    <div class="debt-list">
        {list_html}
    </div>
    <div style="text-align:center; margin-top:20px; font-size:0.85rem; color:#888;">
        Щоб здати гроші, зверніться до адміністратора.
    </div>
    """

async def _get_cashier_dashboard_view(session: AsyncSession, employee: Employee):
    # 1. Перевірка зміни
    shift = await get_any_open_shift(session)
    
    if not shift:
        return """
        <div class="card" style="text-align:center; padding:30px;">
            <i class="fa-solid fa-store-slash" style="font-size:3rem; color:#ccc; margin-bottom:15px;"></i>
            <h3>Зміна закрита</h3>
            <p style="color:#666; margin-bottom:20px;">Для початку роботи відкрийте касову зміну.</p>
            <div class="form-group">
                <label>Початковий залишок (грн):</label>
                <input type="number" id="start-cash-input" class="form-control" value="0.00" style="text-align:center; font-size:1.2rem;">
            </div>
            <button class="big-btn success" onclick="cashierAction('open_shift')">🟢 Відкрити зміну</button>
        </div>
        """

    # 2. Статистика зміни (коротка)
    stats = await get_shift_statistics(session, shift.id)
    cash_in_drawer = stats['theoretical_cash']
    
    # 3. Боржники (хто має здати гроші)
    debtors_res = await session.execute(
        select(Employee).where(Employee.cash_balance > 0).order_by(desc(Employee.cash_balance))
    )
    debtors = debtors_res.scalars().all()
    
    debtors_html = ""
    if debtors:
        for d in debtors:
            debtors_html += f"""
            <div class="debt-item">
                <div>
                    <div style="font-weight:bold;">{html.escape(d.full_name)}</div>
                    <div style="font-size:0.8rem; color:#666;">{d.role.name}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-weight:bold; color:#e74c3c; margin-bottom:5px;">{d.cash_balance:.2f} грн</div>
                    <button class="action-btn" onclick="cashierAction('accept_debt', {d.id})">Прийняти</button>
                </div>
            </div>
            """
    else:
        debtors_html = "<div style='text-align:center; color:#999; padding:15px;'>Всі гроші здано ✅</div>"

    # 4. Неоплачені накладні (Покращене відображення)
    # Фільтруємо: Тільки 'supply', тільки проведені, і тільки ті, де Є ПОСТАЧАЛЬНИК (виключаємо внутрішнє виробництво напівфабрикатів)
    docs_res = await session.execute(
        select(InventoryDoc)
        .options(selectinload(InventoryDoc.items), joinedload(InventoryDoc.supplier))
        .where(
            InventoryDoc.doc_type == 'supply', 
            InventoryDoc.is_processed == True,
            InventoryDoc.supplier_id != None  # <--- Ігноруємо внутрішні акти (П/Ф)
        )
        .order_by(InventoryDoc.created_at.desc())
    )
    docs = docs_res.scalars().all()
    
    unpaid_html = ""
    for d in docs:
        total = sum(i.quantity * i.price for i in d.items)
        # Уникаємо ділення на нуль та помилок з None
        paid = Decimal(str(d.paid_amount or 0))
        debt = total - paid
        
        if debt > 0.01:
            supplier_name = html.escape(d.supplier.name if d.supplier else 'Постачальник')
            percent_paid = (paid / total * 100) if total > 0 else 0
            
            date_str = d.created_at.strftime('%d.%m')
            time_str = d.created_at.strftime('%H:%M')
            
            # Стиль прогрес-бару
            bar_color = "#e74c3c" # Червоний
            if percent_paid > 50: bar_color = "#f39c12" # Помаранчевий
            if percent_paid > 90: bar_color = "#27ae60" # Зелений

            unpaid_html += f"""
            <div class="invoice-card">
                <div class="inv-header">
                    <div class="inv-title">
                        <i class="fa-solid fa-truck-field"></i> {supplier_name}
                    </div>
                    <div class="inv-date">{date_str} <small>{time_str}</small></div>
                </div>
                
                <div class="inv-id">Накладна #{d.id}</div>
                
                <div class="inv-progress-bg">
                    <div class="inv-progress-fill" style="width: {percent_paid}%; background-color: {bar_color};"></div>
                </div>
                
                <div class="inv-footer">
                    <div>
                        <div style="font-size:0.75rem; color:#666;">Залишок боргу:</div>
                        <div style="font-weight:bold; color:#e74c3c; font-size:1.1rem;">{debt:.2f} <small>грн</small></div>
                    </div>
                    <button class="action-btn" onclick="openPayDocModal({d.id}, {debt}, '{supplier_name}')">
                        Сплатити
                    </button>
                </div>
            </div>
            """
            
    if not unpaid_html:
        unpaid_html = "<div style='text-align:center; padding:25px; color:#999; background:#f9f9f9; border-radius:12px;'>Немає неоплачених накладних 🎉</div>"

    # Додаткові CSS стилі для нових карток
    styles = """
    <style>
        .invoice-card { background: white; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #eee; }
        .inv-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .inv-title { font-weight: 700; color: #333; font-size: 1rem; display:flex; align-items:center; gap:8px; }
        .inv-date { background: #f1f5f9; padding: 2px 8px; border-radius: 6px; font-size: 0.8rem; color: #64748b; }
        .inv-id { font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }
        .inv-progress-bg { height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden; margin-bottom: 12px; }
        .inv-progress-fill { height: 100%; transition: width 0.3s ease; }
        .inv-footer { display: flex; justify-content: space-between; align-items: end; }
    </style>
    """

    return f"""
    {styles}
    <div class="finance-card" style="background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%); border: 1px solid #bae6fd;">
        <div class="finance-header" style="color:#0369a1;">В касі (Готівка)</div>
        <div class="finance-amount" style="color:#0284c7;">{cash_in_drawer:.2f} грн</div>
        <div style="font-size:0.8rem; margin-top:5px; color:#0c4a6e;">
            Продажі (Готівка): <b>{stats['total_sales_cash']:.2f}</b> грн
        </div>
    </div>

    <h4 style="margin:25px 0 10px; color:#475569; text-transform:uppercase; font-size:0.85rem; letter-spacing:0.5px;">
        <i class="fa-solid fa-hand-holding-dollar"></i> Прийом виручки від персоналу
    </h4>
    <div class="debt-list">
        {debtors_html}
    </div>
    
    <h4 style="margin:25px 0 10px; color:#475569; text-transform:uppercase; font-size:0.85rem; letter-spacing:0.5px;">
        <i class="fa-solid fa-file-invoice-dollar"></i> Неоплачені накладні
    </h4>
    <div class="invoices-list">
        {unpaid_html}
    </div>

    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:30px;">
        <button class="action-btn secondary" style="justify-content:center; padding:15px; background:#f8fafc; border:1px solid #e2e8f0;" onclick="openSupplyModal()">
            <i class="fa-solid fa-truck-ramp-box" style="color:#333;"></i> Прихід
        </button>
        <button class="action-btn secondary" style="justify-content:center; padding:15px; background:#f8fafc; border:1px solid #e2e8f0;" onclick="openTransactionModal()">
            <i class="fa-solid fa-money-bill-transfer" style="color:#333;"></i> Транзакція
        </button>
    </div>

    <button class="big-btn danger" style="margin-top:30px; background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5;" onclick="cashierAction('close_shift')">
        🛑 Закрити зміну (Z-звіт)
    </button>
    <div style="height: 50px;"></div>
    """

async def _get_production_orders(session: AsyncSession, employee: Employee):
    """
    Генерація списку замовлень для екрану виробництва (Кухня/Бар).
    Суворо використовує прапорці з бази даних та нормалізує типи ID.
    """
    orders_data = []
    
    # Конвертуємо JSON IDs у список цілих чисел для надійного порівняння
    raw_workshop_ids = employee.assigned_workshop_ids or []
    my_workshop_ids = []
    for wid in raw_workshop_ids:
        try:
            my_workshop_ids.append(int(wid))
        except (ValueError, TypeError):
            pass
            
    is_kitchen = employee.role.can_receive_kitchen_orders
    is_bar = employee.role.can_receive_bar_orders

    # Надійний запит: беремо ТІЛЬКИ ті замовлення, статус яких має прапорець requires_kitchen_notify
    q = select(Order).join(OrderStatus).options(
        joinedload(Order.table), 
        selectinload(Order.items).joinedload(OrderItem.product), 
        joinedload(Order.status)
    ).where(
        OrderStatus.requires_kitchen_notify == True,
        or_(OrderStatus.visible_to_chef == True, OrderStatus.visible_to_bartender == True)
    ).order_by(Order.id.asc())
    
    orders = (await session.execute(q)).scalars().all()
    
    if orders:
        for o in orders:
            active_items_html = ""
            done_items_html = ""
            count_active_my_items = 0
            count_total_my_items = 0
            
            for item in o.items:
                is_my_item = False
                prod_wh_id = item.product.production_warehouse_id
                area = item.preparation_area
                
                # Логіка 1: Перевірка по цехах (з урахуванням виправлених типів)
                if my_workshop_ids and prod_wh_id is not None:
                    if int(prod_wh_id) in my_workshop_ids:
                        is_my_item = True
                # Логіка 2: Базова перевірка по ролях (якщо цехи не налаштовані)
                else:
                    if area == 'bar' and is_bar:
                        is_my_item = True
                    elif area != 'bar' and is_kitchen:
                        is_my_item = True
                        
                if not is_my_item:
                    continue
                    
                count_total_my_items += 1
                
                mods = f"<br><small>{', '.join([m['name'] for m in item.modifiers])}</small>" if item.modifiers else ""
                
                if item.is_ready:
                    done_items_html += f"""
                    <div onclick="if(confirm('Повернути цю страву в роботу?')) performAction('toggle_item', {o.id}, {item.id})" 
                         style="padding:12px 15px; border-bottom:1px solid #eee; cursor:pointer; font-size:1rem; display:flex; align-items:center; background:#f9f9f9; color:#999; text-decoration:line-through;">
                        <i class="fa-solid fa-check-circle" style="margin-right:15px; color:#aaa;"></i> 
                        <div style="flex-grow:1;">{html.escape(item.product_name)} x{item.quantity}{mods}</div>
                    </div>
                    """
                else:
                    count_active_my_items += 1
                    active_items_html += f"""
                    <div onclick="if(confirm('Страва готова?')) performAction('toggle_item', {o.id}, {item.id})" 
                         style="padding:18px 15px; border-bottom:1px solid #eee; cursor:pointer; font-size:1.15rem; display:flex; align-items:center; background:white; font-weight:500;">
                        <i class="fa-regular fa-square" style="margin-right:15px; color:#ccc; font-size:1.4rem;"></i> 
                        <div style="flex-grow:1;">{html.escape(item.product_name)} x{item.quantity}{mods}</div>
                    </div>
                    """
            
            if count_total_my_items > 0:
                if count_active_my_items == 0: continue # Все готово, приховуємо

                table_info = o.table.name if o.table else ("Доставка" if o.is_delivery else "Самовивіз")
                
                full_content = f"""
                <div class='info-row'><i class='fa-solid fa-utensils'></i> <b>{table_info}</b> <span style="color:#777; margin-left:10px;">#{o.id}</span></div>
                <div style='border-radius:8px; overflow:hidden; border:1px solid #ddd; margin-top:5px;'>
                    {active_items_html}
                    {done_items_html}
                </div>
                """
                
                orders_data.append({"id": o.id, "html": STAFF_ORDER_CARD.format(
                    id=o.id, 
                    time=o.created_at.strftime('%H:%M'), 
                    badge_class="warning", 
                    status="В роботі", 
                    content=full_content,
                    buttons="", 
                    color="#f39c12"
                )})

    return orders_data

async def _get_my_courier_orders(session: AsyncSession, employee: Employee):
    final_ids = (await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))).scalars().all()
    q = select(Order).options(joinedload(Order.status), selectinload(Order.items)).where(Order.courier_id == employee.id, Order.status_id.not_in(final_ids)).order_by(Order.id.desc())
    orders = (await session.execute(q)).scalars().all()
    res = []
    for o in orders:
        items_html_list = []
        for item in o.items:
            is_ready = item.is_ready
            icon = "✅" if is_ready else "⏳"
            style = "color:#27ae60;" if is_ready else "color:#555;"
            items_html_list.append(f"<div style='{style}'>{icon} {html.escape(item.product_name)} x{item.quantity}</div>")
        
        items_block = "".join(items_html_list)

        # Определение метода оплаты
        pay_method = "Готівка 💵" if o.payment_method == "cash" else "Картка 💳"
        
        # Контент карточки со всей информацией
        content = f"""
        <div class="info-row"><i class="fa-solid fa-user"></i> <b>{html.escape(o.customer_name or 'Клієнт не вказаний')}</b></div>
        <div class="info-row"><i class="fa-solid fa-phone"></i> <a href="tel:{o.phone_number}" style="color:#3498db; text-decoration:none; font-weight:bold;">{html.escape(o.phone_number or 'Немає номеру')}</a></div>
        <div class="info-row"><i class="fa-solid fa-map-pin"></i> {html.escape(o.address or 'Не вказано')}</div>
        <div class="info-row"><i class="fa-solid fa-clock"></i> {html.escape(o.delivery_time or 'Якнайшвидше')}</div>
        <div class="info-row"><i class="fa-solid fa-credit-card"></i> {pay_method}</div>
        <div class="info-row"><i class="fa-solid fa-money-bill"></i> <b style="font-size: 1.1rem; color: #27ae60;">{o.total_price} грн</b></div>
        <div style="margin-top:10px; padding-top:5px; border-top:1px dashed #ccc; font-size:0.9rem;">
            {items_block}
        </div>
        """
        
        status_text = o.status.name
        if o.kitchen_done and o.bar_done: status_text = "📦 ВСЕ ГОТОВО"
        elif o.kitchen_done: status_text = "🍳 Кухня готова"
        
        # Кнопка навигации для курьера
        safe_address = urllib.parse.quote(o.address) if o.address else ""
        nav_btn = f"<a href='https://www.google.com/maps/search/?api=1&query={safe_address}' target='_blank' class='action-btn' style='background:#27ae60; color:white; text-decoration:none;'><i class='fa-solid fa-location-arrow'></i> Навігація</a>" if o.address else ""
        
        btns = f"""
        <div style="display:flex; gap:10px; width:100%; justify-content:flex-end;">
            {nav_btn}
            <button class='action-btn secondary' onclick="openOrderEditModal({o.id})">⚙️ Інфо</button>
        </div>
        """
        res.append({"id": o.id, "html": STAFF_ORDER_CARD.format(
            id=o.id, 
            time=o.created_at.strftime('%H:%M'), 
            badge_class="success" if (o.kitchen_done and o.bar_done) else "info", 
            status=status_text, 
            content=content, 
            buttons=btns, 
            color="#333"
        )})
    return res

async def _get_all_delivery_orders_for_admin(session: AsyncSession, employee: Employee):
    final_ids = (await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))).scalars().all()
    
    q = select(Order).options(
        joinedload(Order.status), joinedload(Order.courier)
    ).where(
        Order.status_id.not_in(final_ids),
        Order.is_delivery == True
    ).order_by(Order.id.desc())

    orders = (await session.execute(q)).scalars().all()
    res = []
    for o in orders:
        courier_info = f"🚴 {o.courier.full_name}" if o.courier else "<span style='color:red'>🔴 Не призначено</span>"
        pay_method = "Готівка 💵" if o.payment_method == "cash" else "Картка 💳"
        
        content = f"""
        <div class="info-row"><i class="fa-solid fa-user"></i> <b>{html.escape(o.customer_name or 'Клієнт')}</b></div>
        <div class="info-row"><i class="fa-solid fa-phone"></i> <a href="tel:{o.phone_number}" style="color:#3498db; text-decoration:none;">{html.escape(o.phone_number or '')}</a></div>
        <div class="info-row"><i class="fa-solid fa-map-pin"></i> <b>{html.escape(o.address or 'Адреса не вказана')}</b></div>
        <div class="info-row"><i class="fa-solid fa-clock"></i> {html.escape(o.delivery_time or 'Якнайшвидше')}</div>
        <div class="info-row"><i class="fa-solid fa-credit-card"></i> {pay_method}</div>
        <div class="info-row"><i class="fa-solid fa-motorcycle"></i> {courier_info}</div>
        <div class="info-row"><i class="fa-solid fa-money-bill-wave"></i> <b style="color:#27ae60;">{o.total_price} грн</b></div>
        """
        
        btns = f"<button class='action-btn' onclick=\"openOrderEditModal({o.id})\">⚙️ Призначити / Змінити</button>"
        
        res.append({"id": o.id, "html": STAFF_ORDER_CARD.format(
            id=o.id, 
            time=o.created_at.strftime('%H:%M'), 
            badge_class="warning" if not o.courier else "info", 
            status=o.status.name, 
            content=content, 
            buttons=btns, 
            color="#e67e22" if not o.courier else "#3498db"
        )})
    return res

async def _get_general_orders(session: AsyncSession, employee: Employee):
    final_ids = (await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))).scalars().all()
    
    q = select(Order).options(
        joinedload(Order.status), joinedload(Order.table), joinedload(Order.accepted_by_waiter), joinedload(Order.courier), selectinload(Order.items)
    ).where(Order.status_id.not_in(final_ids)).order_by(Order.id.desc())

    orders = (await session.execute(q)).scalars().all()
    res = []
    
    # --- НОВА КНОПКА ---
    create_btn = """
    <div style="margin-bottom: 15px;">
        <button class="big-btn success" onclick="startDeliveryCreation()">
            <i class="fa-solid fa-plus"></i> Створити доставку
        </button>
    </div>
    """
    res.append({"id": 0, "html": create_btn})
    # --------------------

    for o in orders:
        table_name = o.table.name if o.table else ("Доставка" if o.is_delivery else "Самовивіз")
        pay_method = "Готівка" if o.payment_method == "cash" else "Картка"
        
        extra_info = ""
        if o.is_delivery:
            courier_name = o.courier.full_name if o.courier else "Не призначено"
            extra_info = f"""
            <div class='info-row'><i class="fa-solid fa-user"></i> {html.escape(o.customer_name or 'Клієнт')}</div>
            <div class='info-row'><i class="fa-solid fa-phone"></i> {html.escape(o.phone_number or '')}</div>
            <div class='info-row'><i class="fa-solid fa-map-pin"></i> {html.escape(o.address or 'Адреса не вказана')}</div>
            <div class='info-row'><i class="fa-solid fa-clock"></i> {html.escape(o.delivery_time or 'Якнайшвидше')}</div>
            <div class='info-row' style='font-size:0.85rem; color:#555;'><i class="fa-solid fa-motorcycle"></i> Кур'єр: {courier_name}</div>
            """
        else:
            extra_info = f"""
            <div class='info-row'><i class="fa-solid fa-user"></i> {html.escape(o.customer_name or 'Клієнт')}</div>
            """

        items_list = []
        for item in o.items:
            mods_str = ""
            if item.modifiers:
                mods_names = [m['name'] for m in item.modifiers]
                mods_str = f" <small>({', '.join(mods_names)})</small>"
            items_list.append(f"{item.product_name}{mods_str}")
        items_preview = ", ".join(items_list)
        if len(items_preview) > 50: items_preview = items_preview[:50] + "..."

        content = f"""
        <div class="info-row"><i class="fa-solid fa-info-circle"></i> <b style="font-size:1.1rem;">{html.escape(table_name)}</b></div>
        <div class="info-row"><i class="fa-solid fa-money-bill-wave"></i> <b>{o.total_price} грн</b> <span style="font-size:0.8rem; color:#777; margin-left:5px;">({pay_method})</span></div>
        {extra_info}
        <div class="info-row" style="font-size:0.85rem; color:#666; margin-top:5px; border-top:1px dashed #eee; padding-top:5px;"><i class="fa-solid fa-list"></i> {html.escape(items_preview)}</div>
        """
        
        btns = f"<button class='action-btn secondary' onclick=\"openOrderEditModal({o.id})\">⚙️ Керувати</button>"
        
        res.append({"id": o.id, "html": STAFF_ORDER_CARD.format(
            id=o.id, 
            time=o.created_at.strftime('%H:%M'), 
            badge_class="info", 
            status=o.status.name, 
            content=content, 
            buttons=btns, 
            color="#333"
        )})
    return res

@router.get("/api/order/{order_id}/details")
async def get_order_details(order_id: int, session: AsyncSession = Depends(get_db_session), employee: Employee = Depends(get_current_staff)):
    order = await session.get(Order, order_id, options=[selectinload(Order.items), joinedload(Order.status), joinedload(Order.courier)])
    if not order: return JSONResponse({"error": "Не знайдено"}, status_code=404)
    
    status_query = select(OrderStatus)
    if employee.role.can_manage_orders:
        status_query = status_query.where(OrderStatus.visible_to_operator == True)
    elif employee.role.can_be_assigned:
        status_query = status_query.where(OrderStatus.visible_to_courier == True)
    elif employee.role.can_serve_tables:
        status_query = status_query.where(OrderStatus.visible_to_waiter == True)
    else:
        status_query = status_query.where(OrderStatus.id == order.status_id)
    
    statuses = (await session.execute(status_query.order_by(OrderStatus.id))).scalars().all()
    
    if order.status_id not in [s.id for s in statuses]:
        current_s = await session.get(OrderStatus, order.status_id)
        if current_s: statuses.append(current_s)

    status_list = [{"id": s.id, "name": s.name, "selected": s.id == order.status_id, "is_completed": s.is_completed_status, "is_cancelled": s.is_cancelled_status} for s in statuses]

    items = []
    for i in order.items:
        modifiers_str = ""
        if i.modifiers:
            mod_names = [m['name'] for m in i.modifiers]
            if mod_names:
                modifiers_str = f" + {', '.join(mod_names)}"
        
        items.append({
            "id": i.product_id, 
            "name": i.product_name + modifiers_str, 
            "qty": i.quantity, 
            "price": float(i.price_at_moment),
            "modifiers": i.modifiers 
        })
    
    couriers_list = []
    if employee.role.can_manage_orders and order.is_delivery:
        courier_role_res = await session.execute(select(Role.id).where(Role.can_be_assigned == True))
        courier_role_ids = courier_role_res.scalars().all()
        if courier_role_ids:
            couriers = (await session.execute(select(Employee).where(Employee.role_id.in_(courier_role_ids), Employee.is_on_shift == True))).scalars().all()
            couriers_list = [{"id": c.id, "name": c.full_name, "selected": c.id == order.courier_id} for c in couriers]

    return JSONResponse({
        "id": order.id,
        "total": float(order.total_price),
        "items": items,
        "statuses": status_list,
        "status_id": order.status_id,
        "is_delivery": order.is_delivery,
        
        # --- ОНОВЛЕНО: Додано delivery_time ---
        "customer_name": order.customer_name,
        "phone_number": order.phone_number,
        "address": order.address,
        "delivery_time": order.delivery_time, # <--- ДОДАНО: Час доставки
        "comment": order.comment,             # <--- ЗМІНЕНО: тепер це поле comment
        "payment_method": order.payment_method,
        "created_at": order.created_at.strftime('%H:%M'),
        # ----------------------------------------------------------------

        "couriers": couriers_list,
        "can_assign_courier": employee.role.can_manage_orders,
        "can_edit_items": check_edit_permissions(employee, order)
    })

@router.post("/api/order/assign_courier")
async def assign_courier_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """
    ВИПРАВЛЕНО: Тепер ця функція не тільки створює сповіщення в PWA,
    а й відправляє повноцінне повідомлення в Telegram кур'єру.
    """
    if not employee.role.can_manage_orders:
        return JSONResponse({"error": "Заборонено"}, status_code=403)
        
    data = await request.json()
    order_id = int(data.get("orderId"))
    courier_id = int(data.get("courierId")) 
    
    order = await session.get(Order, order_id)
    if not order: return JSONResponse({"error": "Замовлення не знайдено"}, 404)
    
    if order.status.is_completed_status:
        return JSONResponse({"error": "Замовлення закрите"}, 400)

    actor_info = f"{employee.full_name} (PWA)"
    msg = ""
    
    if courier_id == 0:
        if order.courier_id is not None:
             session.add(OrderLog(order_id=order.id, message="Кур'єра скасовано (не призначено)", actor=actor_info))
        order.courier_id = None
        msg = "Кур'єра знято"
    else:
        courier = await session.get(Employee, courier_id)
        if not courier: return JSONResponse({"error": "Кур'єра не знайдено"}, 404)
        order.courier_id = courier_id
        msg = f"Призначено: {courier.full_name}"
        
        # ЛОГ
        session.add(OrderLog(order_id=order.id, message=f"Призначено кур'єра: {courier.full_name}", actor=actor_info))
        
        # Відправляємо внутрішнє сповіщення в PWA
        await create_staff_notification(session, courier.id, f"📦 Вам призначено замовлення #{order.id} ({order.address or 'Доставка'})")
        
        # --- ДОДАНО ДЛЯ ВІДПРАВКИ В TELEGRAM ПРЯМО З PWA ---
        admin_bot = request.app.state.admin_bot
        if courier.telegram_user_id and admin_bot:
            try:
                kb_courier = InlineKeyboardBuilder()
                statuses_res = await session.execute(select(OrderStatus).where(OrderStatus.visible_to_courier == True).order_by(OrderStatus.id))
                statuses = statuses_res.scalars().all()

                # Розбиваємо кнопки по 2
                status_buttons = [
                    InlineKeyboardButton(text=s.name, callback_data=f"staff_set_status_{order.id}_{s.id}")
                    for s in statuses
                ]
                for i in range(0, len(status_buttons), 2):
                    kb_courier.row(*status_buttons[i:i+2])

                # Формуємо безпечне посилання на карту для Telegram
                if order.is_delivery and order.address:
                    encoded_address = quote_plus(order.address)
                    map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
                    kb_courier.row(InlineKeyboardButton(text="🗺️ На карті", url=map_url))

                await admin_bot.send_message(
                    courier.telegram_user_id,
                    f"🔔 Вам призначено нове замовлення!\n\n<b>Замовлення #{order.id}</b>\nАдреса: {html.escape(order.address or 'Самовивіз')}\nТелефон: {html.escape(order.phone_number or 'Не вказано')}\nСума: {order.total_price} грн.",
                    reply_markup=kb_courier.as_markup(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Не вдалося сповістити в TG кур'єра {courier.telegram_user_id} з PWA: {e}")
        # ----------------------------------------------------
    
    await session.commit()
    return JSONResponse({"success": True, "message": msg})

@router.post("/api/order/update_status")
async def update_order_status_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    data = await request.json()
    order_id = int(data.get("orderId"))
    new_status_id = int(data.get("statusId"))
    payment_method = data.get("paymentMethod")
    
    order = await session.get(Order, order_id, options=[joinedload(Order.status)])
    if not order: return JSONResponse({"error": "Не знайдено"}, 404)
    
    can_edit = False
    if employee.role.can_manage_orders: can_edit = True
    elif employee.role.can_serve_tables and order.accepted_by_waiter_id == employee.id: can_edit = True
    elif employee.role.can_be_assigned and order.courier_id == employee.id: can_edit = True
    
    if not can_edit:
         return JSONResponse({"error": "Немає прав"}, 403)

    old_status = order.status.name
    new_status = await session.get(OrderStatus, new_status_id)
    actor_info = f"{employee.full_name} (PWA)"
    
    # --- НОВА ПЕРЕВІРКА ПРАВ НА СКАСУВАННЯ ---
    if new_status.is_cancelled_status:
        # Перевіряємо, чи є у співробітника право скасовувати замовлення
        if not employee.role.can_cancel_orders:
            return JSONResponse({"error": "⛔️ У вас немає прав скасовувати замовлення! Зверніться до адміністратора."}, status_code=403)
    # -------------------------------------
    
    is_already_closed = order.status.is_completed_status or order.status.is_cancelled_status
    is_moving_to_cancelled = new_status.is_cancelled_status
    is_moving_to_active = not (new_status.is_completed_status or new_status.is_cancelled_status)

    if is_already_closed:
        if not (is_moving_to_cancelled or is_moving_to_active):
             return JSONResponse({"error": "Замовлення закрите. Зміна заборонена."}, 400)

    # Скасування боргу при переході з Виконано в Скасовано
    if order.status.is_completed_status and new_status.is_cancelled_status:
        await unregister_employee_debt(session, order)
        session.add(OrderLog(order_id=order.id, message="Скасовано борг співробітника", actor=actor_info))

    if payment_method and order.payment_method != payment_method:
        session.add(OrderLog(order_id=order.id, message=f"Змінено метод оплати: {order.payment_method} -> {payment_method}", actor=actor_info))
        order.payment_method = payment_method

    order.status_id = new_status.id
    
    # Нарахування боргу при завершенні
    if new_status.is_completed_status:
        if order.is_delivery:
             if order.courier_id:
                 order.completed_by_courier_id = order.courier_id
             elif employee.role.can_be_assigned:
                 order.completed_by_courier_id = employee.id

        await link_order_to_shift(session, order, employee.id)
        if order.payment_method == 'cash':
            debtor_id = employee.id
            if employee.role.can_manage_orders:
                if order.courier_id: debtor_id = order.courier_id
                elif order.accepted_by_waiter_id: debtor_id = order.accepted_by_waiter_id
            
            await register_employee_debt(session, order, debtor_id)

    session.add(OrderStatusHistory(order_id=order.id, status_id=new_status_id, actor_info=actor_info))
    await session.commit()
    
    await notify_all_parties_on_status_change(
        order, old_status, actor_info, 
        request.app.state.admin_bot, request.app.state.client_bot, session
    )
    
    # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
    await manager.broadcast_staff({
        "type": "order_updated",
        "order_id": order.id
    })

    return JSONResponse({"success": True})

# --- НОВИЙ API ДЛЯ СКЛАДНОГО СКАСУВАННЯ (Як в Telegram) ---
@router.post("/api/order/cancel_complex")
async def cancel_order_complex_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """
    Складне скасування: Списання (Waste) або Повернення (Return) + Штраф.
    """
    if not employee.role.can_cancel_orders:
        return JSONResponse({"error": "Немає прав на скасування"}, status_code=403)

    data = await request.json()
    order_id = int(data.get("orderId"))
    action_type = data.get("actionType") # 'return' (на склад) або 'waste' (списати)
    apply_penalty = data.get("applyPenalty", False) # Нараховувати борг по собівартості
    reason = data.get("reason", "Скасування через PWA")
    
    actor_info = f"{employee.full_name} (PWA)"

    order = await session.get(Order, order_id, options=[joinedload(Order.status)])
    if not order: return JSONResponse({"error": "Замовлення не знайдено"}, 404)

    # Знаходимо статус скасування
    cancel_status = await session.scalar(select(OrderStatus).where(OrderStatus.is_cancelled_status == True).limit(1))
    if not cancel_status: return JSONResponse({"error": "Статус скасування не налаштовано"}, 500)

    old_status_name = order.status.name

    # --- ВИПРАВЛЕННЯ: Списуємо старий борг ---
    # Якщо замовлення було "Виконано", то борг (вся сума) висить на співробітнику.
    # При скасуванні ми повинні цей борг анулювати.
    if order.status.is_completed_status:
        await unregister_employee_debt(session, order)
        session.add(OrderLog(order_id=order.id, message="Скасовано борг співробітника", actor=actor_info))
    # ------------------------------------------

    # 1. Логіка Складу
    if action_type == 'waste':
        # Якщо "Списати", ми ставимо прапор, щоб notification_manager НЕ робив reverse_deduction
        order.skip_inventory_return = True
    else:
        # Якщо "Повернути", notification_manager сам викличе reverse_deduction при зміні статусу
        order.skip_inventory_return = False

    # 2. Логіка Штрафу (Якщо Waste і вибрано)
    debt_msg = ""
    if action_type == 'waste' and apply_penalty:
        # Рахуємо собівартість
        cost_price = await calculate_order_prime_cost(session, order.id)
        if cost_price > 0:
            # На кого вішати? (Офіціант або Кур'єр)
            target_id = order.accepted_by_waiter_id or order.courier_id or employee.id
            target_emp = await session.get(Employee, target_id)
            
            if target_emp:
                target_emp.cash_balance += cost_price
                session.add(BalanceHistory(
                    employee_id=target_emp.id, 
                    amount=cost_price, 
                    new_balance=target_emp.cash_balance,
                    reason=f"Штраф (Собівартість) за скасування #{order.id}"
                ))
                debt_msg = f" (Нараховано борг {cost_price:.2f} грн співробітнику {target_emp.full_name})"

    # 3. Змінюємо статус
    order.status_id = cancel_status.id
    order.cancellation_reason = reason + debt_msg
    
    # ЛОГ СКАСУВАННЯ
    log_msg = f"Скасовано: {reason}. Тип: {'Списання' if action_type == 'waste' else 'Повернення'}.{debt_msg}"
    session.add(OrderLog(order_id=order.id, message=log_msg, actor=actor_info))
    
    session.add(OrderStatusHistory(
        order_id=order.id, 
        status_id=cancel_status.id, 
        actor_info=actor_info
    ))
    
    await session.commit()

    # 4. Сповіщення
    await notify_all_parties_on_status_change(
        order, old_status_name, actor_info, 
        request.app.state.admin_bot, request.app.state.client_bot, session
    )

    # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
    await manager.broadcast_staff({
        "type": "order_updated",
        "order_id": order.id
    })

    return JSONResponse({"success": True, "message": f"Замовлення скасовано.{debt_msg}"})

@router.post("/api/order/update_items")
async def update_order_items_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    data = await request.json()
    order_id = int(data.get("orderId"))
    items = data.get("items") 
    
    actor_info = f"{employee.full_name} (PWA)"
    
    order = await session.get(Order, order_id, options=[joinedload(Order.status), selectinload(Order.items)])
    
    if not order: return JSONResponse({"error": "Замовлення не знайдено"}, 404)
    
    if not check_edit_permissions(employee, order):
        return JSONResponse({"error": "Немає прав на редагування"}, 403)

    if order.status.is_completed_status or order.status.is_cancelled_status:
        return JSONResponse({"error": "Замовлення закрите"}, 400)
        
    if order.status.requires_kitchen_notify:
        return JSONResponse({"error": "Замовлення вже на кухні. Редагування заборонено."}, 403)
    
    if order.is_inventory_deducted:
        return JSONResponse({"error": "Склад вже списано. Редагування заборонено."}, 403)
    
    # --- ЛОГУВАННЯ РІЗНИЦІ ---
    old_items_map = {item.product_id: item.quantity for item in order.items}
    # -------------------------
    
    await session.execute(delete(OrderItem).where(OrderItem.order_id == order_id))
    
    total_price = Decimal(0)
    current_items_map = {} # Для логування
    
    if items:
        prod_ids = [int(i['id']) for i in items]
        products = (await session.execute(select(Product).where(Product.id.in_(prod_ids)))).scalars().all()
        prod_map = {p.id: p for p in products}
        
        db_modifiers = await fetch_db_modifiers(session, items)
        
        for item in items:
            pid = int(item['id'])
            qty = int(item['qty'])
            if pid in prod_map and qty > 0:
                p = prod_map[pid]
                current_items_map[pid] = {"name": p.name, "qty": qty} # Для логування
                
                final_mods = []
                mods_price = Decimal(0)
                for raw_mod in item.get('modifiers', []):
                    mid = int(raw_mod['id'])
                    if mid in db_modifiers:
                        m_db = db_modifiers[mid]
                        mods_price += m_db.price
                        final_mods.append({
                            "id": m_db.id,
                            "name": m_db.name,
                            "price": float(m_db.price),
                            "ingredient_id": m_db.ingredient_id,
                            "ingredient_qty": float(m_db.ingredient_qty),
                            "warehouse_id": m_db.warehouse_id # Зберігаємо склад модифікатора
                        })
                
                item_price = p.price + mods_price
                total_price += item_price * qty
                
                session.add(OrderItem(
                    order_id=order_id,
                    product_id=p.id,
                    product_name=p.name,
                    quantity=qty,
                    price_at_moment=item_price,
                    preparation_area=p.preparation_area,
                    modifiers=final_mods
                ))
    
    # --- ЗАПИС ЛОГУ РІЗНИЦІ ---
    log_diffs = []
    # Додано/Змінено
    for pid, info in current_items_map.items():
        old_qty = old_items_map.get(pid, 0)
        if old_qty == 0:
            log_diffs.append(f"Додано: {info['name']} x{info['qty']}")
        elif old_qty != info['qty']:
            log_diffs.append(f"Змінено к-сть: {info['name']} ({old_qty} -> {info['qty']})")
    # Видалено
    for pid, old_qty in old_items_map.items():
        if pid not in current_items_map:
             log_diffs.append(f"Видалено товар (ID: {pid})")
    
    if log_diffs:
         session.add(OrderLog(order_id=order.id, message="Зміни в товарах: " + "; ".join(log_diffs), actor=actor_info))
    # --------------------------
    
    if order.is_delivery:
        settings = await session.get(Settings, 1) or Settings()
        delivery_cost = settings.delivery_cost
        if settings.free_delivery_from is not None and total_price >= settings.free_delivery_from:
            delivery_cost = Decimal(0)
        total_price += delivery_cost

    order.kitchen_done = False
    order.bar_done = False
    order.total_price = total_price
    await session.commit()
    
    msg = f"🔄 Замовлення #{order.id} оновлено ({employee.full_name})"
    chefs = (await session.execute(
        select(Employee).join(Role).where(Role.can_receive_kitchen_orders==True, Employee.is_on_shift==True)
    )).scalars().all()
    for c in chefs:
        await create_staff_notification(session, c.id, msg)
        
    # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
    await manager.broadcast_staff({
        "type": "order_updated",
        "order_id": order.id
    })

    return JSONResponse({"success": True})

# --- НОВИЙ ENDPOINT: ОНОВЛЕННЯ ДЕТАЛЕЙ ЗАМОВЛЕННЯ ---
@router.post("/api/order/update_details")
async def update_order_details_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """
    Оновлення даних клієнта та коментаря
    """
    data = await request.json()
    order_id = int(data.get("orderId"))
    
    # Отримуємо нові дані
    name = data.get("name")
    phone = data.get("phone")
    address = data.get("address")
    delivery_time = data.get("delivery_time")
    comment = data.get("comment") # Тепер це записуємо в order.comment
    
    order = await session.get(Order, order_id)
    if not order: return JSONResponse({"error": "Замовлення не знайдено"}, 404)
    
    # Перевірка прав (аналогічно update_items)
    if not check_edit_permissions(employee, order):
        return JSONResponse({"error": "Немає прав на редагування"}, 403)

    if order.status.is_completed_status or order.status.is_cancelled_status:
        return JSONResponse({"error": "Замовлення закрите"}, 400)
    
    actor_info = f"{employee.full_name} (PWA)"
    changes = []

    # Логуємо зміни
    if order.customer_name != name:
        changes.append(f"Ім'я: {order.customer_name} -> {name}")
        order.customer_name = name
        
    if order.phone_number != phone:
        changes.append(f"Тел: {order.phone_number} -> {phone}")
        order.phone_number = phone
        
    if order.address != address:
        changes.append(f"Адреса: {order.address} -> {address}")
        order.address = address
        
    if order.delivery_time != delivery_time:
        changes.append(f"Час: {order.delivery_time} -> {delivery_time}")
        order.delivery_time = delivery_time
        
    if order.comment != comment:
        changes.append(f"Коментар: {order.comment or ''} -> {comment}")
        order.comment = comment

    if changes:
        session.add(OrderLog(
            order_id=order.id, 
            message="Змінено деталі: " + "; ".join(changes), 
            actor=actor_info
        ))
        await session.commit()
        
        # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
        await manager.broadcast_staff({
            "type": "order_updated",
            "order_id": order.id
        })
        
        return JSONResponse({"success": True, "message": "Дані оновлено"})
    
    return JSONResponse({"success": True, "message": "Змін немає"})
# ----------------------------------------------------

@router.post("/api/action")
async def handle_action_api(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    try:
        data = await request.json()
        action = data.get("action")
        order_id = int(data.get("orderId"))
        actor_info = f"{employee.full_name} (PWA)"
        
        if action == "toggle_item":
            item_id = int(data.get("extra"))
            item = await session.get(OrderItem, item_id)
            if item:
                # Поштучна готовність
                item.is_ready = not item.is_ready
                await session.commit()
                
                # Перевірка готовності всього замовлення
                await check_and_update_order_readiness(session, order_id, request.app.state.admin_bot)
                
                # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
                await manager.broadcast_staff({
                    "type": "item_ready",
                    "order_id": order_id
                })
                
                return JSONResponse({"success": True})
        
        elif action == "accept_order":
            order = await session.get(Order, order_id)
            if order and not order.accepted_by_waiter_id:
                order.accepted_by_waiter_id = employee.id
                
                # ЛОГ ПРИЙНЯТТЯ
                session.add(OrderLog(order_id=order.id, message="Офіціант прийняв замовлення", actor=actor_info))
                
                proc_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "В обробці").limit(1))
                if proc_status: order.status_id = proc_status.id
                await session.commit()
                
                # --- ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
                await manager.broadcast_staff({
                    "type": "order_updated",
                    "order_id": order.id
                })
                
                return JSONResponse({"success": True})

        return JSONResponse({"success": False, "error": "Unknown action"})
    except Exception as e:
        logger.error(f"Action Error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/menu/full")
async def get_full_menu(session: AsyncSession = Depends(get_db_session)):
    """
    Повертає повне меню ресторану для PWA.
    """
    cats = (await session.execute(select(Category).where(Category.show_in_restaurant==True).order_by(Category.sort_order))).scalars().all()
    
    menu = []
    for c in cats:
        prods = (await session.execute(
            select(Product)
            .where(Product.category_id==c.id, Product.is_active==True)
            .options(selectinload(Product.modifiers))
        )).scalars().all()
        
        prod_list = []
        for p in prods:
            p_mods = []
            if p.modifiers:
                for m in p.modifiers:
                    price_val = m.price if m.price is not None else 0
                    p_mods.append({
                        "id": m.id, 
                        "name": m.name, 
                        "price": float(price_val)
                    })
            
            prod_list.append({
                "id": p.id, 
                "name": p.name, 
                "price": float(p.price), 
                "preparation_area": p.preparation_area,
                "production_warehouse_id": p.production_warehouse_id, # Важливо для фільтрації
                "modifiers": p_mods 
            })
            
        menu.append({
            "id": c.id, 
            "name": c.name, 
            "products": prod_list
        })
        
    return JSONResponse({"menu": menu})

@router.post("/api/order/create")
async def create_waiter_order(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    if not employee.role.can_serve_tables:
        return JSONResponse({"error": "Forbidden"}, 403)

    try:
        data = await request.json()
        table_id = int(data.get("tableId"))
        cart = data.get("cart") 
        
        table = await session.get(Table, table_id)
        if not table or not cart: return JSONResponse({"error": "Invalid data"}, status_code=400)
        
        total = Decimal(0)
        items_obj = []
        log_items = [] # Для логу
        
        prod_ids = [int(item['id']) for item in cart]
        products_res = await session.execute(select(Product).where(Product.id.in_(prod_ids)))
        products_map = {p.id: p for p in products_res.scalars().all()}
        
        # --- Завантажуємо модифікатори для отримання warehouse_id ---
        all_mod_ids = set()
        for item in cart:
            for raw_mod in item.get('modifiers', []):
                all_mod_ids.add(int(raw_mod['id']))
        
        db_modifiers = {}
        if all_mod_ids:
            res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
            for m in res.scalars().all():
                db_modifiers[m.id] = m
        # ---------------------------------------------------------------
        
        for item in cart:
            pid = int(item['id'])
            qty = int(item['qty'])
            
            if pid in products_map and qty > 0:
                prod = products_map[pid]
                log_items.append(f"{prod.name} x{qty}") # Логуємо
                
                final_mods = []
                mods_price = Decimal(0)
                for raw_mod in item.get('modifiers', []):
                    mid = int(raw_mod['id'])
                    if mid in db_modifiers:
                        m_db = db_modifiers[mid]
                        mods_price += m_db.price
                        
                        # Зберігаємо всі дані для списання, включаючи warehouse_id
                        final_mods.append({
                            "id": m_db.id,
                            "name": m_db.name,
                            "price": float(m_db.price),
                            "ingredient_id": m_db.ingredient_id,
                            "ingredient_qty": float(m_db.ingredient_qty),
                            "warehouse_id": m_db.warehouse_id # <--- ВАЖЛИВО ДЛЯ СПИСАННЯ
                        })
                
                item_price = prod.price + mods_price
                total += item_price * qty
                
                items_obj.append(OrderItem(
                    product_id=prod.id, 
                    product_name=prod.name, 
                    quantity=qty, 
                    price_at_moment=item_price,
                    preparation_area=prod.preparation_area,
                    modifiers=final_mods # JSON з warehouse_id
                ))
        
        new_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "Новий").limit(1))
        status_id = new_status.id if new_status else 1
        
        order = Order(
            table_id=table_id, 
            customer_name=f"Стіл: {table.name}", 
            phone_number=f"table_{table_id}",
            total_price=total, 
            order_type="in_house", 
            is_delivery=False, 
            delivery_time="In House",
            accepted_by_waiter_id=employee.id, 
            status_id=status_id, 
            items=items_obj
        )
        session.add(order)
        await session.flush()

        for item_data in items_obj:
            item_data.order_id = order.id
            session.add(item_data)
        
        # ЛОГ СТВОРЕННЯ
        actor_info = f"{employee.full_name} (PWA)"
        session.add(OrderLog(order_id=order.id, message=f"Створено замовлення (Офіціант). Склад: {', '.join(log_items)}", actor=actor_info))

        await session.commit()
        
        await session.refresh(order, ['status'])
        
        session.add(OrderStatusHistory(order_id=order.id, status_id=status_id, actor_info=actor_info))
        await session.commit()
        
        await notify_new_order_to_staff(request.app.state.admin_bot, order, session)
        
        # --- МИТТЄВЕ ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
        await manager.broadcast_staff({
            "type": "new_order",
            "message": f"Нове замовлення #{order.id} (Стіл: {table.name})"
        })
        
        return JSONResponse({"success": True, "orderId": order.id})
    except Exception as e:
        logger.error(f"Order create error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/print_recipe/{order_id}")
async def print_recipe(order_id: int, session: AsyncSession = Depends(get_db_session)):
    """Генерація HTML чека/бігунка для кухаря"""
    from inventory_service import generate_cook_ticket 
    
    try:
        html_content = await generate_cook_ticket(session, order_id)
        return HTMLResponse(html_content)
    except Exception as e:
        logger.error(f"Error generating receipt: {e}")
        return HTMLResponse(f"Помилка друку: {e}", status_code=500)

# --- НОВІ API ENDPOINTS ДЛЯ КАСИРА ---

@router.post("/api/cashier/action")
async def cashier_api_action(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    if not employee.role.can_manage_orders:
        return JSONResponse({"error": "Forbidden"}, 403)

    data = await request.json()
    action = data.get("action")
    
    try:
        if action == "open_shift":
            start_cash = Decimal(str(data.get("start_cash", 0)))
            await open_new_shift(session, employee.id, start_cash)
            return JSONResponse({"success": True, "message": "Зміну відкрито!"})

        elif action == "close_shift":
            shift = await get_any_open_shift(session)
            if not shift: return JSONResponse({"error": "Зміна не знайдена"}, 400)
            
            # Для простоти закриваємо по теоретичному залишку, або можна запитати факт
            stats = await get_shift_statistics(session, shift.id)
            actual_cash = Decimal(str(data.get("actual_cash", stats['theoretical_cash'])))
            
            await close_active_shift(session, shift.id, actual_cash)
            return JSONResponse({"success": True, "message": "Зміну закрито!"})

        elif action == "accept_debt":
            target_emp_id = int(data.get("target_id"))
            shift = await get_any_open_shift(session)
            if not shift: return JSONResponse({"error": "Відкрийте зміну!"}, 400)
            
            # Знаходимо замовлення з боргом
            # --- ВИПРАВЛЕННЯ: Фільтр скасованих ---
            orders_res = await session.execute(
                select(Order.id).where(
                    Order.payment_method == 'cash',
                    Order.is_cash_turned_in == False,
                    Order.status.has(is_cancelled_status=False), # <--- Фільтр
                    or_(
                        Order.courier_id == target_emp_id,
                        Order.accepted_by_waiter_id == target_emp_id,
                        Order.completed_by_courier_id == target_emp_id
                    )
                )
            )
            order_ids = orders_res.scalars().all()
            
            if not order_ids:
                return JSONResponse({"error": "Немає замовлень для здачі"}, 400)
                
            amount = await process_handover(session, shift.id, target_emp_id, order_ids)
            return JSONResponse({"success": True, "message": f"Прийнято {amount} грн"})

        elif action == "transaction":
            shift = await get_any_open_shift(session)
            if not shift: return JSONResponse({"error": "Відкрийте зміну!"}, 400)
            
            t_type = data.get("type") # 'in' or 'out'
            amount = Decimal(str(data.get("amount")))
            comment = data.get("comment")
            
            await add_shift_transaction(session, shift.id, amount, t_type, comment)
            return JSONResponse({"success": True, "message": "Транзакцію проведено"})

    except Exception as e:
        logger.error(f"Cashier API Error: {e}")
        return JSONResponse({"error": str(e)}, 500)

@router.get("/api/cashier/suppliers")
async def get_suppliers_and_warehouses(
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """Отримання даних для форми приходу."""
    suppliers = (await session.execute(select(Supplier).order_by(Supplier.name))).scalars().all()
    warehouses = (await session.execute(select(Warehouse).order_by(Warehouse.name))).scalars().all()
    
    # Повертаємо також всі інгредієнти для пошуку
    from inventory_models import Ingredient, Unit
    ingredients = (await session.execute(select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name))).scalars().all()
    
    return JSONResponse({
        "suppliers": [{"id": s.id, "name": s.name} for s in suppliers],
        "warehouses": [{"id": w.id, "name": w.name} for w in warehouses],
        "ingredients": [{"id": i.id, "name": i.name, "unit": i.unit.name} for i in ingredients]
    })

@router.post("/api/cashier/supply")
async def create_supply_pwa(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    if not employee.role.can_manage_orders:
        return JSONResponse({"error": "Forbidden"}, 403)
        
    data = await request.json()
    try:
        items = data.get("items", []) # List of {ingredient_id, qty, price}
        supplier_id = int(data.get("supplier_id"))
        warehouse_id = int(data.get("warehouse_id"))
        comment = data.get("comment", "PWA Supply")
        
        # Використовуємо універсальну функцію
        await process_movement(
            session, 'supply', items,
            target_wh_id=warehouse_id,
            supplier_id=supplier_id,
            comment=f"{comment} (Created by {employee.full_name})"
        )
        return JSONResponse({"success": True, "message": "Накладна створена та проведена!"})
    except Exception as e:
        logger.error(f"Supply PWA Error: {e}")
        return JSONResponse({"error": str(e)}, 500)

@router.post("/api/cashier/pay_doc")
async def pay_supply_doc_pwa(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    """Оплата накладної з каси через PWA."""
    if not employee.role.can_manage_orders:
        return JSONResponse({"error": "Forbidden"}, 403)
        
    data = await request.json()
    doc_id = int(data.get("doc_id"))
    amount = Decimal(str(data.get("amount", 0)))
    
    if amount <= 0: return JSONResponse({"error": "Невірна сума"}, 400)
    
    doc = await session.get(InventoryDoc, doc_id, options=[joinedload(InventoryDoc.supplier)])
    if not doc: return JSONResponse({"error": "Накладна не знайдена"}, 404)
    
    shift = await get_any_open_shift(session)
    if not shift: return JSONResponse({"error": "Немає відкритої зміни"}, 400)
    
    try:
        comment = f"Оплата накладної #{doc.id}"
        if doc.supplier: comment += f" ({doc.supplier.name})"
        
        await add_shift_transaction(session, shift.id, amount, "out", comment)
        
        doc.paid_amount = float(doc.paid_amount) + float(amount)
        await session.commit()
        return JSONResponse({"success": True, "message": "Оплату проведено!"})
    except Exception as e:
        logger.error(f"Pay Doc API Error: {e}")
        return JSONResponse({"error": str(e)}, 500)

@router.post("/api/order/create_delivery")
async def create_staff_delivery_order(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    employee: Employee = Depends(get_current_staff)
):
    if not employee.role.can_manage_orders:
        return JSONResponse({"error": "Forbidden"}, 403)

    try:
        data = await request.json()
        cart = data.get("cart")
        customer_name = data.get("name")
        phone = data.get("phone")
        address = data.get("address")
        comment = data.get("comment", "")
        # Отримуємо час доставки з запиту, або ставимо "Якнайшвидше"
        delivery_time = data.get("delivery_time", "Якнайшвидше")
        
        if not cart: return JSONResponse({"error": "Кошик порожній"}, status_code=400)
        
        total = Decimal(0)
        items_obj = []
        log_items = [] # Для логу
        
        prod_ids = [int(item['id']) for item in cart]
        products_res = await session.execute(select(Product).where(Product.id.in_(prod_ids)))
        products_map = {p.id: p for p in products_res.scalars().all()}
        
        # Завантаження модифікаторів
        all_mod_ids = set()
        for item in cart:
            for raw_mod in item.get('modifiers', []):
                all_mod_ids.add(int(raw_mod['id']))
        
        db_modifiers = {}
        if all_mod_ids:
            res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
            for m in res.scalars().all():
                db_modifiers[m.id] = m
        
        for item in cart:
            pid = int(item['id'])
            qty = int(item['qty'])
            
            if pid in products_map and qty > 0:
                prod = products_map[pid]
                log_items.append(f"{prod.name} x{qty}") # Логуємо
                
                final_mods = []
                mods_price = Decimal(0)
                for raw_mod in item.get('modifiers', []):
                    mid = int(raw_mod['id'])
                    if mid in db_modifiers:
                        m_db = db_modifiers[mid]
                        mods_price += m_db.price
                        final_mods.append({
                            "id": m_db.id,
                            "name": m_db.name,
                            "price": float(m_db.price),
                            "ingredient_id": m_db.ingredient_id,
                            "ingredient_qty": float(m_db.ingredient_qty),
                            "warehouse_id": m_db.warehouse_id
                        })
                
                item_price = prod.price + mods_price
                total += item_price * qty
                
                items_obj.append(OrderItem(
                    product_id=prod.id, 
                    product_name=prod.name, 
                    quantity=qty, 
                    price_at_moment=item_price,
                    preparation_area=prod.preparation_area,
                    modifiers=final_mods
                ))
        
        # Додаємо вартість доставки якщо є в налаштуваннях
        settings = await session.get(Settings, 1) or Settings()
        if settings.delivery_cost > 0:
             if settings.free_delivery_from is None or total < settings.free_delivery_from:
                 total += settings.delivery_cost

        new_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "Новий").limit(1))
        status_id = new_status.id if new_status else 1
        
        order = Order(
            customer_name=customer_name, 
            phone_number=phone,
            address=address,
            total_price=total, 
            order_type="delivery", 
            is_delivery=True, 
            delivery_time=delivery_time, # Зберігаємо переданий час
            status_id=status_id, 
            items=items_obj,
            comment=comment # <--- ЗМІНЕНО: Тепер пишемо в comment
        )
        session.add(order)
        await session.flush()

        for item_data in items_obj:
            item_data.order_id = order.id
            session.add(item_data)
        
        # ЛОГ СТВОРЕННЯ
        actor_info = f"{employee.full_name} (PWA)"
        session.add(OrderLog(order_id=order.id, message=f"Створено доставку (Адмін PWA). Склад: {', '.join(log_items)}", actor=actor_info))

        await session.commit()
        await session.refresh(order, ['status'])
        
        session.add(OrderStatusHistory(order_id=order.id, status_id=status_id, actor_info=actor_info))
        await session.commit()
        
        # Сповіщаємо систему
        await notify_new_order_to_staff(request.app.state.admin_bot, order, session)
        
        # --- МИТТЄВЕ ОНОВЛЕННЯ ДЛЯ ПЕРСОНАЛУ ЧЕРЕЗ WEBSOCKET ---
        await manager.broadcast_staff({
            "type": "new_order",
            "message": f"Нова доставка #{order.id}"
        })
        
        return JSONResponse({"success": True, "orderId": order.id})
    except Exception as e:
        logger.error(f"Create Delivery Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)