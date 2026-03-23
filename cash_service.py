# cash_service.py

import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from sqlalchemy.orm import joinedload
from models import CashShift, CashTransaction, Order, Employee, BalanceHistory

logger = logging.getLogger(__name__)

async def get_open_shift(session: AsyncSession, employee_id: int) -> CashShift | None:
    """Повертає відкриту зміну конкретного співробітника або None."""
    result = await session.execute(
        select(CashShift).where(
            CashShift.employee_id == employee_id,
            CashShift.is_closed == False
        )
    )
    return result.scalars().first()

async def get_any_open_shift(session: AsyncSession) -> CashShift | None:
    """Повертає першу ліпшу відкриту зміну (для загальної каси)."""
    result = await session.execute(
        select(CashShift).where(CashShift.is_closed == False).limit(1)
    )
    return result.scalars().first()

async def attach_orphaned_orders(session: AsyncSession, shift_id: int):
    """
    Прив'язує 'загублені' замовлення (без зміни) до нової відкритої зміни.
    Це виправляє проблему втрати виручки, якщо замовлення було закрито, коли каса не працювала.
    """
    # Знаходимо ID статусів, які вважаються завершеними (успішними)
    from models import OrderStatus
    completed_statuses = await session.execute(select(OrderStatus.id).where(OrderStatus.is_completed_status == True))
    completed_ids = completed_statuses.scalars().all()
    
    if not completed_ids:
        return

    # Оновлюємо замовлення: ставимо їм поточну зміну
    stmt = (
        update(Order)
        .where(
            Order.cash_shift_id.is_(None), # Замовлення без зміни
            Order.status_id.in_(completed_ids) # Тільки успішні
        )
        .values(cash_shift_id=shift_id)
    )
    result = await session.execute(stmt)
    
    if result.rowcount > 0:
        logger.info(f"💰 AUTOMATIC FIX: Прив'язано {result.rowcount} загублених замовлень до зміни #{shift_id}")
        # session.commit() не потрібен тут, він буде викликаний у батьківській функції

async def open_new_shift(session: AsyncSession, employee_id: int, start_cash: Decimal) -> CashShift:
    """Відкриває нову касову зміну."""
    active_shift = await get_open_shift(session, employee_id)
    if active_shift:
        raise ValueError("У цього співробітника вже є відкрита зміна.")

    # Перевірка, чи немає іншої відкритої зміни (одна каса на всіх)
    any_shift = await get_any_open_shift(session)
    if any_shift:
         raise ValueError(f"Зміна вже відкрита співробітником {any_shift.employee_id}. Закрийте її спочатку.")

    new_shift = CashShift(
        employee_id=employee_id,
        start_time=datetime.now(),
        start_cash=start_cash,
        is_closed=False
    )
    session.add(new_shift)
    await session.commit()
    await session.refresh(new_shift)
    
    # ВАЖЛИВО: Підхоплюємо замовлення, які були закриті поза зміною
    await attach_orphaned_orders(session, new_shift.id)
    await session.commit()
    
    return new_shift

async def link_order_to_shift(session: AsyncSession, order: Order, employee_id: int | None):
    """
    Прив'язує замовлення до відкритої зміни.
    Це важливо для статистики продажів (Z-звіт).
    """
    if order.cash_shift_id:
        return 

    shift = None
    # Якщо це касир/оператор закриває замовлення, шукаємо його зміну
    if employee_id:
        shift = await get_open_shift(session, employee_id)
    
    if not shift:
        # Якщо не знайдено, беремо будь-яку активну зміну (загальна каса)
        shift = await get_any_open_shift(session)
    
    if shift:
        order.cash_shift_id = shift.id
        logger.info(f"Замовлення #{order.id} прив'язано до зміни #{shift.id}.")
    else:
        # Якщо зміни немає, залишаємо None. 
        # Воно буде підхоплено функцією attach_orphaned_orders при відкритті наступної зміни.
        logger.warning(f"УВАГА: Замовлення #{order.id} завершено БЕЗ відкритої зміни. Буде прив'язано пізніше.")

async def register_employee_debt(session: AsyncSession, order: Order, employee_id: int):
    """
    Фіксує, що співробітник (кур'єр/офіціант) отримав готівку за замовлення.
    Збільшує його баланс (борг перед касою) та пише аудит.
    """
    if order.payment_method != 'cash':
        return # Борг виникає тільки при готівці

    # Блокуємо рядок співробітника для уникнення гонки даних
    employee = await session.get(Employee, employee_id, with_for_update=True)
    if not employee:
        logger.error(f"Співробітника {employee_id} не знайдено при реєстрації боргу.")
        return

    amount = Decimal(str(order.total_price))
    
    # Оновлюємо баланс
    employee.cash_balance += amount
    order.is_cash_turned_in = False
    
    # Аудит (Історія балансу)
    history = BalanceHistory(
        employee_id=employee.id,
        amount=amount,
        new_balance=employee.cash_balance,
        reason=f"Замовлення #{order.id} (Борг)"
    )
    session.add(history)
    
    logger.info(f"Борг: Співробітник {employee.full_name} +{amount} грн. Баланс: {employee.cash_balance}")

async def unregister_employee_debt(session: AsyncSession, order: Order):
    """
    Списує борг зі співробітника (наприклад, якщо замовлення було скасовано після завершення).
    """
    # Якщо це не готівка або гроші вже в касі (здані), то борг списувати не треба (його немає на руках)
    if order.payment_method != 'cash' or order.is_cash_turned_in:
        return

    # Визначаємо, на кому висить борг
    employee_id = order.courier_id or order.accepted_by_waiter_id or order.completed_by_courier_id
    
    if not employee_id:
        logger.warning(f"Неможливо скасувати борг для замовлення #{order.id}: виконавець не знайдений.")
        return

    # Блокуємо рядок співробітника
    employee = await session.get(Employee, employee_id, with_for_update=True)
    if not employee: return

    amount = Decimal(str(order.total_price))
    
    # Зменшуємо борг
    employee.cash_balance -= amount
    if employee.cash_balance < 0:
        employee.cash_balance = Decimal(0) # Захист від мінуса
    
    # Аудит
    history = BalanceHistory(
        employee_id=employee.id,
        amount=-amount,
        new_balance=employee.cash_balance,
        reason=f"Скасування замовлення #{order.id}"
    )
    session.add(history)
    
    logger.info(f"Списання боргу: {employee.full_name} -{amount} грн (Скасування #{order.id})")

async def process_handover(session: AsyncSession, cashier_shift_id: int, employee_id: int, order_ids: list[int]):
    """
    Касир приймає гроші від співробітника.
    Транзакційно безпечна операція.
    """
    shift = await session.get(CashShift, cashier_shift_id)
    if not shift or shift.is_closed:
        raise ValueError("Зміна касира не знайдена або закрита.")

    # Блокуємо співробітника для оновлення балансу (FOR UPDATE)
    employee = await session.get(Employee, employee_id, with_for_update=True)
    if not employee:
        raise ValueError("Співробітника не знайдено.")

    orders_res = await session.execute(
        select(Order).where(Order.id.in_(order_ids), Order.is_cash_turned_in == False)
    )
    orders = orders_res.scalars().all()

    if not orders:
        raise ValueError("Немає доступних замовлень для здачі виручки.")

    total_amount = Decimal('0.00')
    
    for order in orders:
        amount = Decimal(str(order.total_price))
        total_amount += amount
        
        # Позначаємо, що гроші в касі
        order.is_cash_turned_in = True
        
        # Якщо замовлення "висіло" (було створено до цієї зміни), прив'язуємо його до поточної зміни,
        # щоб воно потрапило в статистику (хоча б як handover)
        if not order.cash_shift_id:
            order.cash_shift_id = shift.id

    # Зменшуємо борг
    employee.cash_balance -= total_amount
    
    if employee.cash_balance < Decimal('0.00'):
        logger.warning(f"Баланс співробітника {employee.id} пішов у мінус! Скидаємо в 0.")
        employee.cash_balance = Decimal('0.00') 

    # Аудит балансу
    history = BalanceHistory(
        employee_id=employee.id,
        amount=-total_amount,
        new_balance=employee.cash_balance,
        reason=f"Здача виручки (Зміна #{shift.id})"
    )
    session.add(history)

    # Транзакція в касу
    tx = CashTransaction(
        shift_id=shift.id,
        amount=total_amount,
        transaction_type='handover',
        comment=f"Здача: {employee.full_name} ({len(orders)} зам.)"
    )
    session.add(tx)
    
    await session.commit()
    return total_amount

async def get_shift_statistics(session: AsyncSession, shift_id: int):
    """
    Рахує статистику зміни (X-звіт).
    ВИПРАВЛЕНО: Враховує Handover (здачу боргів) у теоретичному залишку.
    """
    shift = await session.get(CashShift, shift_id)
    if not shift:
        return None

    # 1. Продажі (Всі замовлення, прив'язані до зміни)
    sales_query = select(
        Order.payment_method,
        func.sum(Order.total_price)
    ).where(
        Order.cash_shift_id == shift_id
    ).group_by(Order.payment_method)

    sales_res = await session.execute(sales_query)
    sales_data = sales_res.all()

    total_sales_cash_orders = Decimal('0.00') 
    total_card_sales = Decimal('0.00')

    for method, amount in sales_data:
        amount_decimal = Decimal(str(amount)) if amount is not None else Decimal('0.00')
        if method == 'cash':
            total_sales_cash_orders += amount_decimal
        elif method == 'card':
            total_card_sales += amount_decimal

    # 2. Службові операції та Handover
    trans_query = select(
        CashTransaction.transaction_type,
        func.sum(CashTransaction.amount)
    ).where(
        CashTransaction.shift_id == shift_id
    ).group_by(CashTransaction.transaction_type)

    trans_res = await session.execute(trans_query)
    trans_data = trans_res.all()

    service_in = Decimal('0.00')
    service_out = Decimal('0.00')
    handover_in = Decimal('0.00')

    for t_type, amount in trans_data:
        amount_decimal = Decimal(str(amount)) if amount is not None else Decimal('0.00')
        if t_type == 'in':
            service_in += amount_decimal
        elif t_type == 'out':
            service_out += amount_decimal
        elif t_type == 'handover':
            handover_in += amount_decimal

    # 3. Готівка в касі (Cash Drawer)
    # Готівка в касі = Початкова + (Продажі Готівкою, що ВЖЕ в касі) + Handover + Внесення - Вилучення
    
    # Рахуємо продажі за цю зміну, які ВЖЕ здані в касу (безпосередньо на барі/касі)
    # Ті, що пройшли через handover, вже враховані в handover_in
    query_collected_cash = select(func.sum(Order.total_price)).where(
        Order.cash_shift_id == shift_id,
        Order.payment_method == 'cash',
        Order.is_cash_turned_in == True
    )
    collected_cash_res = await session.execute(query_collected_cash)
    collected_cash_scalar = collected_cash_res.scalar()
    
    # ВАЖЛИВО: Оскільки process_handover ставить is_cash_turned_in=True І створює handover транзакцію,
    # нам треба уникнути подвійного підрахунку.
    # Найпростіший спосіб: theoretical_cash = start + service_in - service_out + (сума всіх order.cash, де turned_in=True)
    # Але є нюанс: handover транзакція відображає факт передачі грошей, а order.total_price - суму чека.
    # Використовуємо суму чеків, як найнадійніше джерело.
    # Handover транзакції - для історії.
    
    # Але чекайте, handover транзакції можуть містити суми за замовлення з МИНУЛИХ змін, які ми щойно прикріпили до поточної.
    # Тому краще використовувати саме суму замовлень прив'язаних до цієї зміни.
    
    money_from_orders_in_cash = Decimal(str(collected_cash_scalar)) if collected_cash_scalar is not None else Decimal('0.00')

    start_cash_decimal = Decimal(str(shift.start_cash)) if shift.start_cash is not None else Decimal('0.00')
    
    # Формула розрахунку залишку в скриньці
    # Ми ігноруємо handover_in у формулі, бо всі замовлення з handover ми прикріпили до зміни (link_order_to_shift/process_handover)
    # і вони вже враховані у money_from_orders_in_cash (так як turned_in=True).
    theoretical_cash = start_cash_decimal + money_from_orders_in_cash + service_in - service_out

    return {
        "shift_id": shift.id,
        "start_time": shift.start_time,
        "start_cash": start_cash_decimal,
        "total_sales_cash": total_sales_cash_orders, # Загальна сума продажів (включно з боргами)
        "total_sales_card": total_card_sales,
        "total_sales": total_sales_cash_orders + total_card_sales,
        "service_in": service_in,
        "service_out": service_out,
        "handover_in": handover_in, # Для інформації
        "theoretical_cash": theoretical_cash
    }

async def close_active_shift(session: AsyncSession, shift_id: int, end_cash_actual: Decimal):
    """Закриває зміну (Z-звіт)."""
    shift = await session.get(CashShift, shift_id)
    if not shift or shift.is_closed:
        raise ValueError("Зміна не знайдена або вже закрита.")

    stats = await get_shift_statistics(session, shift_id)
    
    shift.end_time = datetime.now()
    shift.end_cash_actual = end_cash_actual
    
    shift.total_sales_cash = stats['total_sales_cash']
    shift.total_sales_card = stats['total_sales_card']
    shift.service_in = stats['service_in']
    shift.service_out = stats['service_out']
    shift.is_closed = True
    
    await session.commit()
    return shift

async def add_shift_transaction(session: AsyncSession, shift_id: int, amount: Decimal, t_type: str, comment: str):
    """Додає службову транзакцію."""
    tx = CashTransaction(
        shift_id=shift_id,
        amount=amount,
        transaction_type=t_type,
        comment=comment
    )
    session.add(tx)
    await session.commit()