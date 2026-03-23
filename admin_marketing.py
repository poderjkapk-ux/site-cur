# admin_marketing.py

import os
import secrets
import aiofiles
import html
from typing import Optional

from fastapi import APIRouter, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import MarketingPopup, Settings, Banner
from templates import ADMIN_HTML_TEMPLATE, ADMIN_MARKETING_BODY
from dependencies import get_db_session, check_credentials

router = APIRouter()

@router.get("/admin/marketing", response_class=HTMLResponse)
async def get_marketing_page(
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    # Отримуємо налаштування (або створюємо порожній об'єкт, якщо ще немає в БД)
    settings = await session.get(Settings, 1) or Settings()
    
    # --- ОТРИМАННЯ ДАНИХ POPUP ---
    # Отримуємо перший попап (будемо використовувати один редагований)
    result_popup = await session.execute(select(MarketingPopup).limit(1))
    popup = result_popup.scalars().first()
    
    if not popup:
        # Створюємо порожній об'єкт для шаблону, якщо в БД немає запису
        popup = MarketingPopup(title="", content="", button_text="", button_link="", is_active=False, show_once=True)

    current_popup_image = ""
    if popup.image_url:
        current_popup_image = f'<div style="margin: 10px 0;"><img src="/{popup.image_url}" style="max-height: 150px; border-radius: 8px;"></div>'

    # --- ОТРИМАННЯ БАНЕРІВ (КАРУСЕЛЬ) ---
    banners_res = await session.execute(select(Banner).order_by(Banner.sort_order))
    banners = banners_res.scalars().all()

    banners_list_html = ""
    if banners:
        for b in banners:
            status_icon = "✅" if b.is_active else "❌"
            img_html = f'<img src="/{b.image_url}" style="width: 100%; height: 100%; object-fit: cover;">'
            
            banners_list_html += f"""
            <div class="banner-item" style="display: flex; align-items: center; background: #fff; padding: 15px; margin-bottom: 10px; border-radius: 12px; border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.02);">
                <div style="width: 120px; height: 60px; border-radius: 8px; overflow: hidden; margin-right: 15px; background: #f0f0f0; flex-shrink: 0;">
                    {img_html}
                </div>
                <div style="flex-grow: 1; margin-right: 15px;">
                    <div style="font-weight: 600; font-size: 1.05rem;">{html.escape(b.title or 'Без назви')}</div>
                    <div style="font-size: 0.85rem; color: #64748b;">
                        Сортування: <b>{b.sort_order}</b> | 
                        Посилання: <code style="background:#f1f5f9; padding:2px 4px; border-radius:4px;">{html.escape(b.link or '-')}</code>
                    </div>
                </div>
                <div style="display: flex; gap: 15px; align-items: center;">
                    <span style="font-size: 1.2rem; cursor: help;" title="Статус активності">{status_icon}</span>
                    <a href="/admin/marketing/delete_banner/{b.id}" onclick="return confirm('Ви впевнені, що хочете видалити цей банер?')" 
                       style="color: #ef4444; text-decoration: none; display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; background: #fee2e2; border-radius: 8px; transition: background 0.2s;">
                       <i class="fa-solid fa-trash"></i> 🗑️
                    </a>
                </div>
            </div>
            """
    else:
        banners_list_html = '<div style="text-align:center; padding: 30px; color: #94a3b8; background: #f8fafc; border-radius: 12px; border: 1px dashed #cbd5e1;">Список банерів порожній. Додайте перший банер!</div>'

    # --- HTML БЛОКИ СТОРІНКИ ---

    # 1. Блок налаштувань Analytics та Ads
    ga_id_val = html.escape(settings.google_analytics_id or "")
    ads_id_val = html.escape(settings.google_ads_id or "")
    ads_label_val = html.escape(settings.google_ads_conversion_label or "")

    analytics_html = f"""
    <div class="card" style="margin-bottom: 30px;">
        <h3 style="margin-top: 0; margin-bottom: 15px; font-size: 1.2rem; color: #333;">📊 Трекінг та Аналітика</h3>
        <form action="/admin/marketing/save_settings" method="post">
            
            <div style="margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #eee;">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #333;">Google Analytics 4 (Measurement ID)</label>
                <input type="text" name="google_analytics_id" value="{ga_id_val}" 
                       placeholder="G-XXXXXXXXXX" 
                       style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 1rem; background: #f8fafc;">
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 6px;">
                    Ідентифікатор потоку даних.
                </div>
            </div>

            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #333;">Google Ads ID (Conversion ID)</label>
                <input type="text" name="google_ads_id" value="{ads_id_val}" 
                       placeholder="AW-XXXXXXXXXX" 
                       style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 1rem; background: #f8fafc; margin-bottom: 10px;">
                
                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #333;">Google Ads Conversion Label</label>
                <input type="text" name="google_ads_conversion_label" value="{ads_label_val}" 
                       placeholder="Наприклад: AbC_xYz123" 
                       style="width: 100%; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 1rem; background: #f8fafc;">
                <div style="font-size: 0.85rem; color: #64748b; margin-top: 6px;">
                    Label конверсії "Покупка" (Purchase).
                </div>
            </div>

            <button type="submit" style="background: #333; color: white; border: none; padding: 12px 24px; border-radius: 10px; cursor: pointer; font-weight: 600; transition: background 0.2s;">
                Зберегти налаштування трекінгу
            </button>
        </form>
    </div>
    """

    # 2. Блок управління банерами
    banners_section_html = f"""
    <div class="card" style="margin-bottom: 30px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <h3 style="margin:0; font-size: 1.2rem; color: #333;">🖼️ Рекламні банери (Карусель)</h3>
        </div>
        
        <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 25px; border: 1px dashed #cbd5e1;">
            <h4 style="margin-top:0; margin-bottom: 15px; color: #475569;">Додати новий банер</h4>
            <form action="/admin/marketing/add_banner" method="post" enctype="multipart/form-data" style="display: grid; gap: 15px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <label style="display:block; margin-bottom:5px; font-weight:600; font-size: 0.9rem;">Назва (для адміна)</label>
                        <input type="text" name="title" placeholder="Наприклад: Акція піца" style="width:100%; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
                    </div>
                    <div>
                        <label style="display:block; margin-bottom:5px; font-weight:600; font-size: 0.9rem;">Посилання (опціонально)</label>
                        <input type="text" name="link" placeholder="/?p=slug або #cat-1" style="width:100%; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <label style="display:block; margin-bottom:5px; font-weight:600; font-size: 0.9rem;">Зображення (Горизонтальне!)</label>
                        <input type="file" name="image_file" required accept="image/*" style="width:100%; padding: 8px; background: white; border-radius: 8px; border: 1px solid #e2e8f0;">
                    </div>
                    <div>
                        <label style="display:block; margin-bottom:5px; font-weight:600; font-size: 0.9rem;">Сортування (менше число - вище)</label>
                        <input type="number" name="sort_order" value="0" style="width:100%; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
                    </div>
                </div>
                <div>
                     <label style="display:flex; align-items:center; gap: 10px; cursor:pointer; user-select: none;">
                        <input type="checkbox" name="is_active" value="true" checked style="width: 20px; height: 20px; accent-color: #2563eb;">
                        <span style="font-weight:600; color: #333;">Активний (показувати на сайті)</span>
                    </label>
                </div>
                <button type="submit" style="background: #2563eb; color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 600; justify-self: start;">
                    ➕ Додати банер
                </button>
            </form>
        </div>

        <div class="banners-list">
            {banners_list_html}
        </div>
    </div>
    """

    # 3. Блок Popup
    popup_form_body = ADMIN_MARKETING_BODY.format(
        popup_id=popup.id if popup.id else "new",
        title=html.escape(popup.title or ""),
        content=html.escape(popup.content or ""),
        current_image_html=current_popup_image,
        button_text=html.escape(popup.button_text or ""),
        button_link=html.escape(popup.button_link or ""),
        is_active_checked="checked" if popup.is_active else "",
        show_once_checked="checked" if popup.show_once else ""
    )
    
    popup_section_html = f"""
    <div class="card">
        <h3 style="margin-top: 0; margin-bottom: 15px; font-size: 1.2rem; color: #333;">🔔 Спливаючий Popup (Акція)</h3>
        {popup_form_body}
    </div>
    """
    
    # Збираємо все разом
    full_body = analytics_html + banners_section_html + popup_section_html
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    # Активуємо пункт меню налаштувань
    active_classes["settings_active"] = "active" 

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Маркетинг", 
        body=full_body, 
        site_title=settings.site_title or "Назва",
        **active_classes
    ))

# --- HANDLERS (ОБРОБНИКИ ЗАПИТІВ) ---

@router.post("/admin/marketing/save_settings")
async def save_marketing_settings(
    google_analytics_id: str = Form(""),
    google_ads_id: str = Form(""),
    google_ads_conversion_label: str = Form(""),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    settings = await session.get(Settings, 1)
    if not settings:
        settings = Settings(id=1)
        session.add(settings)

    # Зберігаємо або NULL, якщо рядок порожній
    settings.google_analytics_id = google_analytics_id.strip() if google_analytics_id.strip() else None
    settings.google_ads_id = google_ads_id.strip() if google_ads_id.strip() else None
    settings.google_ads_conversion_label = google_ads_conversion_label.strip() if google_ads_conversion_label.strip() else None
    
    await session.commit()
    return RedirectResponse(url="/admin/marketing", status_code=303)

@router.post("/admin/marketing/add_banner")
async def add_banner(
    title: str = Form(""),
    link: str = Form(""),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    image_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    if not image_file or not image_file.filename:
        # Можна додати обробку помилки або просто редірект
        return RedirectResponse(url="/admin/marketing?error=missing_file", status_code=303)

    # Збереження файлу
    ext = image_file.filename.split('.')[-1] if '.' in image_file.filename else 'jpg'
    filename = f"banner_{secrets.token_hex(8)}.{ext}"
    
    # Переконаємось, що папка існує
    os.makedirs("static/images", exist_ok=True)
    fs_path = os.path.join("static", "images", filename)
    
    try:
        async with aiofiles.open(fs_path, 'wb') as f:
            await f.write(await image_file.read())
        
        # Створення запису в БД
        banner = Banner(
            title=title,
            link=link,
            sort_order=sort_order,
            is_active=is_active,
            image_url=f"static/images/{filename}"
        )
        session.add(banner)
        await session.commit()
        
    except Exception as e:
        print(f"Error saving banner: {e}")
        return RedirectResponse(url="/admin/marketing?error=save_failed", status_code=303)

    return RedirectResponse(url="/admin/marketing", status_code=303)

@router.get("/admin/marketing/delete_banner/{banner_id}")
async def delete_banner(
    banner_id: int,
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    banner = await session.get(Banner, banner_id)
    if banner:
        # Видаляємо файл з диску
        if banner.image_url:
            # Нормалізуємо шлях (на випадок Windows/Linux різниці слешів)
            file_path = banner.image_url.replace("/", os.sep)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"Error deleting banner file: {e}")
        
        # Видаляємо з БД
        await session.delete(banner)
        await session.commit()
        
    return RedirectResponse(url="/admin/marketing", status_code=303)

@router.post("/admin/marketing/save")
async def save_marketing_popup(
    popup_id: str = Form(...),
    title: str = Form(""),
    content: str = Form(""),
    button_text: str = Form(""),
    button_link: str = Form(""),
    is_active: bool = Form(False),
    show_once: bool = Form(False),
    image_file: UploadFile = File(None),
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    if popup_id == "new" or not popup_id.isdigit():
        popup = MarketingPopup()
        session.add(popup)
    else:
        popup = await session.get(MarketingPopup, int(popup_id))
        if not popup:
            popup = MarketingPopup()
            session.add(popup)
    
    popup.title = title
    popup.content = content
    popup.button_text = button_text
    popup.button_link = button_link
    popup.is_active = is_active
    popup.show_once = show_once
    
    # Обробка зображення Popup
    if image_file and image_file.filename:
        # Видаляємо старе, якщо було
        if popup.image_url and os.path.exists(popup.image_url):
            try: os.remove(popup.image_url)
            except OSError: pass
            
        ext = image_file.filename.split('.')[-1] if '.' in image_file.filename else 'jpg'
        filename = f"popup_{secrets.token_hex(8)}.{ext}"
        
        os.makedirs("static/images", exist_ok=True)
        fs_path = os.path.join("static", "images", filename)
        
        try:
            async with aiofiles.open(fs_path, 'wb') as f:
                await f.write(await image_file.read())
            popup.image_url = f"static/images/{filename}"
        except Exception as e:
            print(f"Error saving popup image: {e}")

    await session.commit()
    return RedirectResponse(url="/admin/marketing", status_code=303)