# admin_cash.py

import html
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, func
from sqlalchemy.orm import joinedload

# Додано імпорт BalanceHistory та CashTransaction для ручного погашення
from models import Employee, CashShift, Settings, Order, BalanceHistory, CashTransaction
from templates import ADMIN_HTML_TEMPLATE
from dependencies import get_db_session, check_credentials
from cash_service import (
    open_new_shift, get_shift_statistics, close_active_shift, 
    add_shift_transaction, process_handover
)

router = APIRouter()

@router.get("/admin/cash", response_class=HTMLResponse)
async def cash_dashboard(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    
    # Шукаємо будь-яку відкриту зміну
    active_shift_res = await session.execute(
        select(CashShift).where(CashShift.is_closed == False).options(joinedload(CashShift.employee))
    )
    active_shift = active_shift_res.scalars().first()
    
    # Кнопка історії та стиль для карток
    style_block = """
    <style>
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.05); text-align: center; }
        .stat-card h3 { margin: 0 0 10px 0; font-size: 0.9rem; color: #777; text-transform: uppercase; }
        .stat-card .value { font-size: 1.8rem; font-weight: bold; color: #333; }
        .stat-card .icon { font-size: 2rem; margin-bottom: 10px; opacity: 0.8; }
        .stat-card.primary { border-bottom: 4px solid #3498db; }
        .stat-card.success { border-bottom: 4px solid #2ecc71; }
        .stat-card.warning { border-bottom: 4px solid #f39c12; }
        .stat-card.danger { border-bottom: 4px solid #e74c3c; }
    </style>
    """
    
    header_html = f"""
    {style_block}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="margin:0;"><i class="fa-solid fa-cash-register"></i> Керування касою</h2>
        <a href="/admin/cash/history" class="button secondary"><i class="fa-solid fa-clock-rotate-left"></i> Історія змін</a>
    </div>
    """
    
    debtors_html = ""
    
    if active_shift:
        # --- БЛОК БОРЖНИКІВ (Хто не здав касу) ---
        debtors_res = await session.execute(
            select(Employee).where(Employee.cash_balance > 0).order_by(desc(Employee.cash_balance))
        )
        debtors = debtors_res.scalars().all()
        
        total_debt = sum(d.cash_balance for d in debtors)
        
        if debtors:
            debtors_rows = ""
            for d in debtors:
                debtors_rows += f"""
                <tr>
                    <td><b>{html.escape(d.full_name)}</b></td>
                    <td>{d.role.name}</td>
                    <td style="color: #c0392b; font-weight: bold;">{d.cash_balance:.2f} грн</td>
                    <td class="actions">
                        <a href="/admin/cash/handover/{d.id}" class="button-sm"><i class="fa-solid fa-hand-holding-dollar"></i> Прийняти</a>
                    </td>
                </tr>
                """
            
            debtors_html = f"""
            <div class="card" style="border-left: 5px solid #e67e22;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                    <h3 style="margin:0; color:#d35400;"><i class="fa-solid fa-circle-exclamation"></i> Не здана виручка</h3>
                    <span class="badge warning" style="font-size:1rem;">Всього: {total_debt:.2f} грн</span>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead><tr><th>Співробітник</th><th>Роль</th><th>Сума на руках</th><th>Дії</th></tr></thead>
                        <tbody>{debtors_rows}</tbody>
                    </table>
                </div>
            </div>
            """
        else:
            debtors_html = """
            <div class="card" style="border-left: 5px solid #2ecc71; background: #f0fff4;">
                <h3 style="margin:0; color: #27ae60;"><i class="fa-solid fa-check-circle"></i> Всі співробітники здали виручку</h3>
            </div>
            """
        # ------------------------------------------

        # Статистика зміни
        stats = await get_shift_statistics(session, active_shift.id)
        
        # Блок статистики (Grid)
        dashboard_stats = f"""
        <div class="stat-grid">
            <div class="stat-card primary">
                <div class="icon" style="color:#3498db;"><i class="fa-solid fa-coins"></i></div>
                <h3>Готівка (Теорія)</h3>
                <div class="value">{stats['theoretical_cash']:.2f} грн</div>
                <small style="color:#777;">Має бути в скриньці</small>
            </div>
            <div class="stat-card success">
                <div class="icon" style="color:#2ecc71;"><i class="fa-solid fa-money-bill-wave"></i></div>
                <h3>Продажі (Готівка)</h3>
                <div class="value">+{stats['total_sales_cash']:.2f} грн</div>
            </div>
            <div class="stat-card warning">
                <div class="icon" style="color:#f39c12;"><i class="fa-regular fa-credit-card"></i></div>
                <h3>Продажі (Картка)</h3>
                <div class="value">{stats['total_sales_card']:.2f} грн</div>
            </div>
            <div class="stat-card">
                <div class="icon" style="color:#95a5a6;"><i class="fa-solid fa-chart-line"></i></div>
                <h3>Всього за зміну</h3>
                <div class="value">{stats['total_sales']:.2f} грн</div>
            </div>
        </div>
        """
        
        # Деталі розрахунку (Accordion style details)
        calc_details = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #eee;">
            <h4 style="margin-top:0;"><i class="fa-solid fa-calculator"></i> Деталізація залишку:</h4>
            <ul style="list-style:none; padding:0; margin:0; font-family:monospace; font-size:1rem;">
                <li>Початковий залишок: <b>{stats['start_cash']:.2f}</b></li>
                <li>+ Виручка (Готівка): <b>{stats['total_sales_cash']:.2f}</b></li>
                <li>+ Службове внесення: <b>{stats['service_in']:.2f}</b></li>
                <li>- Службове вилучення: <b>{stats['service_out']:.2f}</b></li>
                <hr style="margin:5px 0; border-top:1px dashed #ccc;">
                <li>= Розрахунковий залишок: <b>{stats['theoretical_cash']:.2f}</b></li>
            </ul>
        </div>
        """
        
        actions_html = f"""
        <div class="card">
            <h3><i class="fa-solid fa-money-bill-transfer"></i> Службові операції</h3>
            <form action="/admin/cash/transaction" method="post" class="inline-form">
                <input type="hidden" name="shift_id" value="{active_shift.id}">
                <select name="transaction_type" style="width: 150px;">
                    <option value="in">📥 Внесення</option>
                    <option value="out">📤 Вилучення</option>
                </select>
                <input type="number" step="0.01" name="amount" placeholder="Сума" required style="width: 120px;">
                <input type="text" name="comment" placeholder="Коментар (напр. Розмін, Інкасація)" required>
                <button type="submit">Виконати</button>
            </form>
        </div>

        <div class="card" style="border: 1px solid #e74c3c;">
            <h3 style="color: #c0392b;"><i class="fa-solid fa-lock"></i> Закриття зміни (Z-звіт)</h3>
            <p style="color:#666;">Перерахуйте фактичну готівку в касі перед закриттям. Всі борги співробітників мають бути погашені.</p>
            <form action="/admin/cash/close" method="post" onsubmit="return confirm('Ви впевнені, що хочете закрити зміну? Ця дія незворотна.');">
                <input type="hidden" name="shift_id" value="{active_shift.id}">
                <label><b>Фактичний залишок готівки:</b></label>
                <div style="display:flex; gap:10px; align-items:center;">
                    <input type="number" step="0.01" name="end_cash_actual" required placeholder="0.00" style="font-size:1.2rem; width:200px;">
                    <button type="submit" class="button danger">🖨️ Закрити зміну</button>
                </div>
            </form>
        </div>
        """
        
        body = f"""
        {header_html}
        <div class="card" style="background: #f0fdf4; border: 1px solid #bbf7d0;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h2 style="margin:0; color:#166534;"><i class="fa-solid fa-circle-check"></i> Зміна #{active_shift.id} відкрита</h2>
                    <div style="color:#666; margin-top:5px;">
                        Касир: <b>{html.escape(active_shift.employee.full_name)}</b> | 
                        Початок: {active_shift.start_time.strftime('%d.%m %H:%M')}
                    </div>
                </div>
            </div>
        </div>
        
        {dashboard_stats}
        {calc_details}
        {debtors_html}
        {actions_html}
        """
    else:
        # Зміна закрита
        employees = (await session.execute(select(Employee).where(Employee.is_on_shift == True))).scalars().all()
        emp_options = "".join([f'<option value="{e.id}">{html.escape(e.full_name)}</option>' for e in employees])
        
        body = f"""
        {header_html}
        <div style="max-width: 600px; margin: 50px auto; text-align: center;">
            <div class="card" style="padding: 40px;">
                <i class="fa-solid fa-store-slash" style="font-size: 4rem; color: #ccc; margin-bottom: 20px;"></i>
                <h2 style="color: #555;">Касова зміна закрита</h2>
                <p style="color: #777; margin-bottom: 30px;">Для початку роботи та прийому оплат необхідно відкрити нову зміну.</p>
                
                <form action="/admin/cash/open" method="post" style="text-align: left;">
                    <label>Касир (відповідальний):</label>
                    <select name="employee_id" required>
                        {emp_options or '<option value="" disabled>Немає працівників на зміні</option>'}
                    </select>
                    
                    <label>Залишок в касі (грн):</label>
                    <input type="number" step="0.01" name="start_cash" value="0.00" required style="font-size: 1.2rem;">
                    
                    <button type="submit" class="button" style="width: 100%; justify-content: center; padding: 15px; font-size: 1.1rem;">
                        <i class="fa-solid fa-power-off"></i> Відкрити зміну
                    </button>
                </form>
            </div>
        </div>
        """

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["reports_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Каса", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

# --- СТОРІНКА ПРИЙОМУ ГРОШЕЙ (Handover) ---
@router.get("/admin/cash/handover/{employee_id}", response_class=HTMLResponse)
async def handover_form(
    employee_id: int,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Співробітника не знайдено")

    active_shift_res = await session.execute(select(CashShift).where(CashShift.is_closed == False))
    active_shift = active_shift_res.scalars().first()
    
    if not active_shift:
        return HTMLResponse("<h1>Спочатку відкрийте касову зміну!</h1><a href='/admin/cash'>Назад</a>")

    # --- ВИПРАВЛЕННЯ: ЗАКОМЕНТОВАНО фільтр is_cancelled_status=False ---
    # Це дозволяє бачити скасовані замовлення, якщо за ними "завис" борг.
    orders_res = await session.execute(
        select(Order).where(
            Order.payment_method == 'cash',
            Order.is_cash_turned_in == False,
            # Order.status.has(is_cancelled_status=False), # <--- ЗАКОМЕНТОВАНО, ЩОБ БАЧИТИ ВСІ БОРГИ
            or_(
                Order.courier_id == employee.id,
                Order.accepted_by_waiter_id == employee.id,
                Order.completed_by_courier_id == employee.id
            )
        )
        .options(joinedload(Order.table), joinedload(Order.status))
        .order_by(Order.id.desc())
    )
    orders = orders_res.scalars().all()
    
    rows = ""
    total_sum = Decimal('0.00')
    for o in orders:
        total_sum += o.total_price
        target = o.address if o.is_delivery else (o.table.name if o.table else 'Самовивіз')
        
        status_label = ""
        # Позначаємо скасовані замовлення червоним
        if o.status and o.status.is_cancelled_status:
            status_label = " <span style='color:red; font-size:0.8em; font-weight:bold;'>[СКАСОВАНО]</span>"
        
        rows += f"""
        <tr>
            <td style="text-align:center;"><input type="checkbox" name="order_ids" value="{o.id}" checked onchange="recalcTotal()"></td>
            <td>#{o.id} {status_label}</td>
            <td>{o.created_at.strftime('%d.%m %H:%M')}</td>
            <td>{html.escape(target or '')}</td>
            <td style="text-align:right; font-weight:bold;"><span class="amount">{o.total_price:.2f}</span> грн</td>
        </tr>
        """
    
    js_script = """
    <script>
        function recalcTotal() {
            let total = 0;
            document.querySelectorAll('input[name="order_ids"]:checked').forEach(cb => {
                const row = cb.closest('tr');
                const amountText = row.querySelector('.amount').innerText;
                total += parseFloat(amountText);
            });
            document.getElementById('selected-total').innerText = total.toFixed(2);
            
            const btn = document.getElementById('submit-btn');
            if(total === 0) btn.disabled = true; else btn.disabled = false;
        }
        
        function toggleAll(source) {
            checkboxes = document.getElementsByName('order_ids');
            for(var i=0, n=checkboxes.length;i<n;i++) {
                checkboxes[i].checked = source.checked;
            }
            recalcTotal();
        }
    </script>
    """

    body = f"""
    {js_script}
    <div style="max-width: 800px; margin: 0 auto;">
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #eee; padding-bottom: 15px; margin-bottom: 20px;">
                <h2>💸 Прийом виручки</h2>
                <a href="/admin/cash" class="button secondary">Скасувати</a>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; align-items: center; gap: 15px;">
                <div style="font-size: 2.5rem; color: #555;"><i class="fa-solid fa-user"></i></div>
                <div>
                    <div style="color: #777; font-size: 0.9rem;">Співробітник</div>
                    <div style="font-size: 1.2rem; font-weight: bold;">{html.escape(employee.full_name)}</div>
                    <div style="color: #c0392b;">Загальний борг: {employee.cash_balance:.2f} грн</div>
                </div>
            </div>
            
            <form action="/admin/cash/process_handover" method="post">
                <input type="hidden" name="employee_id" value="{employee.id}">
                <input type="hidden" name="shift_id" value="{active_shift.id}">
                
                <h3>Оберіть замовлення для здачі:</h3>
                <div class="table-wrapper">
                    <table style="width:100%;">
                        <thead>
                            <tr>
                                <th style="width: 40px; text-align:center;"><input type="checkbox" checked onclick="toggleAll(this)"></th>
                                <th>ID</th>
                                <th>Час</th>
                                <th>Джерело</th>
                                <th style="text-align:right;">Сума</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows or "<tr><td colspan='5' style='text-align:center; padding:20px;'>Немає доступних замовлень (або всі борги погашено)</td></tr>"}
                        </tbody>
                    </table>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background: #e8f5e9; border-radius: 8px; text-align: right; display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 1.1rem;">До отримання в касу:</div>
                    <div style="font-size: 2rem; font-weight: bold; color: #27ae60;"><span id="selected-total">{total_sum:.2f}</span> грн</div>
                </div>
                
                <div style="margin-top: 20px; text-align: right;">
                    <button type="submit" id="submit-btn" class="button" style="font-size: 1.1rem; padding: 12px 24px;">
                        <i class="fa-solid fa-check"></i> Підтвердити отримання
                    </button>
                </div>
            </form>

            <div style="margin-top: 40px; border-top: 2px dashed #ccc; padding-top: 20px;">
                <h3 style="color: #2980b9;"><i class="fa-solid fa-pen-to-square"></i> Внести довільну частину боргу</h3>
                <p style="color: #666; font-size: 0.9rem;">Використовуйте, якщо працівник здає суму, яка не збігається з точними сумами замовлень (наприклад, для закриття "завислого" боргу).</p>
                <form action="/admin/cash/manual_handover" method="post" style="display: flex; gap: 15px; align-items: center; background: #ebf5fb; padding: 15px; border-radius: 8px;">
                    <input type="hidden" name="employee_id" value="{employee.id}">
                    <input type="hidden" name="shift_id" value="{active_shift.id}">
                    <input type="number" step="0.01" name="amount" max="{employee.cash_balance}" placeholder="Введіть суму..." required style="font-size: 1.1rem; width: 200px;">
                    <button type="submit" class="button" style="background-color: #2980b9;"><i class="fa-solid fa-coins"></i> Зарахувати суму</button>
                </form>
            </div>
            </div>
    </div>
    """
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["reports_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Прийом виручки", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/cash/process_handover")
async def process_handover_route(
    request: Request,
    employee_id: int = Form(...),
    shift_id: int = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    form_data = await request.form()
    # FIX: Changed 'form' to 'form_data'
    order_ids = [int(x) for x in form_data.getlist("order_ids")]
    
    if not order_ids:
        raise HTTPException(status_code=400, detail="Не вибрано жодного замовлення")
    
    try:
        await process_handover(session, shift_id, employee_id, order_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return RedirectResponse("/admin/cash", status_code=303)

@router.get("/admin/cash/history", response_class=HTMLResponse)
async def cash_history(session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    shifts_res = await session.execute(
        select(CashShift)
        .where(CashShift.is_closed == True)
        .options(joinedload(CashShift.employee))
        .order_by(desc(CashShift.end_time))
        .limit(30)
    )
    shifts = shifts_res.scalars().all()
    
    rows = ""
    for s in shifts:
        theoretical = s.start_cash + s.total_sales_cash + s.service_in - s.service_out
        diff = s.end_cash_actual - theoretical
        
        # Візуалізація різниці
        if diff < -1:
            diff_style = "color:#c0392b; background:#fadbd8; padding: 2px 6px; border-radius: 4px;"
            icon = "<i class='fa-solid fa-circle-exclamation'></i>"
        elif diff > 1:
            diff_style = "color:#2980b9; background:#ebf5fb; padding: 2px 6px; border-radius: 4px;"
            icon = "<i class='fa-solid fa-plus'></i>"
        else:
            diff_style = "color:#27ae60; font-weight:bold;"
            icon = "<i class='fa-solid fa-check'></i>"
            
        diff_str = f"{diff:+.2f}"
        
        total_revenue = s.total_sales_cash + s.total_sales_card
        
        rows += f"""
        <tr>
            <td><b>#{s.id}</b></td>
            <td>
                <div style="font-size:0.9rem;">{s.start_time.strftime('%d.%m')}</div>
                <div style="color:#777; font-size:0.8rem;">{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}</div>
            </td>
            <td>{html.escape(s.employee.full_name)}</td>
            <td>{total_revenue:.2f} грн</td>
            <td>{s.end_cash_actual:.2f} грн</td>
            <td style="{diff_style}">{icon} {diff_str}</td>
            <td>
                <a href="/admin/cash/z_report/{s.id}" target="_blank" class="button-sm" title="Друк Z-звіту"><i class="fa-solid fa-print"></i></a>
            </td>
        </tr>
        """
        
    body = f"""
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <h2><i class="fa-solid fa-clock-rotate-left"></i> Історія касових змін</h2>
            <a href="/admin/cash" class="button secondary">⬅️ Поточна каса</a>
        </div>
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Дата/Час</th>
                        <th>Касир</th>
                        <th>Виручка (Всього)</th>
                        <th>Готівка (Факт)</th>
                        <th>Різниця (Каса)</th>
                        <th>Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or "<tr><td colspan='7' style='text-align:center;'>Історія порожня</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>
    """
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["reports_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Історія змін", body=body, site_title=settings.site_title, **active_classes))

@router.get("/admin/cash/z_report/{shift_id}", response_class=HTMLResponse)
async def print_z_report(shift_id: int, session: AsyncSession = Depends(get_db_session)):
    shift = await session.get(CashShift, shift_id, options=[joinedload(CashShift.employee)])
    if not shift: return HTMLResponse("Зміну не знайдено", status_code=404)
    
    settings = await session.get(Settings, 1) or Settings()
    
    theoretical = shift.start_cash + shift.total_sales_cash + shift.service_in - shift.service_out
    diff = shift.end_cash_actual - theoretical
    
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Z-звіт #{shift.id}</title>
        <style>
            body {{ font-family: 'Courier New', monospace; width: 320px; margin: 0 auto; padding: 20px 10px; }}
            .header {{ text-align: center; margin-bottom: 15px; border-bottom: 1px dashed #000; padding-bottom: 10px; }}
            .row {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
            .total {{ font-weight: bold; border-top: 1px dashed #000; margin-top: 10px; padding-top: 10px; font-size: 1.1em; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.8em; color: #555; }}
            h3 {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h3>{settings.site_title}</h3>
            <div>Z-ЗВІТ (Зміна #{shift.id})</div>
            <div>Відкрито: {shift.start_time.strftime('%d.%m.%Y %H:%M')}</div>
            <div>Закрито: {shift.end_time.strftime('%d.%m.%Y %H:%M')}</div>
            <div>Касир: {shift.employee.full_name}</div>
        </div>
        
        <div class="row"><span>Початковий залишок:</span><span>{shift.start_cash:.2f}</span></div>
        <br>
        <div class="row"><span>Готівка (Продаж):</span><span>+{shift.total_sales_cash:.2f}</span></div>
        <div class="row"><span>Картка (Продаж):</span><span>+{shift.total_sales_card:.2f}</span></div>
        <div class="row total"><span>РАЗОМ ВИРУЧКА:</span><span>{(shift.total_sales_cash + shift.total_sales_card):.2f}</span></div>
        <br>
        <div class="row"><span>Службове внесення:</span><span>+{shift.service_in:.2f}</span></div>
        <div class="row"><span>Службове вилучення:</span><span>-{shift.service_out:.2f}</span></div>
        <br>
        <div class="row" style="font-weight:bold; font-size:1.1em;"><span>В КАСІ (ФАКТ):</span><span>{shift.end_cash_actual:.2f}</span></div>
        <div class="row"><span>Різниця:</span><span>{diff:+.2f}</span></div>
        
        <div class="footer">
            <p>*** ЗМІНА ЗАКРИТА ***</p>
            <p>Нефіскальний документ</p>
        </div>
        
        <script>window.print();</script>
    </body>
    </html>
    """
    return HTMLResponse(html_report)


@router.post("/admin/cash/open")
async def web_open_shift(
    employee_id: int = Form(...),
    start_cash: Decimal = Form(...), 
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    try:
        await open_new_shift(session, employee_id, start_cash)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return RedirectResponse("/admin/cash", status_code=303)

@router.post("/admin/cash/transaction")
async def web_cash_transaction(
    shift_id: int = Form(...),
    transaction_type: str = Form(...),
    amount: Decimal = Form(...), 
    comment: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    await add_shift_transaction(session, shift_id, amount, transaction_type, comment)
    return RedirectResponse("/admin/cash", status_code=303)

@router.post("/admin/cash/close")
async def web_close_shift(
    shift_id: int = Form(...),
    end_cash_actual: Decimal = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    try:
        await close_active_shift(session, shift_id, end_cash_actual)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return RedirectResponse("/admin/cash/history", status_code=303)

# --- НОВИЙ МАРШРУТ: Ручне погашення боргу ---
@router.post("/admin/cash/manual_handover")
async def manual_handover_route(
    request: Request,
    employee_id: int = Form(...),
    shift_id: int = Form(...),
    amount: Decimal = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    employee = await session.get(Employee, employee_id)
    shift = await session.get(CashShift, shift_id)

    if not employee or not shift:
        raise HTTPException(status_code=404, detail="Співробітника або зміну не знайдено")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сума має бути більшою за нуль")

    if amount > employee.cash_balance:
        amount = employee.cash_balance  # Запобігаємо переплаті більше, ніж є борг

    # 1. Зменшуємо загальний борг працівника
    employee.cash_balance -= amount

    # 2. Записуємо історію балансу (якщо використовується)
    session.add(BalanceHistory(
        employee_id=employee.id,
        amount=-amount,
        new_balance=employee.cash_balance,
        reason="Ручне часткове/повне погашення боргу"
    ))

    # 3. Додаємо транзакцію в касову зміну (щоб зійшлася математика каси)
    session.add(CashTransaction(
        shift_id=shift.id,
        amount=amount,
        transaction_type='handover',
        comment=f"Ручне погашення боргу: {employee.full_name}"
    ))

    # 4. Жадібний алгоритм: намагаємося автоматично закрити найстаріші замовлення
    unpaid_orders_res = await session.execute(
        select(Order).where(
            Order.payment_method == 'cash',
            Order.is_cash_turned_in == False,
            or_(
                Order.courier_id == employee.id,
                Order.accepted_by_waiter_id == employee.id,
                Order.completed_by_courier_id == employee.id
            )
        ).order_by(Order.created_at)
    )
    unpaid_orders = unpaid_orders_res.scalars().all()

    remaining_amount = amount
    for order in unpaid_orders:
        if remaining_amount >= order.total_price:
            order.is_cash_turned_in = True
            remaining_amount -= order.total_price

    await session.commit()
    return RedirectResponse("/admin/cash", status_code=303)