# in_house_menu.py

import html as html_module
import json
import logging
import os
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload, selectinload
from aiogram import Bot, html as aiogram_html
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from urllib.parse import quote_plus as url_quote_plus

# Added MenuItem to imports
from models import Table, Product, Category, Order, Settings, Employee, OrderStatusHistory, OrderStatus, OrderItem, MenuItem
from dependencies import get_db_session
from templates import IN_HOUSE_MENU_HTML_TEMPLATE
from notification_manager import distribute_order_to_production, create_staff_notification

# ДОДАНО: Імпорт менеджера WebSocket
from websocket_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/menu/table/{access_token}", response_class=HTMLResponse)
async def get_in_house_menu(access_token: str, request: Request, session: AsyncSession = Depends(get_db_session)):
    """Відображає сторінку меню для конкретного столика з історією замовлень."""

    table_res = await session.execute(
        select(Table).where(Table.access_token == access_token)
    )
    table = table_res.scalar_one_or_none()

    if not table:
        raise HTTPException(status_code=404, detail="Столик не знайдено.")

    settings = await session.get(Settings, 1) or Settings()
    logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" class="header-logo">' if settings and settings.logo_url else ''

    # Отримуємо меню, яке показується в ресторані
    categories_res = await session.execute(
        select(Category)
        .where(Category.show_in_restaurant == True)
        .order_by(Category.sort_order, Category.name)
    )
    
    products_res = await session.execute(
        select(Product)
        .options(selectinload(Product.modifiers))
        .join(Category)
        .where(Product.is_active == True, Category.show_in_restaurant == True)
    )

    categories = [{"id": c.id, "name": c.name} for c in categories_res.scalars().all()]
    
    products = []
    for p in products_res.scalars().all():
        mods_list = []
        if p.modifiers:
            for m in p.modifiers:
                price_val = m.price if m.price is not None else 0
                mods_list.append({
                    "id": m.id, 
                    "name": m.name, 
                    "price": float(price_val)
                })

        products.append({
            "id": p.id, 
            "name": p.name, 
            "description": p.description, 
            "price": float(p.price), 
            "promotional_price": float(p.promotional_price) if p.promotional_price else None, # НОВЕ ПОЛЕ
            "image_url": p.image_url, 
            "category_id": p.category_id,
            "modifiers": mods_list
        })

    # Отримуємо історію неоплачених замовлень для цього столика
    final_statuses_res = await session.execute(
        select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True))
    )
    final_status_ids = final_statuses_res.scalars().all()

    active_orders_res = await session.execute(
        select(Order)
        .where(Order.table_id == table.id, Order.status_id.not_in(final_status_ids))
        .options(joinedload(Order.status), selectinload(Order.items))
        .order_by(Order.id.desc())
    )
    active_orders = active_orders_res.scalars().all()

    history_list = []
    grand_total = Decimal('0.00')

    for o in active_orders:
        grand_total += o.total_price
        status_name = o.status.name if o.status else "Обробяється"
        
        product_strings = []
        for item in o.items:
            mods_str = ""
            if item.modifiers:
                mod_names = [m.get('name', '') for m in item.modifiers]
                if mod_names:
                    mods_str = f" (+ {', '.join(mod_names)})"
            product_strings.append(f"{item.product_name}{mods_str} x {item.quantity}")
            
        products_str = ", ".join(product_strings)
        
        history_list.append({
            "id": o.id,
            "products": products_str,
            "total_price": float(o.total_price), 
            "status": status_name,
            "time": o.created_at.strftime('%H:%M')
        })

    menu_data = json.dumps({"categories": categories, "products": products})
    history_data = json.dumps(history_list) 

    site_title = settings.site_title or "Назва"
    site_header_text = settings.site_header_text or ""  # Отримуємо заголовок шапки
    
    primary_color_val = settings.primary_color or "#5a5a5a"
    secondary_color_val = settings.secondary_color or "#eeeeee"
    background_color_val = settings.background_color or "#f4f4f4"
    text_color_val = settings.text_color or "#333333"
    footer_bg_color_val = settings.footer_bg_color or "#333333"
    footer_text_color_val = settings.footer_text_color or "#ffffff"

    category_nav_bg_color = settings.category_nav_bg_color or "#ffffff"
    category_nav_text_color = settings.category_nav_text_color or "#333333"
    header_image_url = settings.header_image_url or "" 
    
    wifi_ssid = html_module.escape(settings.wifi_ssid or "Не налаштовано")
    wifi_password = html_module.escape(settings.wifi_password or "")

    font_family_sans_val = settings.font_family_sans or "Golos Text"
    font_family_serif_val = settings.font_family_serif or "Playfair Display"

    social_links = []
    if settings.instagram_url:
        social_links.append(f'<a href="{html_module.escape(settings.instagram_url)}" target="_blank"><i class="fa-brands fa-instagram"></i></a>')
    if settings.facebook_url:
        social_links.append(f'<a href="{html_module.escape(settings.facebook_url)}" target="_blank"><i class="fa-brands fa-facebook"></i></a>')
    
    social_links_html = "".join(social_links)

    menu_items_res = await session.execute(
        select(MenuItem)
        .where(MenuItem.show_in_qr == True)
        .order_by(MenuItem.sort_order)
    )
    menu_items = menu_items_res.scalars().all()
    
    menu_links_html = "".join(
        [f'<a href="#" class="footer-link menu-popup-trigger" data-item-id="{item.id}"><i class="fa-solid fa-file-lines"></i> <span>{html_module.escape(item.title)}</span></a>' for item in menu_items]
    )

    return HTMLResponse(content=IN_HOUSE_MENU_HTML_TEMPLATE.format(
        table_name=html_module.escape(table.name),
        table_id=table.id,
        logo_html=logo_html,
        menu_data=menu_data,
        history_data=history_data,   
        grand_total=float(grand_total),     
        
        site_title=html_module.escape(site_title),
        site_header_text=html_module.escape(site_header_text), # Передаємо заголовок шапки
        
        seo_description=html_module.escape(settings.seo_description or ""),
        seo_keywords=html_module.escape(settings.seo_keywords or ""),
        
        primary_color_val=primary_color_val,
        secondary_color_val=secondary_color_val,
        background_color_val=background_color_val,
        text_color_val=text_color_val,
        footer_bg_color_val=footer_bg_color_val,
        footer_text_color_val=footer_text_color_val,
        
        category_nav_bg_color=category_nav_bg_color,
        category_nav_text_color=category_nav_text_color,
        header_image_url=header_image_url,
        wifi_ssid=wifi_ssid,
        wifi_password=wifi_password,
        
        font_family_sans_val=font_family_sans_val,
        font_family_serif_val=font_family_serif_val,
        font_family_sans_encoded=url_quote_plus(font_family_sans_val),
        font_family_serif_encoded=url_quote_plus(font_family_serif_val),

        footer_address=html_module.escape(settings.footer_address or "Адреса не вказана"),
        footer_phone=html_module.escape(settings.footer_phone or ""),
        working_hours=html_module.escape(settings.working_hours or ""),
        social_links_html=social_links_html,
        menu_links_html=menu_links_html
    ))

@router.get("/api/menu/table/{table_id}/updates", response_class=JSONResponse)
async def get_table_updates(table_id: int, session: AsyncSession = Depends(get_db_session)):
    """Повертає актуальний статус замовлень для оновлення фронтенду."""
    
    final_statuses_res = await session.execute(
        select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True))
    )
    final_status_ids = final_statuses_res.scalars().all()

    active_orders_res = await session.execute(
        select(Order)
        .where(Order.table_id == table_id, Order.status_id.not_in(final_status_ids))
        .options(joinedload(Order.status), selectinload(Order.items))
        .order_by(Order.id.desc())
    )
    active_orders = active_orders_res.scalars().all()

    history_list = []
    grand_total = Decimal('0.00')

    for o in active_orders:
        grand_total += o.total_price
        status_name = o.status.name if o.status else "Обробяється"
        
        product_strings = []
        for item in o.items:
            mods_str = ""
            if item.modifiers:
                mod_names = [m.get('name', '') for m in item.modifiers]
                if mod_names:
                    mods_str = f" (+ {', '.join(mod_names)})"
            product_strings.append(f"{item.product_name}{mods_str} x {item.quantity}")
            
        products_str = ", ".join(product_strings)
        
        history_list.append({
            "id": o.id,
            "products": products_str,
            "total_price": float(o.total_price),
            "status": status_name,
            "time": o.created_at.strftime('%H:%M')
        })

    return {
        "history_data": history_list,
        "grand_total": float(grand_total)
    }

@router.post("/api/menu/table/{table_id}/call_waiter", response_class=JSONResponse)
async def call_waiter(
    table_id: int, 
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Обробляє виклик офіціанта зі столика."""
    table = await session.get(Table, table_id, options=[selectinload(Table.assigned_waiters)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    waiters = table.assigned_waiters
    message_text = f"❗️ <b>Виклик зі столика: {html_module.escape(table.name)}</b>"
    pwa_msg = f"🔔 Вас викликають до столика: {table.name}"
    
    # 1. PWA Notification (DB)
    for w in waiters:
        if w.is_on_shift:
            await create_staff_notification(session, w.id, pwa_msg)

    # 2. WebSocket Broadcast (Миттєве сповіщення)
    await manager.broadcast_staff({
        "type": "new_order", # Використовуємо 'new_order' для відображення Toast
        "message": f"🔔 СТІЛ {table.name}: Виклик офіціанта!"
    })

    # 3. Telegram Bot
    admin_chat_id_str = os.environ.get('ADMIN_CHAT_ID')
    admin_bot = request.app.state.admin_bot
    
    if not admin_bot:
        return JSONResponse(content={"message": "Система сповіщень тимчасово недоступна."})

    target_chat_ids = set()
    for w in waiters:
        if w.telegram_user_id and w.is_on_shift:
            target_chat_ids.add(w.telegram_user_id)

    if not target_chat_ids:
        if admin_chat_id_str:
            try:
                target_chat_ids.add(int(admin_chat_id_str))
                message_text += "\n<i>Офіціанта не призначено або він не на зміні.</i>"
            except ValueError: pass

    if target_chat_ids:
        for chat_id in target_chat_ids:
            try:
                await admin_bot.send_message(chat_id, message_text)
            except Exception as e:
                logger.error(f"Не вдалося надіслати виклик офіціанта в чат {chat_id}: {e}")
        return JSONResponse(content={"message": "Офіціанта сповіщено. Будь ласка, зачекайте."})
    else:
        return JSONResponse(content={"message": "Офіціанта сповіщено."})

@router.post("/api/menu/table/{table_id}/request_bill", response_class=JSONResponse)
async def request_bill(
    table_id: int, 
    request: Request,
    method: str = "cash", 
    session: AsyncSession = Depends(get_db_session)
):
    """Обробляє запит на рахунок зі столика."""
    table = await session.get(Table, table_id, options=[selectinload(Table.assigned_waiters)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")

    final_statuses_res = await session.execute(
        select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True))
    )
    final_status_ids = final_statuses_res.scalars().all()

    active_orders_res = await session.execute(
        select(Order).where(Order.table_id == table.id, Order.status_id.not_in(final_status_ids))
    )
    active_orders = active_orders_res.scalars().all()
    total_bill = sum((o.total_price for o in active_orders), start=Decimal('0.00'))

    waiters = table.assigned_waiters
    method_text = "💳 Картка" if method == 'card' else "💵 Готівка"
    
    message_text = (f"💰 <b>Запит на розрахунок ({method_text})</b>\n"
                    f"Столик: {html_module.escape(table.name)}\n"
                    f"Сума до сплати: <b>{total_bill} грн</b>")

    pwa_msg = f"💰 Просять рахунок ({method_text}): Стіл {table.name}. Сума: {total_bill} грн"
    
    # 1. PWA Notification
    for w in waiters:
        if w.is_on_shift:
            await create_staff_notification(session, w.id, pwa_msg)

    # 2. WebSocket Broadcast
    await manager.broadcast_staff({
        "type": "new_order", # Використовуємо 'new_order' для Toast
        "message": f"💰 СТІЛ {table.name}: Рахунок ({method_text})"
    })

    # 3. Telegram Bot
    admin_chat_id_str = os.environ.get('ADMIN_CHAT_ID')
    admin_bot = request.app.state.admin_bot
    
    if not admin_bot:
         return JSONResponse(content={"message": "Система сповіщень недоступна."})

    target_chat_ids = set()
    for w in waiters:
        if w.telegram_user_id and w.is_on_shift:
            target_chat_ids.add(w.telegram_user_id)

    if not target_chat_ids:
        if admin_chat_id_str:
            try:
                target_chat_ids.add(int(admin_chat_id_str))
                message_text += "\n<i>Офіціанта не призначено або він не на зміні.</i>"
            except ValueError: pass

    if target_chat_ids:
        for chat_id in target_chat_ids:
            try:
                await admin_bot.send_message(chat_id, message_text)
            except Exception: pass
        return JSONResponse(content={"message": "Запит надіслано. Офіціант незабаром підійде з рахунком."})
    else:
        return JSONResponse(content={"message": "Запит надіслано."})

@router.post("/api/menu/table/{table_id}/place_order", response_class=JSONResponse)
async def place_in_house_order(
    table_id: int, 
    request: Request,
    items: list = Body(...), 
    session: AsyncSession = Depends(get_db_session)
):
    """Обробляє нове замовлення зі столика (QR-меню)."""
    table = await session.get(Table, table_id, options=[selectinload(Table.assigned_waiters)])
    if not table: raise HTTPException(status_code=404, detail="Столик не знайдено.")
    if not items: raise HTTPException(status_code=400, detail="Замовлення порожнє.")

    try:
        product_ids = [int(item.get('id')) for item in items if item.get('id') is not None]
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Невірний формат ID товару.")

    # Завантажуємо продукти для отримання актуальних цін
    products_res = await session.execute(select(Product).where(Product.id.in_(product_ids)))
    db_products = {str(p.id): p for p in products_res.scalars().all()}

    total_price = Decimal('0.00')
    new_order_items = []
    products_str_for_msg = []

    for item in items:
        pid = str(item.get('id'))
        qty = int(item.get('quantity', 1))
        if pid in db_products and qty > 0:
            product = db_products[pid]
            
            # --- Обробка модифікаторів ---
            modifiers_data = item.get('modifiers', [])
            mods_price = Decimal(0)
            if modifiers_data:
                for m in modifiers_data:
                    price_val = m.get('price', 0)
                    if price_val is None: price_val = 0
                    mods_price += Decimal(str(price_val))
            
            # --- НОВЕ: Акційна ціна ---
            actual_price = product.promotional_price if product.promotional_price and product.promotional_price > 0 else product.price
            item_price = actual_price + mods_price
            # --------------------------
            
            total_price += item_price * qty
            
            mod_names = [m.get('name') for m in modifiers_data]
            mod_str = f" (+ {', '.join(mod_names)})" if mod_names else ""
            
            products_str_for_msg.append(f"{product.name}{mod_str} x {qty}")
            
            new_order_items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                price_at_moment=item_price,
                preparation_area=product.preparation_area,
                modifiers=modifiers_data # Зберігаємо JSON
            ))

    if not new_order_items:
        raise HTTPException(status_code=400, detail="Невалідні товари.")

    new_status = await session.get(OrderStatus, 1)
    if not new_status:
        new_status = OrderStatus(id=1, name="Новий", requires_kitchen_notify=True)

    order = Order(
        customer_name=f"Стіл: {table.name}", phone_number=f"table_{table.id}",
        address=None, 
        total_price=total_price,
        is_delivery=False, delivery_time="In House", order_type="in_house",
        table_id=table.id, status_id=new_status.id,
        items=new_order_items
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    await session.refresh(order, ['status'])

    # --- PWA NOTIFICATION ---
    pwa_msg = f"📝 Нове замовлення #{order.id} (Стіл: {table.name}). Сума: {total_price} грн"
    for w in table.assigned_waiters:
        if w.is_on_shift:
            await create_staff_notification(session, w.id, pwa_msg)

    history_entry = OrderStatusHistory(
        order_id=order.id, status_id=order.status_id,
        actor_info=f"Гість за столиком {table.name}"
    )
    session.add(history_entry)
    await session.commit()

    # --- WEBSOCKET BROADCAST (Миттєве сповіщення персоналу) ---
    await manager.broadcast_staff({
        "type": "new_order",
        "order_id": order.id,
        "message": f"📝 Замовлення #{order.id} (Стіл: {table.name})"
    })

    # --- Telegram сповіщення ---
    products_display = "\n- ".join(products_str_for_msg)
    order_details_text = (f"📝 <b>Нове замовлення зі столика: {aiogram_html.bold(table.name)} (ID: #{order.id})</b>\n\n"
                          f"<b>Склад:</b>\n- {aiogram_html.quote(products_display)}\n\n"
                          f"<b>Сума:</b> {total_price} грн")

    admin_bot = request.app.state.admin_bot
    
    if not admin_bot:
        return JSONResponse(content={"message": "Замовлення прийнято! Очікуйте.", "order_id": order.id})

    kb_waiter = InlineKeyboardBuilder()
    kb_waiter.row(InlineKeyboardButton(text="✅ Прийняти замовлення", callback_data=f"waiter_accept_order_{order.id}"))

    kb_admin = InlineKeyboardBuilder()
    kb_admin.row(InlineKeyboardButton(text="⚙️ Керувати (Адмін)", callback_data=f"waiter_manage_order_{order.id}"))

    waiters = table.assigned_waiters
    admin_chat_id_str = os.environ.get('ADMIN_CHAT_ID')
    admin_chat_id = None
    if admin_chat_id_str:
        try: admin_chat_id = int(admin_chat_id_str)
        except ValueError: pass

    waiter_chat_ids = set()
    for w in waiters:
        if w.telegram_user_id and w.is_on_shift:
            waiter_chat_ids.add(w.telegram_user_id)

    if waiter_chat_ids:
        for chat_id in waiter_chat_ids:
            try:
                await admin_bot.send_message(chat_id, order_details_text, reply_markup=kb_waiter.as_markup())
            except Exception as e:
                logger.error(f"Не вдалося надіслати нове замовлення офіціанту {chat_id}: {e}")

        if admin_chat_id and admin_chat_id not in waiter_chat_ids:
            try:
                await admin_bot.send_message(admin_chat_id, "✅ " + order_details_text, reply_markup=kb_admin.as_markup())
            except Exception: pass
    else:
        if admin_chat_id:
            await admin_bot.send_message(
                admin_chat_id,
                f"❗️ <b>Замовлення з вільного столика {aiogram_html.bold(table.name)} (ID: #{order.id})!</b>\n\n" + order_details_text,
                reply_markup=kb_admin.as_markup()
            )

    if order.status.requires_kitchen_notify:
        try:
            await distribute_order_to_production(admin_bot, order, session)
        except Exception as e:
            logger.error(f"Помилка при розподілі замовлення #{order.id}: {e}")
        
    return JSONResponse(content={"message": "Замовлення прийнято! Офіціант незабаром його підтвердить.", "order_id": order.id})