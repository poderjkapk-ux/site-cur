# main.py

import asyncio
import logging
import sys
import os
import secrets
import re
import aiofiles
import json
import html
from contextlib import asynccontextmanager
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import quote_plus as url_quote_plus

# --- FastAPI & Uvicorn ---
from fastapi import FastAPI, Form, Request, Depends, HTTPException, File, UploadFile, Body, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
# Виправлення для Windows: перемикання на ProactorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- Aiogram ---
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
# ВАЖЛИВО: Імпорт сесії для налаштування таймаутів
from aiogram.client.session.aiohttp import AiohttpSession 
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SQLAlchemy ---
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
import sqlalchemy as sa
from sqlalchemy import select, func, desc, or_

# --- КОНФІГУРАЦІЯ ---
from dotenv import load_dotenv
load_dotenv()

# --- Локальні імпорти ---
from templates import (
    ADMIN_HTML_TEMPLATE, 
    ADMIN_ORDER_FORM_BODY, ADMIN_SETTINGS_BODY, 
    ADMIN_REPORTS_BODY
)
# ВАЖЛИВО: Імпортуємо оновлений шаблон клієнтської частини напряму
from tpl_client_web import WEB_ORDER_HTML
from tpl_404 import HTML_404_TEMPLATE

from models import *
import inventory_models 
from inventory_models import Unit, Warehouse, Modifier

from admin_handlers import register_admin_handlers
from courier_handlers import register_courier_handlers
from notification_manager import notify_new_order_to_staff
from admin_clients import router as clients_router
from dependencies import get_db_session, check_credentials
from auth_utils import get_password_hash 

# Імпорт менеджера WebSocket
from websocket_manager import manager

# --- ІМПОРТИ РОУТЕРІВ ---
from admin_order_management import router as admin_order_router
from admin_tables import router as admin_tables_router
from in_house_menu import router as in_house_menu_router
from admin_design_settings import router as admin_design_router
from admin_cash import router as admin_cash_router
from admin_reports import router as admin_reports_router
from staff_pwa import router as staff_router
from admin_products import router as admin_products_router
from admin_menu_pages import router as admin_menu_pages_router
from admin_employees import router as admin_employees_router
from admin_statuses import router as admin_statuses_router
from admin_inventory import router as admin_inventory_router
import admin_marketing 

PRODUCTS_PER_PAGE = 5

# --- ФУНКЦІЯ НОРМАЛІЗАЦІЇ ТЕЛЕФОНУ ---
def normalize_phone(phone: str) -> Optional[str]:
    """
    Приводить телефон до єдиного формату +380XXXXXXXXX
    """
    if not phone:
        return None
    
    digits = re.sub(r'\D', '', str(phone))
    
    if len(digits) == 10 and digits.startswith('0'):
        digits = '38' + digits
    elif len(digits) == 9:
        digits = '380' + digits
        
    return '+' + digits

# --- ФУНКЦІЯ ТРАНСЛІТЕРАЦІЇ ДЛЯ SEO (SLUG) ---
def transliterate_slug(text: str) -> str:
    converter = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye', 
        'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l', 
        'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 
        'ю': 'yu', 'я': 'ya', ' ': '-', "'": '', '’': ''
    }
    text = text.lower()
    result = []
    for char in text:
        if char in converter:
            result.append(converter[char])
        elif re.match(r'[a-z0-9\-]', char):
            result.append(char)
    
    res_str = "".join(result)
    res_str = re.sub(r'-+', '-', res_str)
    return res_str.strip('-')

class CheckoutStates(StatesGroup):
    waiting_for_delivery_type = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    confirm_data = State()
    waiting_for_order_time = State()
    waiting_for_specific_time = State()
    confirm_order = State()

class OrderStates(StatesGroup):
    choosing_modifiers = State()

# --- TELEGRAM БОТИ ---
dp = Dispatcher()
dp_admin = Dispatcher()

async def get_main_reply_keyboard(session: AsyncSession):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🍽️ Меню"), KeyboardButton(text="🛒 Кошик"))
    builder.row(KeyboardButton(text="📋 Мої замовлення"), KeyboardButton(text="❓ Допомога"))

    menu_items_res = await session.execute(
        select(MenuItem).where(MenuItem.show_in_telegram == True).order_by(MenuItem.sort_order)
    )
    menu_items = menu_items_res.scalars().all()
    if menu_items:
        dynamic_buttons = [KeyboardButton(text=item.title.strip()) for item in menu_items]
        for i in range(0, len(dynamic_buttons), 2):
            builder.row(*dynamic_buttons[i:i+2])

    return builder.as_markup(resize_keyboard=True)

async def handle_dynamic_menu_item(message: Message, session: AsyncSession):
    menu_item_res = await session.execute(
        select(MenuItem.content).where(func.trim(MenuItem.title) == message.text, MenuItem.show_in_telegram == True)
    )
    content = menu_item_res.scalar_one_or_none()

    if content is not None:
        if not content.strip():
            await message.answer("Ця сторінка наразі порожня.")
            return

        try:
            await message.answer(content, parse_mode=ParseMode.HTML)
        except TelegramBadRequest:
            try:
                await message.answer(content, parse_mode=None)
            except Exception as e:
                logging.error(f"Не вдалося надіслати вміст пункту меню '{message.text}': {e}")
                await message.answer("Вибачте, сталася помилка під час відображення цієї сторінки.")
    else:
        await message.answer("Вибачте, я не зрозумів цю команду.")


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    settings = await session.get(Settings, 1) or Settings()
    default_welcome = f"Шановний {{user_name}}, ласкаво просимо! 👋\n\nМи раді вас бачити. Оберіть опцію:"
    welcome_template = settings.telegram_welcome_message or default_welcome
    try:
        caption = welcome_template.format(user_name=html.escape(message.from_user.full_name))
    except (KeyError, ValueError):
        caption = default_welcome.format(user_name=html.escape(message.from_user.full_name))

    keyboard = await get_main_reply_keyboard(session)
    await message.answer(caption, reply_markup=keyboard)


@dp.message(F.text == "🍽️ Меню")
async def handle_menu_message(message: Message, session: AsyncSession):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await show_menu(message, session)

@dp.message(F.text == "🛒 Кошик")
async def handle_cart_message(message: Message, session: AsyncSession):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await show_cart(message, session)

@dp.message(F.text == "📋 Мої замовлення")
async def handle_my_orders_message(message: Message, session: AsyncSession):
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    await show_my_orders(message, session)

@dp.message(F.text == "❓ Допомога")
async def handle_help_message(message: Message):
    text = "Шановний клієнте, ось інструкція:\n- /start: Розпочати роботу з ботом\n- Додайте страви до кошика\n- Оформлюйте замовлення з доставкою\n- Переглядайте свої замовлення\nМи завжди раді допомогти!"
    await message.answer(text)

@dp.message(F.text == "❌ Скасувати")
@dp.message(Command("cancel"))
async def cancel_checkout(message: Message, state: FSMContext, session: AsyncSession):
    await state.clear()
    kb = await get_main_reply_keyboard(session)
    await message.answer("Шановний клієнте, оформлення замовлення скасовано.", reply_markup=kb)

@dp.callback_query(F.data == "start_menu")
async def back_to_start_menu(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    try: await callback.message.delete()
    except TelegramBadRequest: pass

    settings = await session.get(Settings, 1) or Settings()
    default_welcome = f"Шановний {{user_name}}, ласкаво просимо! 👋\n\nМи раді вас бачити. Оберіть опцію:"
    welcome_template = settings.telegram_welcome_message or default_welcome
    try:
        caption = welcome_template.format(user_name=html.escape(callback.from_user.full_name))
    except (KeyError, ValueError):
        caption = default_welcome.format(user_name=html.escape(callback.from_user.full_name))

    keyboard = await get_main_reply_keyboard(session)
    await callback.message.answer(caption, reply_markup=keyboard)
    await callback.answer()

async def show_my_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession):
    is_callback = isinstance(message_or_callback, CallbackQuery)
    message = message_or_callback.message if is_callback else message_or_callback
    user_id = message_or_callback.from_user.id

    orders_result = await session.execute(
        select(Order).options(joinedload(Order.status), selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.id.desc())
        .limit(5)
    )
    orders = orders_result.scalars().all()

    if not orders:
        text = "Шановний клієнте, у вас поки що немає замовлень."
        if is_callback:
            await message_or_callback.answer(text, show_alert=True)
        else:
            await message.answer(text)
        return

    text = "📋 <b>Ваші останні замовлення:</b>\n\n"
    for order in orders:
        status_name = order.status.name if order.status else 'Невідомий'
        
        lines = []
        for item in order.items:
            mods_str = ""
            if item.modifiers:
                mod_names = [m.get('name', '') for m in item.modifiers]
                if mod_names:
                    mods_str = f" (+ {', '.join(mod_names)})"
            lines.append(f"{item.product_name}{mods_str} x {item.quantity}")
            
        products_str = ", ".join(lines)
        text += f"<b>Замовлення #{order.id} ({status_name})</b>\nСтрави: {html.escape(products_str)}\nСума: {order.total_price} грн\n\n"

    kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="⬅️ Головне меню", callback_data="start_menu")).as_markup()

    if is_callback:
        try:
            await message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await message.delete()
            await message.answer(text, reply_markup=kb)
        await message_or_callback.answer()
    else:
        await message.answer(text, reply_markup=kb)

async def show_menu(message_or_callback: Message | CallbackQuery, session: AsyncSession):
    is_callback = isinstance(message_or_callback, CallbackQuery)
    message = message_or_callback.message if is_callback else message_or_callback

    keyboard = InlineKeyboardBuilder()
    categories_result = await session.execute(
        select(Category)
        .where(Category.show_on_delivery_site == True)
        .order_by(Category.sort_order, Category.name)
    )
    categories = categories_result.scalars().all()

    if not categories:
        text = "Шановний клієнте, меню поки що порожнє. Зачекайте на оновлення!"
        if is_callback: await message_or_callback.answer(text, show_alert=True)
        else: await message.answer(text)
        return

    for category in categories:
        keyboard.add(InlineKeyboardButton(text=category.name, callback_data=f"show_category_{category.id}_1"))
    
    keyboard.adjust(2) 
    
    keyboard.row(InlineKeyboardButton(text="🛒 Відкрити кошик", callback_data="cart"))
    keyboard.row(InlineKeyboardButton(text="⬅️ Головне меню", callback_data="start_menu"))

    text = "Шановний клієнте, оберіть категорію:"

    if is_callback:
        try:
            await message.edit_text(text, reply_markup=keyboard.as_markup())
        except TelegramBadRequest:
            await message.delete()
            await message.answer(text, reply_markup=keyboard.as_markup())
        await message_or_callback.answer()
    else:
        await message.answer(text, reply_markup=keyboard.as_markup())

@dp.callback_query(F.data == "menu")
async def show_menu_callback(callback: CallbackQuery, session: AsyncSession):
    await show_menu(callback, session)

@dp.callback_query(F.data.startswith("show_category_"))
async def show_category_paginated(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    
    parts = callback.data.split("_")
    category_id = int(parts[2])
    page = int(parts[3]) if len(parts) > 3 else 1

    category = await session.get(Category, category_id)
    if not category:
        await callback.answer("Категорію не знайдено!", show_alert=True)
        return

    offset = (page - 1) * PRODUCTS_PER_PAGE
    query_total = select(func.count(Product.id)).where(Product.category_id == category_id, Product.is_active == True)
    query_products = select(Product).where(Product.category_id == category_id, Product.is_active == True).order_by(Product.name).offset(offset).limit(PRODUCTS_PER_PAGE)

    total_products_res = await session.execute(query_total)
    total_products = total_products_res.scalar_one_or_none() or 0

    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE

    products_result = await session.execute(query_products)
    products_on_page = products_result.scalars().all()

    keyboard = InlineKeyboardBuilder()
    for product in products_on_page:
        keyboard.add(InlineKeyboardButton(text=f"{product.name} - {product.price} грн", callback_data=f"show_product_{product.id}"))
    keyboard.adjust(1) 

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"show_category_{category_id}_{page-1}"))
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"show_category_{category_id}_{page+1}"))
    if nav_buttons:
        keyboard.row(*nav_buttons)

    keyboard.row(InlineKeyboardButton(text="🛒 Кошик", callback_data="cart"))
    keyboard.row(InlineKeyboardButton(text="🔙 Назад до категорій", callback_data="menu"))
    keyboard.row(InlineKeyboardButton(text="🏠 Головна", callback_data="start_menu"))

    text = f"<b>{html.escape(category.name)}</b> (Сторінка {page}):"

    try:
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" in str(e):
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard.as_markup())
        else:
            logging.error(f"Неочікувана помилка TelegramBadRequest у show_category_paginated: {e}")

async def get_photo_input(image_url: str):
    if image_url and os.path.exists(image_url) and os.path.getsize(image_url) > 0:
        return FSInputFile(image_url)
    return None

@dp.callback_query(F.data.startswith("show_product_"))
async def show_product(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    
    product_id = int(callback.data.split("_")[2])
    product = await session.get(Product, product_id)

    if not product or not product.is_active:
        await callback.answer("Страву не знайдено або вона тимчасово недоступна!", show_alert=True)
        return

    text = (f"<b>{html.escape(product.name)}</b>\n\n"
            f"<i>{html.escape(product.description or 'Опис відсутній.')}</i>\n\n"
            f"<b>Ціна: {product.price} грн</b>")

    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="➕ Додати в кошик", callback_data=f"add_to_cart_{product.id}"))
    kb.adjust(1)
    
    kb.row(InlineKeyboardButton(text="🔙 Назад до страв", callback_data=f"show_category_{product.category_id}_1"))
    kb.row(InlineKeyboardButton(text="🛒 Кошик", callback_data="cart"), InlineKeyboardButton(text="🏠 Головна", callback_data="start_menu"))

    photo_input = await get_photo_input(product.image_url)
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        logging.warning(f"Не вдалося видалити повідомлення в show_product: {e}")

    if photo_input:
        await callback.message.answer_photo(photo=photo_input, caption=text, reply_markup=kb.as_markup())
    else:
        await callback.message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        product_id = int(callback.data.split("_")[3])
    except (IndexError, ValueError):
        return await callback.answer("Помилка! Не вдалося обробити запит.", show_alert=True)

    product = await session.get(Product, product_id, options=[selectinload(Product.modifiers)])
    
    if not product or not product.is_active:
        return await callback.answer("Ця страва тимчасово недоступна.", show_alert=True)

    modifiers = product.modifiers
    
    if not modifiers:
        await _add_item_to_db_cart(callback, product, [], session)
    else:
        await state.set_state(OrderStates.choosing_modifiers)
        await state.update_data(selected_product_id=product.id, selected_modifiers=[])
        await _show_modifier_menu(callback, product, [], modifiers)

async def _show_modifier_menu(callback: CallbackQuery, product, selected_ids, available_modifiers):
    kb = InlineKeyboardBuilder()
    
    for mod in available_modifiers:
        is_selected = mod.id in selected_ids
        marker = "✅" if is_selected else "⬜️"
        kb.add(InlineKeyboardButton(
            text=f"{marker} {mod.name} (+{mod.price} грн)", 
            callback_data=f"toggle_mod_{mod.id}"
        ))
    
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="📥 Додати в кошик", callback_data="confirm_add_to_cart"))
    kb.row(InlineKeyboardButton(text="🔙 Скасувати", callback_data=f"show_product_{product.id}"))
    
    current_price = product.price + sum(m.price for m in available_modifiers if m.id in selected_ids)
    
    text = f"<b>{html.escape(product.name)}</b>\nЦіна з добавками: {current_price} грн\n\nОберіть добавки:"
    
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=kb.as_markup())
    else:
        await callback.message.edit_text(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("toggle_mod_"), OrderStates.choosing_modifiers)
async def toggle_modifier_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    mod_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected_ids = data.get("selected_modifiers", [])
    
    if mod_id in selected_ids:
        selected_ids.remove(mod_id)
    else:
        selected_ids.append(mod_id)
        
    await state.update_data(selected_modifiers=selected_ids)
    
    product = await session.get(Product, data["selected_product_id"], options=[selectinload(Product.modifiers)])
    await _show_modifier_menu(callback, product, selected_ids, product.modifiers)
    await callback.answer()

@dp.callback_query(F.data == "confirm_add_to_cart", OrderStates.choosing_modifiers)
async def confirm_add_to_cart_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    product_id = data.get("selected_product_id")
    mod_ids = data.get("selected_modifiers", [])
    
    product = await session.get(Product, product_id)
    
    selected_mods_objects = []
    if mod_ids:
        selected_mods_objects = (await session.execute(select(Modifier).where(Modifier.id.in_(mod_ids)))).scalars().all()
    
    await _add_item_to_db_cart(callback, product, selected_mods_objects, session)
    await state.clear()

async def _add_item_to_db_cart(callback: CallbackQuery, product: Product, modifiers: list[Modifier], session: AsyncSession):
    user_id = callback.from_user.id
    
    mods_json = [{"id": m.id, "name": m.name, "price": float(m.price or 0), "ingredient_id": m.ingredient_id, "ingredient_qty": float(m.ingredient_qty or 0)} for m in modifiers]
    
    cart_item = CartItem(
        user_id=user_id, 
        product_id=product.id, 
        quantity=1,
        modifiers=mods_json if mods_json else None
    )
    session.add(cart_item)

    await session.commit()
    
    msg = f"✅ {html.escape(product.name)}"
    if modifiers:
        msg += f" (+ {len(modifiers)} доб.)"
    msg += " додано до кошика!"
    
    await callback.answer(msg, show_alert=False)
    
    new_callback = callback.model_copy(update={"data": f"show_category_{product.category_id}_1"})
    
    await show_category_paginated(new_callback, session)

async def show_cart(message_or_callback: Message | CallbackQuery, session: AsyncSession):
    is_callback = isinstance(message_or_callback, CallbackQuery)
    message = message_or_callback.message if is_callback else message_or_callback
    user_id = message_or_callback.from_user.id

    cart_items_result = await session.execute(select(CartItem).options(joinedload(CartItem.product)).where(CartItem.user_id == user_id).order_by(CartItem.id))
    cart_items = cart_items_result.scalars().all()

    if not cart_items:
        text = "Шановний клієнте, ваш кошик порожній. Оберіть щось смачненьке з меню!"
        kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="🍽 До меню", callback_data="menu")).as_markup()
        if is_callback:
            await message_or_callback.answer(text, show_alert=True)
            try: await message.edit_text(text, reply_markup=kb)
            except: await message.answer(text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)
        return

    text = "🛒 <b>Ваш кошик:</b>\n\n"
    total_price = 0
    kb = InlineKeyboardBuilder()

    for item in cart_items:
        if item.product:
            item_base_price = item.product.price
            mods_price = Decimal(0)
            mods_str = ""
            
            if item.modifiers:
                for m in item.modifiers:
                    price_val = m.get('price', 0)
                    if price_val is None: price_val = 0
                    mods_price += Decimal(str(price_val))
                
                mod_names = [m.get('name', '') for m in item.modifiers]
                mods_str = f" (+ {', '.join(mod_names)})"

            final_item_price = item_base_price + mods_price
            item_total = final_item_price * item.quantity
            total_price += item_total
            
            text += f"<b>{html.escape(item.product.name)}</b>{mods_str}\n"
            text += f"<i>{item.quantity} шт. x {final_item_price} грн</i> = <code>{item_total} грн</code>\n\n"
            
            kb.row(
                InlineKeyboardButton(text="➖", callback_data=f"cart_change_{item.id}_-1"),
                InlineKeyboardButton(text=f"{item.quantity}", callback_data="noop"),
                InlineKeyboardButton(text="➕", callback_data=f"cart_change_{item.id}_1"),
                InlineKeyboardButton(text="❌", callback_data=f"cart_del_{item.id}")
            )

    text += f"\n<b>Разом до сплати: {total_price} грн</b>"

    kb.row(InlineKeyboardButton(text="✅ Оформити замовлення", callback_data="checkout"))
    kb.row(InlineKeyboardButton(text="🗑️ Очистити кошик", callback_data="clear_cart"))
    kb.row(InlineKeyboardButton(text="⬅️ Продовжити покупки", callback_data="menu"))
    kb.row(InlineKeyboardButton(text="🏠 Головна", callback_data="start_menu"))

    if is_callback:
        try:
            if message.photo:
                await message.delete() 
                await message.answer(text, reply_markup=kb.as_markup())
            else:
                await message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest:
            await message.delete()
            await message.answer(text, reply_markup=kb.as_markup())
        await message_or_callback.answer()
    else:
        await message.answer(text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "cart")
async def show_cart_callback(callback: CallbackQuery, session: AsyncSession):
    await show_cart(callback, session)

@dp.callback_query(F.data.startswith("cart_change_"))
async def change_cart_item_quantity(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("⏳ Оновлюю...")
    parts = callback.data.split("_")
    cart_item_id = int(parts[2])
    change = int(parts[3])
    
    cart_item = await session.get(CartItem, cart_item_id)
    if not cart_item or cart_item.user_id != callback.from_user.id: return

    cart_item.quantity += change
    if cart_item.quantity < 1:
        await session.delete(cart_item)
    await session.commit()
    await show_cart(callback, session)

@dp.callback_query(F.data.startswith("cart_del_"))
async def delete_cart_item_direct(callback: CallbackQuery, session: AsyncSession):
    await callback.answer("⏳ Видаляю...")
    cart_item_id = int(callback.data.split("_")[2])
    cart_item = await session.get(CartItem, cart_item_id)
    if cart_item and cart_item.user_id == callback.from_user.id:
        await session.delete(cart_item)
        await session.commit()
    await show_cart(callback, session)

@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: CallbackQuery, session: AsyncSession):
    await session.execute(sa.delete(CartItem).where(CartItem.user_id == callback.from_user.id))
    await session.commit()
    await callback.answer("Кошик очищено!", show_alert=True)
    await show_menu(callback, session)

# --- ПРОЦЕС ОФОРМЛЕННЯ ЗАМОВЛЕННЯ ---

@dp.callback_query(F.data == "checkout")
async def start_checkout(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    user_id = callback.from_user.id
    cart_items_result = await session.execute(
        select(CartItem).options(joinedload(CartItem.product)).where(CartItem.user_id == user_id)
    )
    cart_items = cart_items_result.scalars().all()

    if not cart_items:
        await callback.answer("Шановний клієнте, кошик порожній! Оберіть щось з меню.", show_alert=True)
        return

    total_price = Decimal(0)
    for item in cart_items:
        if item.product:
            item_price = item.product.price
            if item.modifiers:
                item_price += sum(Decimal(str(m.get('price', 0) or 0)) for m in item.modifiers)
            total_price += item_price * item.quantity
    
    await state.update_data(
        total_price=float(total_price),
        user_id=user_id,
        username=callback.from_user.username,
        order_type='delivery' 
    )
    await state.set_state(CheckoutStates.waiting_for_delivery_type)
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="🚚 Доставка", callback_data="delivery_type_delivery"))
    kb.add(InlineKeyboardButton(text="🏠 Самовивіз", callback_data="delivery_type_pickup"))
    kb.adjust(1)
    
    kb.row(InlineKeyboardButton(text="🔙 Повернутись в кошик", callback_data="cart"))

    text = "Шановний клієнте, оберіть тип отримання замовлення:"
    
    try:
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=kb.as_markup())
        else:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb.as_markup())

    await callback.answer()

@dp.callback_query(F.data.startswith("delivery_type_"))
async def process_delivery_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    delivery_type = callback.data.split("_")[2]
    is_delivery = delivery_type == "delivery"
    await state.update_data(is_delivery=is_delivery, order_type=delivery_type)
    
    customer = await session.get(Customer, callback.from_user.id)
    if customer and customer.name and customer.phone_number and (not is_delivery or customer.address):
        text = f"Шановний клієнте, ми маємо ваші дані:\n👤 Ім'я: {customer.name}\n📱 Телефон: {customer.phone_number}"
        if is_delivery:
            text += f"\n🏠 Адреса: {customer.address}"
        text += "\n\nБажаєте використати ці дані?"
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="✅ Так", callback_data="confirm_data_yes"))
        kb.add(InlineKeyboardButton(text="✏️ Змінити", callback_data="confirm_data_no"))
        await callback.message.edit_text(text, reply_markup=kb.as_markup())
        await state.set_state(CheckoutStates.confirm_data)
    else:
        await state.set_state(CheckoutStates.waiting_for_name)
        
        kb = ReplyKeyboardBuilder()
        kb.add(KeyboardButton(text="❌ Скасувати"))
        
        try: await callback.message.delete()
        except Exception: pass
        
        await callback.message.answer("Шановний клієнте, будь ласка, введіть ваше ім'я (наприклад, Іван):", reply_markup=kb.as_markup(resize_keyboard=True))
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_data_"))
async def process_confirm_data(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    confirm = callback.data.split("_")[2]
    try:
        await callback.message.delete()
    except TelegramBadRequest as e:
        logging.warning(f"Не вдалося видалити повідомлення в process_confirm_data: {e}")

    message = callback.message

    if confirm == "yes":
        customer = await session.get(Customer, callback.from_user.id)
        data_to_update = {"customer_name": customer.name, "phone_number": customer.phone_number}
        if (await state.get_data()).get("is_delivery"):
            data_to_update["address"] = customer.address
        await state.update_data(**data_to_update)

        await ask_for_order_time(message, state, session)
    else:
        await state.set_state(CheckoutStates.waiting_for_name)
        
        kb = ReplyKeyboardBuilder()
        kb.add(KeyboardButton(text="❌ Скасувати"))
        await message.answer("Шановний клієнте, будь ласка, введіть ваше ім'я:", reply_markup=kb.as_markup(resize_keyboard=True))
    await callback.answer()

@dp.message(CheckoutStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.answer("Шановний клієнте, ім'я повинно бути не менше 2 символів! Спробуйте ще раз.")
        return
    await state.update_data(customer_name=name)
    await state.set_state(CheckoutStates.waiting_for_phone)
    
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="📱 Надіслати мій номер", request_contact=True))
    kb.row(KeyboardButton(text="❌ Скасувати"))
    
    await message.answer("Будь ласка, введіть номер телефону (або натисніть кнопку):", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(CheckoutStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext, session: AsyncSession):
    phone = None
    
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith('+'): phone = '+' + phone
    elif message.text:
        # ВИКОРИСТОВУЄМО НОРМАЛІЗАЦІЮ
        phone = normalize_phone(message.text)
        if not phone or len(phone) < 10: # Проста перевірка довжини
            await message.answer("Некоректний номер! Формат: 0XXXXXXXXX. Або скористайтесь кнопкою.", 
                                 reply_markup=message.reply_markup)
            return
    else:
        await message.answer("Будь ласка, надішліть контакт або введіть номер текстом.")
        return

    await state.update_data(phone_number=phone)
    data = await state.get_data()
    
    remove_kb = ReplyKeyboardRemove()
    
    if data.get('is_delivery'):
        await state.set_state(CheckoutStates.waiting_for_address)
        
        kb = ReplyKeyboardBuilder()
        kb.add(KeyboardButton(text="❌ Скасувати"))
        
        await message.answer("Дякую! Тепер введіть адресу доставки (Вулиця, будинок, під'їзд):", reply_markup=kb.as_markup(resize_keyboard=True))
    else:
        await message.answer("Номер прийнято.", reply_markup=remove_kb)
        await ask_for_order_time(message, state, session)

@dp.message(CheckoutStates.waiting_for_address)
async def process_address(message: Message, state: FSMContext, session: AsyncSession):
    address = message.text.strip()
    if not address or len(address) < 5:
        await message.answer("Адреса занадто коротка. Спробуйте ще раз.")
        return
    await state.update_data(address=address)
    
    await message.answer("Адресу збережено.", reply_markup=ReplyKeyboardRemove())
    await ask_for_order_time(message, state, session)

async def ask_for_order_time(message_or_callback: Message | CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.set_state(CheckoutStates.waiting_for_order_time)
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="🚀 Якнайшвидше", callback_data="order_time_asap"))
    kb.add(InlineKeyboardButton(text="🕒 На конкретний час", callback_data="order_time_specific"))
    text = "Коли хочете отримати замовлення?"

    current_message = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
    await current_message.answer(text, reply_markup=kb.as_markup())
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.answer()

@dp.callback_query(CheckoutStates.waiting_for_order_time, F.data.startswith("order_time_"))
async def process_order_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    time_choice = callback.data.split("_")[2]

    if time_choice == "asap":
        await state.update_data(delivery_time="Якнайшвидше")
        await ask_confirm_order(callback.message, state)
    else: 
        await state.set_state(CheckoutStates.waiting_for_specific_time)
        
        kb = ReplyKeyboardBuilder()
        kb.add(KeyboardButton(text="❌ Скасувати"))
        
        try: await callback.message.delete()
        except Exception: pass
        
        await callback.message.answer("На котру годину? (наприклад, '19:00' або 'на 14:30')", reply_markup=kb.as_markup(resize_keyboard=True))
    await callback.answer()

@dp.message(CheckoutStates.waiting_for_specific_time)
async def process_specific_time(message: Message, state: FSMContext, session: AsyncSession):
    specific_time = message.text.strip()
    if not specific_time:
        await message.answer("Час не може бути порожнім.")
        return
    await state.update_data(delivery_time=specific_time)
    
    await message.answer("Час встановлено.", reply_markup=ReplyKeyboardRemove())
    await ask_confirm_order(message, state)

async def ask_confirm_order(message: Message, state: FSMContext):
    data = await state.get_data()
    
    delivery_text = "🚚 Доставка" if data.get('is_delivery') else "🏠 Самовивіз"
    address_info = f"\n📍 Адреса: {data.get('address')}" if data.get('is_delivery') else ""
    
    summary = (
        f"📝 <b>Перевірте дані замовлення:</b>\n\n"
        f"👤 Ім'я: {data.get('customer_name')}\n"
        f"📱 Телефон: {data.get('phone_number')}\n"
        f"{delivery_text}{address_info}\n"
        f"⏰ Час: {data.get('delivery_time')}\n"
        f"💳 Сума до сплати: <b>{data.get('total_price')} грн</b>"
    )
    
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="✅ Підтвердити замовлення", callback_data="checkout_confirm"))
    kb.add(InlineKeyboardButton(text="❌ Скасувати", callback_data="checkout_cancel"))
    kb.adjust(1)
    
    await state.set_state(CheckoutStates.confirm_order)
    await message.answer(summary, reply_markup=kb.as_markup())

@dp.callback_query(CheckoutStates.confirm_order, F.data == "checkout_confirm")
async def confirm_order_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.edit_reply_markup(reply_markup=None) 
    await finalize_order(callback.message, state, session)
    await callback.answer()

@dp.callback_query(CheckoutStates.confirm_order, F.data == "checkout_cancel")
async def cancel_order_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    await callback.message.edit_text("❌ Замовлення скасовано.")
    
    kb = await get_main_reply_keyboard(session)
    await callback.message.answer("Ви можете продовжити покупки:", reply_markup=kb)
    await callback.answer()

async def finalize_order(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    user_id = data.get('user_id')
    
    # Виконуємо запит
    cart_items_res = await session.execute(
        select(CartItem).options(joinedload(CartItem.product)).where(CartItem.user_id == user_id)
    )
    
    # ПРАВИЛЬНО: використовуємо cart_items_res (а не cart_items_result)
    cart_items = cart_items_res.scalars().all() 
    
    if not cart_items:
        await message.answer("Помилка: кошик порожній.")
        return

    all_mod_ids = set()
    for cart_item in cart_items:
        if cart_item.modifiers:
            for m in cart_item.modifiers:
                all_mod_ids.add(int(m['id']))
    
    db_modifiers = {}
    if all_mod_ids:
        mods_res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
        for m in mods_res.scalars().all():
            db_modifiers[m.id] = m

    total_price = Decimal(0)
    items_obj = []
    log_items = [] # Для логу

    for cart_item in cart_items:
        if cart_item.product:
            item_price = cart_item.product.price
            
            final_mods_data = []
            mods_price_sum = Decimal(0)
            
            if cart_item.modifiers:
                for m_raw in cart_item.modifiers:
                    mid = int(m_raw['id'])
                    if mid in db_modifiers:
                        mod_db = db_modifiers[mid]
                        mods_price_sum += Decimal(str(mod_db.price))
                        # ОНОВЛЕНО: Додаємо warehouse_id для коректного списання
                        final_mods_data.append({
                            "id": mod_db.id,
                            "name": mod_db.name,
                            "price": float(mod_db.price),
                            "ingredient_id": mod_db.ingredient_id,
                            "ingredient_qty": float(mod_db.ingredient_qty),
                            "warehouse_id": mod_db.warehouse_id 
                        })
            
            item_price += mods_price_sum
            total_price += item_price * cart_item.quantity
            
            log_items.append(f"{cart_item.product.name} x{cart_item.quantity}")

            items_obj.append(OrderItem(
                product_id=cart_item.product_id,
                product_name=cart_item.product.name,
                quantity=cart_item.quantity,
                price_at_moment=item_price,
                preparation_area=cart_item.product.preparation_area,
                modifiers=final_mods_data 
            ))

    order = Order(
        user_id=data['user_id'], username=data.get('username'),
        total_price=total_price, customer_name=data['customer_name'],
        phone_number=data['phone_number'], address=data.get('address'),
        is_delivery=data.get('is_delivery', True),
        delivery_time=data.get('delivery_time', 'Якнайшвидше'),
        order_type=data.get('order_type', 'delivery')
    )
    session.add(order)
    
    # --- ВАЖЛИВО: Отримуємо ID ---
    await session.flush()
    # -----------------------------

    for obj in items_obj:
        obj.order_id = order.id
        session.add(obj)

    if user_id:
        customer = await session.get(Customer, user_id)
        if not customer:
            customer = Customer(user_id=user_id)
            session.add(customer)
        customer.name, customer.phone_number = data['customer_name'], data['phone_number']
        if 'address' in data and data['address'] is not None:
            customer.address = data.get('address')
        await session.execute(sa.delete(CartItem).where(CartItem.user_id == user_id))
    
    # --- ЛОГУВАННЯ СТВОРЕННЯ (КЛІЄНТ TG) ---
    actor_name = data.get('customer_name') or "Клієнт (TG Bot)"
    items_str = ", ".join(log_items)
    # Тепер order.id вже існує завдяки flush()
    session.add(OrderLog(order_id=order.id, message=f"Замовлення створено клієнтом через Бот. Склад: {items_str}", actor=actor_name))
    # ---------------------------------------

    await session.commit()
    await session.refresh(order)

    app_admin_bot = message.bot 
    if app_admin_bot:
        await notify_new_order_to_staff(app_admin_bot, order, session)

    await message.answer(f"✅ <b>Дякуємо! Ваше замовлення #{order.id} прийнято!</b>\nМи зв'яжемося з вами для підтвердження.", reply_markup=ReplyKeyboardRemove())

    await state.clear()
    await command_start_handler(message, state, session)

async def start_bot(client_dp: Dispatcher, admin_dp: Dispatcher, client_bot: Bot, admin_bot: Bot):
    try:
        admin_dp["client_bot"] = client_bot
        admin_dp["bot_instance"] = admin_bot
        client_dp["admin_bot_instance"] = admin_bot
        
        client_dp["session_factory"] = async_session_maker
        admin_dp["session_factory"] = async_session_maker

        client_dp.message.register(handle_dynamic_menu_item, F.text)

        register_admin_handlers(admin_dp)
        register_courier_handlers(admin_dp)

        client_dp.callback_query.middleware(DbSessionMiddleware(session_pool=async_session_maker))
        client_dp.message.middleware(DbSessionMiddleware(session_pool=async_session_maker))
        admin_dp.callback_query.middleware(DbSessionMiddleware(session_pool=async_session_maker))
        admin_dp.message.middleware(DbSessionMiddleware(session_pool=async_session_maker))

        await client_bot.delete_webhook(drop_pending_updates=True)
        await admin_bot.delete_webhook(drop_pending_updates=True)

        logging.info("Запускаємо поллінг ботів...")
        # ВАЖЛИВО: Збільшений таймаут для поллінгу
        await asyncio.gather(
            client_dp.start_polling(client_bot, polling_timeout=60, handle_signals=False),
            admin_dp.start_polling(admin_bot, polling_timeout=60, handle_signals=False)
        )
    except Exception as e:
        logging.critical(f"Не вдалося запустити ботів: {e}", exc_info=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Запуск додатка...")
    os.makedirs("static/images", exist_ok=True)
    os.makedirs("static/favicons", exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session_maker() as session:
        result_status = await session.execute(select(OrderStatus).limit(1))
        if not result_status.scalars().first():
            default_statuses = {
                "Новий": {"visible_to_operator": True, "visible_to_courier": False, "visible_to_waiter": True, "visible_to_chef": True, "visible_to_bartender": True, "requires_kitchen_notify": False},
                "В обробці": {"visible_to_operator": True, "visible_to_courier": False, "visible_to_waiter": True, "visible_to_chef": True, "visible_to_bartender": True, "requires_kitchen_notify": True},
                "Готовий до видачі": {"visible_to_operator": True, "visible_to_courier": True, "visible_to_waiter": True, "visible_to_chef": False, "visible_to_bartender": False, "notify_customer": True, "requires_kitchen_notify": False},
                "Доставлений": {"visible_to_operator": True, "visible_to_courier": True, "is_completed_status": True},
                "Скасований": {"visible_to_operator": True, "visible_to_courier": False, "is_cancelled_status": True, "visible_to_waiter": True, "visible_to_chef": False, "visible_to_bartender": False},
                "Оплачено": {"visible_to_operator": True, "is_completed_status": True, "visible_to_waiter": True, "visible_to_chef": False, "visible_to_bartender": False, "notify_customer": False}
            }
            for name, props in default_statuses.items():
                session.add(OrderStatus(name=name, **props))

        result_roles = await session.execute(select(Role).limit(1))
        if not result_roles.scalars().first():
            session.add(Role(name="Адміністратор", can_manage_orders=True, can_be_assigned=True, can_serve_tables=True, can_receive_kitchen_orders=True, can_receive_bar_orders=True))
            session.add(Role(name="Оператор", can_manage_orders=True, can_be_assigned=False, can_serve_tables=True, can_receive_kitchen_orders=True, can_receive_bar_orders=True))
            session.add(Role(name="Кур'єр", can_manage_orders=False, can_be_assigned=True, can_serve_tables=False, can_receive_kitchen_orders=False, can_receive_bar_orders=False))
            session.add(Role(name="Офіціант", can_manage_orders=False, can_be_assigned=False, can_serve_tables=True, can_receive_kitchen_orders=False, can_receive_bar_orders=False))
            session.add(Role(name="Повар", can_manage_orders=False, can_be_assigned=False, can_serve_tables=False, can_receive_kitchen_orders=True, can_receive_bar_orders=False))
            session.add(Role(name="Бармен", can_manage_orders=False, can_be_assigned=False, can_serve_tables=False, can_receive_kitchen_orders=False, can_receive_bar_orders=True))

        result_units = await session.execute(select(Unit).limit(1))
        if not result_units.scalars().first():
            session.add_all([
                Unit(name='кг', is_weighable=True),
                Unit(name='л', is_weighable=True),
                Unit(name='шт', is_weighable=False),
                Unit(name='порц', is_weighable=False)
            ])
            
        result_warehouses = await session.execute(select(Warehouse).limit(1))
        if not result_warehouses.scalars().first():
            logging.info("Створення базових складів...")
            main_wh = Warehouse(name='Основний склад', is_production=False)
            session.add(main_wh)
            await session.flush()
            
            kitchen = Warehouse(name='Кухня', is_production=True, linked_warehouse_id=main_wh.id)
            bar = Warehouse(name='Бар', is_production=True, linked_warehouse_id=main_wh.id)
            session.add_all([kitchen, bar])
            await session.commit()

        await session.commit()
    
    client_token = os.environ.get('CLIENT_BOT_TOKEN')
    admin_token = os.environ.get('ADMIN_BOT_TOKEN')
    
    client_bot = None
    admin_bot = None
    bot_task = None

    # ВАЖЛИВО: Налаштування сесії з таймаутом
    session_config = AiohttpSession(timeout=60)

    if not all([client_token, admin_token]):
        logging.warning("Токени ботів не встановлені! Боти не будуть запущені.")
    else:
        try:
            # Передаємо session_config у конструктор ботів
            client_bot = Bot(token=client_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=session_config)
            admin_bot = Bot(token=admin_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=session_config)
            bot_task = asyncio.create_task(start_bot(dp, dp_admin, client_bot, admin_bot))
        except Exception as e:
             logging.error(f"Помилка при створенні ботів: {e}")

    app.state.client_bot = client_bot
    app.state.admin_bot = admin_bot
    
    yield
    
    logging.info("Зупинка додатка...")
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
    
    if client_bot: await client_bot.session.close()
    if admin_bot: await admin_bot.session.close()


app = FastAPI(lifespan=lifespan)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ДОДАНО 404 HANDLER З ПОВНИМ ДИЗАЙНОМ ---
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    async with async_session_maker() as session:
        settings = await get_settings(session)
        
        logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" class="header-logo">' if settings.logo_url else ''
        
        # Соцмережі
        social_links = []
        if settings.instagram_url:
            social_links.append(f'<a href="{html.escape(settings.instagram_url)}" target="_blank"><i class="fa-brands fa-instagram"></i></a>')
        if settings.facebook_url:
            social_links.append(f'<a href="{html.escape(settings.facebook_url)}" target="_blank"><i class="fa-brands fa-facebook"></i></a>')
        social_links_html = "".join(social_links)
        
        menu_items_res = await session.execute(
            select(MenuItem).where(MenuItem.show_on_website == True).order_by(MenuItem.sort_order)
        )
        menu_items = menu_items_res.scalars().all()
        menu_links_html = "".join(
            [f'<a href="/" class="footer-link"><i class="fa-solid fa-file-lines"></i> <span>{html.escape(item.title)}</span></a>' for item in menu_items]
        )
        
        header_text_val = settings.site_header_text if settings.site_header_text else (settings.site_title or "Назва")

    template_params = {
        "logo_html": logo_html,
        "site_title": html.escape(settings.site_title or "Назва"),
        "site_header_text": html.escape(header_text_val),
        "primary_color_val": settings.primary_color or "#5a5a5a",
        "secondary_color_val": settings.secondary_color or "#eeeeee",
        "background_color_val": settings.background_color or "#f4f4f4",
        "text_color_val": settings.text_color or "#333333",
        "footer_bg_color_val": settings.footer_bg_color or "#333333",
        "footer_text_color_val": settings.footer_text_color or "#ffffff",
        "font_family_sans_val": settings.font_family_sans or "Golos Text",
        "font_family_serif_val": settings.font_family_serif or "Playfair Display",
        "font_family_sans_encoded": url_quote_plus(settings.font_family_sans or "Golos Text"),
        "font_family_serif_encoded": url_quote_plus(settings.font_family_serif or "Playfair Display"),
        "footer_address": html.escape(settings.footer_address or "Адреса не вказана"),
        "footer_phone": html.escape(settings.footer_phone or ""),
        "working_hours": html.escape(settings.working_hours or ""),
        "social_links_html": social_links_html,
        "category_nav_bg_color": settings.category_nav_bg_color or "#ffffff",
        "category_nav_text_color": settings.category_nav_text_color or "#333333",
        "header_image_url": settings.header_image_url or "",
        "menu_links_html": menu_links_html
    }
    
    return HTMLResponse(
        content=HTML_404_TEMPLATE.format(**template_params), 
        status_code=404
    )
# --------------------------------------

# --- WEBSOCKET ENDPOINTS ---

@app.websocket("/ws/staff")
async def websocket_staff_endpoint(websocket: WebSocket):
    """WebSocket для персоналу (PWA)"""
    await manager.connect_staff(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_staff(websocket)
    except Exception as e:
        logging.error(f"Staff WS Error: {e}")
        manager.disconnect_staff(websocket)

@app.websocket("/ws/table/{table_id}")
async def websocket_table_endpoint(websocket: WebSocket, table_id: int):
    """WebSocket для клієнтів (QR Меню)"""
    await manager.connect_table(websocket, table_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_table(websocket, table_id)
    except Exception as e:
        logging.error(f"Table WS Error: {e}")
        manager.disconnect_table(websocket, table_id)

app.include_router(in_house_menu_router)
app.include_router(clients_router)
app.include_router(admin_order_router)
app.include_router(admin_tables_router)
app.include_router(admin_design_router)
app.include_router(admin_cash_router)
app.include_router(admin_reports_router)
app.include_router(staff_router) 
app.include_router(admin_products_router)
app.include_router(admin_menu_pages_router)
app.include_router(admin_employees_router) 
app.include_router(admin_statuses_router) 
app.include_router(admin_inventory_router)
app.include_router(admin_marketing.router)

@app.get("/sw.js", response_class=FileResponse)
async def get_service_worker():
    return FileResponse("sw.js", media_type="application/javascript")

# --- SEO: ROBOTS.TXT & SITEMAP.XML ---
@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    base_url = str(request.base_url).rstrip("/")
    # МИ ДОДАЛИ: Allow: /api/menu та Allow: /api/page/
    # Це дозволяє ботам читати публічні дані, але все ще блокує інші технічні API
    return f"User-agent: *\nAllow: /\nAllow: /api/menu\nAllow: /api/page/\nDisallow: /api\nDisallow: /admin\nSitemap: {base_url}/sitemap.xml"

@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml(request: Request, session: AsyncSession = Depends(get_db_session)):
    base_url = str(request.base_url).rstrip("/")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Отримуємо всі активні товари з бази
    products_res = await session.execute(select(Product).where(Product.is_active == True))
    products = products_res.scalars().all()
    
    urls = []
    
    # Головна сторінка
    urls.append(f"""
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{date_str}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    """)
    
    # Сторінки товарів
    for product in products:
        slug = transliterate_slug(product.name)
        product_url = f"{base_url}/?p={url_quote_plus(slug)}"
        
        urls.append(f"""
    <url>
        <loc>{product_url}</loc>
        <lastmod>{date_str}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
        """)
    
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        {"".join(urls)}
    </urlset>
    """
    return HTMLResponse(content=content, media_type="application/xml")
# -------------------------------------

class DbSessionMiddleware:
    def __init__(self, session_pool): self.session_pool = session_pool
    async def __call__(self, handler, event, data: Dict[str, Any]):
        async with self.session_pool() as session:
            data['session'] = session
            return await handler(event, data)

async def get_settings(session: AsyncSession) -> Settings:
    settings = await session.get(Settings, 1)
    if not settings:
        settings = Settings(id=1)
        session.add(settings)
        try: await session.commit(); await session.refresh(settings)
        except Exception: await session.rollback(); return Settings(id=1)
    if not settings.telegram_welcome_message: settings.telegram_welcome_message = f"Шановний {{user_name}}, ласкаво просимо!"
    return settings

# --- SSR: СЕРВЕРНИЙ РЕНДЕРИНГ ГОЛОВНОЇ СТОРІНКИ ---
@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def get_web_ordering_page(request: Request, session: AsyncSession = Depends(get_db_session)):
    settings = await get_settings(session)
    logo_html = f'<img src="/{settings.logo_url}" alt="Логотип" class="header-logo">' if settings.logo_url else ''
    
    # 1. Отримуємо БАНЕРИ (Нове!)
    banners_res = await session.execute(
        select(Banner).where(Banner.is_active == True).order_by(Banner.sort_order)
    )
    banners = banners_res.scalars().all()
    
    banners_html_content = ""
    if banners:
        slides = []
        dots = []
        for idx, b in enumerate(banners):
            link_attr = f'onclick="window.location.href=\'{b.link}\'"' if b.link else ""
            slides.append(f'''
            <div class="hero-slide" {link_attr}>
                <img src="/{b.image_url}" alt="{html.escape(b.title or '')}" loading="lazy">
            </div>
            ''')
            active_class = "active" if idx == 0 else ""
            dots.append(f'<div class="slider-dot {active_class}"></div>')
            
        banners_html_content = f'''
        <div class="hero-slider-container">
            <div class="hero-slider">
                {"".join(slides)}
            </div>
            <div class="slider-nav-dots">
                {"".join(dots)}
            </div>
        </div>
        '''

    # 2. Отримуємо категорії
    categories_res = await session.execute(
        select(Category)
        .where(Category.show_on_delivery_site == True)
        .order_by(Category.sort_order, Category.name)
    )
    categories = categories_res.scalars().all()

    # 3. Отримуємо товари з модифікаторами
    products_res = await session.execute(
        select(Product)
        .options(selectinload(Product.modifiers), joinedload(Product.category))
        .join(Category)
        .where(Product.is_active == True, Category.show_on_delivery_site == True)
        .order_by(Product.name)
    )
    products = products_res.scalars().all()

    # 4. Генерація HTML для навігації
    nav_html_parts = []
    for idx, cat in enumerate(categories):
        active_class = "active" if idx == 0 else ""
        nav_html_parts.append(f'<a href="#cat-{cat.id}" class="{active_class}">{html.escape(cat.name)}</a>')
    server_rendered_nav = "".join(nav_html_parts)

    # 5. Генерація HTML для меню
    menu_html_parts = []
    for cat in categories:
        cat_products = [p for p in products if p.category_id == cat.id]
        if not cat_products:
            continue

        menu_html_parts.append(f'<div id="cat-{cat.id}" class="category-section">')
        menu_html_parts.append(f'<h2 class="category-title">{html.escape(cat.name)}</h2>')
        menu_html_parts.append('<div class="products-grid">')

        for prod in cat_products:
            img_src = f"/{prod.image_url}" if prod.image_url else "/static/images/placeholder.jpg"
            
            # Формуємо JSON для кнопки (щоб JS підхопив логіку)
            mods_list = []
            if prod.modifiers:
                for m in prod.modifiers:
                    mods_list.append({
                        "id": m.id, "name": m.name, 
                        "price": float(m.price if m.price is not None else 0)
                    })
            
            prod_data = {
                "id": prod.id, "name": prod.name, "description": prod.description,
                "price": float(prod.price), "image_url": prod.image_url,
                "category_id": prod.category_id,
                "category_name": prod.category.name if prod.category else "",
                "modifiers": mods_list,
                "slug": transliterate_slug(prod.name) # Додаємо slug для посилань
            }
            # Екрануємо лапки для HTML атрибута
            prod_json = json.dumps(prod_data).replace('"', '&quot;')

            # HTML картки товару
            menu_html_parts.append(f'''
            <div class="product-card">
                <div class="product-image-wrapper">
                    <img src="{img_src}" alt="{html.escape(prod.name)}" class="product-image" loading="lazy">
                </div>
                <div class="product-info">
                    <div class="product-header">
                        <h3 class="product-name">{html.escape(prod.name)}</h3>
                        <div class="product-desc">{html.escape(prod.description or "")}</div>
                    </div>
                    <div class="product-footer">
                        <div class="product-price">{prod.price} грн</div>
                        <button class="add-btn" data-product="{prod_json}" onclick="event.stopPropagation(); handleAddClick(this)">
                            <span>Додати</span> <i class="fa-solid fa-plus"></i>
                        </button>
                    </div>
                </div>
                <a href="?p={prod_data['slug']}" style="display:none;">{html.escape(prod.name)}</a>
            </div>
            ''')
        
        menu_html_parts.append('</div></div>') # Закриваємо grid і section

    server_rendered_menu = "".join(menu_html_parts)
    if not server_rendered_menu:
        # Якщо меню пусте або помилка - показуємо спіннер (стара логіка)
        server_rendered_menu = '<div style="text-align:center; padding: 80px;"><div class="spinner"></div></div>'
    
    # Маркетинг Popup
    popup_res = await session.execute(select(MarketingPopup).where(MarketingPopup.is_active == True).limit(1))
    popup = popup_res.scalars().first()
    
    popup_json = "null"
    if popup:
        p_data = {
            "id": popup.id, "title": popup.title, "content": popup.content,
            "image_url": popup.image_url, "button_text": popup.button_text,
            "button_link": popup.button_link, "is_active": popup.is_active,
            "show_once": popup.show_once
        }
        popup_json = json.dumps(p_data)

    menu_items_res = await session.execute(
        select(MenuItem).where(MenuItem.show_on_website == True).order_by(MenuItem.sort_order)
    )
    menu_items = menu_items_res.scalars().all()
    
    menu_links_html = "".join(
        [f'<a href="#" class="footer-link menu-popup-trigger" data-item-id="{item.id}"><i class="fa-solid fa-file-lines"></i> <span>{html.escape(item.title)}</span></a>' for item in menu_items]
    )

    social_links = []
    if settings.instagram_url:
        social_links.append(f'<a href="{html.escape(settings.instagram_url)}" target="_blank"><i class="fa-brands fa-instagram"></i></a>')
    if settings.facebook_url:
        social_links.append(f'<a href="{html.escape(settings.facebook_url)}" target="_blank"><i class="fa-brands fa-facebook"></i></a>')
    
    social_links_html = "".join(social_links)
    free_delivery = settings.free_delivery_from if settings.free_delivery_from is not None else "null"
    header_text_val = settings.site_header_text if settings.site_header_text else (settings.site_title or "Назва")

    # --- ЛОГІКА SEO ДЛЯ ТОВАРІВ ---
    # Отримуємо шаблони з налаштувань (або дефолтні)
    mask_title = settings.product_seo_mask_title or "{name} - {price} грн | {site_title}"
    mask_desc = settings.product_seo_mask_desc or "{name}. {description}"
    
    # Дефолтні мета-дані (для Головної)
    page_title = settings.site_title or "Назва"
    page_desc = settings.seo_description or ""
    page_image = settings.header_image_url or ""
    
    # Перевіряємо, чи відкрито конкретний товар через ?p=slug
    product_slug = request.query_params.get('p')
    if product_slug:
        # Шукаємо товар (серед вже завантажених products або окремим запитом)
        # Оскільки ми вже завантажили products вище для меню, шукаємо в списку:
        target_product = next((p for p in products if transliterate_slug(p.name) == product_slug or str(p.id) == product_slug), None)
        
        if target_product:
            # Формуємо змінні для заміни
            replacements = {
                "{name}": target_product.name,
                "{price}": f"{target_product.price:.2f}",
                "{description}": (target_product.description or "").replace('"', '').replace('\n', ' '),
                "{category}": target_product.category.name if target_product.category else "",
                "{site_title}": settings.site_title or ""
            }
            
            # Застосовуємо шаблон
            page_title = mask_title
            page_desc = mask_desc
            for key, val in replacements.items():
                page_title = page_title.replace(key, str(val))
                page_desc = page_desc.replace(key, str(val))
            
            if target_product.image_url:
                page_image = target_product.image_url

    # Передаємо шаблони в JS через змінну template_params
    seo_templates_json = json.dumps({
        "title_mask": mask_title,
        "desc_mask": mask_desc,
        "site_title": settings.site_title or ""
    })

    # SEO Schema
    base_url = str(request.base_url).rstrip("/")
    schema_data = {
        "@context": "https://schema.org",
        "@type": "Restaurant",
        "name": settings.site_title or "Restaurant",
        "image": [f"{base_url}/{settings.logo_url}"] if settings.logo_url else [],
        "description": settings.seo_description or "",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": settings.footer_address or "",
            "addressLocality": "Odesa", 
            "addressCountry": "UA"
        },
        "telephone": settings.footer_phone or "",
        "url": base_url,
        "menu": base_url,
        "priceRange": "$$",
        "servesCuisine": settings.seo_keywords or "",
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "opens": "10:00", 
                "closes": "22:00"
            }
        ]
    }
    schema_json = json.dumps(schema_data, ensure_ascii=False)

    template_params = {
        "banners_html": banners_html_content, # <--- ПЕРЕДАЄМО СЮДИ БАНЕРИ
        "logo_html": logo_html,
        "menu_links_html": menu_links_html,
        "site_title": html.escape(page_title),       # <-- DYNAMIC TITLE
        "site_header_text": html.escape(header_text_val),
        "seo_description": html.escape(page_desc),   # <-- DYNAMIC DESCRIPTION
        "seo_keywords": html.escape(settings.seo_keywords or ""),
        "primary_color_val": settings.primary_color or "#5a5a5a",
        "secondary_color_val": settings.secondary_color or "#eeeeee",
        "background_color_val": settings.background_color or "#f4f4f4",
        "text_color_val": settings.text_color or "#333333",
        "footer_bg_color_val": settings.footer_bg_color or "#333333",
        "footer_text_color_val": settings.footer_text_color or "#ffffff",
        "font_family_sans_val": settings.font_family_sans or "Golos Text",
        "font_family_serif_val": settings.font_family_serif or "Playfair Display",
        "font_family_sans_encoded": url_quote_plus(settings.font_family_sans or "Golos Text"),
        "font_family_serif_encoded": url_quote_plus(settings.font_family_serif or "Playfair Display"),
        "footer_address": html.escape(settings.footer_address or "Адреса не вказана"),
        "footer_phone": html.escape(settings.footer_phone or ""),
        "working_hours": html.escape(settings.working_hours or ""),
        "social_links_html": social_links_html, 
        "category_nav_bg_color": settings.category_nav_bg_color or "#ffffff",
        "category_nav_text_color": settings.category_nav_text_color or "#333333",
        "header_image_url": page_image,              # <-- DYNAMIC IMAGE
        "wifi_ssid": html.escape(settings.wifi_ssid or ""),
        "wifi_password": html.escape(settings.wifi_password or ""),
        "delivery_cost_val": float(settings.delivery_cost),
        "free_delivery_from_val": float(free_delivery) if free_delivery != "null" else "null",
        "popup_data_json": popup_json,
        "delivery_zones_content": settings.delivery_zones_content or "<p>Інформація про зони доставки відсутня.</p>",
        "google_analytics_id": settings.google_analytics_id or "None",
        
        # --- НОВІ ПАРАМЕТРИ ДЛЯ GOOGLE ADS ---
        "google_ads_id": settings.google_ads_id or "None",
        "google_ads_conversion_label": settings.google_ads_conversion_label or "None",
        # -------------------------------------

        "schema_json": schema_json,
        "server_rendered_nav": server_rendered_nav,
        "server_rendered_menu": server_rendered_menu,
        "seo_templates_json": seo_templates_json  # <-- NEW: PASS TEMPLATES TO JS
    }

    return HTMLResponse(content=WEB_ORDER_HTML.format(**template_params))

@app.get("/api/page/{item_id}", response_class=JSONResponse)
async def get_menu_page_content(item_id: int, session: AsyncSession = Depends(get_db_session)):
    menu_item = await session.get(MenuItem, item_id)
    
    if not menu_item or (not menu_item.show_on_website and not menu_item.show_in_qr):
        raise HTTPException(status_code=404, detail="Сторінку не знайдено")
        
    return {"title": menu_item.title, "content": menu_item.content}
@app.get("/api/menu")
async def get_menu_data(session: AsyncSession = Depends(get_db_session)):
    try:
        categories_res = await session.execute(
            select(Category)
            .where(Category.show_on_delivery_site == True)
            .order_by(Category.sort_order, Category.name)
        )
        categories = [{"id": c.id, "name": c.name} for c in categories_res.scalars().all()]
        
        products_res = await session.execute(
            select(Product)
            .options(selectinload(Product.modifiers), joinedload(Product.category)) 
            .join(Category)
            .where(Product.is_active == True, Category.show_on_delivery_site == True)
	    .order_by(Product.name)
        )
        
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
                "image_url": p.image_url, 
                "category_id": p.category_id,
                "category_name": p.category.name if p.category else "", # Added category name
                "modifiers": mods_list,
                # ДОДАЄМО SLUG ТАКОЖ В API (для сумісності)
                "slug": transliterate_slug(p.name)
            })

        return JSONResponse(content={"categories": categories, "products": products})
    except Exception as e:
        logging.error(f"Error in /api/menu: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(e)})


@app.post("/api/place_order")
async def place_web_order(request: Request, order_data: dict = Body(...), session: AsyncSession = Depends(get_db_session)):
    items = order_data.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Кошик порожній")

    try:
        product_ids = [int(item['id']) for item in items]
        
        all_mod_ids = set()
        for item in items:
            for mod in item.get('modifiers', []):
                if 'id' in mod:
                    all_mod_ids.add(int(mod['id']))
        
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Невірний формат ID.")

    products_res = await session.execute(select(Product).where(Product.id.in_(product_ids)))
    db_products = {str(p.id): p for p in products_res.scalars().all()}

    db_modifiers = {}
    if all_mod_ids:
        mods_res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
        for m in mods_res.scalars().all():
            db_modifiers[m.id] = m

    total_price = Decimal('0.00')
    order_items_objects = []
    log_items = [] # Для логу

    for item in items:
        pid = str(item['id'])
        if pid in db_products:
            product = db_products[pid]
            qty = int(item.get('quantity', 1))
            
            final_modifiers_data = []
            mods_price_sum = Decimal(0)
            
            raw_mods = item.get('modifiers', [])
            for raw_mod in raw_mods:
                mid = int(raw_mod.get('id'))
                if mid in db_modifiers:
                    mod_db = db_modifiers[mid]
                    mods_price_sum += mod_db.price
                    final_modifiers_data.append({
                        "id": mod_db.id,
                        "name": mod_db.name,
                        "price": float(mod_db.price),
                        "ingredient_id": mod_db.ingredient_id,
                        "ingredient_qty": float(mod_db.ingredient_qty),
                        "warehouse_id": mod_db.warehouse_id 
                    })
            
            item_total_price = (product.price + mods_price_sum)
            total_price += item_total_price * qty
            
            log_items.append(f"{product.name} x{qty}")

            order_items_objects.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=qty,
                price_at_moment=item_total_price,
                preparation_area=product.preparation_area,
                modifiers=final_modifiers_data 
            ))

    settings = await session.get(Settings, 1) or Settings()
    delivery_cost = Decimal(0)

    is_delivery = order_data.get('is_delivery', True)

    if is_delivery:
        if settings.free_delivery_from is not None and total_price >= settings.free_delivery_from:
            delivery_cost = Decimal(0)
        else:
            delivery_cost = settings.delivery_cost

    total_price += delivery_cost

    address = order_data.get('address') if is_delivery else None
    order_type = 'delivery' if is_delivery else 'pickup'
    payment_method = order_data.get('payment_method', 'cash')
    customer_name = order_data.get('customer_name', 'Клієнт')
    
    # НОРМАЛІЗАЦІЯ ПРИ ЗАМОВЛЕННІ ЧЕРЕЗ WEB
    phone_number = normalize_phone(order_data.get('phone_number'))

    order = Order(
        customer_name=customer_name, 
        phone_number=phone_number, # <-- Використовуємо нормалізований
        address=address, 
        total_price=total_price,
        is_delivery=is_delivery, delivery_time=order_data.get('delivery_time', "Якнайшвидше"),
        order_type=order_type,
        payment_method=payment_method,
        # ДОДАЄМО КОМЕНТАР
        comment=order_data.get('comment'),
        items=order_items_objects
    )
    session.add(order)
    
    # --- ВАЖЛИВО: Отримуємо ID замовлення ---
    await session.flush() 
    # ----------------------------------------
    
    # --- ЛОГУВАННЯ СТВОРЕННЯ (WEB) ---
    items_str = ", ".join(log_items)
    # Тепер order.id вже існує
    session.add(OrderLog(order_id=order.id, message=f"Замовлення створено через сайт/QR. Склад: {items_str}", actor=f"{customer_name} (Web)"))
    # ---------------------------------

    await session.commit()
    await session.refresh(order)

    if request.app.state.admin_bot:
        await notify_new_order_to_staff(request.app.state.admin_bot, order, session)

    return JSONResponse(content={"message": "Замовлення успішно розміщено", "order_id": order.id})

# --- НАСТУПНИЙ БЛОК БУВ ПРОПУЩЕНИЙ У ПОПЕРЕДНІЙ ВЕРСІЇ ---

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    orders_res = await session.execute(select(Order).order_by(Order.id.desc()).limit(5))
    orders_count_res = await session.execute(select(func.count(Order.id)))
    products_count_res = await session.execute(select(func.count(Product.id)))
    orders_count = orders_count_res.scalar_one_or_none() or 0
    products_count = products_count_res.scalar_one_or_none() or 0

    body = f"""
    <div class="card"><strong>Ласкаво просимо, {username}!</strong></div>
    <div class="card"><h2>📈 Швидка статистика</h2><p><strong>Всього страв:</strong> {products_count}</p><p><strong>Всього замовлень:</strong> {orders_count}</p></div>
    <div class="card"><h2>📦 5 останніх замовлень</h2>
        <table><thead><tr><th>ID</th><th>Клієнт</th><th>Телефон</th><th>Сума</th></tr></thead><tbody>
        {''.join([f"<tr><td><a href='/admin/order/manage/{o.id}'>#{o.id}</a></td><td>{html.escape(o.customer_name or '')}</td><td>{html.escape(o.phone_number or '')}</td><td>{o.total_price} грн</td></tr>" for o in orders_res.scalars().all()]) or "<tr><td colspan='4'>Немає замовлень</td></tr>"}
        </tbody></table></div>"""

    active_classes = {key: "" for key in ["orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["main_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Головна панель", body=body, site_title=settings.site_title or "Назва", **active_classes
    ))

@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    categories_res = await session.execute(select(Category).order_by(Category.sort_order, Category.name))
    categories = categories_res.scalars().all()

    def bool_to_icon(val): return '✅' if val else '❌'
    rows = "".join([f"""<tr><td>{c.id}</td><td><form action="/admin/edit_category/{c.id}" method="post" class="inline-form"><input type="hidden" name="field" value="name_sort"><input type="text" name="name" value="{html.escape(c.name)}" style="width: 150px;"><input type="number" name="sort_order" value="{c.sort_order}" style="width: 80px;"><button type="submit">💾</button></form></td><td style="text-align: center;"><form action="/admin/edit_category/{c.id}" method="post" class="inline-form"><input type="hidden" name="field" value="show_on_delivery_site"><input type="hidden" name="value" value="{'false' if c.show_on_delivery_site else 'true'}"><button type="submit" class="button-sm" style="background: none; color: inherit; padding: 0; font-size: 1.2rem;">{bool_to_icon(c.show_on_delivery_site)}</button></form></td><td style="text-align: center;"><form action="/admin/edit_category/{c.id}" method="post" class="inline-form"><input type="hidden" name="field" value="show_in_restaurant"><input type="hidden" name="value" value="{'false' if c.show_in_restaurant else 'true'}"><button type="submit" class="button-sm" style="background: none; color: inherit; padding: 0; font-size: 1.2rem;">{bool_to_icon(c.show_in_restaurant)}</button></form></td><td class='actions'><a href='/admin/delete_category/{c.id}' onclick="return confirm('Ви впевнені?');" class='button-sm danger'>🗑️</a></td></tr>""" for c in categories])

    body = f"""<div class="card"><h2>Додати нову категорію</h2><form action="/admin/add_category" method="post"><label for="name">Назва категорії:</label><input type="text" name="name" required><label for="sort_order">Порядок сортування:</label><input type="number" id="sort_order" name="sort_order" value="100"><div class="checkbox-group"><input type="checkbox" id="show_on_delivery_site" name="show_on_delivery_site" value="true" checked><label for="show_on_delivery_site">Показувати на сайті та в боті (доставка)</label></div><div class="checkbox-group"><input type="checkbox" id="show_in_restaurant" name="show_in_restaurant" value="true" checked><label for="show_in_restaurant">Показувати в закладі (QR-меню)</label></div><button type="submit">Додати</button></form></div><div class="card"><h2>Список категорій</h2><table><thead><tr><th>ID</th><th>Назва та сортування</th><th>Сайт/Бот</th><th>В закладі</th><th>Дії</th></tr></thead><tbody>{rows or "<tr><td colspan='5'>Немає категорій</td></tr>"}</tbody></table></div>"""
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["categories_active"] = "active"
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Категорії", body=body, site_title=settings.site_title or "Назва", **active_classes))

@app.post("/admin/add_category")
async def add_category(name: str = Form(...), sort_order: int = Form(100), show_on_delivery_site: bool = Form(False), show_in_restaurant: bool = Form(False), session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    session.add(Category(name=name, sort_order=sort_order, show_on_delivery_site=show_on_delivery_site, show_in_restaurant=show_in_restaurant))
    await session.commit()
    return RedirectResponse(url="/admin/categories", status_code=303)

@app.post("/admin/edit_category/{cat_id}")
async def edit_category(cat_id: int, name: Optional[str] = Form(None), sort_order: Optional[int] = Form(None), field: Optional[str] = Form(None), value: Optional[str] = Form(None), session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    category = await session.get(Category, cat_id)
    if category:
        if field == "name_sort" and name is not None and sort_order is not None:
            category.name = name
            category.sort_order = sort_order
        elif field in ["show_on_delivery_site", "show_in_restaurant"]:
            setattr(category, field, value.lower() == 'true')
        await session.commit()
    return RedirectResponse(url="/admin/categories", status_code=303)

@app.get("/admin/delete_category/{cat_id}")
async def delete_category(cat_id: int, session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    category = await session.get(Category, cat_id)
    if category:
        products_exist_res = await session.execute(select(func.count(Product.id)).where(Product.category_id == cat_id))
        if products_exist_res.scalar_one_or_none() > 0:
             return RedirectResponse(url="/admin/categories?error=category_in_use", status_code=303)
        await session.delete(category)
        await session.commit()
    return RedirectResponse(url="/admin/categories", status_code=303)

@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(page: int = Query(1, ge=1), q: str = Query(None, alias="search"), session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    per_page = 15
    offset = (page - 1) * per_page
    
    query = select(Order).options(joinedload(Order.status), selectinload(Order.items)).order_by(Order.id.desc())
    
    filters = []
    if q:
        search_term = q.replace('#', '')
        if search_term.isdigit():
             filters.append(or_(Order.id == int(search_term), Order.customer_name.ilike(f"%{q}%"), Order.phone_number.ilike(f"%{q}%")))
        else:
             filters.append(or_(Order.customer_name.ilike(f"%{q}%"), Order.phone_number.ilike(f"%{q}%")))
    if filters:
        query = query.where(*filters)

    count_query = select(func.count(Order.id))
    if filters:
        count_query = count_query.where(*filters)
        
    total_res = await session.execute(count_query)
    total = total_res.scalar_one_or_none() or 0
    
    orders_res = await session.execute(query.limit(per_page).offset(offset))
    orders = orders_res.scalars().all()
    pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    rows = ""
    for o in orders:
        items_str = ", ".join([f"{i.product_name} x {i.quantity}" for i in o.items])
        if len(items_str) > 50:
            items_str = items_str[:50] + "..."
            
        rows += f"""
        <tr>
            <td><a href="/admin/order/manage/{o.id}" title="Керувати замовленням">#{o.id}</a></td>
            <td>{html.escape(o.customer_name or '')}</td>
            <td>{html.escape(o.phone_number or '')}</td>
            <td>{o.total_price} грн</td>
            <td><span class='status'>{o.status.name if o.status else '-'}</span></td>
            <td>{html.escape(items_str)}</td>
            <td class='actions'>
                <a href='/admin/order/manage/{o.id}' class='button-sm' title="Керувати статусом та кур'єром">⚙️ Керувати</a>
                <a href='/admin/order/edit/{o.id}' class='button-sm' title="Редагувати склад замовлення">✏️ Редагувати</a>
            </td>
        </tr>"""

    links_orders = []
    for i in range(1, pages + 1):
        search_part = f'&search={q}' if q else ''
        class_part = 'active' if i == page else ''
        links_orders.append(f'<a href="/admin/orders?page={i}{search_part}" class="{class_part}">{i}</a>')
    
    pagination = f"<div class='pagination'>{' '.join(links_orders)}</div>"

    body = f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2>📋 Список замовлень</h2>
            <a href="/admin/order/new" class="button"><i class="fa-solid fa-plus"></i> Створити замовлення</a>
        </div>
        <form action="/admin/orders" method="get" class="search-form">
            <input type="text" name="search" placeholder="Пошук за ID, іменем, телефоном..." value="{q or ''}">
            <button type="submit">🔍 Знайти</button>
        </form>
        <table><thead><tr><th>ID</th><th>Клієнт</th><th>Телефон</th><th>Сума</th><th>Статус</th><th>Склад</th><th>Дії</th></tr></thead><tbody>
        {rows or "<tr><td colspan='7'>Немає замовлень</td></tr>"}
        </tbody></table>{pagination if pages > 1 else ''}
    </div>"""
    active_classes = {key: "" for key in ["main_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["orders_active"] = "active"
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Замовлення", body=body, site_title=settings.site_title or "Назва", **active_classes))

@app.get("/admin/order/new", response_class=HTMLResponse)
async def get_add_order_form(session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    initial_data = {"items": {}, "action": "/api/admin/order/new", "submit_text": "Створити замовлення", "form_values": None}
    script = f"<script>document.addEventListener('DOMContentLoaded',()=>{{if(typeof window.initializeForm==='function'&&!window.orderFormInitialized){{window.initializeForm({json.dumps(initial_data)});window.orderFormInitialized=true;}}else if(!window.initializeForm){{document.addEventListener('formScriptLoaded',()=>{{if(!window.orderFormInitialized){{window.initializeForm({json.dumps(initial_data)});window.orderFormInitialized=true;}}}});}}}});</script>"
    body = ADMIN_ORDER_FORM_BODY + script
    active_classes = {key: "" for key in ["main_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["orders_active"] = "active"
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title="Нове замовлення", body=body, site_title=settings.site_title or "Назва", **active_classes))

@app.get("/admin/order/edit/{order_id}", response_class=HTMLResponse)
async def get_edit_order_form(order_id: int, session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    order = await session.get(Order, order_id, options=[joinedload(Order.status), selectinload(Order.items)])
    if not order: raise HTTPException(404, "Замовлення не знайдено")

    if order.status.is_completed_status or order.status.is_cancelled_status:
        return HTMLResponse(f"""<div style="padding: 20px; font-family: sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;"><h2 style="color: #d32f2f;">⛔️ Замовлення #{order.id} закрите</h2><p>Редагування заборонено.</p><div style="margin-top: 20px;"><a href="/admin/orders" style="display: inline-block; padding: 10px 20px; background: #5a5a5a; color: white; text-decoration: none; border-radius: 5px;">⬅️ Назад</a><a href="/admin/order/manage/{order.id}" style="display: inline-block; padding: 10px 20px; background: #0d6efd; color: white; text-decoration: none; border-radius: 5px; margin-left: 10px;">⚙️ Керувати</a></div></div>""")

    initial_items = {}
    for item in order.items:
        initial_items[item.product_id] = {"name": item.product_name, "price": float(item.price_at_moment), "quantity": item.quantity}

    initial_data = {
        "items": initial_items,
        "action": f"/api/admin/order/edit/{order_id}",
        "submit_text": "Зберегти зміни",
        "form_values": {
            "phone_number": order.phone_number or "", 
            "customer_name": order.customer_name or "", 
            "is_delivery": order.is_delivery, 
            "address": order.address or "",
            "comment": order.comment or "" # ДОДАЄМО КОМЕНТАР
        }
    }
    script = f"<script>document.addEventListener('DOMContentLoaded',()=>{{if(typeof window.initializeForm==='function'&&!window.orderFormInitialized){{window.initializeForm({json.dumps(initial_data)});window.orderFormInitialized=true;}}else if(!window.initializeForm){{document.addEventListener('formScriptLoaded',()=>{{if(!window.orderFormInitialized){{window.initializeForm({json.dumps(initial_data)});window.orderFormInitialized=true;}}}});}}}});</script>"
    body = ADMIN_ORDER_FORM_BODY + script
    active_classes = {key: "" for key in ["main_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["orders_active"] = "active"
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(title=f"Редагування замовлення #{order.id}", body=body, site_title=settings.site_title or "Назва", **active_classes))

async def _process_and_save_order(order: Order, data: dict, session: AsyncSession, request: Request):
    is_new_order = order.id is None
    actor_name = "Адмін (Веб)"
    
    # НОРМАЛІЗАЦІЯ В АДМІНЦІ
    normalized_phone = normalize_phone(data.get("phone_number"))

    # Логування змін інформації про клієнта
    if not is_new_order:
        changes = []
        if order.customer_name != data.get("customer_name"):
            changes.append(f"Ім'я: {order.customer_name} -> {data.get('customer_name')}")
        if order.phone_number != normalized_phone:
            changes.append(f"Тел: {order.phone_number} -> {normalized_phone}")
        if order.is_delivery != (data.get("delivery_type") == "delivery"):
            changes.append(f"Тип: {'Доставка' if order.is_delivery else 'Самовивіз'} -> {data.get('delivery_type')}")
        
        if changes:
             session.add(OrderLog(order_id=order.id, message="Змінено дані: " + "; ".join(changes), actor=actor_name))

    order.customer_name = data.get("customer_name")
    order.phone_number = normalized_phone
    order.is_delivery = data.get("delivery_type") == "delivery"
    order.address = data.get("address") if order.is_delivery else None
    order.order_type = "delivery" if order.is_delivery else "pickup"
    # ОНОВЛЮЄМО КОМЕНТАР
    order.comment = data.get("comment")

    items_from_js = data.get("items", {})
    
    # Логування змін складу (тільки для існуючих замовлень)
    new_items_log = []
    
    old_items_map = {}
    if order.id:
        if 'items' not in order.__dict__:
             await session.refresh(order, ['items'])
        old_items_map = {item.product_id: item.quantity for item in order.items}
        await session.execute(sa.delete(OrderItem).where(OrderItem.order_id == order.id))
    
    total_price = Decimal('0.00') 
    new_items_objects = []
    
    current_items_map = {} 

    if items_from_js:
        valid_product_ids = [int(pid) for pid in items_from_js.keys() if pid.isdigit()]
        if valid_product_ids:
            products_res = await session.execute(select(Product).where(Product.id.in_(valid_product_ids)))
            db_products_map = {p.id: p for p in products_res.scalars().all()}

            for pid_str, item_data in items_from_js.items():
                if not pid_str.isdigit(): continue
                pid = int(pid_str)
                product = db_products_map.get(pid)
                if product:
                    qty = int(item_data.get('quantity', 0))
                    if qty > 0:
                        current_items_map[pid] = {"name": product.name, "qty": qty}
                        total_price += product.price * qty
                        new_items_objects.append(OrderItem(
                            product_id=pid,
                            product_name=product.name,
                            quantity=qty,
                            price_at_moment=product.price, 
                            preparation_area=product.preparation_area
                        ))

    # Рахуємо різницю для логу (якщо це не нове замовлення)
    if not is_new_order:
        log_diffs = []
        for pid, info in current_items_map.items():
            old_qty = old_items_map.get(pid, 0)
            if old_qty == 0:
                log_diffs.append(f"Додано: {info['name']} x{info['qty']}")
            elif old_qty != info['qty']:
                log_diffs.append(f"Змінено к-сть: {info['name']} ({old_qty} -> {info['qty']})")
        
        for pid, old_qty in old_items_map.items():
            if pid not in current_items_map:
                log_diffs.append(f"Видалено товар (ID: {pid})")
        
        if log_diffs:
             session.add(OrderLog(order_id=order.id, message="Зміни в товарах: " + "; ".join(log_diffs), actor=actor_name))


    order.total_price = total_price
    
    if is_new_order:
        session.add(order)
        if not order.status_id:
            new_status_res = await session.execute(select(OrderStatus.id).where(OrderStatus.name == "Новий").limit(1))
            order.status_id = new_status_res.scalar_one_or_none() or 1
        
        await session.flush()
        
        # Лог створення
        items_str = ", ".join([f"{item.product_name} x{item.quantity}" for item in new_items_objects])
        session.add(OrderLog(order_id=order.id, message=f"Замовлення створено через адмінку. Товари: {items_str}", actor=actor_name))
        
        for item in new_items_objects:
            item.order_id = order.id
            session.add(item)
    else:
        for item in new_items_objects:
            item.order_id = order.id
            session.add(item)

    await session.commit()
    await session.refresh(order)

    if is_new_order:
        try:
             session.add(OrderStatusHistory(order_id=order.id, status_id=order.status_id, actor_info="Адміністративна панель"))
             await session.commit()
        except Exception as e: logging.error(f"History error: {e}")

        admin_bot = request.app.state.admin_bot
        if admin_bot:
            await notify_new_order_to_staff(admin_bot, order, session)

@app.post("/api/admin/order/new", response_class=JSONResponse)
async def api_create_order(request: Request, session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    try: data = await request.json()
    except json.JSONDecodeError: raise HTTPException(400, "Invalid JSON")
    try:
        await _process_and_save_order(Order(), data, session, request)
        return JSONResponse(content={"message": "Замовлення створено успішно", "redirect_url": "/admin/orders"})
    except Exception as e:
        logging.error(f"Create order error: {e}", exc_info=True)
        raise HTTPException(500, "Failed to create order")

@app.post("/api/admin/order/edit/{order_id}", response_class=JSONResponse)
async def api_update_order(order_id: int, request: Request, session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    try: data = await request.json()
    except json.JSONDecodeError: raise HTTPException(400, "Invalid JSON")
    
    order = await session.get(Order, order_id, options=[joinedload(Order.status)])
    if not order: raise HTTPException(404, "Order not found")
    if order.status.is_completed_status or order.status.is_cancelled_status: raise HTTPException(400, "Order closed")

    try:
        await _process_and_save_order(order, data, session, request)
        return JSONResponse(content={"message": "Замовлення оновлено успішно", "redirect_url": "/admin/orders"})
    except Exception as e:
        logging.error(f"Update order error: {e}", exc_info=True)
        raise HTTPException(500, "Failed to update order")

@app.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_menu(session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    
    body = ADMIN_REPORTS_BODY
    
    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["reports_active"] = "active"
    
    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Звіти", 
        body=body, 
        site_title=settings.site_title, 
        **active_classes
    ))

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(saved: bool = False, session: AsyncSession = Depends(get_db_session), username: str = Depends(check_credentials)):
    settings = await get_settings(session)
    
    current_logo_html = f'<img src="/{settings.logo_url}" alt="Лого" style="height: 50px;">' if settings.logo_url else "Логотип не завантажено"
    cache_buster = secrets.token_hex(4)
    
    body = ADMIN_SETTINGS_BODY.format(
        current_logo_html=current_logo_html,
        cache_buster=cache_buster
    )
    
    if saved:
        body = "<div class='card' style='background:#d4edda; color:#155724; padding:10px; margin-bottom:20px;'>✅ Налаштування збережено!</div>" + body

    active_classes = {key: "" for key in ["main_active", "orders_active", "clients_active", "tables_active", "products_active", "categories_active", "menu_active", "employees_active", "statuses_active", "reports_active", "settings_active", "design_active", "inventory_active"]}
    active_classes["settings_active"] = "active"

    return HTMLResponse(ADMIN_HTML_TEMPLATE.format(
        title="Налаштування", body=body, site_title=settings.site_title or "Назва", **active_classes
    ))

@app.post("/admin/settings")
async def save_admin_settings(
    session: AsyncSession = Depends(get_db_session), 
    username: str = Depends(check_credentials), 
    logo_file: UploadFile = File(None), 
    apple_touch_icon: UploadFile = File(None), 
    favicon_32x32: UploadFile = File(None), 
    favicon_16x16: UploadFile = File(None), 
    favicon_ico: UploadFile = File(None), 
    site_webmanifest: UploadFile = File(None),
    icon_192: UploadFile = File(None),   # <-- Додано
    icon_512: UploadFile = File(None)    # <-- Додано
):
    settings = await get_settings(session)
    if logo_file and logo_file.filename:
        if settings.logo_url and os.path.exists(settings.logo_url):
            try: os.remove(settings.logo_url)
            except OSError: pass
        ext = os.path.splitext(logo_file.filename)[1]
        path = os.path.join("static/images", secrets.token_hex(8) + ext)
        try:
            async with aiofiles.open(path, 'wb') as f: await f.write(await logo_file.read())
            settings.logo_url = path.replace("\\", "/") 
        except Exception as e: logging.error(f"Save logo error: {e}")

    favicon_dir = "static/favicons"
    os.makedirs(favicon_dir, exist_ok=True)
    
    # Оновлений словник для збереження
    files_to_save = {
        "apple-touch-icon.png": apple_touch_icon, 
        "favicon-32x32.png": favicon_32x32, 
        "favicon-16x16.png": favicon_16x16, 
        "favicon.ico": favicon_ico, 
        "site.webmanifest": site_webmanifest,
        "icon-192.png": icon_192,  # <-- Додано
        "icon-512.png": icon_512   # <-- Додано
    }
    
    for name, file in files_to_save.items():
        if file and file.filename:
            try:
                async with aiofiles.open(os.path.join(favicon_dir, name), 'wb') as f: 
                    await f.write(await file.read())
            except Exception as e: 
                logging.error(f"Save favicon error: {e}")

    await session.commit()
    return RedirectResponse(url="/admin/settings?saved=true", status_code=303)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)