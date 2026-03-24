# admin_design_settings.py

import html
import os
import secrets
import aiofiles
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Settings
from templates import ADMIN_HTML_TEMPLATE, ADMIN_DESIGN_SETTINGS_BODY
from dependencies import get_db_session, check_credentials

router = APIRouter()

# --- Словники шрифтів для легкого керування ---
FONT_FAMILIES_SANS = [
    "Golos Text", "Inter", "Roboto", "Open Sans", "Montserrat", "Lato", "Nunito"
]
DEFAULT_FONT_SANS = "Golos Text"

FONT_FAMILIES_SERIF = [
    "Playfair Display", "Lora", "Merriweather", "EB Garamond", "PT Serif", "Cormorant"
]
DEFAULT_FONT_SERIF = "Playfair Display"
# -----------------------------------------------

@router.get("/admin/design_settings", response_class=HTMLResponse)
async def get_design_settings_page(
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Відображає сторінку налаштувань дизайну, SEO та текстів."""
    settings = await session.get(Settings, 1)
    if not settings:
        settings = Settings(id=1)
        session.add(settings)
        await session.commit()

    # --- Функція для генерації HTML <option> для <select> ---
    def get_font_options(font_list: list, selected_font: str, default_font: str) -> str:
        options_html = ""
        current_font = selected_font or default_font
        for font in font_list:
            is_default = "(За замовчуванням)" if font == default_font else ""
            is_selected = "selected" if font == current_font else ""
            options_html += f'<option value="{html.escape(font)}" {is_selected}>{html.escape(font)} {is_default}</option>\n'
        return options_html
    # -----------------------------------------------------

    font_options_sans = get_font_options(FONT_FAMILIES_SANS, settings.font_family_sans, DEFAULT_FONT_SANS)
    font_options_serif = get_font_options(FONT_FAMILIES_SERIF, settings.font_family_serif, DEFAULT_FONT_SERIF)

    # Отримуємо поточний логотип для відображення
    logo_url_fixed = settings.logo_url.replace("\\", "/") if settings.logo_url else ""
    current_logo_html = f'<img src="/{logo_url_fixed}" alt="Поточний логотип" style="height: 50px; margin-top: 10px;">' if logo_url_fixed else ''
    
    # Cache buster для фавіконок
    cache_buster = secrets.token_hex(4)

    # Підготовка значень доставки
    free_delivery_val = settings.free_delivery_from if settings.free_delivery_from is not None else ""

    # Формуємо основне тіло з існуючого шаблону
    body_content = ADMIN_DESIGN_SETTINGS_BODY.format(
        # --- SEO Заголовок ---
        site_title=html.escape(settings.site_title or "Назва"),
        site_header_text=html.escape(settings.site_header_text or ""),
        
        seo_description=html.escape(settings.seo_description or ""),
        seo_keywords=html.escape(settings.seo_keywords or ""),
        
        # --- Кольори ---
        primary_color=settings.primary_color or "#5a5a5a",
        secondary_color=settings.secondary_color or "#eeeeee",
        background_color=settings.background_color or "#f4f4f4",
        text_color=settings.text_color or "#333333",
        footer_bg_color=settings.footer_bg_color or "#333333",
        footer_text_color=settings.footer_text_color or "#ffffff",
        
        # --- Навігація ---
        category_nav_bg_color=settings.category_nav_bg_color or "#ffffff",
        category_nav_text_color=settings.category_nav_text_color or "#333333",

        current_logo_html=current_logo_html,
        cache_buster=cache_buster,

        # --- Шрифти ---
        font_options_sans=font_options_sans,
        font_options_serif=font_options_serif,
        
        # --- Контакти ---
        footer_address=html.escape(settings.footer_address or ""),
        footer_phone=html.escape(settings.footer_phone or ""),
        working_hours=html.escape(settings.working_hours or ""),
        instagram_url=html.escape(settings.instagram_url or ""),
        facebook_url=html.escape(settings.facebook_url or ""),
        wifi_ssid=html.escape(settings.wifi_ssid or ""),
        wifi_password=html.escape(settings.wifi_password or ""),

        # --- Доставка ---
        delivery_cost=settings.delivery_cost,
        free_delivery_from=free_delivery_val,
        delivery_zones_content=html.escape(settings.delivery_zones_content or ""),

        telegram_welcome_message=html.escape(settings.telegram_welcome_message or "Шановний {user_name}, ласкаво просимо! 👋\n\nМи раді вас бачити. Оберіть опцію:"),
    )

    # --- ДОДАВАННЯ БЛОКУ ДЛЯ SEO ШАБЛОНІВ ТА ANALYTICS ---
    seo_mask_title = html.escape(settings.product_seo_mask_title or "{name} - {price} грн | {site_title}")
    seo_mask_desc = html.escape(settings.product_seo_mask_desc or "{name}. {description}")
    ga_id = html.escape(settings.google_analytics_id or "")

    seo_extensions_html = f"""
    <div class="card" style="margin-top: 20px;">
        <h3 style="margin-bottom: 15px; display:flex; align-items:center; gap:10px;">
            <i class="fa-solid fa-robot"></i> Авто-SEO для товарів
        </h3>
        <p style="font-size: 0.9em; color: #666; margin-bottom: 15px; background: #f8f9fa; padding: 10px; border-radius: 5px;">
            Ці шаблони використовуються для автоматичної генерації мета-тегів сторінок товарів.<br>
            <strong>Змінні:</strong> <code>{{name}}</code> (назва), <code>{{price}}</code> (ціна), 
            <code>{{description}}</code> (опис), <code>{{category}}</code> (категорія), <code>{{site_title}}</code> (назва сайту).
        </p>
        
        <div class="form-grid">
            <div>
                <label>Шаблон Заголовка (Browser Title)</label>
                <input type="text" name="product_seo_mask_title" value="{seo_mask_title}" placeholder="{{name}} - {{price}} грн">
            </div>
            <div>
                <label>Шаблон Опису (Meta Description)</label>
                <textarea name="product_seo_mask_desc" rows="1" style="resize:vertical;">{seo_mask_desc}</textarea>
            </div>
        </div>
    </div>

    <div class="card" style="margin-top: 20px;">
        <h3 style="margin-bottom: 15px;"><i class="fa-solid fa-chart-line"></i> Аналітика</h3>
        <label>Google Analytics 4 ID (G-XXXXXXXXXX)</label>
        <input type="text" name="google_analytics_id" value="{ga_id}" placeholder="G-XXXXXXXXXX">
        <p style="font-size: 0.85rem; color: #888;">Залиште порожнім, щоб вимкнути.</p>
    </div>
    """

    # --- БЛОК ІНТЕГРАЦІЇ З RESTIFY ---
    restify_email = html.escape(settings.restify_email or "")
    restify_password = settings.restify_password if settings.restify_password else ""

    restify_html = f"""
    <div class="card" style="margin-top: 20px; border: 2px solid #c7d2fe; background: #e0e7ff;">
        <h3 style="margin-bottom: 15px; display:flex; align-items:center; gap:10px; color: #3730a3;">
            <i class="fa-solid fa-rocket"></i> Інтеграція з Restify (Глобальна Доставка)
        </h3>
        <p style="font-size: 0.9em; color: #4338ca; margin-bottom: 15px; background: #c7d2fe; padding: 10px; border-radius: 5px;">
            Введіть Email та Пароль від вашого акаунту <b>ресторану-партнера</b> у системі Restify. Це дозволить адміністраторам автоматично викликати кур'єрів через PWA.
        </p>
        
        <div class="form-grid">
            <div>
                <label style="color: #3730a3;">Email від акаунту Restify</label>
                <input type="email" name="restify_email" value="{restify_email}" placeholder="restaurant@example.com" style="border: 1px solid #a5b4fc;">
            </div>
            <div>
                <label style="color: #3730a3;">Пароль від акаунту Restify</label>
                <input type="password" name="restify_password" value="{restify_password}" placeholder="Введіть пароль" style="border: 1px solid #a5b4fc;">
            </div>
        </div>
    </div>
    """

    # Вставляємо нові блоки перед закриваючим тегом форми (перед кнопкою зберегти)
    final_body = body_content.replace('</form>', f'{seo_extensions_html}{restify_html}<div style="height:20px;"></div></form>')

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["design_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Дизайн та SEO", 
        body=final_body, 
        site_title=settings.site_title or "Назва",
        **active_classes
    ))

@router.post("/admin/design_settings")
async def save_design_settings(
    site_title: str = Form(...),
    site_header_text: str = Form(""),
    
    seo_description: str = Form(""),
    seo_keywords: str = Form(""),
    
    # --- SEO Templates & Analytics ---
    product_seo_mask_title: str = Form("{name} - {price} грн | {site_title}"),
    product_seo_mask_desc: str = Form("{name}. {description}"),
    google_analytics_id: str = Form(""),
    
    # --- RESTIFY INTEGRATION ---
    restify_email: str = Form(""),
    restify_password: str = Form(""),
    
    # --- Кольори ---
    primary_color: str = Form(...),
    secondary_color: str = Form(...),
    background_color: str = Form(...),
    text_color: str = Form("#333333"),
    footer_bg_color: str = Form("#333333"),
    footer_text_color: str = Form("#ffffff"),
    category_nav_bg_color: str = Form("#ffffff"),
    category_nav_text_color: str = Form("#333333"),

    # --- Зображення та іконки ---
    header_image_file: UploadFile = File(None),
    logo_file: UploadFile = File(None),
    apple_touch_icon: UploadFile = File(None),
    favicon_32x32: UploadFile = File(None),
    favicon_16x16: UploadFile = File(None),
    favicon_ico: UploadFile = File(None),
    site_webmanifest: UploadFile = File(None),
    
    # --- PWA Android Icons ---
    icon_192: UploadFile = File(None),
    icon_512: UploadFile = File(None),
    
    # --- Підвал та контакти ---
    footer_address: str = Form(""),
    footer_phone: str = Form(""),
    working_hours: str = Form(""),
    instagram_url: str = Form(""),
    facebook_url: str = Form(""),
    wifi_ssid: str = Form(""),
    wifi_password: str = Form(""),

    # --- Доставка ---
    delivery_cost: Decimal = Form(0.00),
    free_delivery_from: Optional[str] = Form(None),
    delivery_zones_content: str = Form(""),

    font_family_sans: str = Form(...),
    font_family_serif: str = Form(...),
    telegram_welcome_message: str = Form(...),
    
    session: AsyncSession = Depends(get_db_session),
    username: str = Depends(check_credentials)
):
    """Зберігає налаштування дизайну, SEO, контактів та текстів."""
    settings = await session.get(Settings, 1)
    if not settings:
        settings = Settings(id=1)
        session.add(settings)

    # --- Збереження основних текстів ---
    settings.site_title = site_title
    settings.site_header_text = site_header_text
    settings.seo_description = seo_description
    settings.seo_keywords = seo_keywords
    
    # --- Збереження нових SEO полів ---
    settings.product_seo_mask_title = product_seo_mask_title
    settings.product_seo_mask_desc = product_seo_mask_desc
    settings.google_analytics_id = google_analytics_id.strip() if google_analytics_id else None
    
    # --- ЗБЕРЕЖЕННЯ RESTIFY ---
    if restify_email and restify_email.strip():
        settings.restify_email = restify_email.strip()
    else:
        settings.restify_email = None
        settings.restify_password = None
        settings.restify_token = None
        
    if restify_password and restify_password.strip():
        # Якщо пароль змінився, очищаємо старий токен, щоб система здійснила перелогін
        if settings.restify_password != restify_password.strip():
            settings.restify_token = None
        settings.restify_password = restify_password.strip()

    # --- Збереження кольорів ---
    settings.primary_color = primary_color
    settings.secondary_color = secondary_color
    settings.background_color = background_color
    settings.text_color = text_color
    settings.footer_bg_color = footer_bg_color
    settings.footer_text_color = footer_text_color
    settings.category_nav_bg_color = category_nav_bg_color
    settings.category_nav_text_color = category_nav_text_color

    # --- Обробка ЛОГОТИПУ ---
    if logo_file and logo_file.filename:
        if settings.logo_url and os.path.exists(settings.logo_url):
            try: os.remove(settings.logo_url)
            except OSError: pass
        
        ext = logo_file.filename.split('.')[-1] if '.' in logo_file.filename else 'jpg'
        filename = f"logo_{secrets.token_hex(8)}.{ext}"
        fs_path = os.path.join("static", "images", filename)
        
        try:
            async with aiofiles.open(fs_path, 'wb') as f:
                await f.write(await logo_file.read())
            settings.logo_url = f"static/images/{filename}"
        except Exception as e:
            print(f"Error saving logo: {e}")

    # --- Обробка зображення ШАПКИ ---
    if header_image_file and header_image_file.filename:
        if settings.header_image_url and os.path.exists(settings.header_image_url):
            try: os.remove(settings.header_image_url)
            except OSError: pass
        
        ext = header_image_file.filename.split('.')[-1] if '.' in header_image_file.filename else 'jpg'
        filename = f"header_bg_{secrets.token_hex(8)}.{ext}"
        fs_path = os.path.join("static", "images", filename)
        
        try:
            async with aiofiles.open(fs_path, 'wb') as f:
                await f.write(await header_image_file.read())
            settings.header_image_url = f"static/images/{filename}"
        except Exception as e:
            print(f"Error saving header image: {e}")
    
    # --- Збереження ФАВІКОНІВ та PWA іконок ---
    favicon_dir = "static/favicons"
    os.makedirs(favicon_dir, exist_ok=True)
    
    icons_to_save = {
        "apple-touch-icon.png": apple_touch_icon,
        "favicon-32x32.png": favicon_32x32,
        "favicon-16x16.png": favicon_16x16,
        "favicon.ico": favicon_ico,
        "site.webmanifest": site_webmanifest,
        "icon-192.png": icon_192,
        "icon-512.png": icon_512
    }

    for name, file_obj in icons_to_save.items():
        if file_obj and file_obj.filename:
            try:
                async with aiofiles.open(os.path.join(favicon_dir, name), 'wb') as f:
                    await f.write(await file_obj.read())
            except Exception as e:
                print(f"Error saving icon {name}: {e}")

    # --- Збереження контактів та Wi-Fi ---
    settings.footer_address = footer_address
    settings.footer_phone = footer_phone
    settings.working_hours = working_hours
    settings.instagram_url = instagram_url
    settings.facebook_url = facebook_url
    settings.wifi_ssid = wifi_ssid
    settings.wifi_password = wifi_password

    # --- Збереження Доставки ---
    settings.delivery_cost = delivery_cost
    settings.delivery_zones_content = delivery_zones_content
    
    if free_delivery_from and free_delivery_from.strip():
        try:
            settings.free_delivery_from = Decimal(free_delivery_from)
        except:
            settings.free_delivery_from = None
    else:
        settings.free_delivery_from = None

    settings.font_family_sans = font_family_sans
    settings.font_family_serif = font_family_serif
    settings.telegram_welcome_message = telegram_welcome_message

    await session.commit()
    
    return RedirectResponse(url="/admin/design_settings?saved=true", status_code=303)