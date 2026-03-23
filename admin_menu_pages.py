# admin_menu_pages.py

import html
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import MenuItem, Settings
from templates import ADMIN_HTML_TEMPLATE
from dependencies import get_db_session, check_credentials

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/admin/menu", response_class=HTMLResponse)
async def admin_menu_items(
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Відображає список інформаційних сторінок (меню)."""
    settings = await session.get(Settings, 1) or Settings()
    
    # Отримуємо всі сторінки, відсортовані за порядком
    menu_items_res = await session.execute(select(MenuItem).order_by(MenuItem.sort_order, MenuItem.title))
    menu_items = menu_items_res.scalars().all()

    rows = ""
    for item in menu_items:
        # Бейджи для статусів
        web_badge = "<span class='badge badge-success'>Так</span>" if item.show_on_website else "<span class='badge badge-secondary'>Ні</span>"
        tg_badge = "<span class='badge badge-success'>Так</span>" if item.show_in_telegram else "<span class='badge badge-secondary'>Ні</span>"
        # НОВИЙ БЕЙДЖ
        qr_badge = "<span class='badge badge-success'>Так</span>" if item.show_in_qr else "<span class='badge badge-secondary'>Ні</span>"
        
        rows += f"""
        <tr>
            <td style="text-align:center; color:#888;">{item.id}</td>
            <td style="font-weight:600;">{html.escape(item.title)}</td>
            <td style="text-align:center;">{item.sort_order}</td>
            <td style="text-align:center;">{web_badge}</td>
            <td style="text-align:center;">{tg_badge}</td>
            <td style="text-align:center;">{qr_badge}</td>
            <td class="actions">
                <a href="/admin/menu/edit/{item.id}" class="button-sm" title="Редагувати"><i class="fa-solid fa-pen"></i></a>
                <a href="/admin/menu/delete/{item.id}" onclick="return confirm('Ви впевнені, що хочете видалити цю сторінку?');" class="button-sm danger" title="Видалити"><i class="fa-solid fa-trash"></i></a>
            </td>
        </tr>"""

    # Стилі (такі ж, як в admin_products для єдиного стилю)
    styles = """
    <style>
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; display: inline-block; }
        .badge-success { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
        .badge-secondary { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
        .toolbar { display: flex; justify-content: flex-end; margin-bottom: 20px; }
        .button-sm i { pointer-events: none; }
    </style>
    """

    body = f"""
    {styles}
    
    <div class="card">
        <div class="toolbar">
            <button class="button" onclick="document.getElementById('add-page-modal').classList.add('active')">
                <i class="fa-solid fa-plus"></i> Додати сторінку
            </button>
        </div>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th width="50">ID</th>
                        <th>Заголовок (Назва кнопки)</th>
                        <th width="80" style="text-align:center;">Сорт.</th>
                        <th width="80" style="text-align:center;">Сайт</th>
                        <th width="80" style="text-align:center;">TG</th>
                        <th width="80" style="text-align:center;">QR</th>
                        <th width="100" style="text-align:right;">Дії</th>
                    </tr>
                </thead>
                <tbody>
                    {rows or "<tr><td colspan='7' style='text-align:center; padding:20px; color:#777;'>Сторінок поки немає</td></tr>"}
                </tbody>
            </table>
        </div>
    </div>

    <div class="modal-overlay" id="add-page-modal">
        <div class="modal">
            <div class="modal-header">
                <h4><i class="fa-solid fa-file-lines"></i> Нова сторінка</h4>
                <button type="button" class="close-button" onclick="document.getElementById('add-page-modal').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <form action="/admin/menu/add" method="post">
                    <label for="title">Заголовок (на кнопці) *</label>
                    <input type="text" id="title" name="title" required placeholder="Наприклад: Про нас">
                    
                    <label for="sort_order">Порядок сортування</label>
                    <input type="number" id="sort_order" name="sort_order" value="100" required>
                    
                    <div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
                        <div class="checkbox-group">
                            <input type="checkbox" id="show_on_website" name="show_on_website" value="true">
                            <label for="show_on_website">На сайті</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="show_in_telegram" name="show_in_telegram" value="true">
                            <label for="show_in_telegram">В Telegram</label>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" id="show_in_qr" name="show_in_qr" value="true">
                            <label for="show_in_qr">В QR Меню</label>
                        </div>
                    </div>

                    <label for="content">Зміст сторінки (HTML підтримується) *</label>
                    <textarea id="content" name="content" rows="8" required placeholder="Текст, картинки, опис..."></textarea>
                    
                    <button type="submit" class="button" style="width: 100%; margin-top: 10px;">Додати</button>
                </form>
            </div>
        </div>
    </div>
    """

    # --- ИСПРАВЛЕНИЕ ---
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["menu_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Сторінки меню", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/menu/add")
async def add_menu_item(
    title: str = Form(...), 
    content: str = Form(...), 
    sort_order: int = Form(100), 
    show_on_website: bool = Form(False), 
    show_in_telegram: bool = Form(False), 
    show_in_qr: bool = Form(False),
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    session.add(MenuItem(
        title=title.strip(), 
        content=content, 
        sort_order=sort_order, 
        show_on_website=show_on_website, 
        show_in_telegram=show_in_telegram,
        show_in_qr=show_in_qr
    ))
    await session.commit()
    return RedirectResponse(url="/admin/menu", status_code=303)

@router.get("/admin/menu/edit/{item_id}", response_class=HTMLResponse)
async def get_edit_menu_item_form(
    item_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1) or Settings()
    item = await session.get(MenuItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")

    body = f"""
    <div class="card" style="max-width: 700px; margin: 0 auto;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <h2>✏️ Редагування сторінки</h2>
            <a href="/admin/menu" class="button secondary">Скасувати</a>
        </div>
        
        <form action="/admin/menu/edit/{item_id}" method="post">
            <label for="title">Заголовок (на кнопці) *</label>
            <input type="text" id="title" name="title" value="{html.escape(item.title)}" required>
            
            <label for="sort_order">Порядок сортування</label>
            <input type="number" id="sort_order" name="sort_order" value="{item.sort_order}" required>
            
            <div style="display: flex; gap: 20px; margin-bottom: 15px; flex-wrap: wrap;">
                <div class="checkbox-group">
                    <input type="checkbox" id="show_on_website" name="show_on_website" value="true" {'checked' if item.show_on_website else ''}>
                    <label for="show_on_website">Показувати на сайті</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="show_in_telegram" name="show_in_telegram" value="true" {'checked' if item.show_in_telegram else ''}>
                    <label for="show_in_telegram">Показувати в Telegram</label>
                </div>
                <div class="checkbox-group">
                    <input type="checkbox" id="show_in_qr" name="show_in_qr" value="true" {'checked' if item.show_in_qr else ''}>
                    <label for="show_in_qr">Показувати в QR Меню</label>
                </div>
            </div>

            <label for="content">Зміст сторінки (HTML підтримується) *</label>
            <textarea id="content" name="content" rows="12" required>{html.escape(item.content)}</textarea>
            
            <button type="submit" class="button" style="width: 100%; margin-top: 20px;">💾 Зберегти зміни</button>
        </form>
    </div>
    """

    # --- ИСПРАВЛЕНИЕ ---
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["menu_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title=f"Редагування: {html.escape(item.title)}", 
        body=body, 
        site_title=settings.site_title or "Назва", 
        **active_classes
    ))

@router.post("/admin/menu/edit/{item_id}")
async def edit_menu_item(
    item_id: int, 
    title: str = Form(...), 
    content: str = Form(...), 
    sort_order: int = Form(100), 
    show_on_website: bool = Form(False), 
    show_in_telegram: bool = Form(False),
    show_in_qr: bool = Form(False),
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    item = await session.get(MenuItem, item_id)
    if item:
        item.title = title.strip()
        item.content = content
        item.sort_order = sort_order
        item.show_on_website = show_on_website
        item.show_in_telegram = show_in_telegram
        item.show_in_qr = show_in_qr
        await session.commit()
    return RedirectResponse(url="/admin/menu", status_code=303)

@router.get("/admin/menu/delete/{item_id}")
async def delete_menu_item(
    item_id: int, 
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials)
):
    item = await session.get(MenuItem, item_id)
    if item:
        await session.delete(item)
        await session.commit()
    return RedirectResponse(url="/admin/menu", status_code=303)