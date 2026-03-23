# admin_employees.py

import html
import re
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from models import Employee, Role, Order, Settings, CashShift, OrderStatus
# Імпортуємо Warehouse для вибору цеху
from inventory_models import Warehouse
from templates import ADMIN_HTML_TEMPLATE
from dependencies import get_db_session, check_credentials
from auth_utils import get_password_hash

router = APIRouter()
logger = logging.getLogger(__name__)

# --- СПІВРОБІТНИКИ ---

@router.get("/admin/employees", response_class=HTMLResponse)
async def admin_employees(
    error: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    """Відображає список співробітників."""
    settings = await session.get(Settings, 1) or Settings()
    
    # Обробка помилок видалення
    error_msg = ""
    if error == "assigned":
        error_msg = "<div class='card' style='background:#fee2e2; color:#991b1b; margin-bottom:20px; border:1px solid #fecaca;'>⚠️ Неможливо видалити: співробітник має активні замовлення або відкриту зміну.</div>"
    elif error == "integrity":
        error_msg = "<div class='card' style='background:#fee2e2; color:#991b1b; margin-bottom:20px; border:1px solid #fecaca;'>⚠️ Неможливо видалити: співробітник пов'язаний з архівними даними (замовленнями).</div>"
    elif error == "has_debt":
        error_msg = "<div class='card' style='background:#fee2e2; color:#991b1b; margin-bottom:20px; border:1px solid #fecaca;'>⚠️ Неможливо видалити: у співробітника є борг (готівка на руках). Спочатку прийміть кошти в розділі Каса.</div>"

    # Завантажуємо співробітників з ролями
    employees_res = await session.execute(
        select(Employee)
        .options(joinedload(Employee.role))
        .order_by(Employee.id.desc())
    )
    employees = employees_res.scalars().all()
    
    # Завантажуємо ролі для форми додавання
    roles_res = await session.execute(select(Role).order_by(Role.id))
    roles = roles_res.scalars().all()
    role_options = "".join([f'<option value="{r.id}">{html.escape(r.name)}</option>' for r in roles])

    # Завантажуємо виробничі цехи (склади) для прив'язки кухарів
    warehouses_res = await session.execute(select(Warehouse).where(Warehouse.is_production == True).order_by(Warehouse.name))
    warehouses = warehouses_res.scalars().all()
    
    # Створюємо мапу імен складів для відображення в таблиці
    wh_map = {w.id: w.name for w in warehouses}

    # Генеруємо чекбокси для модального вікна додавання
    wh_checkboxes = ""
    for w in warehouses:
        wh_checkboxes += f"""
        <div class="checkbox-group" style="margin-bottom:5px;">
            <input type="checkbox" id="new_wh_{w.id}" name="workshop_ids" value="{w.id}">
            <label for="new_wh_{w.id}" style="margin-bottom:0; font-weight:normal;">{html.escape(w.name)}</label>
        </div>
        """
    if not wh_checkboxes:
        wh_checkboxes = "<div style='color:#777; font-size:0.9em;'>Немає виробничих цехів</div>"

    rows = ""
    for e in employees:
        # Статус зміни
        status_badge = "<span class='badge badge-success'>🟢 На зміні</span>" if e.is_on_shift else "<span class='badge badge-secondary'>🔴 Вихідний</span>"
        
        # Роль (бейдж)
        role_badge = f"<span class='role-tag'>{html.escape(e.role.name if e.role else 'N/A')}</span>"
        
        # Цехи (якщо є)
        wh_info = ""
        # Підтримка нового поля (список)
        if e.assigned_workshop_ids:
            # assigned_workshop_ids - це список int
            names = []
            for wid in e.assigned_workshop_ids:
                if wid in wh_map:
                    names.append(html.escape(wh_map[wid]))
            
            if names:
                wh_info = f"<br><span style='font-size:0.8em; color:#6b7280;'><i class='fa-solid fa-fire-burner'></i> {', '.join(names)}</span>"
        
        # Підтримка старого поля (для сумісності)
        elif e.assigned_warehouse_id and e.assigned_warehouse_id in wh_map:
            wh_info = f"<br><span style='font-size:0.8em; color:#6b7280;'><i class='fa-solid fa-fire-burner'></i> {html.escape(wh_map[e.assigned_warehouse_id])}</span>"
        
        # Індикатор боргу (якщо є)
        debt_info = ""
        if e.cash_balance > 0:
            debt_info = f"<div style='color:#c0392b; font-size:0.85em; font-weight:bold; margin-top:2px;'>Борг: {e.cash_balance:.2f} грн</div>"
        
        rows += f"""
        <tr>
            <td style="text-align:center; color:#888;">{e.id}</td>
            <td style="font-weight:600;">
                {html.escape(e.full_name)}
                {debt_info}
            </td>
            <td>{html.escape(e.phone_number or '-')}</td>
            <td>{role_badge}{wh_info}</td>
            <td>{status_badge}</td>
            <td style="font-family:monospace; font-size:0.9em;">{e.telegram_user_id or '–'}</td>
            <td class="actions">
                <a href='/admin/edit_employee/{e.id}' class='button-sm' title="Редагувати"><i class="fa-solid fa-pen"></i></a>
                <a href='/admin/delete_employee/{e.id}' onclick="return confirm('Ви впевнені? Це безповоротна дія.');" class='button-sm danger' title="Видалити"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>"""

    styles = """
    <style>
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; }
        .badge-success { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
        .badge-secondary { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
        .role-tag { background: #eff6ff; color: #1e40af; padding: 3px 8px; border-radius: 6px; font-size: 0.85rem; border: 1px solid #dbeafe; }
        .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .nav-tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
        .nav-tabs a { padding: 10px 20px; text-decoration: none; color: #6b7280; border-bottom: 2px solid transparent; transition: all 0.2s; font-weight: 500; }
        .nav-tabs a.active { color: #4a4a4a; border-bottom-color: #4a4a4a; }
        .nav-tabs a:hover { color: #111827; }
    </style>
    """

    body = f"""
    {styles}
    
    <div class="card">
        <div class="nav-tabs">
            <a href="/admin/employees" class="active"><i class="fa-solid fa-users"></i> Співробітники</a>
            <a href="/admin/roles"><i class="fa-solid fa-user-tag"></i> Ролі та Доступи</a>
        </div>

        {error_msg}

        <div class="toolbar">
            <h3>Список персоналу</h3>
            <button class="button" onclick="document.getElementById('add-employee-modal').classList.add('active')">
                <i class="fa-solid fa-user-plus"></i> Додати співробітника
            </button>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th width="50">ID</th>
                        <th>Ім'я</th>
                        <th>Телефон</th>
                        <th>Роль / Цех</th>
                        <th>Статус</th>
                        <th>Telegram ID</th>
                        <th width="100" style="text-align:right;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or '<tr><td colspan="7" style="text-align:center; padding:20px;">Немає співробітників</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="add-employee-modal">
        <div class="modal">
            <div class="modal-header">
                <h4><i class="fa-solid fa-user-plus"></i> Новий співробітник</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-employee-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/add_employee" method="post">
                    <label for="full_name">Повне ім'я *</label>
                    <input type="text" id="full_name" name="full_name" required placeholder="Іванов Іван">
                    
                    <div class="form-grid" style="grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <label for="phone_number">Телефон (Логін) *</label>
                            <input type="text" id="phone_number" name="phone_number" placeholder="0671234567" required>
                        </div>
                        <div>
                            <label for="role_id">Роль *</label>
                            <select id="role_id" name="role_id" required>
                                {role_options}
                            </select>
                        </div>
                    </div>

                    <label>Цехи (для Поварів/Барменів):</label>
                    <div style="max-height:150px; overflow-y:auto; border:1px solid #ddd; padding:10px; border-radius:5px; background:#f9f9f9; margin-bottom:15px;">
                        {wh_checkboxes}
                    </div>
                    <small style="color:#666; display:block; margin-bottom:10px; margin-top:-10px;">Відмітьте цехи, замовлення з яких повинен бачити цей працівник.</small>

                    <label for="password">Пароль (для входу в Staff App)</label>
                    <input type="text" id="password" name="password" placeholder="Залиште пустим, якщо не потрібен">
                    
                    <button type="submit" class="button" style="width: 100%; margin-top: 10px;">Створити</button>
                </form>
            </div>
        </div>
    </div>
    """

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["employees_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Співробітники", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/add_employee")
async def add_employee(
    request: Request,
    full_name: str = Form(...), 
    phone_number: str = Form(None), 
    role_id: int = Form(...), 
    password: str = Form(None), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    form = await request.form()
    # Отримуємо список вибраних цехів
    workshop_ids = [int(x) for x in form.getlist("workshop_ids")]

    cleaned_phone = re.sub(r'\D', '', phone_number) if phone_number else None
    if cleaned_phone and not (10 <= len(cleaned_phone) <= 15): 
        raise HTTPException(status_code=400, detail="Невірний формат телефону")
    
    pw_hash = None
    if password and password.strip():
        pw_hash = get_password_hash(password)

    session.add(Employee(
        full_name=full_name, 
        phone_number=cleaned_phone, 
        role_id=role_id, 
        assigned_workshop_ids=workshop_ids, 
        assigned_warehouse_id=workshop_ids[0] if workshop_ids else None, 
        password_hash=pw_hash
    ))
    
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Цей номер телефону вже використовується")
        
    return RedirectResponse(url="/admin/employees", status_code=303)

@router.get("/admin/edit_employee/{employee_id}", response_class=HTMLResponse)
async def get_edit_employee_form(
    employee_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    employee = await session.get(Employee, employee_id, options=[joinedload(Employee.role)])
    if not employee: 
        raise HTTPException(status_code=404, detail="Співробітника не знайдено")
        
    roles_res = await session.execute(select(Role))
    roles = roles_res.scalars().all()
    role_options = "".join([f'<option value="{r.id}" {"selected" if r.id == employee.role_id else ""}>{html.escape(r.name)}</option>' for r in roles])
    
    # Завантажуємо цехи для редагування
    warehouses_res = await session.execute(select(Warehouse).where(Warehouse.is_production == True).order_by(Warehouse.name))
    warehouses = warehouses_res.scalars().all()
    
    # Отримуємо поточні прив'язані цехи
    current_wh_ids = employee.assigned_workshop_ids or []
    # Підтримка старого поля, якщо нове пусте
    if not current_wh_ids and employee.assigned_warehouse_id:
        current_wh_ids = [employee.assigned_warehouse_id]

    wh_checkboxes = ""
    for w in warehouses:
        checked = "checked" if w.id in current_wh_ids else ""
        wh_checkboxes += f"""
        <div class="checkbox-group" style="margin-bottom:5px;">
            <input type="checkbox" id="edit_wh_{w.id}" name="workshop_ids" value="{w.id}" {checked}>
            <label for="edit_wh_{w.id}" style="margin-bottom:0; font-weight:normal;">{html.escape(w.name)}</label>
        </div>
        """
    if not wh_checkboxes:
        wh_checkboxes = "<div style='color:#777; font-size:0.9em;'>Немає виробничих цехів</div>"

    body = f"""
    <div class="card" style="max-width: 500px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <h2>✏️ Редагування: {html.escape(employee.full_name)}</h2>
            <a href="/admin/employees" class="button secondary">Скасувати</a>
        </div>
        
        <form action="/admin/edit_employee/{employee_id}" method="post">
            <label>Ім'я:</label>
            <input type="text" name="full_name" value="{html.escape(employee.full_name)}" required>
            
            <label>Телефон:</label>
            <input type="text" name="phone_number" value="{html.escape(employee.phone_number or '')}">
            
            <label>Роль:</label>
            <select name="role_id" required>{role_options}</select>
            
            <label>Прив'язка до цехів (фільтр замовлень):</label>
            <div style="max-height:150px; overflow-y:auto; border:1px solid #ddd; padding:10px; border-radius:5px; background:#f9f9f9; margin-bottom:15px;">
                {wh_checkboxes}
            </div>

            <label>Новий пароль (залиште пустим, якщо не змінюєте):</label>
            <input type="text" name="password" placeholder="******">
            
            <label style="color:#777; font-size:0.9em;">Telegram ID (змінюється через бот):</label>
            <input type="text" value="{employee.telegram_user_id or ''}" disabled style="background:#f3f4f6;">
            
            <button type="submit" class="button" style="width:100%; margin-top:15px;">Зберегти зміни</button>
        </form>
    </div>"""
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["employees_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Редагування співробітника", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/edit_employee/{employee_id}")
async def edit_employee(
    request: Request,
    employee_id: int, 
    full_name: str = Form(...), 
    phone_number: str = Form(None), 
    role_id: int = Form(...), 
    password: str = Form(None),
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    form = await request.form()
    workshop_ids = [int(x) for x in form.getlist("workshop_ids")]

    employee = await session.get(Employee, employee_id)
    if employee:
        cleaned = re.sub(r'\D', '', phone_number) if phone_number else None
        if cleaned and not (10 <= len(cleaned) <= 15): 
            raise HTTPException(status_code=400, detail="Невірний формат телефону")
        
        employee.full_name = full_name
        employee.phone_number = cleaned
        employee.role_id = role_id
        
        # Оновлюємо список цехів
        employee.assigned_workshop_ids = workshop_ids
        employee.assigned_warehouse_id = workshop_ids[0] if workshop_ids else None
        
        if password and password.strip():
            employee.password_hash = get_password_hash(password)

        try: 
            await session.commit()
        except IntegrityError: 
            await session.rollback()
            raise HTTPException(status_code=400, detail="Цей номер телефону вже зайнятий")
            
    return RedirectResponse(url="/admin/employees", status_code=303)

@router.get("/admin/delete_employee/{employee_id}")
async def delete_employee(
    employee_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    employee = await session.get(Employee, employee_id)
    if employee:
        if employee.cash_balance > 0:
             return RedirectResponse(url="/admin/employees?error=has_debt", status_code=303)

        final_statuses_res = await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))
        final_status_ids = final_statuses_res.scalars().all()

        active_assignments = await session.execute(
            select(func.count(Order.id)).where(
                Order.status_id.not_in(final_status_ids),
                or_(Order.courier_id == employee_id, Order.accepted_by_waiter_id == employee_id)
            )
        )
        
        active_shift = await session.execute(
            select(func.count(CashShift.id)).where(CashShift.employee_id == employee_id, CashShift.is_closed == False)
        )

        if active_assignments.scalar() > 0 or active_shift.scalar() > 0:
             return RedirectResponse(url="/admin/employees?error=assigned", status_code=303)
        
        try:
            await session.delete(employee)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return RedirectResponse(url="/admin/employees?error=integrity", status_code=303)

    return RedirectResponse(url="/admin/employees", status_code=303)


# --- РОЛІ (ОНОВЛЕНО) ---

@router.get("/admin/roles", response_class=HTMLResponse)
async def admin_roles(
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    """Відображає список ролей."""
    settings = await session.get(Settings, 1) or Settings()
    roles_res = await session.execute(select(Role).order_by(Role.id))
    roles = roles_res.scalars().all()
    
    rows = ""
    for r in roles:
        def icon(val): return '<i class="fa-solid fa-check" style="color:green;"></i>' if val else '<span style="color:#eee;">•</span>'
        
        # Іконка для права скасування
        cancel_icon = '<i class="fa-solid fa-check" style="color:green;"></i>' if r.can_cancel_orders else '<span style="color:#eee;">•</span>'

        rows += f"""
        <tr>
            <td>{r.id}</td>
            <td style="font-weight:600;">{html.escape(r.name)}</td>
            <td style="text-align:center;">{icon(r.can_manage_orders)}</td>
            <td style="text-align:center;">{icon(r.can_be_assigned)}</td>
            <td style="text-align:center;">{icon(r.can_serve_tables)}</td>
            <td style="text-align:center;">{cancel_icon}</td> <td style="text-align:center;">{icon(r.can_receive_kitchen_orders)}</td>
            <td style="text-align:center;">{icon(r.can_receive_bar_orders)}</td>
            <td class="actions">
                <a href="/admin/edit_role/{r.id}" class="button-sm" title="Редагувати"><i class="fa-solid fa-pen"></i></a>
                <a href="/admin/delete_role/{r.id}" onclick="return confirm('Видалити роль?');" class='button-sm danger' title="Видалити"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>"""

    styles = """
    <style>
        .nav-tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
        .nav-tabs a { padding: 10px 20px; text-decoration: none; color: #6b7280; border-bottom: 2px solid transparent; transition: all 0.2s; font-weight: 500; }
        .nav-tabs a.active { color: #4a4a4a; border-bottom-color: #4a4a4a; }
        .nav-tabs a:hover { color: #111827; }
        .perm-group { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; background: #f9fafb; padding: 10px; border-radius: 8px; }
    </style>
    """

    body = f"""
    {styles}
    
    <div class="card">
        <div class="nav-tabs">
            <a href="/admin/employees"><i class="fa-solid fa-users"></i> Співробітники</a>
            <a href="/admin/roles" class="active"><i class="fa-solid fa-user-tag"></i> Ролі та Доступи</a>
        </div>
        
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3>Налаштування доступів</h3>
            <button class="button" onclick="document.getElementById('add-role-modal').classList.add('active')">
                <i class="fa-solid fa-plus"></i> Нова роль
            </button>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th width="50">ID</th>
                        <th>Назва</th>
                        <th style="text-align:center;">Оператор</th>
                        <th style="text-align:center;">Кур'єр</th>
                        <th style="text-align:center;">Офіціант</th>
                        <th style="text-align:center; color:#c0392b;">Скасування</th>
                        <th style="text-align:center;">Кухня</th>
                        <th style="text-align:center;">Бар</th>
                        <th width="100" style="text-align:right;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or '<tr><td colspan="9" style="text-align:center; padding:20px;">Ролей немає</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="add-role-modal">
        <div class="modal">
            <div class="modal-header">
                <h4>Нова роль</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-role-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/add_role" method="post">
                    <label for="name">Назва ролі *</label>
                    <input type="text" id="name" name="name" required placeholder="Наприклад: Менеджер">
                    
                    <label style="margin-bottom: 10px; display:block;">Права доступу:</label>
                    <div class="perm-group">
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_manage_orders" name="can_manage_orders" value="true">
                            <label for="can_manage_orders">Оператор (Адмін)</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_be_assigned" name="can_be_assigned" value="true">
                            <label for="can_be_assigned">Кур'єр (Доставка)</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_serve_tables" name="can_serve_tables" value="true">
                            <label for="can_serve_tables">Офіціант (Зал)</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_cancel_orders" name="can_cancel_orders" value="true">
                            <label for="can_cancel_orders" style="color:#c0392b; font-weight:bold;">❌ Скасування замовлень</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_receive_kitchen_orders" name="can_receive_kitchen_orders" value="true">
                            <label for="can_receive_kitchen_orders">Кухня</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="can_receive_bar_orders" name="can_receive_bar_orders" value="true">
                            <label for="can_receive_bar_orders">Бар</label> 
                        </div>
                    </div>
                    
                    <button type="submit" class="button" style="width: 100%;">Додати роль</button>
                </form>
            </div>
        </div>
    </div>
    """
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["employees_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Ролі", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/add_role")
async def add_role(
    name: str = Form(...), 
    can_manage_orders: bool = Form(False), 
    can_be_assigned: bool = Form(False), 
    can_serve_tables: bool = Form(False), 
    can_cancel_orders: bool = Form(False), # <-- Нове поле
    can_receive_kitchen_orders: bool = Form(False), 
    can_receive_bar_orders: bool = Form(False), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    session.add(Role(
        name=name, 
        can_manage_orders=can_manage_orders, 
        can_be_assigned=can_be_assigned, 
        can_serve_tables=can_serve_tables, 
        can_cancel_orders=can_cancel_orders, # <-- Зберігаємо
        can_receive_kitchen_orders=can_receive_kitchen_orders, 
        can_receive_bar_orders=can_receive_bar_orders
    ))
    await session.commit()
    return RedirectResponse(url="/admin/roles", status_code=303)

@router.get("/admin/edit_role/{role_id}", response_class=HTMLResponse)
async def get_edit_role_form(
    role_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    role = await session.get(Role, role_id)
    if not role: raise HTTPException(404, "Роль не знайдено")
    
    body = f"""
    <div class="card" style="max-width: 500px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2>✏️ Редагування ролі</h2>
            <a href="/admin/roles" class="button secondary">Скасувати</a>
        </div>
        
        <form action="/admin/edit_role/{role_id}" method="post">
            <label>Назва:</label>
            <input type="text" name="name" value="{html.escape(role.name)}" required>
            
            <label style="margin-bottom: 10px; display:block;">Права доступу:</label>
            <div style="background: #f9fafb; padding: 15px; border-radius: 8px; border: 1px solid #eee;">
                <div class="checkbox-group">
                    <input type="checkbox" name="can_manage_orders" value="true" {'checked' if role.can_manage_orders else ''}>
                    <label>Оператор (Адмін-панель)</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" name="can_be_assigned" value="true" {'checked' if role.can_be_assigned else ''}>
                    <label>Кур'єр (Доставка)</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" name="can_serve_tables" value="true" {'checked' if role.can_serve_tables else ''}>
                    <label>Офіціант (Зал)</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" name="can_cancel_orders" value="true" {'checked' if role.can_cancel_orders else ''}>
                    <label style="color:#c0392b; font-weight:bold;">❌ Скасування замовлень</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" name="can_receive_kitchen_orders" value="true" {'checked' if role.can_receive_kitchen_orders else ''}>
                    <label>Кухня (Екран повара)</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" name="can_receive_bar_orders" value="true" {'checked' if role.can_receive_bar_orders else ''}>
                    <label>Бар (Екран бармена)</label>
                </div>
            </div>
            
            <button type="submit" class="button" style="width: 100%; margin-top: 20px;">Зберегти зміни</button>
        </form>
    </div>"""
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["employees_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Редагування ролі", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/edit_role/{role_id}")
async def edit_role(
    role_id: int, 
    name: str = Form(...), 
    can_manage_orders: bool = Form(False), 
    can_be_assigned: bool = Form(False), 
    can_serve_tables: bool = Form(False), 
    can_cancel_orders: bool = Form(False), # <-- Оновлюємо
    can_receive_kitchen_orders: bool = Form(False), 
    can_receive_bar_orders: bool = Form(False), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    role = await session.get(Role, role_id)
    if role:
        role.name = name
        role.can_manage_orders = can_manage_orders
        role.can_be_assigned = can_be_assigned
        role.can_serve_tables = can_serve_tables
        role.can_cancel_orders = can_cancel_orders # <--
        role.can_receive_kitchen_orders = can_receive_kitchen_orders
        role.can_receive_bar_orders = can_receive_bar_orders
        await session.commit()
    return RedirectResponse(url="/admin/roles", status_code=303)

@router.get("/admin/delete_role/{role_id}")
async def delete_role(
    role_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    role = await session.get(Role, role_id)
    if role:
        try: 
            await session.delete(role)
            await session.commit()
        except IntegrityError: 
            return RedirectResponse(url="/admin/roles?error=role_in_use", status_code=303)
            
    return RedirectResponse(url="/admin/roles", status_code=303)