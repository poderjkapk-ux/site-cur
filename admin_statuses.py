# admin_statuses.py

import html
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import OrderStatus, Settings
from templates import ADMIN_HTML_TEMPLATE
from dependencies import get_db_session, check_credentials

router = APIRouter()

# --- КОНФІГУРАЦІЯ БЕЗПЕКИ ---
# ID статусів, які критично важливі для початку роботи системи (наприклад, ID 1 - це "Новий")
# Їх не можна видаляти, щоб не зламати логіку створення замовлення.
PROTECTED_STATUS_IDS = [1] 

@router.get("/admin/statuses", response_class=HTMLResponse)
async def admin_statuses(
    error: Optional[str] = None, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    """Відображає сторінку управління статусами замовлень."""
    settings = await session.get(Settings, 1) or Settings()
    
    # Завантажуємо статуси
    statuses_res = await session.execute(select(OrderStatus).order_by(OrderStatus.id))
    statuses = statuses_res.scalars().all()

    # Обробка помилок
    error_html = ""
    if error == "in_use":
        error_html = """
        <div class='card' style='background:#fee2e2; color:#991b1b; border:1px solid #fecaca; margin-bottom:20px;'>
            ⚠️ <b>Помилка!</b> Неможливо видалити цей статус, оскільки існують замовлення з ним.
        </div>
        """
    elif error == "protected":
        error_html = """
        <div class='card' style='background:#fff3cd; color:#856404; border:1px solid #ffeeba; margin-bottom:20px;'>
            🔒 <b>Заборонено!</b> Цей статус є системним або фінальним. Його видалення порушить роботу каси або складу.
            <br><small>Ви можете перейменувати його або змінити налаштування видимості.</small>
        </div>
        """

    # Допоміжна функція для кнопок-перемикачів
    def toggle_btn(id, field, val, icon_class, title, active_color="green"):
        color = active_color if val else "#cbd5e1" # Сірий, якщо вимкнено
        opacity = "1" if val else "0.6"
        return f"""
        <form action="/admin/edit_status/{id}" method="post" style="display:inline-block; margin:0 3px;">
            <input type="hidden" name="field" value="{field}">
            <input type="hidden" name="value" value="{'false' if val else 'true'}">
            <button type="submit" class="icon-btn" title="{title}: {'Увімкнено' if val else 'Вимкнено'}" style="color:{color}; opacity:{opacity};">
                <i class="{icon_class}"></i>
            </button>
        </form>
        """

    rows = ""
    for s in statuses:
        # Перевірка: чи захищений статус?
        # Захищаємо: ID 1 ("Новий"), Статуси завершення (Каса), Статуси скасування (Склад)
        is_protected = (s.id in PROTECTED_STATUS_IDS) or s.is_completed_status or s.is_cancelled_status
        
        # 1. Колонка: Хто бачить (Доступи)
        visibility_icons = (
            toggle_btn(s.id, "visible_to_operator", s.visible_to_operator, "fa-solid fa-headset", "Оператор (Адмін)", "#475569") +
            toggle_btn(s.id, "visible_to_courier", s.visible_to_courier, "fa-solid fa-motorcycle", "Кур'єр", "#475569") +
            toggle_btn(s.id, "visible_to_waiter", s.visible_to_waiter, "fa-solid fa-user-tie", "Офіціант", "#475569") +
            "<span style='color:#e2e8f0; margin:0 8px; font-size:1.2em;'>|</span>" +
            toggle_btn(s.id, "visible_to_chef", s.visible_to_chef, "fa-solid fa-utensils", "Екран Кухні", "#ea580c") +
            toggle_btn(s.id, "visible_to_bartender", s.visible_to_bartender, "fa-solid fa-martini-glass", "Екран Бару", "#d946ef")
        )

        # 2. Колонка: Системна логіка
        system_icons = (
            toggle_btn(s.id, "notify_customer", s.notify_customer, "fa-regular fa-bell", "Сповіщати клієнта (Telegram)", "#3b82f6") +
            toggle_btn(s.id, "requires_kitchen_notify", s.requires_kitchen_notify, "fa-solid fa-bullhorn", "Відправляти на приготування (Тригер)", "#f59e0b") +
            toggle_btn(s.id, "is_completed_status", s.is_completed_status, "fa-solid fa-flag-checkered", "Успіх / Гроші в касу", "#16a34a") +
            toggle_btn(s.id, "is_cancelled_status", s.is_cancelled_status, "fa-solid fa-ban", "Скасування / Повернення на склад", "#dc2626")
        )

        # 3. Дії (Видалити або Замок)
        if is_protected:
            actions = "<span class='icon-btn' title='Системний статус (Не можна видалити)' style='color:#94a3b8; cursor:help;'><i class='fa-solid fa-lock'></i></span>"
        else:
            actions = f"""
            <a href="/admin/delete_status/{s.id}" onclick="return confirm('Ви впевнені?');" class="button-sm danger" style="padding:5px 8px;" title="Видалити">
                <i class="fa-solid fa-trash"></i>
            </a>
            """

        # Стилізація рядка
        bg_style = ""
        if s.is_completed_status: bg_style = "background-color: #f0fdf4;" # Зелений відтінок
        if s.is_cancelled_status: bg_style = "background-color: #fef2f2;" # Червоний відтінок
        if s.requires_kitchen_notify: bg_style = "background-color: #fff7ed;" # Помаранчевий (В роботі)

        rows += f"""
        <tr style="{bg_style}">
            <td style="text-align:center; color:#64748b; font-weight:bold;">{s.id}</td>
            <td>
                <form action="/admin/edit_status/{s.id}" method="post" class="inline-form" style="margin-bottom:0;">
                    <input type="text" name="name" value="{html.escape(s.name)}" style="width: 100%; min-width:140px; padding: 6px; border:1px solid #cbd5e1; border-radius:6px; font-weight:500;">
                    <button type="submit" class="button-sm secondary" title="Зберегти назву" style="padding: 6px 10px; margin-left:5px;"><i class="fa-solid fa-floppy-disk"></i></button>
                </form>
            </td>
            <td style="text-align:center; white-space: nowrap;">{visibility_icons}</td>
            <td style="text-align:center; white-space: nowrap; border-left: 1px solid #e2e8f0;">{system_icons}</td>
            <td style="text-align:center;">{actions}</td>
        </tr>"""

    # CSS Стилі
    styles = """
    <style>
        .icon-btn { background: none; border: none; cursor: pointer; font-size: 1.15rem; transition: all 0.2s; padding: 4px; display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border-radius:6px; }
        .icon-btn:hover { background-color: rgba(0,0,0,0.05); transform: scale(1.1); opacity: 1 !important; }
        
        .legend-box { background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 25px; font-size: 0.9rem; }
        .legend-title { font-weight: 700; margin-bottom: 10px; display: block; color: #334155; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 0.5px; }
        .legend-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .l-item { display: flex; align-items: center; gap: 8px; color: #475569; }
        .l-item i { font-size: 1.1em; width: 20px; text-align: center; }
    </style>
    """

    body = f"""
    {styles}
    {error_html}
    
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2 style="margin:0;"><i class="fa-solid fa-list-check"></i> Статуси замовлень</h2>
            <button class="button" onclick="document.getElementById('add-status-modal').classList.add('active')">
                <i class="fa-solid fa-plus"></i> Додати статус
            </button>
        </div>
        
        <div class="legend-box">
            <span class="legend-title">ℹ️ Розшифровка іконок та логіки:</span>
            <div class="legend-grid">
                <div class="l-item"><i class="fa-solid fa-bullhorn" style="color:#f59e0b"></i> <b>Старт приготування:</b> Замовлення з'являється у Повара/Бармена.</div>
                <div class="l-item"><i class="fa-solid fa-flag-checkered" style="color:#16a34a"></i> <b>Успіх (Фінал):</b> Гроші зараховуються в касу, склад списується.</div>
                <div class="l-item"><i class="fa-solid fa-ban" style="color:#dc2626"></i> <b>Скасування:</b> Замовлення анулюється, товари повертаються на склад.</div>
                <div class="l-item"><i class="fa-solid fa-lock" style="color:#94a3b8"></i> <b>Захищений:</b> Статус не можна видалити (системний).</div>
            </div>
        </div>

        <div class="table-wrapper">
            <table class="inv-table">
                <thead>
                    <tr>
                        <th width="40">ID</th>
                        <th>Назва</th>
                        <th style="text-align:center;">Видимість (Ролі)</th>
                        <th style="text-align:center;">Системна логіка</th>
                        <th width="60" style="text-align:center;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or "<tr><td colspan='5' style='text-align:center; padding:20px;'>Статусів ще немає</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="add-status-modal">
        <div class="modal">
            <div class="modal-header">
                <h4>Новий статус</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-status-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/add_status" method="post">
                    <label>Назва статусу *</label>
                    <input type="text" name="name" placeholder="Наприклад: Очікує оплати" required>
                    
                    <div style="background:#f1f5f9; padding:15px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:15px;">
                        <label style="margin-bottom:10px; display:block; font-weight:bold; color:#334155;">Хто бачить цей статус?</label>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                            <div class="checkbox-group"><input type="checkbox" name="visible_to_operator" value="true" checked><label>Оператор</label></div>
                            <div class="checkbox-group"><input type="checkbox" name="visible_to_courier" value="true"><label>Кур'єр</label></div>
                            <div class="checkbox-group"><input type="checkbox" name="visible_to_waiter" value="true"><label>Офіціант</label></div>
                            <div class="checkbox-group"><input type="checkbox" name="visible_to_chef" value="true"><label>Повар (Екран)</label></div>
                            <div class="checkbox-group"><input type="checkbox" name="visible_to_bartender" value="true"><label>Бармен (Екран)</label></div>
                        </div>
                    </div>

                    <div style="background:#fff7ed; padding:15px; border-radius:8px; border:1px solid #ffedd5; margin-bottom:15px;">
                        <label style="margin-bottom:10px; display:block; font-weight:bold; color:#9a3412;">Системна поведінка (Обережно!)</label>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" name="notify_customer" value="true" checked>
                            <label>🔔 Сповіщати клієнта (Telegram)</label>
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" name="requires_kitchen_notify" value="true">
                            <label>👨‍🍳 Тригер виробництва (З'являється на Кухні)</label>
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" name="is_completed_status" value="true">
                            <label>🏁 Фінальний: Виконано (Гроші в касу)</label>
                        </div>
                        
                        <div class="checkbox-group">
                            <input type="checkbox" name="is_cancelled_status" value="true">
                            <label>🚫 Фінальний: Скасовано (Без грошей)</label>
                        </div>
                    </div>

                    <button type="submit" class="button" style="width:100%;">Створити</button>
                </form>
            </div>
        </div>
    </div>
    """

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["statuses_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Статуси замовлень", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/add_status")
async def add_status(
    name: str = Form(...), 
    notify_customer: bool = Form(False), 
    visible_to_operator: bool = Form(False), 
    visible_to_courier: bool = Form(False), 
    visible_to_waiter: bool = Form(False), 
    visible_to_chef: bool = Form(False), 
    visible_to_bartender: bool = Form(False), 
    requires_kitchen_notify: bool = Form(False), 
    is_completed_status: bool = Form(False), 
    is_cancelled_status: bool = Form(False), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    session.add(OrderStatus(
        name=name, 
        notify_customer=notify_customer, 
        visible_to_operator=visible_to_operator, 
        visible_to_courier=visible_to_courier, 
        visible_to_waiter=visible_to_waiter, 
        visible_to_chef=visible_to_chef, 
        visible_to_bartender=visible_to_bartender, 
        requires_kitchen_notify=requires_kitchen_notify, 
        is_completed_status=is_completed_status, 
        is_cancelled_status=is_cancelled_status
    ))
    await session.commit()
    return RedirectResponse(url="/admin/statuses", status_code=303)

@router.post("/admin/edit_status/{status_id}")
async def edit_status(
    status_id: int, 
    name: Optional[str] = Form(None), 
    field: Optional[str] = Form(None), 
    value: Optional[str] = Form(None), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    status = await session.get(OrderStatus, status_id)
    if status:
        if name and not field: 
            status.name = name
        elif field: 
            setattr(status, field, value.lower() == 'true')
        await session.commit()
    return RedirectResponse(url="/admin/statuses", status_code=303)

@router.get("/admin/delete_status/{status_id}")
async def delete_status(
    status_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    status = await session.get(OrderStatus, status_id)
    if not status:
        return RedirectResponse(url="/admin/statuses", status_code=303)

    # ЗАХИСТ: Не дозволяємо видаляти критично важливі статуси
    if status.id in PROTECTED_STATUS_IDS or status.is_completed_status or status.is_cancelled_status:
        return RedirectResponse(url="/admin/statuses?error=protected", status_code=303)

    try: 
        await session.delete(status)
        await session.commit()
    except IntegrityError: 
        return RedirectResponse(url="/admin/statuses?error=in_use", status_code=303)
            
    return RedirectResponse(url="/admin/statuses", status_code=303)