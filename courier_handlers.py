# courier_handlers.py

import logging
import html as html_module
from aiogram import Dispatcher, F, html, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload, selectinload
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus
import re 
import os
from decimal import Decimal

# Импорт моделей
from models import Employee, Order, OrderStatus, Settings, OrderStatusHistory, Table, Category, Product, OrderItem, OrderLog
# Импорт модификаторов
from inventory_models import Modifier
from notification_manager import notify_new_order_to_staff, notify_all_parties_on_status_change, notify_station_completion
from cash_service import link_order_to_shift, register_employee_debt

logger = logging.getLogger(__name__)

class StaffAuthStates(StatesGroup):
    waiting_for_phone = State()

class WaiterCreateOrderStates(StatesGroup):
    managing_cart = State()
    choosing_category = State()
    choosing_product = State()
    choosing_modifiers = State()

def get_staff_login_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🔐 Вхід оператора"))
    builder.row(KeyboardButton(text="🚚 Вхід кур'єра"))
    builder.row(KeyboardButton(text="🤵 Вхід офіціанта"))
    # Універсальна кнопка для входу виробничого персоналу
    builder.row(KeyboardButton(text="🧑‍🍳 Вхід на зміну (Цех)"))
    return builder.as_markup(resize_keyboard=True)

def get_staff_keyboard(employee: Employee):
    builder = ReplyKeyboardBuilder()
    role = employee.role
    
    if employee.is_on_shift:
        builder.row(KeyboardButton(text="🔴 Завершити зміну"))
    else:
        builder.row(KeyboardButton(text="🟢 Почати зміну"))

    role_buttons = []
    if employee.is_on_shift:
        if role.can_be_assigned:
            role_buttons.append(KeyboardButton(text="📦 Мої замовлення"))
        if role.can_serve_tables:
            role_buttons.append(KeyboardButton(text="🍽 Мої столики"))
        # Універсальна кнопка для виробництва (Кухня/Бар/Піца і т.д.)
        if role.can_receive_kitchen_orders or role.can_receive_bar_orders:
             role_buttons.append(KeyboardButton(text="🔥 Замовлення (Цех)"))
            
    if role_buttons:
        builder.row(*role_buttons)

    builder.row(KeyboardButton(text="🚪 Вийти"))
    return builder.as_markup(resize_keyboard=True)

# --- ДОПОМІЖНА ФУНКЦІЯ: Отримання відфільтрованого тексту чека по ID цехів ---
async def _get_workshop_order_text(session: AsyncSession, order: Order, workshop_ids: list[int]) -> str:
    """
    Повертає текст складу замовлення, залишаючи ТІЛЬКИ товари, 
    які готуються у цехах зі списку workshop_ids.
    """
    if 'items' not in order.__dict__:
        await session.refresh(order, ['items'])
        
    if not order.items:
        return ""

    filtered_lines = []
    for item in order.items:
        # Завантажуємо продукт, якщо його немає, щоб отримати production_warehouse_id
        # (зазвичай він завантажується через selectinload, але перевірка не завадить)
        if 'product' not in item.__dict__:
             item.product = await session.get(Product, item.product_id)

        # Перевіряємо, чи належить товар до одного з цехів працівника
        # item.product.production_warehouse_id - це ID складу виробництва
        if item.product and item.product.production_warehouse_id in workshop_ids:
            mods_str = ""
            if item.modifiers:
                mod_names = [m.get('name', '') for m in item.modifiers]
                if mod_names:
                    mods_str = f" (+ {', '.join(mod_names)})"
            
            # Статус конкретної страви
            status_icon = "✅" if item.is_ready else "⏳"
            
            filtered_lines.append(f"{status_icon} {html_module.escape(item.product_name)}{mods_str} x {item.quantity}")

    if not filtered_lines:
        return ""
        
    return "\n".join(filtered_lines)


# --- УНІВЕРСАЛЬНИЙ ЕКРАН ВИРОБНИЦТВА (Цех) ---
async def show_workshop_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
    user_id = message_or_callback.from_user.id
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role)))
    
    if not employee: return await message.answer("❌ Авторизуйтесь.")
    if not employee.is_on_shift: return await message.answer("🔴 Ви не на зміні.")
    
    # Отримуємо ID цехів співробітника (налаштовується в адмінці)
    my_workshop_ids = employee.assigned_workshop_ids or []
    if not my_workshop_ids:
        # Спроба фолбека для старих налаштувань (якщо поле пусте, але є роль)
        # Але краще вимагати налаштування.
        return await message.answer("❌ За вами не закріплено жодного цеху. Зверніться до адміністратора для налаштування прав.")

    # Статуси "В роботі"
    statuses_res = await session.execute(select(OrderStatus.id).where(OrderStatus.requires_kitchen_notify == True))
    status_ids = statuses_res.scalars().all()

    orders_res = await session.execute(
        select(Order)
        .options(joinedload(Order.status), joinedload(Order.table), selectinload(Order.items).joinedload(OrderItem.product))
        .where(Order.status_id.in_(status_ids))
        .order_by(Order.id.asc())
    )
    all_orders = orders_res.scalars().all()

    text = "🔥 <b>Черга замовлень (Ваш цех):</b>\n\n"
    count = 0
    
    kb = InlineKeyboardBuilder()
    
    for order in all_orders:
        # Отримуємо текст тільки для товарів мого цеху
        products_text = await _get_workshop_order_text(session, order, my_workshop_ids)
        
        # Якщо тексту немає - значить в цьому замовленні немає страв для мого цеху
        if not products_text: continue 
            
        # Якщо в тексті немає іконки "⏳" - значить всі мої страви вже готові, ховати замовлення
        if "⏳" not in products_text: continue 
            
        count += 1
        table_info = order.table.name if order.table else ('Доставка' if order.is_delivery else 'Самовивіз')
        
        text += (f"═════════════════\n"
                 f"<b>№{order.id}</b> ({table_info})\n"
                 f"Час: {order.created_at.strftime('%H:%M')}\n"
                 f"{products_text}\n\n")
        
        # Кнопка "Все готово" для цього замовлення (для цього цеху)
        kb.row(InlineKeyboardButton(text=f"✅ Готово #{order.id}", callback_data=f"chef_ready_all_{order.id}"))
    
    if count == 0:
        text += "👍 Черга пуста. Все приготовлено."
        
    kb.adjust(1)
    # Кнопка оновлення
    kb.row(InlineKeyboardButton(text="🔄 Оновити список", callback_data="refresh_workshop"))
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            # Щоб не блимало, якщо текст не змінився
            if message.text != text.replace("<b>", "").replace("</b>", ""): # Aiogram іноді псує форматування при порівнянні
                 await message.edit_text(text, reply_markup=kb.as_markup())
            else:
                 # Просто оновлюємо клавіатуру якщо треба
                 try: await message.edit_reply_markup(reply_markup=kb.as_markup())
                 except: pass
            await message_or_callback.answer()
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass


# --- ЕКРАН КУР'ЄРА ---
async def show_courier_orders(message_or_callback: Message | CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
    user_id = message_or_callback.from_user.id
    message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback

    employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role)))
    
    if not employee or not employee.role.can_be_assigned:
         return await message.answer("❌ У вас немає прав кур'єра.")

    final_statuses_res = await session.execute(
        select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True))
    )
    final_status_ids = final_statuses_res.scalars().all()

    orders_res = await session.execute(
        select(Order).options(joinedload(Order.status)).where(
            Order.courier_id == employee.id,
            Order.status_id.not_in(final_status_ids)
        ).order_by(Order.id.desc())
    )
    orders = orders_res.scalars().all()

    text = "🚚 <b>Ваші активні замовлення:</b>\n\n"
    if not employee.is_on_shift:
         text += "🔴 Ви не на зміні. Натисніть '🟢 Почати зміну', щоб отримувати нові замовлення.\n\n"
    if not orders:
        text += "На даний момент немає активних замовлень, призначених вам."
    
    kb = InlineKeyboardBuilder()
    if orders:
        for order in orders:
            status_name = order.status.name if order.status else "Невідомий"
            address_info = order.address if order.is_delivery else 'Самовивіз'
            
            # ВІДОБРАЖЕННЯ ІКОНКИ ОПЛАТИ В СПИСКУ
            pay_icon = "💳" if order.payment_method == 'card' else "💵"
            
            text += (f"<b>Замовлення #{order.id}</b> ({status_name})\n"
                     f"📍 Адреса: {html_module.escape(address_info)}\n"
                     f"💰 Сума: {order.total_price} грн | {pay_icon}\n\n")
            kb.row(InlineKeyboardButton(text=f"Дії по замовленню #{order.id}", callback_data=f"courier_view_order_{order.id}"))
        kb.adjust(1)
    
    try:
        if isinstance(message_or_callback, CallbackQuery):
            await message.edit_text(text, reply_markup=kb.as_markup())
            await message_or_callback.answer()
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass

async def show_waiter_tables(message_or_callback: Message | CallbackQuery, session: AsyncSession, state: FSMContext):
    is_callback = isinstance(message_or_callback, CallbackQuery)
    message = message_or_callback.message if is_callback else message_or_callback
    user_id = message_or_callback.from_user.id
    
    await state.clear()
    
    employee = await session.scalar(
        select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role))
    )
    
    if not employee or not employee.role.can_serve_tables:
        return await message.answer("❌ У вас немає прав офіціанта.") if not is_callback else message_or_callback.answer("❌ Немає прав.", show_alert=True)

    if not employee.is_on_shift:
        text_off = "🔴 Ви не на зміні."
        return await message.answer(text_off) if not is_callback else message_or_callback.answer(text_off, show_alert=True)

    tables_res = await session.execute(
        select(Table).where(Table.assigned_waiters.any(Employee.id == employee.id)).order_by(Table.name)
    )
    tables = tables_res.scalars().all()

    text = "🍽 <b>Закріплені за вами столики:</b>\n\n"
    kb = InlineKeyboardBuilder()
    if not tables:
        text += "За вами не закріплено жодного столика."
    else:
        for table in tables:
            kb.add(InlineKeyboardButton(text=f"Столик: {html_module.escape(table.name)}", callback_data=f"waiter_view_table_{table.id}"))
    kb.adjust(1)
    
    try:
        if is_callback:
            await message.edit_text(text, reply_markup=kb.as_markup())
            await message_or_callback.answer()
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except TelegramBadRequest: pass


async def start_handler(message: Message, state: FSMContext, session: AsyncSession, **kwargs: Dict[str, Any]):
    await state.clear()
    employee = await session.scalar(
        select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
    )
    if employee:
        keyboard = get_staff_keyboard(employee)
        await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви увійшли в режим {employee.role.name}.",
                             reply_markup=keyboard)
    else:
        await message.answer("👋 Ласкаво просимо! Використовуйте цей бот для управління замовленнями.",
                             reply_markup=get_staff_login_keyboard())

async def _generate_waiter_order_view(order: Order, session: AsyncSession):
    await session.refresh(order, ['status', 'accepted_by_waiter', 'table', 'items'])
    status_name = order.status.name if order.status else 'Невідомий'
    
    products_formatted = ""
    if order.items:
        lines = []
        for item in order.items:
            mods_str = ""
            if item.modifiers:
                mod_names = [m.get('name', '') for m in item.modifiers]
                if mod_names:
                    mods_str = f" (+ {', '.join(mod_names)})"
            
            # Додаємо галочку готовності
            icon = "✅" if item.is_ready else ""
            lines.append(f"- {icon} {html_module.escape(item.product_name)}{mods_str} x {item.quantity}")
        products_formatted = "\n".join(lines)
    else:
        products_formatted = "- <i>(Пусто)</i>"
    
    if order.accepted_by_waiter:
        accepted_by_text = f"<b>Прийнято:</b> {html_module.escape(order.accepted_by_waiter.full_name)}\n\n"
    else:
        accepted_by_text = "<b>Прийнято:</b> <i>Очікує...</i>\n\n"
    
    table_name = order.table.name if order.table else "N/A"
    
    payment_info = ""
    if order.status.is_completed_status:
         payment_info = f"\n<b>Оплата:</b> {'💳 Картка' if order.payment_method == 'card' else '💵 Готівка'}"
         if order.payment_method == 'cash':
             payment_info += " (В касі)" if order.is_cash_turned_in else " (У вас)"

    text = (f"<b>Керування замовленням #{order.id}</b> (Стіл: {table_name})\n\n"
            f"<b>Склад:</b>\n{products_formatted}\n\n<b>Сума:</b> {order.total_price} грн\n\n"
            f"{accepted_by_text}"
            f"<b>Поточний статус:</b> {status_name}{payment_info}")

    kb = InlineKeyboardBuilder()
    
    if not order.accepted_by_waiter_id:
        kb.row(InlineKeyboardButton(text="✅ Прийняти це замовлення", callback_data=f"waiter_accept_order_{order.id}"))

    statuses_res = await session.execute(
        select(OrderStatus).where(OrderStatus.visible_to_waiter == True).order_by(OrderStatus.id)
    )
    statuses = statuses_res.scalars().all()
    status_buttons = [
        InlineKeyboardButton(text=f"{'✅ ' if s.id == order.status_id else ''}{s.name}", callback_data=f"staff_set_status_{order.id}_{s.id}")
        for s in statuses
    ]
    for i in range(0, len(status_buttons), 2):
        kb.row(*status_buttons[i:i+2])

    kb.row(InlineKeyboardButton(text="✏️ Редагувати замовлення", callback_data=f"edit_order_{order.id}"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад до столика", callback_data=f"waiter_view_table_{order.table_id}"))
    
    return text, kb.as_markup()

def register_courier_handlers(dp_admin: Dispatcher):
    dp_admin.message.register(start_handler, CommandStart())

    @dp_admin.message(F.text.in_({"🚚 Вхід кур'єра", "🔐 Вхід оператора", "🤵 Вхід офіціанта", "🧑‍🍳 Вхід на зміну (Цех)"}))
    async def staff_login_start(message: Message, state: FSMContext, session: AsyncSession):
        user_id = message.from_user.id
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == user_id).options(joinedload(Employee.role))
        )
        if employee:
            return await message.answer(f"✅ Ви вже авторизовані як {employee.role.name}. Спочатку вийдіть із системи.", 
                                        reply_markup=get_staff_login_keyboard())
        
        role_type = "unknown"
        if "кур'єра" in message.text: role_type = "courier"
        elif "оператора" in message.text: role_type = "operator"
        elif "офіціанта" in message.text: role_type = "waiter"
        elif "Цех" in message.text: role_type = "workshop" # Повар/Бармен
            
        await state.set_state(StaffAuthStates.waiting_for_phone)
        await state.update_data(role_type=role_type)
        kb = InlineKeyboardBuilder().add(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_auth")).as_markup()
        await message.answer(f"Будь ласка, введіть номер телефону для авторизації:", reply_markup=kb)

    @dp_admin.message(StaffAuthStates.waiting_for_phone)
    async def process_staff_phone(message: Message, state: FSMContext, session: AsyncSession):
        phone = re.sub(r'\D', '', message.text.strip())
        
        data = await state.get_data()
        role_type = data.get("role_type")
        
        employee = await session.scalar(select(Employee).options(joinedload(Employee.role)).where(Employee.phone_number == phone))
        
        # Перевірка прав
        is_allowed = False
        if employee:
            if role_type == "courier" and employee.role.can_be_assigned: is_allowed = True
            elif role_type == "operator" and employee.role.can_manage_orders: is_allowed = True
            elif role_type == "waiter" and employee.role.can_serve_tables: is_allowed = True
            elif role_type == "workshop" and (employee.role.can_receive_kitchen_orders or employee.role.can_receive_bar_orders): is_allowed = True
        
        if is_allowed:
            employee.telegram_user_id = message.from_user.id
            await session.commit()
            await state.clear()
            
            keyboard = get_staff_keyboard(employee)
            await message.answer(f"🎉 Доброго дня, {employee.full_name}! Ви успішно авторизовані як {employee.role.name}.", reply_markup=keyboard)
        else:
            await message.answer(f"❌ Співробітника з таким номером не знайдено або він не має відповідних прав. Спробуйте ще раз.")

    @dp_admin.callback_query(F.data == "cancel_auth")
    async def cancel_auth(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        try: await callback.message.edit_text("Авторизацію скасовано.")
        except Exception: await callback.message.delete()

    @dp_admin.message(F.text.in_({"🟢 Почати зміну", "🔴 Завершити зміну"}))
    async def toggle_shift(message: Message, session: AsyncSession):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee: return
        is_start = message.text.startswith("🟢")
        
        employee.is_on_shift = is_start
        await session.commit()
        
        action = "почали" if is_start else "завершили"
        
        debt_text = ""
        if not is_start and employee.cash_balance > 0:
            debt_text = f"\n\n⚠️ <b>Увага!</b> У вас на руках: <b>{employee.cash_balance:.2f} грн</b>.\nБудь ласка, здайте виручку касиру."
            
        await message.answer(f"✅ Ви успішно {action} зміну.{debt_text}", reply_markup=get_staff_keyboard(employee))


    @dp_admin.message(F.text == "🚪 Вийти")
    async def logout_handler(message: Message, session: AsyncSession):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id)
            .options(joinedload(Employee.role))
        )
        if employee:
            if employee.cash_balance > 0:
                await message.answer(f"⚠️ У вас борг {employee.cash_balance} грн. Спочатку здайте касу, потім виходьте.")
                return
                
            employee.telegram_user_id = None
            employee.is_on_shift = False
            await session.commit()
            await message.answer("👋 Ви вийшли з системи.", reply_markup=get_staff_login_keyboard())
        else:
            await message.answer("❌ Ви не авторизовані.")

    # --- МАРШРУТИЗАЦІЯ КНОПОК ---
    @dp_admin.message(F.text.in_({"📦 Мої замовлення", "🍽 Мої столики", "🔥 Замовлення (Цех)", "🔪 Кухня", "🍹 Бар"}))
    async def handle_show_items_by_role(message: Message, session: AsyncSession, state: FSMContext, **kwargs: Dict[str, Any]):
        employee = await session.scalar(
            select(Employee).where(Employee.telegram_user_id == message.from_user.id).options(joinedload(Employee.role))
        )
        if not employee: return await message.answer("❌ Ви не авторизовані.")

        text = message.text
        # Кур'єр
        if text == "📦 Мої замовлення" and employee.role.can_be_assigned:
            await show_courier_orders(message, session)
        # Офіціант
        elif text == "🍽 Мої столики" and employee.role.can_serve_tables:
            await show_waiter_tables(message, session, state)
        # Виробництво (Універсально)
        elif (text in ["🔥 Замовлення (Цех)", "🔪 Кухня", "🍹 Бар"]) and (employee.role.can_receive_kitchen_orders or employee.role.can_receive_bar_orders):
            await show_workshop_orders(message, session)
        else:
            await message.answer("❌ Ваша роль не дозволяє переглядати ці дані або кнопка застаріла.")

    @dp_admin.callback_query(F.data == "refresh_workshop")
    async def refresh_workshop_handler(callback: CallbackQuery, session: AsyncSession):
        await show_workshop_orders(callback, session)

    # --- МАСОВА ГОТОВНІСТЬ (Для Telegram) ---
    @dp_admin.callback_query(F.data.startswith("chef_ready_all_"))
    async def chef_mark_all_ready(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[-1])
        user_id = callback.from_user.id
        
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == user_id))
        if not employee or not employee.assigned_workshop_ids:
            return await callback.answer("Помилка прав доступу або не призначено цехи", show_alert=True)
            
        order = await session.get(Order, order_id, options=[selectinload(Order.items).joinedload(OrderItem.product)])
        if not order: return await callback.answer("Замовлення не знайдено")
        
        marked_count = 0
        for item in order.items:
            # Відмічаємо тільки ті товари, які належать до цехів цього співробітника
            if item.product.production_warehouse_id in employee.assigned_workshop_ids:
                if not item.is_ready:
                    item.is_ready = True
                    marked_count += 1
        
        if marked_count > 0:
            await session.commit()
            
            # Імпортуємо тут, щоб уникнути циклічного імпорту в notification_manager
            from staff_pwa import check_and_update_order_readiness
            await check_and_update_order_readiness(session, order_id, callback.bot)
            
            await callback.answer(f"✅ Відмічено {marked_count} страв як готові")
            await show_workshop_orders(callback, session)
        else:
            await callback.answer("Всі ваші страви вже готові")

    @dp_admin.callback_query(F.data.startswith("courier_view_order_"))
    async def courier_view_order_details(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        order_id = int(callback.data.split("_")[3])
        # Отримуємо свіжі дані, включаючи статус
        order = await session.get(Order, order_id, options=[selectinload(Order.items), joinedload(Order.status)])
        if not order: return await callback.answer("Замовлення не знайдено.")
        
        # Оновлюємо об'єкт із БД, щоб переконатися, що статус актуальний
        await session.refresh(order, ['status'])

        status_name = order.status.name if order.status else 'Невідомий'
        address_info = order.address if order.is_delivery else 'Самовивіз'
        
        # ВІДОБРАЖЕННЯ ОПЛАТИ (ЗАВЖДИ, А НЕ ТІЛЬКИ ПРИ ЗАВЕРШЕННІ)
        payment_method_text = '💳 Картка / Термінал' if order.payment_method == 'card' else '💵 Готівка'
        pay_info = f"\n<b>Оплата:</b> {payment_method_text}"
            
        products_text = ", ".join([f"{i.product_name} x {i.quantity}" for i in order.items])

        text = (f"<b>Деталі замовлення #{order.id}</b>\n\n"
                f"Статус: {status_name}\n"
                f"Адреса: {html_module.escape(address_info)}\n"
                f"Клієнт: {html_module.escape(order.customer_name or '')}\n"
                f"Телефон: {html_module.escape(order.phone_number or '')}\n" 
                f"Склад: {html_module.escape(products_text)}\n"
                f"Сума: {order.total_price} грн{pay_info}\n\n")
        
        kb = InlineKeyboardBuilder()
        statuses_res = await session.execute(select(OrderStatus).where(OrderStatus.visible_to_courier == True).order_by(OrderStatus.id))
        
        # --- ИСПРАВЛЕНИЕ: Разбиваем кнопки статусов по 2 в ряд ---
        status_buttons = [InlineKeyboardButton(text=status.name, callback_data=f"staff_set_status_{order.id}_{status.id}") for status in statuses_res.scalars().all()]
        for i in range(0, len(status_buttons), 2):
            kb.row(*status_buttons[i:i+2])
        # ---------------------------------------------------------
        
        # --- ИСПРАВЛЕНИЕ: Валидная ссылка Google Карт для Telegram ---
        if order.is_delivery and order.address:
            encoded_address = quote_plus(order.address)
            map_query = f"https://www.google.com/maps/search/?api=1&query={encoded_address}"
            kb.row(InlineKeyboardButton(text="🗺️ Показати на карті", url=map_query))
        # -------------------------------------------------------------

        kb.row(InlineKeyboardButton(text="⬅️ До моїх замовлень", callback_data="show_courier_orders_list"))
        
        try:
            await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()

    @dp_admin.callback_query(F.data == "show_courier_orders_list")
    async def back_to_list(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        await show_courier_orders(callback, session)

    @dp_admin.callback_query(F.data.startswith("staff_ask_payment_"))
    async def staff_ask_payment_method(callback: CallbackQuery, session: AsyncSession):
        parts = callback.data.split("_")
        order_id, status_id = int(parts[3]), int(parts[4])
        
        order = await session.get(Order, order_id)
        if not order: return await callback.answer("Замовлення не знайдено.")
        
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="💵 Готівка", callback_data=f"staff_set_status_{order_id}_{status_id}_cash"))
        kb.row(InlineKeyboardButton(text="💳 Картка / Термінал", callback_data=f"staff_set_status_{order_id}_{status_id}_card"))
        
        if order.order_type == "in_house":
             kb.row(InlineKeyboardButton(text="🔙 Скасувати", callback_data=f"waiter_manage_order_{order_id}"))
        else:
             kb.row(InlineKeyboardButton(text="🔙 Скасувати", callback_data=f"courier_view_order_{order_id}"))
        
        await callback.message.edit_text(
            f"💰 <b>Оплата замовлення #{order.id}</b>\nСума: {order.total_price} грн\n\nОберіть спосіб оплати:",
            reply_markup=kb.as_markup()
        )
        await callback.answer()

    @dp_admin.callback_query(F.data.startswith("staff_set_status_"))
    async def staff_set_status(callback: CallbackQuery, session: AsyncSession, **kwargs: Dict[str, Any]):
        client_bot = dp_admin.get("client_bot")
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id).options(joinedload(Employee.role)))
        actor_info = f"{employee.role.name}: {employee.full_name}" if employee else f"Співробітник (ID: {callback.from_user.id})"
        
        parts = callback.data.split("_")
        order_id, new_status_id = int(parts[3]), int(parts[4])
        payment_method_override = parts[5] if len(parts) > 5 else None

        order = await session.get(Order, order_id, options=[joinedload(Order.table)])
        if not order: return await callback.answer("Замовлення не знайдено.")
        
        new_status = await session.get(OrderStatus, new_status_id)
        old_status_name = order.status.name if order.status else "Невідомий"
        
        if order.status.is_completed_status or order.status.is_cancelled_status:
             return await callback.answer("⛔️ Замовлення вже закрите. Зміна заборонена.", show_alert=True)

        if new_status.is_completed_status and not payment_method_override:
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="💵 Готівка", callback_data=f"staff_set_status_{order_id}_{new_status_id}_cash"))
            kb.row(InlineKeyboardButton(text="💳 Картка", callback_data=f"staff_set_status_{order_id}_{new_status_id}_card"))
            
            await callback.message.edit_text(
                f"⚠️ <b>Уточніть оплату для замовлення #{order.id}:</b>", 
                reply_markup=kb.as_markup()
            )
            return

        if payment_method_override:
            order.payment_method = payment_method_override

        order.status_id = new_status.id
        # ЯВНЕ ОНОВЛЕННЯ ОБ'ЄКТА СТАТУСУ В ПАМ'ЯТІ (Fix stale status)
        order.status = new_status
        
        session.add(OrderStatusHistory(order_id=order.id, status_id=new_status.id, actor_info=actor_info))
        
        debt_message = ""
        
        if new_status.is_completed_status:
            if order.is_delivery:
                order.completed_by_courier_id = employee.id

            await link_order_to_shift(session, order, employee.id)
            
            if order.payment_method == 'cash':
                await register_employee_debt(session, order, employee.id)
                debt_message = f"\n\n💰 <b>Готівка: {order.total_price} грн</b> записана на ваш баланс. Здайте її касиру в кінці зміни."

        await session.commit()
        
        # Оновлюємо замовлення після коміту, щоб переконатися, що статус зберігся коректно
        await session.refresh(order, ['status'])
        
        await notify_all_parties_on_status_change(
            order=order,
            old_status_name=old_status_name,
            actor_info=actor_info,
            admin_bot=callback.bot,
            client_bot=client_bot,
            session=session
        )

        pay_text = f" ({'Готівка' if order.payment_method == 'cash' else 'Картка'})" if new_status.is_completed_status else ""
        await callback.answer(f"Статус змінено: {new_status.name}{pay_text}")
        
        if order.order_type == "in_house":
            await manage_in_house_order_handler(callback, session, order_id=order.id)
        else:
            await courier_view_order_details(callback, session)
            
        if debt_message:
             await callback.message.answer(debt_message)

    # --- ОБРОБНИКИ ДЛЯ ОФІЦІАНТА ---
    
    @dp_admin.callback_query(F.data.startswith("waiter_view_table_"))
    async def show_waiter_table_orders(callback: CallbackQuery, session: AsyncSession, state: FSMContext, table_id: int = None):
        await state.clear()
        if table_id is None:
            try: table_id = int(callback.data.split("_")[-1])
            except ValueError: return await callback.answer("Помилка даних.", show_alert=True)
        
        table = await session.get(Table, table_id)
        if not table: return await callback.answer("Столик не знайдено!", show_alert=True)

        final_statuses_res = await session.execute(select(OrderStatus.id).where(or_(OrderStatus.is_completed_status == True, OrderStatus.is_cancelled_status == True)))
        final_statuses = final_statuses_res.scalars().all()
        
        active_orders_res = await session.execute(select(Order).where(Order.table_id == table_id, Order.status_id.not_in(final_statuses)).options(joinedload(Order.status)))
        active_orders = active_orders_res.scalars().all()

        text = f"<b>Столик: {html_module.escape(table.name)}</b>\n\nАктивні замовлення:\n"
        kb = InlineKeyboardBuilder()
        if not active_orders:
            text += "\n<i>Немає активних замовлень.</i>"
        else:
            for order in active_orders:
                kb.row(InlineKeyboardButton(
                    text=f"Замовлення #{order.id} ({order.status.name}) - {order.total_price} грн",
                    callback_data=f"waiter_manage_order_{order.id}"
                ))
        
        kb.row(InlineKeyboardButton(text="➕ Створити замовлення", callback_data=f"waiter_create_order_{table.id}"))
        kb.row(InlineKeyboardButton(text="⬅️ До списку столиків", callback_data="back_to_tables_list"))
        
        try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: 
             await callback.message.delete()
             await callback.message.answer(text, reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "back_to_tables_list")
    async def back_to_waiter_tables(callback: CallbackQuery, session: AsyncSession, state: FSMContext): 
        await show_waiter_tables(callback, session, state) 

    @dp_admin.callback_query(F.data.startswith("waiter_manage_order_"))
    async def manage_in_house_order_handler(callback: CallbackQuery, session: AsyncSession, order_id: int = None):
        if not order_id: order_id = int(callback.data.split("_")[-1])
        order = await session.get(Order, order_id, options=[joinedload(Order.table), joinedload(Order.status), joinedload(Order.accepted_by_waiter)])
        if not order: return await callback.answer("Замовлення не знайдено", show_alert=True)

        text, keyboard = await _generate_waiter_order_view(order, session) 
        try: await callback.message.edit_text(text, reply_markup=keyboard)
        except TelegramBadRequest: 
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()

    @dp_admin.callback_query(F.data.startswith("waiter_accept_order_"))
    async def waiter_accept_order(callback: CallbackQuery, session: AsyncSession):
        order_id = int(callback.data.split("_")[-1])
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id))
        
        order = await session.get(Order, order_id, options=[joinedload(Order.status)])
        if order.accepted_by_waiter_id:
            return await callback.answer("Вже прийнято іншим.", show_alert=True)

        order.accepted_by_waiter_id = employee.id
        
        # ЛОГ ПРИЙНЯТТЯ
        session.add(OrderLog(order_id=order.id, message=f"Офіціант прийняв замовлення", actor=employee.full_name))

        processing_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "В обробці").limit(1))
        if processing_status:
            order.status_id = processing_status.id
            session.add(OrderStatusHistory(order_id=order.id, status_id=processing_status.id, actor_info=f"Офіціант: {employee.full_name}"))

        await session.commit()
        await callback.answer(f"Замовлення #{order.id} прийнято!")
        await manage_in_house_order_handler(callback, session, order_id=order.id)

    # --- FSM СТВОРЕННЯ ЗАМОВЛЕННЯ (ОФІЦІАНТ) ---

    async def _display_waiter_cart(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        data = await state.get_data()
        cart = data.get("cart", {})
        table_name = data.get("table_name", "N/A")
        table_id = data.get("table_id")

        text = f"📝 <b>Створення замовлення для: {html_module.escape(table_name)}</b>\n\n<b>Склад:</b>\n"
        kb = InlineKeyboardBuilder()
        total_price = 0

        if not cart:
            text += "<i>Кошик порожній</i>"
        else:
            for item_key, item in cart.items():
                item_total = item['price'] * item['quantity']
                total_price += item_total
                
                mods_str = ""
                if item.get('modifiers'):
                    mod_names = [m['name'] for m in item['modifiers']]
                    mods_str = f" (+ {', '.join(mod_names)})"

                text += f"- {html_module.escape(item['name'])}{mods_str} ({item['quantity']} шт.) = {item_total:.2f} грн\n"
                
                kb.row(
                    InlineKeyboardButton(text="➖", callback_data=f"waiter_cart_qnt_{item_key}_-1"),
                    InlineKeyboardButton(text=f"{item['quantity']}x {html_module.escape(item['name'])}", callback_data="noop"),
                    InlineKeyboardButton(text="➕", callback_data=f"waiter_cart_qnt_{item_key}_1")
                )
        
        text += f"\n\n<b>Загальна сума: {total_price:.2f} грн</b>"
    
        kb.row(InlineKeyboardButton(text="➕ Додати страву", callback_data="waiter_cart_add_item"))
        if cart:
            kb.row(InlineKeyboardButton(text="✅ Оформити замовлення", callback_data="waiter_cart_finalize"))
        kb.row(InlineKeyboardButton(text="⬅️ Скасувати", callback_data=f"waiter_view_table_{table_id}")) 
    
        try: await callback.message.edit_text(text, reply_markup=kb.as_markup())
        except TelegramBadRequest: pass
        await callback.answer()

    @dp_admin.callback_query(F.data.startswith("waiter_create_order_"))
    async def waiter_create_order_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        table_id = int(callback.data.split("_")[-1])
        table = await session.get(Table, table_id)
        if not table: return await callback.answer("Столик не знайдено!", show_alert=True)
        
        await state.set_state(WaiterCreateOrderStates.managing_cart)
        await state.update_data(cart={}, table_id=table_id, table_name=table.name)
        await _display_waiter_cart(callback, state, session)

    @dp_admin.callback_query(WaiterCreateOrderStates.managing_cart, F.data == "waiter_cart_add_item")
    async def waiter_cart_add_item(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        await state.set_state(WaiterCreateOrderStates.choosing_category)
        categories_res = await session.execute(select(Category).where(Category.show_in_restaurant == True).order_by(Category.sort_order, Category.name))
        
        kb = InlineKeyboardBuilder()
        for cat in categories_res.scalars().all():
            kb.add(InlineKeyboardButton(text=cat.name, callback_data=f"waiter_cart_cat_{cat.id}"))
        kb.adjust(2)
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="waiter_cart_back_to_cart"))
        
        await callback.message.edit_text("Виберіть категорію:", reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "waiter_cart_back_to_cart", WaiterCreateOrderStates.choosing_category)
    @dp_admin.callback_query(F.data == "waiter_cart_back_to_cart", WaiterCreateOrderStates.choosing_product)
    async def waiter_cart_back_to_cart(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        await state.set_state(WaiterCreateOrderStates.managing_cart)
        await _display_waiter_cart(callback, state, session)

    @dp_admin.callback_query(WaiterCreateOrderStates.choosing_category, F.data.startswith("waiter_cart_cat_"))
    async def waiter_cart_show_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        category_id = int(callback.data.split("_")[-1])
        await state.set_state(WaiterCreateOrderStates.choosing_product)
        
        products_res = await session.execute(select(Product).where(Product.category_id == category_id, Product.is_active == True).order_by(Product.name))
        
        kb = InlineKeyboardBuilder()
        for prod in products_res.scalars().all():
            kb.add(InlineKeyboardButton(text=f"{prod.name} - {prod.price} грн", callback_data=f"waiter_cart_prod_{prod.id}"))
        kb.adjust(1)
        kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="waiter_cart_back_to_categories"))
        
        await callback.message.edit_text("Виберіть страву:", reply_markup=kb.as_markup())
        await callback.answer()

    @dp_admin.callback_query(F.data == "waiter_cart_back_to_categories", WaiterCreateOrderStates.choosing_product)
    async def waiter_cart_back_to_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        await waiter_cart_add_item(callback, state, session)

    # --- ЛОГИКА ВЫБОРА МОДИФИКАТОРОВ ---

    @dp_admin.callback_query(WaiterCreateOrderStates.choosing_product, F.data.startswith("waiter_cart_prod_"))
    async def waiter_cart_add_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        product_id = int(callback.data.split("_")[-1])
        product = await session.get(Product, product_id, options=[selectinload(Product.modifiers)])
        
        if not product:
            return await callback.answer("Помилка", show_alert=True)

        if product.modifiers:
            await state.set_state(WaiterCreateOrderStates.choosing_modifiers)
            await state.update_data(
                current_product_id=product.id,
                current_product_name=product.name,
                current_product_price=float(product.price),
                current_product_area=product.preparation_area,
                selected_mod_ids=[] 
            )
            await _show_modifier_selection(callback, product, [])
        else:
            await _add_product_to_fsm_cart(state, product, [])
            await state.set_state(WaiterCreateOrderStates.managing_cart)
            await _display_waiter_cart(callback, state, session)
            await callback.answer(f"{product.name} додано.")

    async def _show_modifier_selection(callback: CallbackQuery, product: Product, selected_ids: list):
        kb = InlineKeyboardBuilder()
        
        for mod in product.modifiers:
            is_selected = mod.id in selected_ids
            marker = "✅" if is_selected else "⬜️"
            kb.row(InlineKeyboardButton(
                text=f"{marker} {mod.name} (+{mod.price} грн)", 
                callback_data=f"waiter_mod_toggle_{mod.id}"
            ))
        
        kb.row(InlineKeyboardButton(text="📥 Додати в замовлення", callback_data="waiter_mod_confirm"))
        kb.row(InlineKeyboardButton(text="⬅️ Назад до страв", callback_data="waiter_cart_back_to_cart"))

        current_total = product.price + sum(m.price for m in product.modifiers if m.id in selected_ids)
        
        text = f"<b>{html_module.escape(product.name)}</b>\nЦіна: {current_total} грн\nОберіть добавки:"
        await callback.message.edit_text(text, reply_markup=kb.as_markup())

    @dp_admin.callback_query(WaiterCreateOrderStates.choosing_modifiers, F.data.startswith("waiter_mod_toggle_"))
    async def waiter_mod_toggle(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        mod_id = int(callback.data.split("_")[-1])
        data = await state.get_data()
        selected_ids = data.get("selected_mod_ids", [])
        
        if mod_id in selected_ids:
            selected_ids.remove(mod_id)
        else:
            selected_ids.append(mod_id)
            
        await state.update_data(selected_mod_ids=selected_ids)
        
        product = await session.get(Product, data["current_product_id"], options=[selectinload(Product.modifiers)])
        await _show_modifier_selection(callback, product, selected_ids)
        await callback.answer()

    @dp_admin.callback_query(WaiterCreateOrderStates.choosing_modifiers, F.data == "waiter_mod_confirm")
    async def waiter_mod_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        data = await state.get_data()
        product_id = data["current_product_id"]
        mod_ids = data.get("selected_mod_ids", [])
        
        product = await session.get(Product, product_id)
        modifiers = []
        if mod_ids:
            modifiers = (await session.execute(select(Modifier).where(Modifier.id.in_(mod_ids)))).scalars().all()
            
        await _add_product_to_fsm_cart(state, product, modifiers)
        await state.set_state(WaiterCreateOrderStates.managing_cart)
        await _display_waiter_cart(callback, state, session)
        await callback.answer("Додано.")

    async def _add_product_to_fsm_cart(state: FSMContext, product: Product, modifiers: list):
        data = await state.get_data()
        cart = data.get("cart", {})
        
        mod_ids_str = "-".join(sorted([str(m.id) for m in modifiers]))
        unique_key = f"{product.id}_{mod_ids_str}"
        
        mods_data = [{"id": m.id, "name": m.name} for m in modifiers]
        
        if unique_key in cart:
            cart[unique_key]["quantity"] += 1
        else:
            unit_price = float(product.price) + sum(float(m.price) for m in modifiers)
            cart[unique_key] = {
                "product_id": product.id,
                "name": product.name,
                "price": unit_price,
                "quantity": 1,
                "area": product.preparation_area,
                "modifiers": mods_data
            }
            
        await state.update_data(cart=cart)

    @dp_admin.callback_query(WaiterCreateOrderStates.managing_cart, F.data.startswith("waiter_cart_qnt_"))
    async def waiter_cart_change_quantity(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        parts = callback.data.split("_")
        change = int(parts[-1])
        unique_key = "_".join(parts[3:-1])
        
        data = await state.get_data()
        cart = data.get("cart", {})
        
        if unique_key in cart:
            cart[unique_key]["quantity"] += change
            if cart[unique_key]["quantity"] <= 0: del cart[unique_key]
        
        await state.update_data(cart=cart)
        await _display_waiter_cart(callback, state, session)

    @dp_admin.callback_query(WaiterCreateOrderStates.managing_cart, F.data == "waiter_cart_finalize")
    async def waiter_cart_finalize(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        data = await state.get_data()
        cart = data.get("cart", {})
        table_id = data.get("table_id")
        table_name = data.get("table_name")
        
        employee = await session.scalar(select(Employee).where(Employee.telegram_user_id == callback.from_user.id))
        
        if not cart:
             return await callback.answer("Кошик порожній.", show_alert=True)

        product_ids = {item['product_id'] for item in cart.values()}
        
        all_mod_ids = set()
        for item in cart.values():
            for m in item.get('modifiers', []):
                all_mod_ids.add(int(m['id']))

        products_res = await session.execute(select(Product).where(Product.id.in_(product_ids)))
        db_products = {p.id: p for p in products_res.scalars().all()}
        
        db_modifiers = {}
        if all_mod_ids:
            mods_res = await session.execute(select(Modifier).where(Modifier.id.in_(all_mod_ids)))
            for m in mods_res.scalars().all():
                db_modifiers[m.id] = m
        
        total_price = Decimal('0.00')
        items_to_create = []

        for item_data in cart.values():
            prod_id = item_data['product_id']
            product = db_products.get(prod_id)
            
            if not product: continue
                
            qty = item_data['quantity']
            
            base_price = product.price
            mods_price_sum = Decimal(0)
            final_mods_data = []
            
            for m_raw in item_data.get('modifiers', []):
                mid = int(m_raw['id'])
                if mid in db_modifiers:
                    m_db = db_modifiers[mid]
                    mods_price_sum += m_db.price
                    final_mods_data.append({
                        "id": m_db.id,
                        "name": m_db.name,
                        "price": float(m_db.price),
                        "ingredient_id": m_db.ingredient_id,
                        "ingredient_qty": float(m_db.ingredient_qty)
                    })

            actual_price = base_price + mods_price_sum
            total_price += actual_price * qty
            
            items_to_create.append({
                "product_id": prod_id,
                "name": product.name,
                "quantity": qty,
                "price": actual_price,
                "area": product.preparation_area,
                "modifiers": final_mods_data
            })
            
        if not items_to_create:
             return await callback.answer("Помилка: товари не знайдено.", show_alert=True)
        
        new_status = await session.scalar(select(OrderStatus).where(OrderStatus.name == "Новий").limit(1))
        status_id = new_status.id if new_status else 1

        order = Order(
            customer_name=f"Стіл: {table_name}", phone_number=f"table_{table_id}",
            total_price=total_price, is_delivery=False,
            delivery_time="In House", order_type="in_house", table_id=table_id,
            status_id=status_id, accepted_by_waiter_id=employee.id
        )
        session.add(order)
        await session.flush()

        for item_data in items_to_create:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data["product_id"],
                product_name=item_data["name"],
                quantity=item_data["quantity"],
                price_at_moment=item_data["price"],
                preparation_area=item_data["area"],
                modifiers=item_data["modifiers"]
            )
            session.add(order_item)

        await session.commit()
        await session.refresh(order, ['status'])
        
        session.add(OrderStatusHistory(order_id=order.id, status_id=order.status_id, actor_info=f"Офіціант: {employee.full_name}"))
        
        # ЛОГ СТВОРЕННЯ
        items_summary = ", ".join([f"{i['name']} x{i['quantity']}" for i in items_to_create])
        session.add(OrderLog(order_id=order.id, message=f"Замовлення створено офіціантом. Склад: {items_summary}", actor=employee.full_name))

        await session.commit()
        
        admin_bot = dp_admin.get("bot_instance")
        if admin_bot:
            await notify_new_order_to_staff(admin_bot, order, session)

        await callback.answer(f"Замовлення #{order.id} створено!")
        await state.clear()
        await show_waiter_table_orders(callback, session, state, table_id=table_id)