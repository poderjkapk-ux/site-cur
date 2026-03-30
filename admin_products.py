# admin_products.py

import html
import os
import secrets
import aiofiles
import logging
import io  # Додано для роботи з байтами
from decimal import Decimal
from typing import Optional, List
from PIL import Image  # Додано для обробки зображень

from fastapi import APIRouter, Depends, Form, HTTPException, File, UploadFile, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from models import Product, Category, Settings, product_modifier_association
from inventory_models import Modifier, Warehouse
from templates import ADMIN_HTML_TEMPLATE
from dependencies import get_db_session, check_credentials

router = APIRouter()
logger = logging.getLogger(__name__)

# Налаштування для зображень
IMG_MAX_SIZE = (800, 800)
IMG_QUALITY = 80

@router.get("/admin/products", response_class=HTMLResponse)
async def admin_products(
    page: int = Query(1, ge=1), 
    q: str = Query(None, alias="search"), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    """Відображає список страв (товарів) з пагінацією та пошуком."""
    settings = await session.get(Settings, 1) or Settings()
    per_page = 10
    offset = (page - 1) * per_page

    query = select(Product).options(joinedload(Product.category)).order_by(Product.id.desc())
    
    # Фільтрація пошуку
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))

    # Підрахунок загальної кількості
    count_query = select(func.count(Product.id))
    if q:
        count_query = count_query.where(Product.name.ilike(f"%{q}%"))
        
    total_res = await session.execute(count_query)
    total = total_res.scalar_one_or_none() or 0
    
    products_res = await session.execute(query.limit(per_page).offset(offset))
    products = products_res.scalars().all()

    pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    # --- Load warehouses for mapping and options ---
    warehouses_res = await session.execute(select(Warehouse).where(Warehouse.is_production == True).order_by(Warehouse.name))
    warehouses = warehouses_res.scalars().all()
    wh_map = {w.id: w.name for w in warehouses}
    
    # Options for Add Modal
    wh_options = "<option value=''>-- Оберіть цех --</option>" + "".join([f'<option value="{w.id}">{html.escape(w.name)}</option>' for w in warehouses])
    # ----------------------------------------

    # Генерація таблиці
    product_rows = ""
    for p in products:
        # Логіка бейджів
        active_badge = f"<span class='badge badge-active'>Активний</span>" if p.is_active else f"<span class='badge badge-inactive'>Прихований</span>"
        
        # --- Badge for Warehouse ---
        if p.production_warehouse_id and p.production_warehouse_id in wh_map:
            wh_name = html.escape(wh_map[p.production_warehouse_id])
            # Використовуємо іконку складу для позначення цеху
            area_badge = f"<span class='badge badge-kitchen'><i class='fa-solid fa-warehouse'></i> {wh_name}</span>"
        else:
            # Fallback для старих записів або якщо цех видалено
            if p.preparation_area == 'bar':
                 area_badge = f"<span class='badge badge-bar'><i class='fa-solid fa-martini-glass'></i> Бар</span>"
            elif p.preparation_area == 'kitchen':
                 area_badge = f"<span class='badge badge-kitchen'><i class='fa-solid fa-fire-burner'></i> Кухня</span>"
            else:
                 area_badge = f"<span class='badge' style='background:#eee; color:#666;'>Не призначено</span>"
        # -------------------------------------
        
        # Картинка
        img_html = f'<img src="/{p.image_url}" class="product-img-preview" alt="img">' if p.image_url else '<div class="no-img"><i class="fa-regular fa-image"></i></div>'

        # Відображення акційної ціни
        if p.promotional_price and p.promotional_price > 0:
            price_html = f"<del style='color:#ef4444; font-size:0.85em;'>{p.price}</del><br><strong>{p.promotional_price}</strong> <small>грн</small>"
        else:
            price_html = f"{p.price} <small>грн</small>"

        # Кнопка перемикання статусу
        toggle_icon = "fa-eye-slash" if p.is_active else "fa-eye"
        toggle_title = "Приховати" if p.is_active else "Активувати"
        toggle_btn_class = "secondary" if p.is_active else "success"

        product_rows += f"""
        <tr>
            <td style="text-align:center; color:#888;">{p.id}</td>
            <td>{img_html}</td>
            <td style="font-weight:600;">{html.escape(p.name)}</td>
            <td>{price_html}</td>
            <td>{html.escape(p.category.name if p.category else '–')}</td>
            <td>{area_badge}</td> 
            <td>{active_badge}</td>
            <td class='actions'>
                <a href='/admin/product/toggle_active/{p.id}' class='button-sm {toggle_btn_class}' title="{toggle_title}"><i class="fa-solid {toggle_icon}"></i></a>
                <a href='/admin/edit_product/{p.id}' class='button-sm' title="Редагувати"><i class="fa-solid fa-pen"></i></a>
                <a href='/admin/delete_product/{p.id}' onclick="return confirm('Видалити цю страву?');" class='button-sm danger' title="Видалити"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>"""

    # Опції для селекту категорій (для форми додавання)
    categories_res = await session.execute(select(Category))
    category_options = "".join([f'<option value="{c.id}">{html.escape(c.name)}</option>' for c in categories_res.scalars().all()])
    
    # --- ЗАВАНТАЖЕННЯ МОДИФІКАТОРІВ ДЛЯ ФОРМИ ДОДАВАННЯ ---
    all_modifiers = (await session.execute(select(Modifier).order_by(Modifier.name))).scalars().all()
    
    modifiers_html = "<div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px; max-height:150px; overflow-y:auto; border:1px solid #eee; padding:10px; border-radius:5px; margin-bottom:15px;'>"
    for mod in all_modifiers:
        modifiers_html += f"""
        <div class="checkbox-group" style="margin-bottom:0;">
            <input type="checkbox" id="new_mod_{mod.id}" name="modifier_ids" value="{mod.id}">
            <label for="new_mod_{mod.id}" style="font-weight:normal; font-size:0.9em;">{html.escape(mod.name)} (+{mod.price} грн)</label>
        </div>
        """
    modifiers_html += "</div>"
    # -------------------------------------------------------

    # Пагінація
    links_products = []
    for i in range(1, pages + 1):
        search_part = f'&search={q}' if q else ''
        class_part = 'active' if i == page else ''
        links_products.append(f'<a href="/admin/products?page={i}{search_part}" class="{class_part}">{i}</a>')
    
    pagination = f"<div class='pagination'>{' '.join(links_products)}</div>"
    
    # --- CSS Styles ---
    styles = """
    <style>
        /* Header Actions */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 15px;
        }
        .search-group {
            display: flex;
            gap: 10px;
            flex-grow: 1;
            max-width: 400px;
        }
        .search-group input { margin-bottom: 0; }
        
        /* Table Styles */
        .product-img-preview {
            width: 48px; height: 48px;
            border-radius: 8px;
            object-fit: cover;
            border: 1px solid #eee;
        }
        .no-img {
            width: 48px; height: 48px;
            border-radius: 8px;
            background: #f3f4f6;
            display: flex; align-items: center; justify-content: center;
            color: #ccc; font-size: 1.2rem;
        }
        
        /* Badges */
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; }
        .badge-active { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
        .badge-inactive { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        
        .badge-kitchen { background: #fff7ed; color: #9a3412; border: 1px solid #ffedd5; }
        .badge-bar { background: #eff6ff; color: #1e40af; border: 1px solid #dbeafe; }
        
        /* Button Icons fix */
        .button-sm i { pointer-events: none; }
        .button-sm.success { background-color: #10b981; }
    </style>
    """

    # --- HTML Body ---
    body = f"""
    {styles}
    
    <div class="card">
        <div class="toolbar">
            <form action="/admin/products" method="get" class="search-group">
                <input type="text" name="search" placeholder="Пошук страви..." value="{q or ''}">
                <button type="submit" class="button secondary"><i class="fa-solid fa-magnifying-glass"></i></button>
                {f'<a href="/admin/products" class="button secondary" title="Скинути"><i class="fa-solid fa-xmark"></i></a>' if q else ''}
            </form>
            
            <div style="display:flex; gap:10px;">
                <a href="/admin/modifiers" class="button secondary"><i class="fa-solid fa-layer-group"></i> Модифікатори</a>
                <button class="button" onclick="document.getElementById('add-product-modal').classList.add('active')">
                    <i class="fa-solid fa-plus"></i> Додати страву
                </button>
            </div>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th width="50">ID</th>
                        <th width="60">Фото</th>
                        <th>Назва</th>
                        <th>Ціна</th>
                        <th>Категорія</th>
                        <th>Цех (Склад)</th>
                        <th>Статус</th>
                        <th style="text-align:right;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {product_rows or "<tr><td colspan='8' style='text-align:center; padding: 20px; color: #777;'>Страви не знайдені</td></tr>"}
                </tbody>
            </table>
        </div>
        {pagination if pages > 1 else ''}
    </div>

    <div class="modal-overlay" id="add-product-modal">
        <div class="modal">
            <div class="modal-header">
                <h4><i class="fa-solid fa-burger"></i> Нова страва</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-product-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/add_product" method="post" enctype="multipart/form-data">
                    <div class="form-grid">
                        <div>
                            <label for="name">Назва страви *</label>
                            <input type="text" id="name" name="name" required placeholder="Наприклад: Борщ">
                        </div>
                        <div>
                            <label for="price">Ціна (грн) *</label>
                            <input type="number" id="price" name="price" min="1" step="0.01" required placeholder="0.00">
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <label for="promotional_price">Акційна ціна (грн) <small style="color:#888;">(необов'язково)</small></label>
                        <input type="number" id="promotional_price" name="promotional_price" min="0" step="0.01" placeholder="0.00">
                    </div>
                    
                    <label for="category_id">Категорія *</label>
                    <select id="category_id" name="category_id" required>
                        {category_options}
                    </select>
                    
                    <label for="production_warehouse_id">Цех приготування (для списання та чеків) *</label>
                    <select id="production_warehouse_id" name="production_warehouse_id" required>
                        {wh_options}
                    </select>

                    <label style="margin-top:10px;">Доступні модифікатори:</label>
                    {modifiers_html}

                    <label for="description">Опис (склад)</label>
                    <textarea id="description" name="description" rows="3" placeholder="Опис для меню..."></textarea>
                    
                    <label for="image">Фото</label>
                    <input type="file" id="image" name="image" accept="image/*">
                    
                    <button type="submit" class="button" style="width: 100%; margin-top: 10px;">Зберегти</button>
                </form>
            </div>
        </div>
    </div>
    """

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["products_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Страви", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/add_product")
async def add_product(
    name: str = Form(...), 
    price: Decimal = Form(...), 
    promotional_price: Optional[Decimal] = Form(None),
    description: str = Form(""), 
    category_id: int = Form(...), 
    production_warehouse_id: int = Form(None),
    modifier_ids: List[int] = Form([]), 
    image: UploadFile = File(None), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    if price <= 0: 
        raise HTTPException(status_code=400, detail="Ціна повинна бути позитивною")
    
    image_url = None
    
    # --- ЛОГІКА ЗБЕРЕЖЕННЯ ТА ОПТИМІЗАЦІЇ ФОТО ---
    if image and image.filename:
        try:
            # Читаємо файл у пам'ять
            file_bytes = await image.read()
            img = Image.open(io.BytesIO(file_bytes))
            
            # Зменшуємо розмір
            img.thumbnail(IMG_MAX_SIZE)
            
            # Зберігаємо в буфер як WebP
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=IMG_QUALITY, optimize=True)
            output.seek(0)
            
            # Формуємо шлях з розширенням .webp
            filename = f"{secrets.token_hex(8)}.webp"
            path = os.path.join("static/images", filename)
            os.makedirs("static/images", exist_ok=True)
            
            # Записуємо оптимізовані байти на диск
            async with aiofiles.open(path, 'wb') as f: 
                await f.write(output.read())
            
            image_url = path
        except Exception as e:
            logger.error(f"Помилка обробки зображення (Pillow): {e}")
            # Fallback: Спробувати зберегти оригінал, якщо оптимізація не вдалася
            try:
                # Повертаємо курсор на початок, бо ми його вже читали
                await image.seek(0)
                ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
                filename = f"{secrets.token_hex(8)}.{ext}"
                path = os.path.join("static/images", filename)
                os.makedirs("static/images", exist_ok=True)
                async with aiofiles.open(path, 'wb') as f: 
                    await f.write(await image.read())
                image_url = path
            except Exception as e2:
                 logger.error(f"Критична помилка збереження файлу: {e2}")
    # -----------------------------------------------

    product = Product(
        name=name, 
        price=price, 
        promotional_price=promotional_price if promotional_price and promotional_price > 0 else None,
        description=description, 
        image_url=image_url, 
        category_id=category_id, 
        production_warehouse_id=production_warehouse_id
    )

    # Додаємо модифікатори, якщо обрані
    if modifier_ids:
        modifiers = (await session.execute(select(Modifier).where(Modifier.id.in_(modifier_ids)))).scalars().all()
        product.modifiers = modifiers

    session.add(product)
    await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

@router.get("/admin/edit_product/{product_id}", response_class=HTMLResponse)
async def get_edit_product_form(
    product_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    # Завантажуємо продукт разом з його модифікаторами
    product = await session.get(Product, product_id, options=[selectinload(Product.modifiers)])
    if not product: 
        raise HTTPException(status_code=404, detail="Товар не знайдено")

    categories_res = await session.execute(select(Category))
    category_options = "".join([f'<option value="{c.id}" {"selected" if c.id == product.category_id else ""}>{html.escape(c.name)}</option>' for c in categories_res.scalars().all()])
    
    # --- Warehouse options for edit ---
    warehouses_res = await session.execute(select(Warehouse).where(Warehouse.is_production == True).order_by(Warehouse.name))
    warehouses = warehouses_res.scalars().all()
    
    wh_options = "<option value=''>-- Оберіть цех --</option>"
    for w in warehouses:
        selected = "selected" if product.production_warehouse_id == w.id else ""
        wh_options += f'<option value="{w.id}" {selected}>{html.escape(w.name)}</option>'
    # ---------------------------------------

    # --- ЛОГІКА МОДИФІКАТОРІВ ---
    all_modifiers = (await session.execute(select(Modifier).order_by(Modifier.name))).scalars().all()
    current_mod_ids = [m.id for m in product.modifiers]
    
    modifiers_html = "<div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px; max-height:200px; overflow-y:auto; border:1px solid #eee; padding:10px; border-radius:5px;'>"
    for mod in all_modifiers:
        checked = "checked" if mod.id in current_mod_ids else ""
        modifiers_html += f"""
        <div class="checkbox-group" style="margin-bottom:0;">
            <input type="checkbox" id="mod_{mod.id}" name="modifier_ids" value="{mod.id}" {checked}>
            <label for="mod_{mod.id}" style="font-weight:normal; font-size:0.9em;">{html.escape(mod.name)} (+{mod.price} грн)</label>
        </div>
        """
    modifiers_html += "</div>"
    # -----------------------------

    body = f"""
    <div class="card" style="max-width: 600px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <h2>✏️ Редагування: {html.escape(product.name)}</h2>
            <a href="/admin/products" class="button secondary">Скасувати</a>
        </div>
        
        <form action="/admin/edit_product/{product_id}" method="post" enctype="multipart/form-data">
            <div class="form-grid">
                <div>
                    <label for="name">Назва страви</label>
                    <input type="text" id="name" name="name" value="{html.escape(product.name)}" required>
                </div>
                <div>
                    <label for="price">Ціна (грн)</label>
                    <input type="number" id="price" name="price" min="1" step="0.01" value="{product.price}" required>
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label for="promotional_price">Акційна ціна (грн) <small style="color:#888;">(необов'язково)</small></label>
                <input type="number" id="promotional_price" name="promotional_price" min="0" step="0.01" value="{product.promotional_price or ''}" placeholder="0.00">
            </div>
            
            <label for="category_id">Категорія</label>
            <select id="category_id" name="category_id" required>
                {category_options}
            </select>
            
            <label for="production_warehouse_id">Цех приготування (для списання та чеків)</label>
            <select id="production_warehouse_id" name="production_warehouse_id" required>
                {wh_options}
            </select>

            <label style="margin-top:10px;">Доступні модифікатори:</label>
            {modifiers_html}
            <br>

            <label for="description">Опис</label>
            <textarea id="description" name="description" rows="4">{html.escape(product.description or '')}</textarea>
            
            <label for="image">Зображення (завантажте, щоб змінити)</label>
            <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 10px;">
                {f'<img src="/{product.image_url}" style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover; border: 1px solid #ccc;">' if product.image_url else '<div style="width:60px; height:60px; background:#eee; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#999;"><i class="fa-regular fa-image"></i></div>'}
                <input type="file" id="image" name="image" accept="image/*" style="margin-bottom: 0;">
            </div>
            
            <button type="submit" class="button" style="width: 100%; margin-top: 20px;">💾 Зберегти зміни</button>
        </form>
    </div>"""
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["products_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Редагування страви", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/edit_product/{product_id}")
async def edit_product(
    product_id: int, 
    name: str = Form(...), 
    price: Decimal = Form(...), 
    promotional_price: Optional[Decimal] = Form(None),
    description: str = Form(""), 
    category_id: int = Form(...), 
    production_warehouse_id: int = Form(None),
    modifier_ids: List[int] = Form([]),
    image: UploadFile = File(None), 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    product = await session.get(Product, product_id, options=[selectinload(Product.modifiers)])
    if not product: 
        raise HTTPException(status_code=404, detail="Товар не знайдено")

    product.name = name
    product.price = price
    product.promotional_price = promotional_price if promotional_price and promotional_price > 0 else None
    product.description = description
    product.category_id = category_id
    product.production_warehouse_id = production_warehouse_id

    # Оновлюємо список модифікаторів
    if modifier_ids:
        modifiers = (await session.execute(select(Modifier).where(Modifier.id.in_(modifier_ids)))).scalars().all()
        product.modifiers = modifiers
    else:
        product.modifiers = [] 

    # --- ОНОВЛЕННЯ ФОТО З ОПТИМІЗАЦІЄЮ ---
    if image and image.filename:
        # Видаляємо старе фото
        if product.image_url and os.path.exists(product.image_url):
            try: 
                os.remove(product.image_url)
            except OSError: 
                pass
        
        try:
            # Читаємо та оптимізуємо
            file_bytes = await image.read()
            img = Image.open(io.BytesIO(file_bytes))
            
            img.thumbnail(IMG_MAX_SIZE)
            
            output = io.BytesIO()
            img.save(output, format="WEBP", quality=IMG_QUALITY, optimize=True)
            output.seek(0)
            
            filename = f"{secrets.token_hex(8)}.webp"
            path = os.path.join("static/images", filename)
            
            async with aiofiles.open(path, 'wb') as f: 
                await f.write(output.read())
            
            product.image_url = path
        except Exception as e:
            logger.error(f"Не вдалося оптимізувати/зберегти нове зображення: {e}")
            try:
                await image.seek(0)
                ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
                filename = f"{secrets.token_hex(8)}.{ext}"
                path = os.path.join("static/images", filename)
                async with aiofiles.open(path, 'wb') as f: 
                    await f.write(await image.read())
                product.image_url = path
            except: pass

    await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

@router.get("/admin/product/toggle_active/{product_id}")
async def toggle_product_active(
    product_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    product = await session.get(Product, product_id)
    if product:
        product.is_active = not product.is_active
        await session.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

@router.get("/admin/delete_product/{product_id}")
async def delete_product(
    product_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    product = await session.get(Product, product_id)
    if product:
        image_to_delete = product.image_url
        await session.delete(product)
        await session.commit()
        
        if image_to_delete and os.path.exists(image_to_delete):
            try: 
                os.remove(image_to_delete)
            except OSError: 
                pass
                
    return RedirectResponse(url="/admin/products", status_code=303)

# --- НОВІ ФУНКЦІЇ ДЛЯ КЕРУВАННЯ МОДИФІКАТОРАМИ ---

@router.get("/admin/modifiers", response_class=HTMLResponse)
async def admin_modifiers(
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Список модифікаторів з можливістю додавання/редагування."""
    settings = await session.get(Settings, 1) or Settings()
    
    # Отримуємо всі модифікатори
    modifiers_res = await session.execute(select(Modifier).order_by(Modifier.name))
    modifiers = modifiers_res.scalars().all()
    
    rows = ""
    for m in modifiers:
        rows += f"""
        <tr>
            <td>{m.id}</td>
            <td>{html.escape(m.name)}</td>
            <td>{m.price} грн</td>
            <td class="actions">
                <a href="/admin/modifiers/edit/{m.id}" class="button-sm" title="Редагувати"><i class="fa-solid fa-pen"></i></a>
                <a href="/admin/modifiers/delete/{m.id}" onclick="return confirm('Видалити цей модифікатор? Це прибере його з усіх страв.');" class="button-sm danger" title="Видалити"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>
        """
    
    body = f"""
    <div class="card">
        <div class="toolbar">
            <h2>🥗 Модифікатори</h2>
            <div style="display:flex; gap:10px;">
                <a href="/admin/products" class="button secondary"><i class="fa-solid fa-arrow-left"></i> До страв</a>
                <button onclick="document.getElementById('add-modifier-modal').classList.add('active')" class="button"><i class="fa-solid fa-plus"></i> Додати модифікатор</button>
            </div>
        </div>
        
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th width="50">ID</th>
                        <th>Назва</th>
                        <th>Ціна</th>
                        <th style="text-align:right;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows if rows else "<tr><td colspan='4' style='text-align:center; color:#999;'>Список порожній</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="add-modifier-modal">
        <div class="modal">
            <div class="modal-header">
                <h4>Новий модифікатор</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-modifier-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/modifiers/add" method="post">
                    <label>Назва</label>
                    <input type="text" name="name" required placeholder="Наприклад: Сир">
                    <label>Ціна (грн)</label>
                    <input type="number" step="0.01" name="price" required value="0">
                    <button type="submit" class="button" style="width:100%; margin-top:15px;">Зберегти</button>
                </form>
            </div>
        </div>
    </div>
    """
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["products_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Модифікатори", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/modifiers/add")
async def add_modifier(
    name: str = Form(...),
    price: Decimal = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    mod = Modifier(name=name, price=price)
    session.add(mod)
    await session.commit()
    return RedirectResponse(url="/admin/modifiers", status_code=303)

@router.get("/admin/modifiers/edit/{modifier_id}", response_class=HTMLResponse)
async def get_edit_modifier_form(
    modifier_id: int,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    mod = await session.get(Modifier, modifier_id)
    if not mod: raise HTTPException(404, "Not found")
    
    body = f"""
    <div class="card" style="max-width:500px; margin:0 auto;">
        <h2>Редагування модифікатора</h2>
        <form action="/admin/modifiers/edit/{modifier_id}" method="post">
            <label>Назва</label>
            <input type="text" name="name" required value="{html.escape(mod.name)}">
            <label>Ціна (грн)</label>
            <input type="number" step="0.01" name="price" required value="{mod.price}">
            
            <div style="margin-top:20px; display:flex; gap:10px;">
                <button type="submit" class="button">Зберегти</button>
                <a href="/admin/modifiers" class="button secondary">Скасувати</a>
            </div>
        </form>
    </div>
    """
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["products_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Редагування модифікатора", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/modifiers/edit/{modifier_id}")
async def edit_modifier(
    modifier_id: int,
    name: str = Form(...),
    price: Decimal = Form(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    mod = await session.get(Modifier, modifier_id)
    if mod:
        mod.name = name
        mod.price = price
        await session.commit()
    return RedirectResponse(url="/admin/modifiers", status_code=303)

@router.get("/admin/modifiers/delete/{modifier_id}")
async def delete_modifier(
    modifier_id: int,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    mod = await session.get(Modifier, modifier_id)
    if mod:
        # Безпечне видалення зв'язків перед видаленням самого модифікатора
        await session.execute(product_modifier_association.delete().where(product_modifier_association.c.modifier_id == modifier_id))
        await session.delete(mod)
        await session.commit()
    return RedirectResponse(url="/admin/modifiers", status_code=303)

@router.get("/api/admin/products", response_class=JSONResponse)
async def api_get_products(
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    """API для отримання списку продуктів (використовується в JS при створенні замовлення)."""
    res = await session.execute(
        select(Product.id, Product.name, Product.price, Product.promotional_price, Product.preparation_area, Category.name.label("category"))
        .join(Category, Product.category_id == Category.id, isouter=True)
        .where(Product.is_active == True)
        .order_by(Category.sort_order, Product.name)
    )
    products = [{
        "id": row.id, 
        "name": row.name, 
        "price": float(row.price),
        "promotional_price": float(row.promotional_price) if row.promotional_price else None,
        "category": row.category or "Без категорії",
        "preparation_area": row.preparation_area
    } for row in res.mappings().all()]
    
    return JSONResponse(content=products)
