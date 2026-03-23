# admin_inventory.py
import html
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import joinedload, selectinload

# Імпорт моделей
from inventory_models import (
    Ingredient, Unit, Warehouse, TechCard, TechCardItem, Stock, Supplier, 
    InventoryDoc, InventoryDocItem, Modifier, AutoDeductionRule,
    IngredientRecipeItem
)
# Додали Order в імпорт
from models import Product, Settings, Order
from dependencies import get_db_session, check_credentials
from templates import ADMIN_HTML_TEMPLATE
# Імпортуємо функції сервісу
from inventory_service import apply_doc_stock_changes, process_inventory_check
from cash_service import add_shift_transaction, get_any_open_shift

router = APIRouter(prefix="/admin/inventory", tags=["inventory"])

# --- СТИЛІ ТА КОМПОНЕНТИ ---

INVENTORY_STYLES = """
<style>
    :root { --inv-bg: #f8fafc; --inv-border: #e2e8f0; --inv-text: #334155; }
    
    /* Sub-navigation */
    .inv-nav { display: flex; gap: 8px; margin-bottom: 25px; background: #fff; padding: 8px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid var(--inv-border); overflow-x: auto; }
    .inv-nav a { padding: 10px 18px; border-radius: 8px; text-decoration: none; color: #64748b; font-weight: 600; font-size: 0.9rem; transition: all 0.2s; display: flex; align-items: center; gap: 8px; white-space: nowrap; }
    .inv-nav a:hover { background: #f1f5f9; color: #0f172a; }
    .inv-nav a.active { background: #333; color: #fff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    
    /* Stats Cards */
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 25px; }
    .stat-box { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid var(--inv-border); box-shadow: 0 1px 2px rgba(0,0,0,0.03); position: relative; overflow: hidden; }
    .stat-box h4 { margin: 0 0 8px 0; color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
    .stat-box .value { font-size: 2rem; font-weight: 800; color: #0f172a; line-height: 1; }
    .stat-box .icon { position: absolute; right: 20px; top: 20px; font-size: 2.5rem; opacity: 0.08; color: #333; }
    
    /* Modern Tables */
    .inv-table-wrapper { background: #fff; border-radius: 12px; border: 1px solid var(--inv-border); overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02); }
    .inv-table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
    .inv-table th { text-align: left; padding: 16px 20px; background: #f8fafc; color: #475569; font-weight: 600; border-bottom: 1px solid var(--inv-border); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .inv-table td { padding: 16px 20px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; color: #334155; }
    .inv-table tr:last-child td { border-bottom: none; }
    .inv-table tr:hover td { background: #f8fafc; }
    
    /* Badges */
    .inv-badge { padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; display: inline-flex; align-items: center; gap: 5px; line-height: 1.2; }
    .badge-green { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
    .badge-red { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
    .badge-blue { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-gray { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
    .badge-orange { background: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }

    /* Action Toolbar */
    .inv-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 15px; flex-wrap: wrap; }
    .search-input-wrapper { position: relative; width: 300px; }
    .search-input-wrapper i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #94a3b8; }
    .search-input { padding: 10px 10px 10px 38px; border: 1px solid var(--inv-border); border-radius: 8px; width: 100%; font-size: 0.95rem; transition: border-color 0.2s; }
    .search-input:focus { border-color: #333; outline: none; }
    
    /* Forms within cards */
    .inline-add-form { display: flex; gap: 10px; background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid var(--inv-border); align-items: center; margin-bottom: 20px; }
    .inline-add-form input, .inline-add-form select { margin-bottom: 0; background: #fff; }
    
    /* Doc View Specific */
    .doc-meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 20px; background: #f8fafc; border-radius: 10px; margin-bottom: 20px; border: 1px solid var(--inv-border); }
    .meta-item label { font-size: 0.8rem; color: #64748b; display: block; margin-bottom: 4px; text-transform: uppercase; font-weight: 600; }
    .meta-item div { font-size: 1.1rem; font-weight: 500; color: #0f172a; }
</style>
"""

def get_nav(active_tab):
    tabs = {
        "dashboard": {"icon": "fa-chart-pie", "label": "Дашборд"},
        "production": {"icon": "fa-fire-burner", "label": "Виробництво (П/Ф)"}, 
        "warehouses": {"icon": "fa-warehouse", "label": "Склади та Цеха"},
        "suppliers": {"icon": "fa-truck-field", "label": "Постачальники"},
        "ingredients": {"icon": "fa-carrot", "label": "Інгредієнти"},
        "modifiers": {"icon": "fa-layer-group", "label": "Модифікатори"},
        "stock": {"icon": "fa-boxes-stacked", "label": "Залишки"},
        "docs": {"icon": "fa-file-invoice", "label": "Накладні"},
        "checks": {"icon": "fa-clipboard-list", "label": "Інвентаризація"},
        "tech_cards": {"icon": "fa-book-open", "label": "Техкарти"},
        "reports/usage": {"icon": "fa-chart-line", "label": "Рух (Звіт)"},
        "reports/profitability": {"icon": "fa-money-bill-trend-up", "label": "Рентабельність"},
        "reports/suppliers": {"icon": "fa-file-invoice-dollar", "label": "Звіт по накладних"} 
    }
    # Підсвітка батьківської вкладки
    if active_tab == 'rules': active_tab = 'modifiers'
    
    html = f"{INVENTORY_STYLES}<div class='inv-nav'>"
    for k, v in tabs.items():
        cls = "active" if k == active_tab else ""
        html += f"<a href='/admin/inventory/{k}' class='{cls}'><i class='fa-solid {v['icon']}'></i> {v['label']}</a>"
    html += "</div>"
    return html

def get_active_classes():
    return {k: "active" if k == "inventory_active" else "" for k in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}

# --- DASHBOARD ---
@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def inv_dashboard(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    total_cost_res = await session.execute(
        select(func.sum(Stock.quantity * Ingredient.current_cost))
        .select_from(Stock)
        .join(Ingredient)
    )
    total_cost = total_cost_res.scalar() or 0
    
    low_stock = (await session.execute(
        select(Stock)
        .options(
            joinedload(Stock.ingredient).joinedload(Ingredient.unit),
            joinedload(Stock.warehouse)
        )
        .join(Ingredient)
        .where(Stock.quantity < 5, Stock.quantity > 0)
        .limit(5)
    )).scalars().all()
    
    docs_today = await session.scalar(select(func.count(InventoryDoc.id)).where(func.date(InventoryDoc.created_at) == datetime.now().date()))
    
    ls_rows = "".join([f"<tr><td>{s.ingredient.name}</td><td>{s.warehouse.name}</td><td style='color:#e11d48; font-weight:bold;'>{s.quantity:.2f} {s.ingredient.unit.name}</td></tr>" for s in low_stock])
    
    body = f"""
    {get_nav('dashboard')}
    <div class="stats-grid">
        <div class="stat-box">
            <i class="fa-solid fa-sack-dollar icon"></i>
            <h4>Вартість складу</h4>
            <div class="value">{total_cost:.2f} <small>грн</small></div>
        </div>
        <div class="stat-box">
            <i class="fa-solid fa-file-contract icon"></i>
            <h4>Документів за сьогодні</h4>
            <div class="value">{docs_today}</div>
        </div>
        <div class="stat-box">
            <i class="fa-solid fa-triangle-exclamation icon"></i>
            <h4>Мало на залишку</h4>
            <div class="value" style="color:#e11d48;">{len(low_stock)} <small>поз.</small></div>
        </div>
    </div>
    
    <div style="display:grid; grid-template-columns: 2fr 1fr; gap:20px;">
        <div class="card">
            <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                <h3 style="margin:0;">📉 Критичні залишки</h3>
                <a href="/admin/inventory/stock" class="button-sm secondary">Всі залишки</a>
            </div>
            <div class="inv-table-wrapper">
                <table class="inv-table">
                    <thead><tr><th>Товар</th><th>Склад</th><th>Залишок</th></tr></thead>
                    <tbody>{ls_rows or "<tr><td colspan='3' style='text-align:center; padding:20px; color:#999;'>Все в нормі ✅</td></tr>"}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <h3 style="margin-bottom:15px;">⚡️ Швидкі дії</h3>
            <div style="display:flex; flex-direction:column; gap:10px;">
                <a href="/admin/inventory/docs/create?type=supply" class="button" style="text-align:center; justify-content:center; padding:15px;"><i class="fa-solid fa-truck-ramp-box"></i> Створити Прихід</a>
                <a href="/admin/inventory/checks" class="button success" style="text-align:center; justify-content:center; padding:15px;"><i class="fa-solid fa-clipboard-check"></i> Інвентаризація</a>
                <a href="/admin/inventory/docs/create?type=writeoff" class="button danger" style="text-align:center; justify-content:center; padding:15px;"><i class="fa-solid fa-trash"></i> Створити Списання</a>
                <a href="/admin/inventory/reports/profitability" class="button secondary" style="text-align:center; justify-content:center;"><i class="fa-solid fa-money-bill-trend-up"></i> Перевірити ціни</a>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Огляд", body=body, site_title=settings.site_title, **get_active_classes()))

# --- WAREHOUSES (Склади та Цеха) ---
@router.get("/warehouses", response_class=HTMLResponse)
async def warehouses_list(
    error: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
    user=Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    
    warehouses = (await session.execute(
        select(Warehouse).options(joinedload(Warehouse.linked_warehouse)).order_by(Warehouse.name)
    )).scalars().all()
    
    all_storage_warehouses = (await session.execute(select(Warehouse).where(Warehouse.is_production == False))).scalars().all()
    storage_opts = "<option value=''>-- Без прив'язки --</option>" + "".join([f"<option value='{w.id}'>{w.name}</option>" for w in all_storage_warehouses])
    
    error_html = ""
    if error == "has_stock":
        error_html = """
        <div class='card' style='background:#fee2e2; color:#991b1b; border:1px solid #fecaca; margin-bottom:20px;'>
            ⚠️ <b>Помилка!</b> Неможливо видалити цей склад, оскільки на ньому є залишки товарів. Спочатку спишіть або перемістіть товари.
        </div>
        """

    rows = ""
    for w in warehouses:
        type_badge = "<span class='inv-badge badge-orange'>🍳 Цех (Виробництво)</span>" if w.is_production else "<span class='inv-badge badge-blue'>📦 Склад зберігання</span>"
        
        linked_info = ""
        if w.is_production and w.linked_warehouse:
            linked_info = f"<br><small style='color:#666;'><i class='fa-solid fa-link'></i> Списує з: <b>{w.linked_warehouse.name}</b></small>"
        
        count_res = await session.execute(select(func.count(Stock.id)).where(Stock.warehouse_id == w.id, Stock.quantity != 0))
        items_count = count_res.scalar() or 0

        rows += f"""
        <tr>
            <td><b>{html.escape(w.name)}</b></td>
            <td>{type_badge}{linked_info}</td>
            <td>{items_count} позицій</td>
            <td style="text-align:right;">
                <a href="/admin/inventory/warehouses/delete/{w.id}" class="button-sm danger" onclick="return confirm('Видалити склад? Всі залишки будуть втрачені!')"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>
        """
    
    body = f"""
    {get_nav('warehouses')}
    {error_html}
    <div class="card">
        <div class="inv-toolbar">
            <h3><i class="fa-solid fa-warehouse"></i> Склади та Цеха</h3>
        </div>
        
        <div style="background:#f0f9ff; padding:15px; border-radius:8px; border:1px solid #bae6fd; margin-bottom:20px; font-size:0.9rem;">
            <i class="fa-solid fa-info-circle"></i> 
            <b>Склад зберігання:</b> Використовується для прийому та зберігання товару.<br>
            <b>Цех (Виробництво):</b> Використовується для приготування. Можна прив'язати до "Складу зберігання", щоб продукти списувалися звідти автоматично.
        </div>
        
        <form action="/admin/inventory/warehouses/add" method="post" class="inline-add-form" style="flex-wrap:wrap;">
            <strong style="white-space:nowrap;">➕ Новий:</strong>
            <input type="text" name="name" placeholder="Назва (напр. Гарячий цех, Основний склад)" required style="flex:2;">
            
            <div style="display:flex; align-items:center; gap:10px; border:1px solid #ddd; padding:5px; border-radius:5px; background:white;">
                <div class="checkbox-group" style="margin:0;">
                    <input type="checkbox" id="is_prod" name="is_production" value="true" onchange="toggleStorageSelect(this)">
                    <label for="is_prod" style="font-weight:normal; font-size:0.9em; margin-bottom:0;">Це виробничий цех</label>
                </div>
                
                <div id="storage_select_div" style="display:none; border-left:1px solid #ccc; padding-left:10px;">
                    <small style="display:block; font-size:0.75rem; color:#666;">Списувати з:</small>
                    <select name="linked_warehouse_id" style="width:150px; margin-bottom:0;">{storage_opts}</select>
                </div>
            </div>
            
            <button type="submit" class="button">Додати</button>
        </form>
        
        <script>
        function toggleStorageSelect(cb) {{
            document.getElementById('storage_select_div').style.display = cb.checked ? 'block' : 'none';
        }}
        </script>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Назва</th><th>Тип / Прив'язка</th><th>Завантаженість</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='4' style='text-align:center; padding:20px;'>Складів ще немає</td></tr>"}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склади", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/warehouses/add")
async def add_warehouse(
    name: str = Form(...), 
    is_production: bool = Form(False), 
    linked_warehouse_id: int = Form(None),
    session: AsyncSession = Depends(get_db_session)
):
    linked_id = linked_warehouse_id if is_production else None
    
    session.add(Warehouse(
        name=name, 
        is_production=is_production,
        linked_warehouse_id=linked_id
    ))
    await session.commit()
    return RedirectResponse("/admin/inventory/warehouses", 303)

@router.get("/warehouses/delete/{w_id}")
async def delete_warehouse(w_id: int, session: AsyncSession = Depends(get_db_session)):
    w = await session.get(Warehouse, w_id)
    if w:
        stock_count = await session.scalar(select(func.count(Stock.id)).where(Stock.warehouse_id == w_id, Stock.quantity != 0))
        if stock_count > 0:
            return RedirectResponse("/admin/inventory/warehouses?error=has_stock", 303)
            
        await session.delete(w)
        await session.commit()
    return RedirectResponse("/admin/inventory/warehouses", 303)

# --- SUPPLIERS ---
@router.get("/suppliers", response_class=HTMLResponse)
async def suppliers_list(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    suppliers = (await session.execute(select(Supplier).order_by(Supplier.name))).scalars().all()
    
    rows = ""
    for s in suppliers:
        rows += f"""
        <tr>
            <td><b>{html.escape(s.name)}</b></td>
            <td>{html.escape(s.contact_person or '-')}</td>
            <td>{html.escape(s.phone or '-')}</td>
            <td>{html.escape(s.comment or '-')}</td>
            <td style="text-align:right;">
                <a href="#" class="button-sm secondary"><i class="fa-solid fa-pen"></i></a>
            </td>
        </tr>
        """
    
    body = f"""
    {get_nav('suppliers')}
    <div class="card">
        <div class="inv-toolbar">
            <h3><i class="fa-solid fa-truck-field"></i> Контрагенти</h3>
        </div>
        
        <form action="/admin/inventory/suppliers/add" method="post" class="inline-add-form">
            <strong style="white-space:nowrap;">➕ Новий:</strong>
            <input type="text" name="name" placeholder="Назва компанії" required style="flex:2;">
            <input type="text" name="contact_person" placeholder="Контактна особа" style="flex:1;">
            <input type="text" name="phone" placeholder="Телефон" style="flex:1;">
            <button type="submit" class="button">Додати</button>
        </form>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Назва</th><th>Контакт</th><th>Телефон</th><th>Коментар</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='5' style='text-align:center; padding:20px;'>Список порожній</td></tr>"}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Постачальники", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/suppliers/add")
async def add_supplier(name: str = Form(...), contact_person: str = Form(None), phone: str = Form(None), session: AsyncSession = Depends(get_db_session)):
    session.add(Supplier(name=name, contact_person=contact_person, phone=phone))
    await session.commit()
    return RedirectResponse("/admin/inventory/suppliers", 303)

# --- MODIFIERS ---
@router.get("/modifiers", response_class=HTMLResponse)
async def modifiers_list(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    mods = (await session.execute(
        select(Modifier)
        .options(joinedload(Modifier.ingredient).joinedload(Ingredient.unit), joinedload(Modifier.warehouse))
    )).scalars().all()
    
    ingredients = (await session.execute(select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name))).scalars().all()
    warehouses = (await session.execute(select(Warehouse).order_by(Warehouse.name))).scalars().all()
    
    ing_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in ingredients])
    wh_opts = "<option value=''>-- Як страва --</option>" + "".join([f"<option value='{w.id}'>{w.name}</option>" for w in warehouses])
    
    rows = ""
    for m in mods:
        wh_name = f"<span class='inv-badge badge-gray'>{m.warehouse.name}</span>" if m.warehouse else "<span class='inv-badge'>Як страва</span>"
        link_info = f"{m.ingredient_qty} {m.ingredient.unit.name} <b>{m.ingredient.name}</b>" if m.ingredient else "<span style='color:#ccc'>Без списання</span>"
        
        rows += f"""
        <tr>
            <td><b>{html.escape(m.name)}</b></td>
            <td>{m.price:.2f} грн</td>
            <td>{link_info}</td>
            <td>{wh_name}</td>
            <td style="text-align:right;"><a href="/admin/inventory/modifiers/delete/{m.id}" class="button-sm danger" onclick="return confirm('Видалити?')"><i class="fa-solid fa-trash"></i></a></td>
        </tr>
        """
        
    body = f"""
    {get_nav('modifiers')}
    <div class="card">
        <div class="inv-toolbar">
            <h3><i class="fa-solid fa-layer-group"></i> Модифікатори (Добавки)</h3>
        </div>
        
        <div style="background:#fff7ed; border:1px solid #ffedd5; color:#9a3412; padding:15px; border-radius:8px; margin-bottom:20px; font-size:0.9rem;">
            <i class="fa-solid fa-info-circle"></i> Модифікатори додаються до замовлення. Якщо вказано інгредієнт, він автоматично списується зі складу при продажу.
        </div>
        
        <form action="/admin/inventory/modifiers/add" method="post" class="inline-add-form" style="flex-wrap:wrap;">
            <strong style="width:100%; margin-bottom:10px;">➕ Додати модифікатор:</strong>
            <input type="text" name="name" placeholder="Назва (напр. Подвійний сир)" required style="flex:2; min-width:200px;">
            <input type="number" name="price" step="0.01" placeholder="Ціна (грн)" required style="width:100px;">
            
            <div style="display:flex; align-items:center; gap:5px; border-left:1px solid #ddd; padding-left:10px;">
                <small>Склад:</small>
                <select name="warehouse_id" style="width:140px;">{wh_opts}</select>
            </div>

            <div style="display:flex; align-items:center; gap:5px; border-left:1px solid #ddd; padding-left:10px;">
                <small>Сировина:</small>
                <select name="ingredient_id" style="width:150px;"><option value="">- Не списувати -</option>{ing_opts}</select>
                <input type="number" name="ingredient_qty" step="0.001" placeholder="К-сть" style="width:80px;">
            </div>
            <button type="submit" class="button">OK</button>
        </form>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Назва добавки</th><th>Ціна продажу</th><th>Списання (Інгредієнт)</th><th>Склад списання</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='5' style='text-align:center; padding:20px;'>Немає модифікаторів</td></tr>"}</tbody>
            </table>
        </div>
    </div>

    <div class="card" style="margin-top:30px; border-top: 4px solid #f59e0b;">
        <h3 style="margin-bottom:10px;"><i class="fa-solid fa-box-open"></i> Авто-списання упаковки</h3>
        <p style="color:#666; font-size:0.9rem; margin-bottom:15px;">Налаштуйте, що списувати автоматично при кожному замовленні (пакети, серветки).</p>
        
        <div id="packaging-rules-container">
            <a href="/admin/inventory/rules" class="button secondary">Налаштувати правила упаковки</a>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Модифікатори", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/modifiers/add")
async def add_modifier(
    name: str = Form(...), price: float = Form(...), 
    ingredient_id: int = Form(None), ingredient_qty: float = Form(0),
    warehouse_id: int = Form(None),
    session: AsyncSession = Depends(get_db_session)
):
    session.add(Modifier(
        name=name, price=price, 
        ingredient_id=ingredient_id, ingredient_qty=ingredient_qty,
        warehouse_id=warehouse_id
    ))
    await session.commit()
    return RedirectResponse("/admin/inventory/modifiers", 303)

@router.get("/modifiers/delete/{mod_id}")
async def delete_modifier(mod_id: int, session: AsyncSession = Depends(get_db_session)):
    mod = await session.get(Modifier, mod_id)
    if mod:
        await session.delete(mod)
        await session.commit()
    return RedirectResponse("/admin/inventory/modifiers", 303)

# --- PACKAGING RULES (RULES) ---
@router.get("/rules", response_class=HTMLResponse)
async def rules_list(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    rules = (await session.execute(
        select(AutoDeductionRule)
        .options(joinedload(AutoDeductionRule.ingredient).joinedload(Ingredient.unit), joinedload(AutoDeductionRule.warehouse))
    )).scalars().all()
    
    ingredients = (await session.execute(select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name))).scalars().all()
    warehouses = (await session.execute(select(Warehouse).order_by(Warehouse.name))).scalars().all()
    
    ing_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in ingredients])
    wh_opts = "".join([f"<option value='{w.id}'>{w.name}</option>" for w in warehouses])
    
    rows = ""
    for r in rules:
        trigger_badges = {
            'delivery': '<span class="inv-badge badge-blue"><i class="fa-solid fa-truck"></i> Доставка</span>',
            'pickup': '<span class="inv-badge badge-orange"><i class="fa-solid fa-person-walking"></i> Самовивіз</span>',
            'in_house': '<span class="inv-badge badge-green"><i class="fa-solid fa-utensils"></i> В закладі</span>',
            'all': '<span class="inv-badge badge-gray">Всі типи</span>',
        }
        badge = trigger_badges.get(r.trigger_type, r.trigger_type)
        
        rows += f"""
        <tr>
            <td>{badge}</td>
            <td>{r.ingredient.name}</td>
            <td>{r.quantity} {r.ingredient.unit.name}</td>
            <td>{r.warehouse.name}</td>
            <td style="text-align:right;"><a href="/admin/inventory/rules/delete/{r.id}" class="button-sm danger"><i class="fa-solid fa-trash"></i></a></td>
        </tr>
        """
        
    body = f"""
    {get_nav('rules')} 
    
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h3><i class="fa-solid fa-box-open"></i> Правила списання упаковки</h3>
            <a href="/admin/inventory/modifiers" class="button secondary">Назад</a>
        </div>
        
        <form action="/admin/inventory/rules/add" method="post" class="inline-add-form" style="align-items:flex-end;">
            <div style="flex:1;">
                <label style="font-size:0.8rem; font-weight:bold;">Коли списувати:</label>
                <select name="trigger_type" style="width:100%;">
                    <option value="delivery">Тільки Доставка</option>
                    <option value="pickup">Тільки Самовивіз</option>
                    <option value="in_house">Тільки В закладі</option>
                    <option value="all">Завжди (Будь-яке замовлення)</option>
                </select>
            </div>
            <div style="flex:2;">
                <label style="font-size:0.8rem; font-weight:bold;">Що списувати (Матеріал):</label>
                <select name="ingredient_id" style="width:100%;">{ing_opts}</select>
            </div>
            <div style="width:100px;">
                <label style="font-size:0.8rem; font-weight:bold;">К-сть:</label>
                <input type="number" name="quantity" step="0.001" value="1" style="width:100%;">
            </div>
            <div style="flex:1;">
                <label style="font-size:0.8rem; font-weight:bold;">Зі складу:</label>
                <select name="warehouse_id" style="width:100%;">{wh_opts}</select>
            </div>
            <button type="submit" class="button" style="margin-bottom:0; height:42px;">Додати</button>
        </form>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Умова</th><th>Матеріал</th><th>Кількість на замовлення</th><th>Склад</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='5' style='text-align:center; padding:20px;'>Правил немає</td></tr>"}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Упаковка", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/rules/add")
async def add_rule(
    trigger_type: str = Form(...), ingredient_id: int = Form(...), 
    quantity: float = Form(...), warehouse_id: int = Form(...), 
    session: AsyncSession = Depends(get_db_session)
):
    session.add(AutoDeductionRule(
        trigger_type=trigger_type, ingredient_id=ingredient_id,
        quantity=quantity, warehouse_id=warehouse_id
    ))
    await session.commit()
    return RedirectResponse("/admin/inventory/rules", 303)

@router.get("/rules/delete/{r_id}")
async def delete_rule(r_id: int, session: AsyncSession = Depends(get_db_session)):
    r = await session.get(AutoDeductionRule, r_id)
    if r:
        await session.delete(r)
        await session.commit()
    return RedirectResponse("/admin/inventory/rules", 303)

# --- INGREDIENTS ---
@router.get("/ingredients", response_class=HTMLResponse)
async def ingredients_page(q: str = Query(None), session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    query = select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name)
    if q: query = query.where(Ingredient.name.ilike(f"%{q}%"))
    ingredients = (await session.execute(query)).scalars().all()
    units = (await session.execute(select(Unit))).scalars().all()
    
    unit_opts = "".join([f"<option value='{u.id}'>{u.name}</option>" for u in units])
    
    rows = ""
    for i in ingredients:
        pf_badge = "<span class='inv-badge badge-orange'>П/Ф</span>" if i.is_semi_finished else ""
        
        # Кнопка рецепта тільки для П/Ф
        recipe_btn = ""
        if i.is_semi_finished:
            recipe_btn = f"<a href='/admin/inventory/ingredients/{i.id}/recipe' class='button-sm' style='margin-right:5px;' title='Склад рецепту'><i class='fa-solid fa-list'></i> Рецепт</a>"
            
        rows += f"""
        <tr>
            <td>{i.id}</td>
            <td><b>{html.escape(i.name)}</b> {pf_badge}</td>
            <td>{i.unit.name}</td>
            <td>{i.current_cost:.2f} грн</td>
            <td style='text-align:right;'>
                {recipe_btn}
                <button class='button-sm secondary'><i class='fa-solid fa-pen'></i></button>
            </td>
        </tr>
        """
    
    body = f"""
    {get_nav('ingredients')}
    <div class="card">
        <div class="inv-toolbar">
            <form action="" method="get" class="search-input-wrapper">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" name="search" class="search-input" placeholder="Пошук сировини..." value="{q or ''}">
            </form>
        </div>
        
        <form action="/admin/inventory/ingredients/add" method="post" class="inline-add-form" style="align-items:center;">
            <strong style="white-space:nowrap;">🥬 Новий:</strong>
            <input type="text" name="name" placeholder="Назва (напр. Тісто, Картопля)" required style="flex:1;">
            <select name="unit_id" style="width:100px;">{unit_opts}</select>
            
            <div class="checkbox-group" style="margin:0 10px; background:white; padding:5px 10px; border:1px solid #ddd; border-radius:5px;">
                <input type="checkbox" id="is_pf" name="is_semi_finished" value="true">
                <label for="is_pf" style="margin:0; font-size:0.9em; cursor:pointer;">Це напівфабрикат</label>
            </div>
            
            <button type="submit" class="button">Створити</button>
        </form>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>ID</th><th>Назва</th><th>Од. вим.</th><th>Собівартість</th><th></th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Інгредієнти", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/ingredients/add")
async def add_ing(
    name: str = Form(...), 
    unit_id: int = Form(...), 
    is_semi_finished: bool = Form(False), 
    session: AsyncSession = Depends(get_db_session)
):
    session.add(Ingredient(name=name, unit_id=unit_id, is_semi_finished=is_semi_finished))
    await session.commit()
    return RedirectResponse("/admin/inventory/ingredients", 303)

# --- РЕДАКТИРОВАНИЕ РЕЦЕПТА ПОЛУФАБРИКАТА ---
@router.get("/ingredients/{pf_id}/recipe", response_class=HTMLResponse)
async def edit_pf_recipe(pf_id: int, session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    pf = await session.get(Ingredient, pf_id, options=[
        joinedload(Ingredient.recipe_components).joinedload(IngredientRecipeItem.child_ingredient).joinedload(Ingredient.unit),
        joinedload(Ingredient.unit)
    ])
    
    if not pf or not pf.is_semi_finished:
        return HTMLResponse("Не є напівфабрикатом")

    # Список сировини для додавання (виключаючи самого себе, щоб уникнути циклів)
    all_ing = (await session.execute(select(Ingredient).where(Ingredient.id != pf_id).order_by(Ingredient.name))).scalars().all()
    ing_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in all_ing])

    rows = ""
    total_cost_per_unit = 0
    
    # Розрахунок вартості рецепта на 1 одиницю П/Ф
    for item in pf.recipe_components:
        cost = float(item.gross_amount) * float(item.child_ingredient.current_cost or 0)
        total_cost_per_unit += cost
        
        raw_price = float(item.child_ingredient.current_cost or 0)
        
        rows += f"""
        <tr>
            <td>{item.child_ingredient.name}</td>
            <td>{float(item.gross_amount)} {item.child_ingredient.unit.name}</td>
            <td>{raw_price:.2f} грн</td>
            <td>{cost:.2f} грн</td>
            <td style="text-align:right;"><a href="/admin/inventory/ingredients/recipe/del/{item.id}" style="color:red;">X</a></td>
        </tr>
        """

    body = f"""
    {get_nav('ingredients')}
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <div>
                <h2>🥣 Рецепт: {pf.name}</h2>
                <div style="color:#666;">Розрахунок на <b>1 {pf.unit.name}</b> готового продукту</div>
            </div>
            <a href="/admin/inventory/ingredients" class="button secondary">Назад</a>
        </div>
        
        <div style="margin-bottom:20px; padding:15px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px;">
            <strong>Розрахункова собівартість:</strong> {total_cost_per_unit:.2f} грн / {pf.unit.name}
        </div>

        <form action="/admin/inventory/ingredients/{pf.id}/recipe/add" method="post" class="inline-add-form">
            <strong>➕ Додати складову:</strong>
            <select name="child_id" required style="width:200px;">{ing_opts}</select>
            <input type="number" step="0.001" name="gross" placeholder="Кількість (Брутто)" required style="width:120px;">
            <button type="submit" class="button">Додати</button>
        </form>

        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Сировина</th><th>Кількість (на 1 од. П/Ф)</th><th>Ціна сировини</th><th>Вартість в П/Ф</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='5' style='text-align:center;'>Рецепт порожній</td></tr>"}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title=f"Рецепт {pf.name}", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/ingredients/{pf_id}/recipe/add")
async def add_pf_component(pf_id: int, child_id: int = Form(...), gross: float = Form(...), session: AsyncSession = Depends(get_db_session)):
    session.add(IngredientRecipeItem(parent_ingredient_id=pf_id, child_ingredient_id=child_id, gross_amount=gross))
    await session.commit()
    return RedirectResponse(f"/admin/inventory/ingredients/{pf_id}/recipe", 303)

@router.get("/ingredients/recipe/del/{item_id}")
async def del_pf_component(item_id: int, session: AsyncSession = Depends(get_db_session)):
    item = await session.get(IngredientRecipeItem, item_id)
    if item:
        pf_id = item.parent_ingredient_id
        await session.delete(item)
        await session.commit()
        return RedirectResponse(f"/admin/inventory/ingredients/{pf_id}/recipe", 303)
    return RedirectResponse("/admin/inventory/ingredients", 303)

# --- STOCK ---
@router.get("/stock", response_class=HTMLResponse)
async def stock_page(warehouse_id: int = Query(None), session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    warehouses = (await session.execute(select(Warehouse))).scalars().all()
    
    query = select(Stock).options(joinedload(Stock.warehouse), joinedload(Stock.ingredient).joinedload(Ingredient.unit))
    if warehouse_id: query = query.where(Stock.warehouse_id == warehouse_id)
    stocks = (await session.execute(query.order_by(Stock.warehouse_id))).scalars().all()
    
    wh_links = f"<a href='/admin/inventory/stock' class='{'active' if not warehouse_id else ''}' style='margin-right:10px; font-weight:bold;'>Всі</a>"
    for w in warehouses:
        cls = "active" if warehouse_id == w.id else ""
        wh_links += f"<a href='/admin/inventory/stock?warehouse_id={w.id}' class='{cls}' style='margin-right:10px; text-decoration:none; color:#333; padding:5px 10px; border-radius:5px; background:#eee;'>{w.name}</a>"
    
    rows = ""
    total_val = 0
    for s in stocks:
        val = float(s.quantity) * float(s.ingredient.current_cost)
        total_val += val
        qty_style = "color:#ef4444; font-weight:bold;" if s.quantity < 0 else "color:#0f172a; font-weight:bold;"
        rows += f"<tr><td>{s.warehouse.name}</td><td>{s.ingredient.name}</td><td style='{qty_style}'>{s.quantity:.3f} {s.ingredient.unit.name}</td><td>{s.ingredient.current_cost:.2f}</td><td>{val:.2f} грн</td></tr>"
        
    body = f"""
    {get_nav('stock')}
    <div class="card">
        <div style="margin-bottom:20px; border-bottom:1px solid #eee; padding-bottom:10px;">{wh_links}</div>
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Склад</th><th>Товар</th><th>Залишок</th><th>Ціна</th><th>Сума</th></tr></thead>
                <tbody>{rows}</tbody>
                <tfoot><tr style="background:#f8fafc; font-weight:bold;"><td colspan="4" style="text-align:right;">Загальна вартість:</td><td>{total_val:.2f} грн</td></tr></tfoot>
            </table>
        </div>
    </div>
    <style>a.active {{ background: #333 !important; color: #fff !important; }}</style>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Залишки", body=body, site_title=settings.site_title, **get_active_classes()))

# --- ІНВЕНТАРИЗАЦІЯ (CHECKS) ---
@router.get("/checks", response_class=HTMLResponse)
async def inventory_checks_list(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    query = select(InventoryDoc).options(joinedload(InventoryDoc.source_warehouse))\
        .where(InventoryDoc.doc_type == 'inventory')\
        .order_by(desc(InventoryDoc.created_at))
    
    docs = (await session.execute(query)).scalars().all()
    
    rows = ""
    for d in docs:
        status = "<span class='inv-badge badge-green'>Проведено</span>" if d.is_processed else "<span class='inv-badge badge-orange'>В роботі</span>"
        wh_name = d.source_warehouse.name if d.source_warehouse else '-'
        
        rows += f"""
        <tr onclick="window.location='/admin/inventory/checks/{d.id}'" style="cursor:pointer;">
            <td><b>#{d.id}</b></td>
            <td>{d.created_at.strftime('%d.%m.%Y %H:%M')}</td>
            <td>{html.escape(wh_name)}</td>
            <td>{html.escape(d.comment or '-')}</td>
            <td>{status}</td>
            <td style="text-align:right; color:#94a3b8;"><i class="fa-solid fa-chevron-right"></i></td>
        </tr>
        """
    
    warehouses = (await session.execute(select(Warehouse).order_by(Warehouse.name))).scalars().all()
    wh_opts = "".join([f"<option value='{w.id}'>{w.name}</option>" for w in warehouses])

    body = f"""
    {get_nav('checks')}
    
    <div class="card">
        <div class="inv-toolbar">
            <h3><i class="fa-solid fa-clipboard-list"></i> Акти інвентаризації</h3>
            <button onclick="document.getElementById('new-inv-modal').classList.add('active')" class="button"><i class="fa-solid fa-plus"></i> Почати інвентаризацію</button>
        </div>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>ID</th><th>Дата</th><th>Склад</th><th>Коментар</th><th>Статус</th><th></th></tr></thead>
                <tbody>{rows or "<tr><td colspan='6' style='text-align:center; padding:30px; color:#999;'>Актів ще немає</td></tr>"}</tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="new-inv-modal">
        <div class="modal">
            <div class="modal-header">
                <h4>Нова інвентаризація</h4>
                <button type="button" class="close-button" onclick="document.getElementById('new-inv-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/inventory/checks/create" method="post">
                    <label>Оберіть склад для перевірки:</label>
                    <select name="warehouse_id" required style="width:100%; padding:10px; margin-bottom:15px;">
                        {wh_opts}
                    </select>
                    
                    <label>Коментар:</label>
                    <input type="text" name="comment" placeholder="Наприклад: Планова ревізія" style="width:100%; margin-bottom:15px;">
                    
                    <div style="background:#f0f9ff; padding:10px; border-radius:5px; margin-bottom:15px; font-size:0.9rem;">
                        <i class="fa-solid fa-info-circle"></i> Буде створено список усіх інгредієнтів. Поточні залишки будуть зафіксовані в момент проведення акту.
                    </div>
                    
                    <button type="submit" class="button" style="width:100%;">Створити бланк</button>
                </form>
            </div>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Інвентаризація", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/checks/create")
async def create_inventory_check(
    warehouse_id: int = Form(...), 
    comment: str = Form(None),
    session: AsyncSession = Depends(get_db_session)
):
    doc = InventoryDoc(
        doc_type='inventory',
        source_warehouse_id=warehouse_id, 
        comment=comment,
        is_processed=False
    )
    session.add(doc)
    await session.flush()
    
    # Додаємо всі інгредієнти
    all_ingredients = (await session.execute(select(Ingredient))).scalars().all()
    
    for ing in all_ingredients:
        item = InventoryDocItem(
            doc_id=doc.id,
            ingredient_id=ing.id,
            quantity=0, 
            price=0
        )
        session.add(item)
    
    await session.commit()
    return RedirectResponse(f"/admin/inventory/checks/{doc.id}", 303)

@router.get("/checks/{doc_id}", response_class=HTMLResponse)
async def view_inventory_check(
    doc_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    user=Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    
    doc = await session.get(InventoryDoc, doc_id, options=[
        joinedload(InventoryDoc.items).joinedload(InventoryDocItem.ingredient).joinedload(Ingredient.unit),
        joinedload(InventoryDoc.source_warehouse)
    ])
    if not doc: return HTMLResponse("Документ не знайдено")

    doc.items.sort(key=lambda x: x.ingredient.name)

    rows = ""
    # Для підрахунку в режимі перегляду
    total_diff_money_plus = 0
    total_diff_money_minus = 0

    for item in doc.items:
        system_qty_display = "-"
        diff_display = "-"
        current_stock_val = 0
        
        cost = float(item.ingredient.current_cost or 0)

        if not doc.is_processed:
            # Чернетка - показуємо актуальний залишок
            current_stock = await session.scalar(
                select(Stock.quantity).where(
                    Stock.warehouse_id == doc.source_warehouse_id, 
                    Stock.ingredient_id == item.ingredient_id
                )
            ) or 0
            current_stock_val = float(current_stock)
            system_qty_display = f"{current_stock_val:.3f}"
            
            input_field = f"""
            <input type="number" step="0.001" name="qty_{item.id}" 
                   value="{float(item.quantity)}" 
                   class="inv-qty-input"
                   data-system="{current_stock_val}"
                   data-cost="{cost}"
                   style="width:100px; padding:5px; border:1px solid #ccc; border-radius:4px; text-align:center; font-weight:bold;">
            """
            
            diff_display = f"<span class='diff-cell' data-id='{item.id}'>0</span>"
            
        else:
            # Проведено
            input_field = f"<b>{float(item.quantity)}</b>"
            diff_display = "-" 
            system_qty_display = "Архів"

        rows += f"""
        <tr class="inv-row">
            <td class="name-cell">{html.escape(item.ingredient.name)}</td>
            <td>{item.ingredient.unit.name}</td>
            <td style="background:#f9f9f9; color:#555;">{system_qty_display}</td>
            <td>{input_field}</td>
            <td>{diff_display}</td>
        </tr>
        """

    controls = ""
    js_script = ""
    
    if not doc.is_processed:
        controls = f"""
        <div style="margin-bottom:20px;">
            <div style="background:#fff7ed; border:1px solid #ffedd5; padding:15px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:15px;">
                <div>
                    <strong style="color:#c2410c;">⚠️ Режим редагування</strong>
                    <p style="margin:5px 0 0; font-size:0.9rem; color:#666;">Введіть фактичну кількість.</p>
                </div>
                
                <div style="display:flex; gap:20px; align-items:center;">
                    <div style="text-align:right; font-size:0.9rem;">
                        <div>Надлишок: <b style="color:green" id="total-plus">0.00</b> грн</div>
                        <div>Нестача: <b style="color:red" id="total-minus">0.00</b> грн</div>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <button type="button" onclick="fillSystemValues()" class="button-sm secondary" title="Встановити Факт = Системний для всіх">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Авто-заповнення
                        </button>
                        <button type="submit" form="inv-form" name="action" value="save" class="button secondary">
                            <i class="fa-solid fa-floppy-disk"></i> Зберегти
                        </button>
                        <button type="submit" form="inv-form" name="action" value="approve" class="button success" onclick="return confirm('Завершити інвентаризацію? Створяться документи списання/оприходування.')">
                            <i class="fa-solid fa-check-double"></i> ПРОВЕСТИ
                        </button>
                    </div>
                </div>
            </div>
            
            <div style="margin-top:10px; position:relative;">
                <i class="fa-solid fa-search" style="position:absolute; left:12px; top:12px; color:#999;"></i>
                <input type="text" id="inv-search" onkeyup="filterTable()" placeholder="Швидкий пошук інгредієнта..." 
                       style="width:100%; padding:10px 10px 10px 35px; border:1px solid #ccc; border-radius:6px;">
            </div>
        </div>
        """
        
        js_script = """
        <script>
            // Живий пошук
            function filterTable() {
                const input = document.getElementById('inv-search');
                const filter = input.value.toLowerCase();
                const rows = document.getElementsByClassName('inv-row');

                for (let i = 0; i < rows.length; i++) {
                    const nameCell = rows[i].getElementsByClassName('name-cell')[0];
                    if (nameCell) {
                        const txtValue = nameCell.textContent || nameCell.innerText;
                        rows[i].style.display = txtValue.toLowerCase().indexOf(filter) > -1 ? "" : "none";
                    }
                }
            }

            // Авто-заповнення (Факт = Система)
            function fillSystemValues() {
                if(!confirm("Заповнити всі поля 'Факт' системними значеннями? Це зітре введені дані.")) return;
                
                const inputs = document.querySelectorAll('.inv-qty-input');
                inputs.forEach(inp => {
                    inp.value = inp.dataset.system;
                });
                recalcTotals();
            }

            // Перерахунок різниці та підсумків
            function recalcTotals() {
                let totalPlus = 0;
                let totalMinus = 0;
                
                const inputs = document.querySelectorAll('.inv-qty-input');
                inputs.forEach(inp => {
                    const fact = parseFloat(inp.value) || 0;
                    const sys = parseFloat(inp.dataset.system) || 0;
                    const cost = parseFloat(inp.dataset.cost) || 0;
                    const diff = fact - sys;
                    
                    // Знаходимо комірку різниці
                    const row = inp.closest('tr');
                    const diffCell = row.querySelector('.diff-cell');
                    
                    if(diffCell) {
                        let diffHtml = diff.toFixed(3);
                        if(diff > 0) {
                            diffCell.innerHTML = `<span style='color:green'>+${diffHtml}</span>`;
                            totalPlus += diff * cost;
                        } else if (diff < 0) {
                            diffCell.innerHTML = `<span style='color:red'>${diffHtml}</span>`;
                            totalMinus += Math.abs(diff) * cost;
                        } else {
                            diffCell.innerHTML = `<span style='color:#ccc'>0</span>`;
                        }
                    }
                });
                
                document.getElementById('total-plus').innerText = totalPlus.toFixed(2);
                document.getElementById('total-minus').innerText = totalMinus.toFixed(2);
            }

            // Слухаємо зміни
            document.addEventListener('DOMContentLoaded', () => {
                const inputs = document.querySelectorAll('.inv-qty-input');
                inputs.forEach(inp => {
                    inp.addEventListener('input', recalcTotals);
                });
                recalcTotals(); // Initial calc
            });
        </script>
        """
    else:
        controls = """
        <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:15px; border-radius:8px; margin-bottom:20px; text-align:center; color:#15803d; font-weight:bold;">
            <i class="fa-solid fa-lock"></i> Інвентаризацію завершено. Документи коригування створено.
        </div>
        """

    body = f"""
    {get_nav('checks')}
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2><i class="fa-solid fa-list-ol"></i> Акт інвентаризації #{doc.id}</h2>
            <a href="/admin/inventory/checks" class="button secondary">Назад</a>
        </div>
        
        <div class="doc-meta">
            <div class="meta-item"><label>Склад:</label> <div>{html.escape(doc.source_warehouse.name)}</div></div>
            <div class="meta-item"><label>Дата створення:</label> <div>{doc.created_at.strftime('%d.%m.%Y %H:%M')}</div></div>
            <div class="meta-item"><label>Коментар:</label> <div>{html.escape(doc.comment or '-')}</div></div>
        </div>
        
        {controls}
        
        <form id="inv-form" action="/admin/inventory/checks/{doc.id}/update" method="post">
            <div class="inv-table-wrapper">
                <table class="inv-table">
                    <thead>
                        <tr>
                            <th>Товар</th>
                            <th>Од. вим.</th>
                            <th title="Залишок у програмі на даний момент">Системний</th>
                            <th title="Скільки реально на полиці" style="width:150px;">ФАКТ (Ввести)</th>
                            <th>Різниця</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </form>
    </div>
    {js_script}
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title=f"Ревізія #{doc.id}", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/checks/{doc_id}/update")
async def update_inventory_check(
    doc_id: int, 
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    form_data = await request.form()
    action = form_data.get("action")
    
    doc = await session.get(InventoryDoc, doc_id, options=[selectinload(InventoryDoc.items)])
    if not doc or doc.is_processed:
        raise HTTPException(400, "Документ не знайдено або вже закрито")

    # Оновлюємо кількості
    for key, value in form_data.items():
        if key.startswith("qty_"):
            try:
                item_id = int(key.split("_")[1])
                qty = float(value)
                for item in doc.items:
                    if item.id == item_id:
                        item.quantity = qty
                        break
            except ValueError:
                continue
    
    await session.commit()
    
    if action == "approve":
        try:
            await process_inventory_check(session, doc.id)
        except ValueError as e:
            raise HTTPException(400, str(e))
            
    return RedirectResponse(f"/admin/inventory/checks/{doc.id}", 303)

# --- DOCS ---
@router.get("/docs", response_class=HTMLResponse)
async def docs_page(type: str = Query(None), session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    query = select(InventoryDoc).options(joinedload(InventoryDoc.supplier), joinedload(InventoryDoc.source_warehouse), joinedload(InventoryDoc.target_warehouse)).order_by(desc(InventoryDoc.created_at))
    if type: query = query.where(InventoryDoc.doc_type == type)
    docs = (await session.execute(query)).scalars().all()
    
    rows = ""
    for d in docs:
        badges = {
            'supply': ('📥 Прихід', 'badge-green'),
            'writeoff': ('🗑️ Списання', 'badge-red'),
            'transfer': ('🔄 Переміщення', 'badge-blue'),
            'deduction': ('🤖 Авто-списання', 'badge-gray'),
            'inventory': ('📝 Інвентаризація', 'badge-orange')
        }
        lbl, cls = badges.get(d.doc_type, (d.doc_type, ''))
        status = "<span class='inv-badge badge-green'>Проведено</span>" if d.is_processed else "<span class='inv-badge badge-orange'>Чернетка</span>"
        
        desc_txt = ""
        paid_info = ""

        # --- ПОКРАЩЕНА ЛОГІКА ВІДОБРАЖЕННЯ ТИПУ ---
        if d.doc_type == 'supply': 
            if d.supplier:
                # Звичайна зовнішня поставка
                desc_txt = f"<b>{html.escape(d.supplier.name)}</b> ➔ {d.target_warehouse.name if d.target_warehouse else '?'}"
                if d.paid_amount > 0:
                    paid_info = f"<br><span style='font-size:0.75rem; color:#15803d;'>💸 Сплачено: {d.paid_amount}</span>"
            else:
                # Внутрішнє виробництво (П/Ф) - виділяємо це!
                lbl = "🍳 Виробництво"
                cls = "badge-orange" # Помаранчевий бейдж
                desc_txt = f"На склад: <b>{d.target_warehouse.name if d.target_warehouse else '?'}</b>"
                paid_info = "<br><span style='font-size:0.75rem; color:#666;'>Внутрішній акт</span>"

        elif d.doc_type == 'writeoff': 
            desc_txt = f"Зі складу: {d.source_warehouse.name if d.source_warehouse else '?'}"
        elif d.doc_type == 'transfer': 
            desc_txt = f"{d.source_warehouse.name if d.source_warehouse else '?'} ➔ {d.target_warehouse.name if d.target_warehouse else '?'}"
        elif d.doc_type == 'inventory': 
            desc_txt = f"Склад: {d.source_warehouse.name if d.source_warehouse else '?'}"
        
        # Посилання
        link = f"/admin/inventory/docs/{d.id}"
        if d.doc_type == 'inventory':
            link = f"/admin/inventory/checks/{d.id}"

        rows += f"""
        <tr onclick="window.location='{link}'" style="cursor:pointer;">
            <td><b>#{d.id}</b></td>
            <td>{d.created_at.strftime('%d.%m %H:%M')}</td>
            <td><span class='inv-badge {cls}'>{lbl}</span></td>
            <td>{desc_txt} {paid_info}</td>
            <td>{html.escape(d.comment or '')}</td>
            <td>{status}</td>
            <td style="text-align:right; color:#94a3b8;"><i class="fa-solid fa-chevron-right"></i></td>
        </tr>
        """
        
    filter_btns = f"""
    <div style="display:flex; gap:10px; margin-bottom:10px;">
        <a href="/admin/inventory/docs" class="button-sm {'secondary' if type else ''}">Всі</a>
        <a href="/admin/inventory/docs?type=supply" class="button-sm {'secondary' if type!='supply' else ''}">Прихід / Виробництво</a>
        <a href="/admin/inventory/docs?type=writeoff" class="button-sm {'secondary' if type!='writeoff' else ''}">Списання</a>
        <a href="/admin/inventory/docs?type=transfer" class="button-sm {'secondary' if type!='transfer' else ''}">Переміщення</a>
    </div>
    """
        
    body = f"""
    {get_nav('docs')}
    <div class="card">
        <div class="inv-toolbar">
            <h3>Журнал документів</h3>
            <a href="/admin/inventory/docs/create" class="button"><i class="fa-solid fa-plus"></i> Створити</a>
        </div>
        {filter_btns}
        <div class="table-wrapper">
            <table class="inv-table">
                <thead><tr><th>ID</th><th>Дата</th><th>Тип</th><th>Деталі</th><th>Коментар</th><th>Статус</th><th></th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Склад: Накладні", body=body, site_title=settings.site_title, **get_active_classes()))

@router.get("/docs/create", response_class=HTMLResponse)
async def create_doc_page(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    warehouses = (await session.execute(select(Warehouse))).scalars().all()
    suppliers = (await session.execute(select(Supplier))).scalars().all()
    
    wh_opts = "".join([f"<option value='{w.id}'>{w.name}</option>" for w in warehouses])
    sup_opts = "".join([f"<option value='{s.id}'>{s.name}</option>" for s in suppliers])
    
    body = f"""
    {get_nav('docs')}
    <div class="card" style="max-width:600px; margin:0 auto;">
        <h2 style="margin-bottom:20px;"><i class="fa-solid fa-file-circle-plus"></i> Створення документа</h2>
        <form action="/admin/inventory/docs/create" method="post">
            <div style="margin-bottom:15px;">
                <label>Тип операції</label>
                <div class="radio-group" style="display:flex; gap:10px;">
                    <label style="flex:1; padding:10px; border:1px solid #ddd; border-radius:5px; text-align:center; cursor:pointer;">
                        <input type="radio" name="doc_type" value="supply" checked onclick="toggleFields()"> 📥 Прихід
                    </label>
                    <label style="flex:1; padding:10px; border:1px solid #ddd; border-radius:5px; text-align:center; cursor:pointer;">
                        <input type="radio" name="doc_type" value="writeoff" onclick="toggleFields()"> 🗑️ Списання
                    </label>
                    <label style="flex:1; padding:10px; border:1px solid #ddd; border-radius:5px; text-align:center; cursor:pointer;">
                        <input type="radio" name="doc_type" value="transfer" onclick="toggleFields()"> 🔄 Переміщ.
                    </label>
                </div>
            </div>
            
            <div id="supplier_div">
                <label>Постачальник:</label>
                <select name="supplier_id"><option value="">Оберіть...</option>{sup_opts}</select>
            </div>
            
            <div id="source_wh_div" style="display:none;">
                <label>Склад ЗВІДКИ (Списання/Переміщення):</label>
                <select name="source_warehouse_id"><option value="">Оберіть...</option>{wh_opts}</select>
            </div>
            
            <div id="target_wh_div">
                <label>Склад КУДИ (Зарахування/Переміщення):</label>
                <select name="target_warehouse_id"><option value="">Оберіть...</option>{wh_opts}</select>
            </div>
            
            <label>Коментар:</label>
            <input type="text" name="comment" placeholder="Наприклад: Закупівля на базарі">
            
            <button type="submit" class="button" style="width:100%; margin-top:20px;">Створити та додати товари</button>
        </form>
    </div>
    <script>
        function toggleFields() {{
            const type = document.querySelector('input[name="doc_type"]:checked').value;
            const sup = document.getElementById('supplier_div');
            const src = document.getElementById('source_wh_div');
            const tgt = document.getElementById('target_wh_div');
            
            if(type === 'supply') {{
                sup.style.display = 'block'; src.style.display = 'none'; tgt.style.display = 'block';
            }} else if (type === 'transfer') {{
                sup.style.display = 'none'; src.style.display = 'block'; tgt.style.display = 'block';
            }} else if (type === 'writeoff') {{
                sup.style.display = 'none'; src.style.display = 'block'; tgt.style.display = 'none';
            }}
        }}
        toggleFields();
    </script>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Новий документ", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/docs/create")
async def create_doc_action(
    doc_type: str = Form(...), 
    supplier_id: str = Form(None), 
    source_warehouse_id: str = Form(None), 
    target_warehouse_id: str = Form(None), 
    comment: str = Form(None),
    session: AsyncSession = Depends(get_db_session)
):
    s_id = int(supplier_id) if supplier_id and supplier_id.strip().isdigit() else None
    src_id = int(source_warehouse_id) if source_warehouse_id and source_warehouse_id.strip().isdigit() else None
    tgt_id = int(target_warehouse_id) if target_warehouse_id and target_warehouse_id.strip().isdigit() else None

    # ВАЛІДАЦІЯ
    if doc_type == 'supply':
        if not s_id: raise HTTPException(400, "Для типу 'Прихід' обов'язковий Постачальник.")
        if not tgt_id: raise HTTPException(400, "Для типу 'Прихід' обов'язковий Склад (Куди).")
    elif doc_type == 'transfer':
        if not src_id or not tgt_id: raise HTTPException(400, "Для переміщення потрібні обидва склади.")
        if src_id == tgt_id: raise HTTPException(400, "Склади 'Звідки' і 'Куди' повинні відрізнятися.")
    elif doc_type == 'writeoff':
        if not src_id: raise HTTPException(400, "Для списання обов'язковий Склад (Звідки).")

    doc = InventoryDoc(
        doc_type=doc_type,
        supplier_id=s_id,
        source_warehouse_id=src_id,
        target_warehouse_id=tgt_id,
        comment=comment,
        is_processed=False
    )
    session.add(doc)
    await session.commit()
    return RedirectResponse(f"/admin/inventory/docs/{doc.id}", status_code=303)

@router.get("/docs/delete/{doc_id}")
async def delete_document(doc_id: int, session: AsyncSession = Depends(get_db_session)):
    doc = await session.get(InventoryDoc, doc_id)
    if not doc:
        raise HTTPException(404, "Документ не знайдено")
    
    if doc.is_processed:
        raise HTTPException(400, "Неможливо видалити вже проведений документ!")
        
    await session.delete(doc)
    await session.commit()
    return RedirectResponse("/admin/inventory/docs", status_code=303)

@router.get("/docs/{doc_id}", response_class=HTMLResponse)
async def view_doc(doc_id: int, session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    doc = await session.get(InventoryDoc, doc_id, options=[
        joinedload(InventoryDoc.items).joinedload(InventoryDocItem.ingredient).joinedload(Ingredient.unit),
        joinedload(InventoryDoc.source_warehouse),
        joinedload(InventoryDoc.target_warehouse),
        joinedload(InventoryDoc.supplier)
    ])
    if not doc: return HTMLResponse("Документ не знайдено")
    
    ingredients = (await session.execute(select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name))).scalars().all()
    ing_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in ingredients])
    
    rows = ""
    total_sum = 0
    for item in doc.items:
        sum_row = float(item.quantity) * float(item.price)
        total_sum += sum_row
        
        delete_btn = ""
        if not doc.is_processed:
            delete_btn = f"<a href='/admin/inventory/docs/{doc.id}/del_item/{item.id}' style='color:#ef4444;' title='Видалити'><i class='fa-solid fa-xmark'></i></a>"
            
        rows += f"""
        <tr>
            <td>{item.ingredient.name}</td>
            <td>{item.quantity} {item.ingredient.unit.name}</td>
            <td>{item.price}</td>
            <td>{sum_row:.2f}</td>
            <td style="text-align:center;">{delete_btn}</td>
        </tr>
        """
        
    type_label = {'supply': 'Прихід', 'transfer': 'Переміщення', 'writeoff': 'Списання', 'deduction': 'Авто-списання'}.get(doc.doc_type, doc.doc_type)
    header_info = ""
    if doc.doc_type == 'supply':
        supplier_name = doc.supplier.name if doc.supplier else "Внутрішнє виробництво"
        header_info = f"<div class='doc-info-row'><span>Постачальник:</span> <b>{supplier_name}</b></div>"
        header_info += f"<div class='doc-info-row'><span>На склад:</span> <b>{doc.target_warehouse.name if doc.target_warehouse else '-'}</b></div>"
    elif doc.doc_type == 'writeoff' or doc.doc_type == 'deduction':
        header_info = f"<div class='doc-info-row'><span>Зі складу:</span> <b>{doc.source_warehouse.name if doc.source_warehouse else '-'}</b></div>"
    elif doc.doc_type == 'transfer':
        header_info = f"<div class='doc-info-row'><span>Зі складу:</span> <b>{doc.source_warehouse.name if doc.source_warehouse else '-'}</b></div>"
        header_info += f"<div class='doc-info-row'><span>На склад:</span> <b>{doc.target_warehouse.name if doc.target_warehouse else '-'}</b></div>"
    
    # --- НОВЕ: Відображення деталей замовлення (страв) ---
    order_info_html = ""
    if doc.linked_order_id:
        # Завантажуємо замовлення
        res_order = await session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == doc.linked_order_id)
        )
        linked_order = res_order.scalar_one_or_none()

        if linked_order:
            dishes_list = ""
            for o_item in linked_order.items:
                # Додаємо модифікатори, якщо є
                mods_str = ""
                if o_item.modifiers:
                    mod_names = [m.get('name', '') for m in o_item.modifiers]
                    if mod_names:
                        mods_str = f" <small style='color:#666;'>(+ {', '.join(mod_names)})</small>"
                
                dishes_list += f"<li style='margin-bottom:4px;'>🍽 <b>{o_item.product_name}</b> {mods_str} <span style='background:#eee; padding:2px 6px; border-radius:4px;'>x{o_item.quantity}</span></li>"
            
            order_link = f"<a href='/admin/order/manage/{linked_order.id}' target='_blank'>#{linked_order.id}</a>"
            
            order_info_html = f"""
            <div style="margin-top: 20px; background: #fff7ed; padding: 15px; border-radius: 10px; border: 1px solid #ffedd5;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h4 style="margin:0; color: #9a3412;"><i class="fa-solid fa-utensils"></i> Списано під замовлення {order_link}</h4>
                    <span style="font-size:0.85rem; color:#c2410c;">Автоматичний розрахунок</span>
                </div>
                <ul style="margin:0; padding-left: 20px; color: #333; list-style-type: none;">
                    {dishes_list}
                </ul>
            </div>
            """
    # -----------------------------------------------------

    status_ui = ""
    add_form = ""
    
    if not doc.is_processed:
        status_ui = f"""
        <div style="margin-top:20px; display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end;">
            <a href="/admin/inventory/docs/delete/{doc.id}" onclick="return confirm('Видалити цю чернетку повністю?');" class="button danger">
                <i class="fa-solid fa-trash"></i> Видалити
            </a>
            <form action="/admin/inventory/docs/{doc.id}/approve" method="post" style="margin:0;">
                <button type="submit" class="button success" onclick="return confirm('Провести документ? Залишки оновляться.')">
                    <i class="fa-solid fa-check"></i> ПРОВЕСТИ
                </button>
            </form>
        </div>
        <div style="text-align:right; margin-top:5px; color:#c2410c; font-weight:bold; font-size:0.9rem;">
            ⚠️ Чернетка (Не проведено)
        </div>
        """
        
        add_form = f"""
        <tr style="background:#f8fafc;">
            <form action="/admin/inventory/docs/{doc.id}/add_item" method="post">
                <td style="padding:5px;">
                    <select name="ingredient_id" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;" required>{ing_opts}</select>
                </td>
                <td style="padding:5px;">
                    <input type="number" step="0.001" name="quantity" placeholder="К-сть" required style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                </td>
                <td style="padding:5px;">
                    <input type="number" step="0.01" name="price" placeholder="Ціна" value="0" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:4px;">
                </td>
                <td>-</td>
                <td style="text-align:center; padding:5px;">
                    <button type="submit" class="button-sm" style="width:100%;"><i class="fa-solid fa-plus"></i></button>
                </td>
            </form>
        </tr>
        """
    else:
        status_ui = """
        <div style="margin-top:20px; padding:15px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; color:#15803d; text-align:center; font-weight:bold;">
            <i class="fa-solid fa-check-circle"></i> Документ проведено
        </div>
        """
        
        pay_block = ""
        if doc.doc_type == 'supply' and doc.supplier_id:
            debt = float(total_sum) - float(doc.paid_amount)
            if debt > 0.01:
                pay_block = f"""
                <div style="margin-top:20px; padding:20px; background:#f0f9ff; border:1px solid #e0f2fe; border-radius:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h4 style="margin:0 0 5px 0; color:#0369a1;">Оплата накладної</h4>
                            <div style="font-size:0.9rem; color:#334155;">Сплачено: <b>{doc.paid_amount}</b> / Борг: <b style="color:#dc2626;">{debt:.2f} грн</b></div>
                        </div>
                        <form action="/admin/inventory/docs/{doc.id}/pay" method="post" class="inline-form" onsubmit="return confirm('Створити витратний ордер в касі?')">
                            <input type="number" name="amount" step="0.01" value="{debt:.2f}" style="width:120px; padding:8px;">
                            <button type="submit" class="button">💸 Оплатити з каси</button>
                        </form>
                    </div>
                </div>
                """
            else:
                pay_block = "<div style='margin-top:20px; text-align:center; color:#15803d; font-weight:bold;'>🎉 Накладна повністю оплачена</div>"
    
    pay_block = pay_block if 'pay_block' in locals() else ""

    body = f"""
    {get_nav('docs')}
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:20px;">
            <div>
                <h2 style="margin:0;">{type_label} #{doc.id}</h2>
                <div style="color:#666; font-size:0.9rem;">від {doc.created_at.strftime('%d.%m.%Y %H:%M')}</div>
            </div>
            <a href="/admin/inventory/docs" class="button secondary">Назад</a>
        </div>
        
        <div class="doc-header">
            <div>
                {header_info}
                <div class="doc-info-row"><span>Коментар:</span> <i>{doc.comment or '-'}</i></div>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center; width: 300px;">
                {status_ui}
            </div>
        </div>
        
        {order_info_html}
        
        <div class="table-wrapper">
            <table class="inv-table">
                <thead><tr><th width="40%">Товар</th><th>К-сть</th><th>Ціна</th><th>Сума</th><th width="50"></th></tr></thead>
                <tbody>
                    {rows}
                    {add_form}
                </tbody>
            </table>
        </div>
        
        <div class="doc-total">
            Разом: {total_sum:.2f} грн
        </div>
        
        {pay_block}
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title=f"Док #{doc.id}", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/docs/{doc_id}/add_item")
async def add_doc_item(
    doc_id: int, 
    ingredient_id: int = Form(...), 
    quantity: float = Form(...), 
    price: float = Form(0),
    session: AsyncSession = Depends(get_db_session)
):
    doc = await session.get(InventoryDoc, doc_id)
    if not doc or doc.is_processed: raise HTTPException(400, "Не можна змінювати проведений документ")
    
    item = InventoryDocItem(doc_id=doc_id, ingredient_id=ingredient_id, quantity=quantity, price=price)
    session.add(item)
    await session.commit()
    return RedirectResponse(f"/admin/inventory/docs/{doc_id}", status_code=303)

@router.get("/docs/{doc_id}/del_item/{item_id}")
async def del_doc_item(doc_id: int, item_id: int, session: AsyncSession = Depends(get_db_session)):
    doc = await session.get(InventoryDoc, doc_id)
    if not doc or doc.is_processed: raise HTTPException(400, "Заблоковано")
    
    item = await session.get(InventoryDocItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()
    return RedirectResponse(f"/admin/inventory/docs/{doc_id}", status_code=303)

@router.post("/docs/{doc_id}/approve")
async def approve_doc(doc_id: int, session: AsyncSession = Depends(get_db_session)):
    count_res = await session.execute(select(func.count(InventoryDocItem.id)).where(InventoryDocItem.doc_id == doc_id))
    if count_res.scalar() == 0:
        raise HTTPException(400, "Неможливо провести порожній документ!")

    try:
        await apply_doc_stock_changes(session, doc_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse(f"/admin/inventory/docs/{doc_id}", status_code=303)

@router.post("/docs/{doc_id}/pay")
async def pay_document(doc_id: int, amount: Decimal = Form(...), session: AsyncSession = Depends(get_db_session)):
    doc = await session.get(InventoryDoc, doc_id, options=[joinedload(InventoryDoc.supplier)])
    if not doc: raise HTTPException(404)
    
    shift = await get_any_open_shift(session)
    if not shift:
        raise HTTPException(400, "Немає відкритої касової зміни для проведення оплати!")
    
    comment = f"Оплата накладної #{doc.id}"
    if doc.supplier: comment += f" ({doc.supplier.name})"
    
    await add_shift_transaction(session, shift.id, amount, "out", comment)
    
    doc.paid_amount = float(doc.paid_amount) + float(amount)
    await session.commit()
    
    return RedirectResponse(f"/admin/inventory/docs/{doc_id}", 303)

# --- TECH CARDS ---
@router.get("/tech_cards", response_class=HTMLResponse)
async def tc_list(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    tcs = (await session.execute(select(TechCard).options(joinedload(TechCard.product)))).scalars().all()
    
    rows = "".join([f"""
    <tr>
        <td>{tc.id}</td>
        <td><b>{tc.product.name}</b></td>
        <td class='actions'>
            <a href='/admin/inventory/tech_cards/{tc.id}' class='button-sm'>Редагувати</a>
            <a href='/admin/inventory/tech_cards/delete/{tc.id}' onclick="return confirm('Видалити техкарту?');" class='button-sm danger'><i class="fa-solid fa-trash"></i></a>
        </td>
    </tr>""" for tc in tcs])
    
    prods = (await session.execute(select(Product).outerjoin(TechCard).where(TechCard.id == None, Product.is_active == True))).scalars().all()
    prod_opts = "".join([f"<option value='{p.id}'>{p.name}</option>" for p in prods])
    
    body = f"""
    {get_nav('tech_cards')}
    <div class="card">
        <div class="inv-toolbar"><h3>Технологічні карти</h3></div>
        <form action="/admin/inventory/tech_cards/create" method="post" class="inline-add-form">
            <strong>Створити ТК:</strong>
            <select name="product_id" style="width:200px;">{prod_opts}</select>
            <button type="submit" class="button">OK</button>
        </form>
        <div class="inv-table-wrapper"><table class="inv-table"><thead><tr><th>ID</th><th>Страва</th><th>Дії</th></tr></thead><tbody>{rows}</tbody></table></div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Техкарти", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/tech_cards/create")
async def create_tc(product_id: int = Form(...), session: AsyncSession = Depends(get_db_session)):
    tc = TechCard(product_id=product_id)
    session.add(tc)
    await session.commit()
    await session.refresh(tc)
    return RedirectResponse(f"/admin/inventory/tech_cards/{tc.id}", 303)

@router.get("/tech_cards/delete/{tc_id}")
async def delete_tech_card(tc_id: int, session: AsyncSession = Depends(get_db_session)):
    tc = await session.get(TechCard, tc_id)
    if tc:
        await session.delete(tc)
        await session.commit()
    return RedirectResponse("/admin/inventory/tech_cards", status_code=303)

# --- РЕДАГУВАННЯ ТЕХКАРТИ (З ЦІНОЮ ТА ПРИБУТКОМ) ---
@router.get("/tech_cards/{tc_id}", response_class=HTMLResponse)
async def edit_tc(
    tc_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    # Завантажуємо техкарту разом з продуктом
    tc = await session.get(TechCard, tc_id, options=[joinedload(TechCard.product), joinedload(TechCard.components).joinedload(TechCardItem.ingredient).joinedload(Ingredient.unit)])
    
    ing_res = await session.execute(
        select(Ingredient).options(joinedload(Ingredient.unit)).order_by(Ingredient.name))
    ingredients = ing_res.scalars().all()
    
    ing_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in ingredients])
    
    comp_rows = ""
    cost = 0.0
    
    if tc:
        for c in tc.components:
            ing_cost = float(c.ingredient.current_cost or 0)
            sub = float(c.gross_amount) * ing_cost
            cost += sub
            takeaway_icon = "<span class='inv-badge badge-blue'><i class='fa-solid fa-box'></i> Тільки винос</span>" if c.is_takeaway else ""
            
            comp_rows += f"""
            <tr>
                <td>{c.ingredient.name}</td>
                <td>{ing_cost:.2f} грн</td>
                <td>{c.gross_amount}</td>
                <td>{c.net_amount}</td>
                <td>{takeaway_icon}</td>
                <td>{sub:.2f}</td>
                <td><a href='/admin/inventory/tc/del/{c.id}' style='color:red'>X</a></td>
            </tr>
            """

    # --- БЛОК РОЗРАХУНКУ ПРИБУТКУ ---
    product_price = float(tc.product.price)
    profit = product_price - cost
    markup = (profit / cost * 100) if cost > 0 else 0
    margin = (profit / product_price * 100) if product_price > 0 else 0
    
    profit_color = "#16a34a" if profit > 0 else "#dc2626"

    stats_html = f"""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin-bottom: 25px; display: flex; gap: 30px; align-items: center; flex-wrap: wrap;">
        
        <div>
            <div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: bold;">Собівартість</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: #334155;">{cost:.2f} <small>грн</small></div>
        </div>

        <form action="/admin/inventory/tc/{tc.id}/update_price" method="post" style="display:flex; flex-direction:column; margin:0;">
            <label style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: bold; margin-bottom: 5px;">Ціна продажу</label>
            <div style="display:flex; gap: 5px;">
                <input type="number" step="0.01" name="price" value="{product_price:.2f}" style="width: 100px; padding: 5px 10px; font-size: 1.1rem; font-weight: bold; border: 2px solid #cbd5e1; border-radius: 6px; margin:0;">
                <button type="submit" class="button-sm" title="Зберегти ціну"><i class="fa-solid fa-floppy-disk"></i></button>
            </div>
        </form>

        <div style="width: 1px; height: 40px; background: #cbd5e1;"></div>

        <div>
            <div style="font-size: 0.85rem; color: #64748b; text-transform: uppercase; font-weight: bold;">Прибуток (Маржа)</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {profit_color};">
                {profit:+.2f} <small>грн</small>
            </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:2px; font-size: 0.9rem;">
            <div>Націнка: <b>{markup:.0f}%</b></div>
            <div>Маржинальність: <b>{margin:.0f}%</b></div>
        </div>
    </div>
    """
    # -------------------------------------

    body = f"""
    {get_nav('tech_cards')}
    <div class="card">
        <div style="display:flex; justify-content:space-between; margin-bottom:20px;">
            <h2>ТК: {tc.product.name}</h2>
            <a href="/admin/inventory/tech_cards" class="button secondary">Назад</a>
        </div>
        
        {stats_html}

        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>Інгредієнт</th><th>Ціна од.</th><th>Брутто</th><th>Нетто</th><th>Умови</th><th>Вартість</th><th></th></tr></thead>
                <tbody>
                    {comp_rows}
                    <tr style="background:#f8f9fa;">
                        <form action="/admin/inventory/tc/{tc.id}/add" method="post">
                            <td style="padding:5px;"><select name="ingredient_id" style="width:100%;">{ing_opts}</select></td>
                            <td>-</td>
                            <td style="padding:5px;"><input type="number" step="0.001" name="gross" placeholder="Брутто" required style="width:80px;"></td>
                            <td style="padding:5px;"><input type="number" step="0.001" name="net" placeholder="Нетто" required style="width:80px;"></td>
                            <td style="padding:5px;">
                                <div style="display:flex; align-items:center; gap:5px;">
                                    <input type="checkbox" id="takeaway_only" name="is_takeaway" value="true">
                                    <label for="takeaway_only" style="font-size:0.8rem; margin:0; cursor:pointer;">Тільки винос</label>
                                </div>
                            </td>
                            <td>-</td>
                            <td style="padding:5px;"><button type="submit" class="button-sm">+</button></td>
                        </form>
                    </tr>
                </tbody>
            </table>
        </div>
        <div style="margin-top:10px; font-size:0.85rem; color:#666;">
            <i class="fa-solid fa-circle-info"></i> Позначте "Тільки винос", якщо цей інгредієнт (наприклад, коробка) має списуватись тільки при Доставці або Самовивозі.
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title=f"ТК {tc.product.name}", body=body, site_title=settings.site_title, **get_active_classes()))

# --- МЕТОД ДЛЯ ОНОВЛЕННЯ ЦІНИ ПРОДУКТУ З ТЕХКАРТИ ---
@router.post("/tc/{tc_id}/update_price")
async def update_tc_product_price(
    tc_id: int,
    price: Decimal = Form(...),
    session: AsyncSession = Depends(get_db_session)
):
    tc = await session.get(TechCard, tc_id, options=[joinedload(TechCard.product)])
    if tc and tc.product:
        tc.product.price = price
        await session.commit()
    return RedirectResponse(f"/admin/inventory/tech_cards/{tc_id}", 303)

@router.post("/tc/{tc_id}/add")
async def add_tc_comp(
    tc_id: int, 
    ingredient_id: int = Form(...), 
    gross: float = Form(...), 
    net: float = Form(...), 
    is_takeaway: bool = Form(False),
    session: AsyncSession = Depends(get_db_session)
):
    session.add(TechCardItem(
        tech_card_id=tc_id, 
        ingredient_id=ingredient_id, 
        gross_amount=gross, 
        net_amount=net,
        is_takeaway=is_takeaway
    ))
    await session.commit()
    return RedirectResponse(f"/admin/inventory/tech_cards/{tc_id}", 303)

@router.get("/tc/del/{item_id}")
async def del_tc_comp(item_id: int, session: AsyncSession = Depends(get_db_session)):
    item = await session.get(TechCardItem, item_id)
    tc_id = item.tech_card_id
    await session.delete(item)
    await session.commit()
    return RedirectResponse(f"/admin/inventory/tech_cards/{tc_id}", 303)

# --- ЗВІТ ПО РУХУ ІНГРЕДІЄНТА ---
@router.get("/reports/usage", response_class=HTMLResponse)
async def inventory_usage_report(
    ingredient_id: int = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    session: AsyncSession = Depends(get_db_session),
    user=Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    
    ingredients = (await session.execute(select(Ingredient).order_by(Ingredient.name))).scalars().all()
    ing_options = "".join([f'<option value="{i.id}" {"selected" if ingredient_id == i.id else ""}>{html.escape(i.name)}</option>' for i in ingredients])
    
    report_rows = ""
    
    if ingredient_id:
        query = select(InventoryDocItem).join(InventoryDoc).options(
            joinedload(InventoryDocItem.doc)
        ).where(
            InventoryDocItem.ingredient_id == ingredient_id, 
            InventoryDoc.is_processed == True
        )
        
        if date_from:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.where(InventoryDoc.created_at >= dt_from)
        if date_to:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.where(InventoryDoc.created_at <= dt_to)
            
        query = query.order_by(desc(InventoryDoc.created_at))
        
        items = (await session.execute(query)).scalars().all()
        
        for item in items:
            doc = item.doc
            
            type_map = {
                'supply': ('📥 Прихід', 'green'),
                'writeoff': ('🗑️ Списання', 'red'),
                'deduction': ('🤖 Авто-списання', 'gray'),
                'transfer': ('🔄 Переміщення', 'blue'),
                'return': ('♻️ Повернення', 'orange'),
                'inventory': ('📝 Інвентаризація', 'orange')
            }
            type_label, color = type_map.get(doc.doc_type, (doc.doc_type, 'black'))
            
            details = html.escape(doc.comment or '-')
            if doc.linked_order_id:
                details = f"<a href='/admin/order/manage/{doc.linked_order_id}'>Замовлення #{doc.linked_order_id}</a>"
            
            qty_formatted = f"{item.quantity:.3f}"
            
            if doc.doc_type == 'inventory':
                qty_formatted = f"Факт: {qty_formatted}"
                color = "black"
            elif doc.doc_type in ['writeoff', 'deduction', 'transfer']:
                 if doc.doc_type == 'transfer' and not doc.source_warehouse_id: 
                     pass
                 else: 
                     qty_formatted = f"-{qty_formatted}"
            
            report_rows += f"""
            <tr>
                <td>{doc.created_at.strftime('%d.%m.%Y %H:%M')}</td>
                <td style="color:{color}; font-weight:bold;">{type_label}</td>
                <td>{qty_formatted}</td>
                <td>{item.price:.2f}</td>
                <td>{details}</td>
            </tr>
            """
    
    body = f"""
    {get_nav('reports/usage')}
    <div class="card">
        <h2 style="margin-bottom:20px;"><i class="fa-solid fa-chart-line"></i> Історія руху товару</h2>
        
        <form action="/admin/inventory/reports/usage" method="get" class="search-form" style="background: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
            <div style="display:flex; gap:15px; flex-wrap:wrap; align-items:flex-end;">
                <div style="flex:1; min-width:200px;">
                    <label style="display:block; margin-bottom:5px; font-weight:bold;">Інгредієнт:</label>
                    <select name="ingredient_id" required style="width:100%; padding:10px; border-radius:6px; border:1px solid #ccc;">
                        <option value="">-- Оберіть товар --</option>
                        {ing_options}
                    </select>
                </div>
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold;">З:</label>
                    <input type="date" name="date_from" value="{date_from or ''}" style="padding:9px; border-radius:6px; border:1px solid #ccc;">
                </div>
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold;">По:</label>
                    <input type="date" name="date_to" value="{date_to or ''}" style="padding:9px; border-radius:6px; border:1px solid #ccc;">
                </div>
                <button type="submit" class="button" style="height:42px;"><i class="fa-solid fa-filter"></i> Показати</button>
            </div>
        </form>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead>
                    <tr>
                        <th>Дата/Час</th>
                        <th>Операція</th>
                        <th>Кількість</th>
                        <th>Ціна (обл.)</th>
                        <th>Деталі / Замовлення</th>
                    </tr>
                </thead>
                <tbody>
                    {report_rows or "<tr><td colspan='5' style='text-align:center; padding:30px; color:#999;'>Дані відсутні. Оберіть товар та період.</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Звіт по руху", body=body, site_title=settings.site_title, **get_active_classes()))

# --- ЗВІТ ПО РЕНТАБЕЛЬНОСТІ ---
@router.get("/reports/profitability", response_class=HTMLResponse)
async def report_profitability(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    products_res = await session.execute(
        select(Product)
        .where(Product.is_active == True)
        .options(joinedload(Product.category))
    )
    products = products_res.scalars().all()
    
    data = []
    
    for p in products:
        tc = await session.scalar(
            select(TechCard)
            .where(TechCard.product_id == p.id)
            .options(joinedload(TechCard.components).joinedload(TechCardItem.ingredient))
        )
        
        cost_price = 0.0
        if tc:
            for item in tc.components:
                ing_cost = float(item.ingredient.current_cost or 0)
                amount = float(item.gross_amount or 0)
                cost_price += ing_cost * amount
        
        sale_price = float(p.price)
        margin = sale_price - cost_price
        
        margin_percent = (margin / sale_price * 100) if sale_price > 0 else 0
        markup_percent = (margin / cost_price * 100) if cost_price > 0 else 0
        
        data.append({
            "name": p.name,
            "category": p.category.name if p.category else "-",
            "sale_price": sale_price,
            "cost_price": cost_price,
            "margin": margin,
            "margin_percent": margin_percent,
            "markup_percent": markup_percent
        })
    
    data.sort(key=lambda x: x['margin_percent'])
    
    rows = ""
    for item in data:
        row_style = ""
        margin_badge = f"{item['margin_percent']:.1f}%"
        
        if item['margin_percent'] < 30:
            row_style = "background-color: #fff1f2;"
            margin_badge = f"<span style='color:#e11d48; font-weight:bold;'>📉 {item['margin_percent']:.1f}%</span>"
        elif item['margin_percent'] > 60:
            margin_badge = f"<span style='color:#16a34a; font-weight:bold;'>🚀 {item['margin_percent']:.1f}%</span>"
            
        rows += f"""
        <tr style="{row_style}">
            <td><b>{html.escape(item['name'])}</b> <div style="color:#777; font-size:0.8em;">{html.escape(item['category'])}</div></td>
            <td>{item['sale_price']:.2f}</td>
            <td>{item['cost_price']:.2f}</td>
            <td>{item['margin']:.2f}</td>
            <td>{margin_badge}</td>
            <td style="color:#666;">{item['markup_percent']:.0f}%</td>
        </tr>
        """
        
    body = f"""
    {get_nav('reports/profitability')}
    <div class="card">
        <div style="margin-bottom:20px;">
            <h2 style="margin:0;"><i class="fa-solid fa-money-bill-trend-up"></i> Рентабельність страв</h2>
            <p style="color:#666; margin-top:5px;">
                Розрахунок базується на <b>поточних</b> цінах інгредієнтів у складському обліку.
                <br> <small>⚠️ Якщо собівартість 0.00 — перевірте наявність техкарти або закупівельних цін.</small>
            </p>
        </div>
        
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead>
                    <tr>
                        <th>Страва</th>
                        <th>Ціна продажу</th>
                        <th>Собівартість (Cost)</th>
                        <th>Прибуток (Margin)</th>
                        <th>Маржа %</th>
                        <th>Націнка %</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or "<tr><td colspan='6' style='text-align:center; padding:30px;'>Немає активних страв</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>
    """
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Рентабельність", body=body, site_title=settings.site_title, **get_active_classes()))

@router.get("/reports/suppliers", response_class=HTMLResponse)
async def report_suppliers(
    supplier_id: int = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    sort_by: str = Query("date_desc"),
    session: AsyncSession = Depends(get_db_session),
    user=Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    
    suppliers = (await session.execute(select(Supplier).order_by(Supplier.name))).scalars().all()
    sup_opts = f"<option value=''>-- Всі постачальники --</option>"
    for s in suppliers:
        selected = "selected" if supplier_id == s.id else ""
        sup_opts += f"<option value='{s.id}' {selected}>{html.escape(s.name)}</option>"

    query = select(InventoryDoc).options(
        joinedload(InventoryDoc.supplier),
        selectinload(InventoryDoc.items) 
    ).where(InventoryDoc.doc_type == 'supply')

    if supplier_id:
        query = query.where(InventoryDoc.supplier_id == supplier_id)
    
    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        query = query.where(InventoryDoc.created_at >= dt_from)
    
    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        query = query.where(InventoryDoc.created_at <= dt_to)

    docs_res = await session.execute(query)
    docs = docs_res.scalars().all()

    report_data = []
    total_period_sum = Decimal(0)
    total_period_paid = Decimal(0)

    for d in docs:
        doc_total = sum((item.quantity * item.price) for item in d.items)
        doc_debt = doc_total - d.paid_amount
        
        total_period_sum += doc_total
        total_period_paid += d.paid_amount

        report_data.append({
            "id": d.id,
            "date": d.created_at,
            "supplier_name": d.supplier.name if d.supplier else "Невідомий",
            "total": doc_total,
            "paid": d.paid_amount,
            "debt": doc_debt,
            "comment": d.comment or "",
            "is_processed": d.is_processed
        })

    if sort_by == 'date_desc':
        report_data.sort(key=lambda x: x['date'], reverse=True)
    elif sort_by == 'date_asc':
        report_data.sort(key=lambda x: x['date'])
    elif sort_by == 'amount_desc':
        report_data.sort(key=lambda x: x['total'], reverse=True)
    elif sort_by == 'amount_asc':
        report_data.sort(key=lambda x: x['total'])

    rows = ""
    for row in report_data:
        status_icon = "✅" if row['is_processed'] else "⚠️"
        date_str = row['date'].strftime('%d.%m.%Y %H:%M')
        
        debt_display = f"{row['debt']:.2f}"
        if row['debt'] > 0:
            debt_display = f"<span style='color:#dc2626; font-weight:bold;'>{debt_display}</span>"
        elif row['debt'] < 0:
             debt_display = f"<span style='color:#2563eb;'>+{abs(row['debt']):.2f} (Переплата)</span>"
        else:
             debt_display = "<span style='color:#16a34a;'>Оплачено</span>"

        rows += f"""
        <tr onclick="window.location='/admin/inventory/docs/{row['id']}'" style="cursor:pointer;">
            <td>{row['id']}</td>
            <td>{date_str}</td>
            <td><b>{html.escape(row['supplier_name'])}</b></td>
            <td>{row['total']:.2f} грн</td>
            <td>{row['paid']:.2f} грн</td>
            <td>{debt_display}</td>
            <td>{status_icon}</td>
            <td style="color:#666; font-size:0.9em;">{html.escape(row['comment'])}</td>
        </tr>
        """

    body = f"""
    {get_nav('reports/suppliers')}
    
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
            <h2 style="margin:0;"><i class="fa-solid fa-file-invoice-dollar"></i> Звіт по постачальниках</h2>
            
            <div style="text-align:right;">
                <div style="font-size:0.9rem; color:#666;">Загальна сума закупівель:</div>
                <div style="font-size:1.5rem; font-weight:bold; color:#0f172a;">{total_period_sum:.2f} грн</div>
                <div style="font-size:0.8rem; color:#16a34a;">Сплачено: {total_period_paid:.2f} грн</div>
            </div>
        </div>

        <form action="/admin/inventory/reports/suppliers" method="get" class="search-form" style="background: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
            <div style="display:flex; gap:15px; flex-wrap:wrap; align-items:flex-end;">
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold; font-size:0.8rem;">Постачальник:</label>
                    <select name="supplier_id" style="padding:8px; border-radius:6px; border:1px solid #ccc; min-width:200px;">
                        {sup_opts}
                    </select>
                </div>
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold; font-size:0.8rem;">Період з:</label>
                    <input type="date" name="date_from" value="{date_from or ''}" style="padding:7px; border-radius:6px; border:1px solid #ccc;">
                </div>
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold; font-size:0.8rem;">по:</label>
                    <input type="date" name="date_to" value="{date_to or ''}" style="padding:7px; border-radius:6px; border:1px solid #ccc;">
                </div>
                <div>
                    <label style="display:block; margin-bottom:5px; font-weight:bold; font-size:0.8rem;">Сортування:</label>
                    <select name="sort_by" style="padding:8px; border-radius:6px; border:1px solid #ccc;">
                        <option value="date_desc" {'selected' if sort_by=='date_desc' else ''}>Дата (нові)</option>
                        <option value="date_asc" {'selected' if sort_by=='date_asc' else ''}>Дата (старі)</option>
                        <option value="amount_desc" {'selected' if sort_by=='amount_desc' else ''}>Сума (дорогі)</option>
                        <option value="amount_asc" {'selected' if sort_by=='amount_asc' else ''}>Сума (дешеві)</option>
                    </select>
                </div>
                <button type="submit" class="button" style="height:38px;"><i class="fa-solid fa-filter"></i> Показати</button>
            </div>
        </form>

        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Дата</th>
                        <th>Постачальник</th>
                        <th>Сума накладної</th>
                        <th>Сплачено</th>
                        <th>Борг</th>
                        <th>Статус</th>
                        <th>Коментар</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or "<tr><td colspan='8' style='text-align:center; padding:30px; color:#999;'>Документів не знайдено</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>
    """
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Звіт: Постачальники", body=body, site_title=settings.site_title, **get_active_classes()))

# --- ВИРОБНИЦТВО ---
@router.get("/production", response_class=HTMLResponse)
async def production_page(session: AsyncSession = Depends(get_db_session), user=Depends(check_credentials)):
    settings = await session.get(Settings, 1) or Settings()
    
    # Список П/Ф для выбора
    pfs = (await session.execute(
        select(Ingredient)
        .options(joinedload(Ingredient.unit)) 
        .where(Ingredient.is_semi_finished==True)
        .order_by(Ingredient.name)
    )).scalars().all()
    
    pf_opts = "".join([f"<option value='{i.id}'>{i.name} ({i.unit.name})</option>" for i in pfs])
    
    # Склади
    warehouses = (await session.execute(select(Warehouse).order_by(Warehouse.name))).scalars().all()
    wh_opts = "".join([f"<option value='{w.id}'>{w.name}</option>" for w in warehouses])
    
    # Останні акти виробництва
    query = select(InventoryDoc).options(joinedload(InventoryDoc.target_warehouse))\
        .where(InventoryDoc.doc_type == 'supply', InventoryDoc.supplier_id == None)\
        .order_by(desc(InventoryDoc.created_at)).limit(20)
        
    docs = (await session.execute(query)).scalars().all()
    
    history_rows = ""
    for d in docs:
        history_rows += f"""
        <tr onclick="window.location='/admin/inventory/docs/{d.id}'" style="cursor:pointer;">
            <td>#{d.id}</td>
            <td>{d.created_at.strftime('%d.%m %H:%M')}</td>
            <td>{d.comment}</td>
            <td>{d.target_warehouse.name}</td>
        </tr>
        """

    body = f"""
    {get_nav('production')}
    
    <div class="card" style="border-left: 5px solid #f59e0b;">
        <h3 style="color:#d97706;"><i class="fa-solid fa-fire-burner"></i> Акт виробництва</h3>
        <p style="color:#666; font-size:0.9rem;">
            Створює напівфабрикат на складі, списуючи сировину згідно з рецептом.
            <br>Собівартість П/Ф буде перерахована автоматично на основі списаних продуктів.
        </p>
        
        <form action="/admin/inventory/production/create" method="post" style="background:#fff7ed; padding:20px; border-radius:10px; border:1px solid #ffedd5;">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-bottom:15px;">
                <div>
                    <label><b>Що готуємо (П/Ф):</b></label>
                    <select name="ingredient_id" required style="width:100%; padding:10px;">
                        <option value="">-- Оберіть --</option>
                        {pf_opts}
                    </select>
                </div>
                <div>
                    <label><b>На який склад (Цех):</b></label>
                    <select name="warehouse_id" required style="width:100%; padding:10px;">
                        {wh_opts}
                    </select>
                </div>
            </div>
            
            <div style="margin-bottom:20px;">
                <label><b>Кількість готового продукту:</b></label>
                <input type="number" step="0.001" name="quantity" required placeholder="Напр. 5.0" style="width:150px; padding:10px; font-size:1.1em;">
            </div>
            
            <button type="submit" class="button warning">🍳 Виробити та списати сировину</button>
        </form>
    </div>
    
    <div class="card">
        <h3>Історія виробництва</h3>
        <div class="inv-table-wrapper">
            <table class="inv-table">
                <thead><tr><th>ID</th><th>Дата</th><th>Опис</th><th>Склад</th></tr></thead>
                <tbody>{history_rows or "<tr><td colspan='4' style='text-align:center; padding:20px;'>Історія порожня</td></tr>"}</tbody>
            </table>
        </div>
    </div>
    """
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Виробництво", body=body, site_title=settings.site_title, **get_active_classes()))

@router.post("/production/create")
async def create_production(
    ingredient_id: int = Form(...),
    quantity: float = Form(...),
    warehouse_id: int = Form(...),
    session: AsyncSession = Depends(get_db_session)
):
    from inventory_service import process_production
    try:
        await process_production(session, ingredient_id, quantity, warehouse_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
        
    return RedirectResponse("/admin/inventory/production", 303)