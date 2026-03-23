# models.py

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text, ForeignKey, JSON, func
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import secrets
import os
from decimal import Decimal

# Якщо потрібно для тайп-хінтингу (щоб IDE розуміла, що таке Modifier),
# але уникаючи циклічного імпорту в рантаймі
if TYPE_CHECKING:
    from inventory_models import Modifier

# Зчитування DATABASE_URL зі змінних оточення
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("Помилка: Змінна оточення DATABASE_URL не встановлена.")

engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass

# Асоціативна таблиця для зв'язку "багато-до-багатьох" (Офіціанти <-> Столи)
waiter_table_association = sa.Table(
    'waiter_table_association',
    Base.metadata,
    sa.Column('employee_id', sa.ForeignKey('employees.id'), primary_key=True),
    sa.Column('table_id', sa.ForeignKey('tables.id'), primary_key=True)
)

# Асоціативна таблиця Продукти <-> Модифікатори
product_modifier_association = sa.Table(
    'product_modifier_association',
    Base.metadata,
    sa.Column('product_id', sa.ForeignKey('products.id'), primary_key=True),
    sa.Column('modifier_id', sa.ForeignKey('modifiers.id'), primary_key=True)
)


class MenuItem(Base):
    __tablename__ = 'menu_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=100)
    show_on_website: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    show_in_telegram: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    show_in_qr: Mapped[bool] = mapped_column(sa.Boolean, default=False)


class Role(Base):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True)
    
    # Права доступу
    can_manage_orders: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    can_be_assigned: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    can_serve_tables: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    
    # --- НОВЕ ПРАВО: Скасування замовлень ---
    can_cancel_orders: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    # ----------------------------------------
    
    can_receive_kitchen_orders: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    can_receive_bar_orders: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="role")


class Employee(Base):
    __tablename__ = 'employees'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(sa.BigInteger, nullable=True, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(sa.String(20), nullable=True, unique=True)
    
    # Для входу в PWA
    password_hash: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)

    role_id: Mapped[int] = mapped_column(sa.ForeignKey('roles.id'), nullable=False)
    role: Mapped["Role"] = relationship("Role", back_populates="employees", lazy='selectin')
    
    # --- НОВЕ: Прив'язка до складу/цеху ---
    # Дозволяє закріпити кухаря за конкретним цехом (Кухня, Бар, Піца-цех)
    assigned_warehouse_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    
    # НОВЕ ПОЛЕ: Список ID цехів, за які відповідає співробітник (JSON)
    assigned_workshop_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    is_on_shift: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # Баланс готівки "на руках" (борг перед касою)
    cash_balance: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.00, server_default=text("0.00"))

    current_order_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('orders.id', ondelete="SET NULL"), nullable=True)
    current_order: Mapped[Optional["Order"]] = relationship("Order", foreign_keys="Employee.current_order_id")
    
    assigned_tables: Mapped[List["Table"]] = relationship("Table", secondary=waiter_table_association, back_populates="assigned_waiters")
    accepted_orders: Mapped[List["Order"]] = relationship("Order", back_populates="accepted_by_waiter", foreign_keys="Order.accepted_by_waiter_id")
    
    # Зв'язок зі сповіщеннями
    notifications: Mapped[List["StaffNotification"]] = relationship("StaffNotification", back_populates="employee")
    
    # --- НОВЕ: Зв'язок з історією балансу ---
    balance_history: Mapped[List["BalanceHistory"]] = relationship("BalanceHistory", back_populates="employee", cascade="all, delete-orphan")


class BalanceHistory(Base):
    """
    Історія змін фінансового балансу співробітника.
    Потрібна для аудиту: звідки з'явився борг і куди зникли гроші.
    """
    __tablename__ = 'balance_history'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(sa.ForeignKey('employees.id'), nullable=False, index=True)
    
    # Сума зміни (+ збільшення боргу, - погашення)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    
    # Баланс після операції
    new_balance: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    
    # Причина (наприклад: "Оплата замовлення #123", "Здача виручки в касу")
    reason: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), server_default=func.now())
    
    employee: Mapped["Employee"] = relationship("Employee", back_populates="balance_history")


class StaffNotification(Base):
    """Сповіщення для PWA (червона крапка, тости)"""
    __tablename__ = 'staff_notifications'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(sa.ForeignKey('employees.id'), nullable=False, index=True)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    
    employee: Mapped["Employee"] = relationship("Employee", back_populates="notifications")


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=100, server_default=text("100"))
    show_on_delivery_site: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=text("true"))
    show_in_restaurant: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=text("true"))
    products: Mapped[list["Product"]] = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    description: Mapped[str] = mapped_column(sa.String(500), nullable=True)
    image_url: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False) 
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=text("true"))
    category_id: Mapped[int] = mapped_column(sa.ForeignKey('categories.id'))
    
    # Цех приготування (застаріле, використовується для сумісності)
    preparation_area: Mapped[str] = mapped_column(sa.String(20), default='kitchen', server_default=text("'kitchen'"))
    
    # --- НОВЕ: Прив'язка до цеху ---
    # Вказує ID складу/цеху, з якого списувати інгредієнти та куди відправляти замовлення
    production_warehouse_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    
    # --- SEO НАЛАШТУВАННЯ (ІНДИВІДУАЛЬНІ) ---
    seo_title: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    seo_description_meta: Mapped[Optional[str]] = mapped_column(sa.String(500), nullable=True)
    # ----------------------------------------

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    cart_items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="product")

    # Зв'язок з модифікаторами
    modifiers: Mapped[List["Modifier"]] = relationship(
        "Modifier", 
        secondary=product_modifier_association,
        lazy="selectin"
    )


class OrderStatus(Base):
    __tablename__ = 'order_statuses'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    
    # Налаштування видимості та логіки
    notify_customer: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=text("true"))
    visible_to_operator: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=text("true"))
    visible_to_courier: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    visible_to_waiter: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    visible_to_chef: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    visible_to_bartender: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    requires_kitchen_notify: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # Фінальні статуси
    is_completed_status: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    is_cancelled_status: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="status")
    history_entries: Mapped[list["OrderStatusHistory"]] = relationship("OrderStatusHistory", back_populates="status")


# --- КАСОВІ ЗМІНИ ---

class CashShift(Base):
    """Касова зміна"""
    __tablename__ = 'cash_shifts'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(sa.ForeignKey('employees.id'), nullable=False)
    
    start_time: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    end_time: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    
    start_cash: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.0)
    end_cash_actual: Mapped[Optional[Decimal]] = mapped_column(sa.Numeric(10, 2), nullable=True)
    
    total_sales_cash: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.0)
    total_sales_card: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.0)
    service_in: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.0)
    service_out: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.0)
    
    is_closed: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    
    employee: Mapped["Employee"] = relationship("Employee")
    transactions: Mapped[list["CashTransaction"]] = relationship("CashTransaction", back_populates="shift")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="cash_shift")


class CashTransaction(Base):
    """Службові операції з готівкою"""
    __tablename__ = 'cash_transactions'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shift_id: Mapped[int] = mapped_column(sa.ForeignKey('cash_shifts.id'), nullable=False)
    
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(sa.String(20), nullable=False) # 'in', 'out', 'handover'
    comment: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    
    shift: Mapped["CashShift"] = relationship("CashShift", back_populates="transactions")


class OrderItem(Base):
    __tablename__ = 'order_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(sa.ForeignKey('orders.id', ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('products.id', ondelete="SET NULL"), nullable=True)
    
    product_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    price_at_moment: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), nullable=False)
    preparation_area: Mapped[str] = mapped_column(sa.String(20), default='kitchen', server_default=text("'kitchen'"))
    
    # --- НОВЕ ПОЛЕ: Готовність конкретної страви ---
    is_ready: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # --- МОДИФІКАТОРИ (JSON) ---
    # Зберігає список обраних модифікаторів:
    # [{"id": 1, "name": "Сир", "price": 10.0, "ingredient_id": 5, "ingredient_qty": 0.05}, ...]
    modifiers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")


# --- НОВА ТАБЛИЦЯ ЛОГІВ ---
class OrderLog(Base):
    """Детальний лог всіх дій із замовленням"""
    __tablename__ = 'order_logs'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(sa.ForeignKey('orders.id', ondelete="CASCADE"), nullable=False, index=True)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    actor: Mapped[str] = mapped_column(sa.String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), server_default=func.now())
    
    order: Mapped["Order"] = relationship("Order", back_populates="logs")
# ---------------------------


class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(sa.BigInteger, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy='selectin')
    
    total_price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.00)
    
    customer_name: Mapped[str] = mapped_column(sa.String(100), nullable=True)
    phone_number: Mapped[str] = mapped_column(sa.String(20), nullable=True, index=True)
    address: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    
    status_id: Mapped[int] = mapped_column(sa.ForeignKey('order_statuses.id'), default=1, nullable=False)
    status: Mapped["OrderStatus"] = relationship("OrderStatus", back_populates="orders", lazy='selectin')
    
    is_delivery: Mapped[bool] = mapped_column(default=True)
    delivery_time: Mapped[str] = mapped_column(sa.String(50), nullable=True, default="Якнайшвидше")
    
    courier_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('employees.id', ondelete="SET NULL"), nullable=True)
    courier: Mapped[Optional["Employee"]] = relationship("Employee", foreign_keys="Order.courier_id")
    
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    
    completed_by_courier_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('employees.id'), nullable=True)
    completed_by_courier: Mapped[Optional["Employee"]] = relationship("Employee", foreign_keys="Order.completed_by_courier_id")
    
    history: Mapped[list["OrderStatusHistory"]] = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", lazy='selectin')
    
    # --- НОВЕ: Зв'язок з логами ---
    logs: Mapped[list["OrderLog"]] = relationship("OrderLog", back_populates="order", cascade="all, delete-orphan", lazy='selectin')
    # ------------------------------

    table_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('tables.id'), nullable=True)
    table: Mapped[Optional["Table"]] = relationship("Table", back_populates="orders")
    order_type: Mapped[str] = mapped_column(sa.String(20), default='delivery', server_default=text("'delivery'"))
    
    accepted_by_waiter_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('employees.id'), nullable=True)
    accepted_by_waiter: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="accepted_orders", foreign_keys="Order.accepted_by_waiter_id")
    
    cancellation_reason: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)

    # --- НОВЕ ПОЛЕ: Коментар ---
    comment: Mapped[Optional[str]] = mapped_column(sa.String(500), nullable=True)
    # ---------------------------
    
    # --- КАСА ТА ОПЛАТА ---
    payment_method: Mapped[str] = mapped_column(sa.String(20), default='cash', server_default=text("'cash'"))
    cash_shift_id: Mapped[Optional[int]] = mapped_column(sa.ForeignKey('cash_shifts.id'), nullable=True)
    cash_shift: Mapped[Optional["CashShift"]] = relationship("CashShift", back_populates="orders")
    
    is_cash_turned_in: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # Статуси готовності по цехах
    kitchen_done: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    bar_done: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))

    # --- СКЛАД: Прапор списання інгредієнтів ---
    # Запобігає повторному списанню при багаторазовій зміні статусу
    is_inventory_deducted: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # --- ДОДАТКОВО: Для логіки повернення ---
    # Не зберігається в БД (property або тимчасовий атрибут), але в SQLAlchemy
    # краще не додавати поля без маппінгу, якщо ми не використовуємо @hybrid_property.
    # В даному випадку ми просто використовуємо це як динамічний атрибут в коді (setattr).

    @property
    def products_text(self) -> str:
        if not self.items:
            return ""
        lines = []
        for item in self.items:
            txt = f"{item.product_name} x {item.quantity}"
            # Відображення модифікаторів у тексті замовлення
            if item.modifiers:
                mods_names = [m.get('name', '') for m in item.modifiers]
                if mods_names:
                    txt += f" ({', '.join(mods_names)})"
            lines.append(txt)
        return ", ".join(lines)


class OrderStatusHistory(Base):
    __tablename__ = 'order_status_history'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('orders.id', ondelete="CASCADE"), nullable=False, index=True)
    status_id: Mapped[int] = mapped_column(ForeignKey('order_statuses.id'), nullable=False)
    actor_info: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="history")
    status: Mapped["OrderStatus"] = relationship("OrderStatus", back_populates="history_entries", lazy='selectin')


class Customer(Base):
    __tablename__ = 'customers'
    user_id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=True)
    phone_number: Mapped[str] = mapped_column(sa.String(20), nullable=True)
    address: Mapped[str] = mapped_column(sa.String(255), nullable=True)


class CartItem(Base):
    __tablename__ = 'cart_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True)
    product_id: Mapped[int] = mapped_column(sa.ForeignKey('products.id'))
    quantity: Mapped[int] = mapped_column(default=1)
    
    # --- МОДИФІКАТОРИ (JSON) ---
    # Додано для збереження вибору в кошику
    modifiers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    product: Mapped["Product"] = relationship("Product", back_populates="cart_items", lazy='selectin')


class Table(Base):
    __tablename__ = 'tables'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    access_token: Mapped[str] = mapped_column(sa.String(32), default=lambda: secrets.token_urlsafe(16), nullable=False, unique=True, index=True)
    qr_code_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    assigned_waiters: Mapped[List["Employee"]] = relationship("Employee", secondary=waiter_table_association, back_populates="assigned_tables")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="table")


class Settings(Base):
    __tablename__ = 'settings'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    logo_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    site_title: Mapped[Optional[str]] = mapped_column(sa.String(100), default="Назва")
    
    # --- НОВЕ ПОЛЕ: Текст в шапці сайту ---
    site_header_text: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    # ---------------------------------------

    seo_description: Mapped[Optional[str]] = mapped_column(sa.String(255))
    seo_keywords: Mapped[Optional[str]] = mapped_column(sa.String(255))
    
    # Дизайн
    primary_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#5a5a5a")
    secondary_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#eeeeee")
    background_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#f4f4f4")
    text_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#333333")
    footer_bg_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#333333")
    footer_text_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#ffffff")
    font_family_sans: Mapped[Optional[str]] = mapped_column(sa.String(100), default="Golos Text")
    font_family_serif: Mapped[Optional[str]] = mapped_column(sa.String(100), default="Playfair Display")
    header_image_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    category_nav_bg_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#ffffff")
    category_nav_text_color: Mapped[Optional[str]] = mapped_column(sa.String(7), default="#333333")
    
    # Тексти та контакти
    telegram_welcome_message: Mapped[Optional[str]] = mapped_column(sa.Text)
    footer_address: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    footer_phone: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    working_hours: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    instagram_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    facebook_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    
    # Wi-Fi
    wifi_ssid: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    wifi_password: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)

    # --- ДОСТАВКА ---
    delivery_cost: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2), default=0.00, server_default=text("0.00"))
    free_delivery_from: Mapped[Optional[Decimal]] = mapped_column(sa.Numeric(10, 2), nullable=True)
    
    # --- ЗОНИ ДОСТАВКИ (НОВЕ ПОЛЕ) ---
    delivery_zones_content: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True, default="<p>Інформація про зони доставки.</p>")

    # --- GOOGLE ANALYTICS (НОВЕ ПОЛЕ) ---
    google_analytics_id: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)

    # --- GOOGLE ADS (НОВІ ПОЛЯ) ---
    google_ads_id: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    google_ads_conversion_label: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    # ------------------------------

    # --- ГЛОБАЛЬНІ SEO ШАБЛОНИ ДЛЯ ТОВАРІВ ---
    # Наприклад: "{name} - {price} грн | {site_title}"
    product_seo_mask_title: Mapped[Optional[str]] = mapped_column(sa.String(255), default="{name} - {price} грн | {site_title}")
    
    # Наприклад: "{name} - {description}. Ціна: {price} грн."
    product_seo_mask_desc: Mapped[Optional[str]] = mapped_column(sa.String(500), default="{name} - {description}. Ціна: {price} грн.")
    # ------------------------------------------


class MarketingPopup(Base):
    __tablename__ = 'marketing_popups'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(sa.String(100), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=True)
    
    button_text: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    button_link: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    # Якщо True, показується 1 раз за сесію (через localStorage), інакше при кожному завантаженні
    show_once: Mapped[bool] = mapped_column(sa.Boolean, default=True)


class Banner(Base):
    __tablename__ = 'banners'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    image_url: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    link: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True) # Посилання при кліку (наприклад, на категорію або товар)
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)


async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Ініціалізація базових даних (ролі, статуси)
    async with async_session_maker() as session:
        result_status = await session.execute(sa.select(OrderStatus).limit(1))
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

        result_roles = await session.execute(sa.select(Role).limit(1))
        if not result_roles.scalars().first():
            # По умолчанию can_cancel_orders=False, включаем только для Админа і Оператора
            session.add(Role(name="Адміністратор", can_manage_orders=True, can_be_assigned=True, can_serve_tables=True, can_receive_kitchen_orders=True, can_receive_bar_orders=True, can_cancel_orders=True))
            session.add(Role(name="Оператор", can_manage_orders=True, can_be_assigned=False, can_serve_tables=True, can_receive_kitchen_orders=True, can_receive_bar_orders=True, can_cancel_orders=True))
            session.add(Role(name="Кур'єр", can_manage_orders=False, can_be_assigned=True, can_serve_tables=False, can_receive_kitchen_orders=False, can_receive_bar_orders=False))
            session.add(Role(name="Офіціант", can_manage_orders=False, can_be_assigned=False, can_serve_tables=True, can_receive_kitchen_orders=False, can_receive_bar_orders=False))
            session.add(Role(name="Повар", can_manage_orders=False, can_be_assigned=False, can_serve_tables=False, can_receive_kitchen_orders=True, can_receive_bar_orders=False))
            session.add(Role(name="Бармен", can_manage_orders=False, can_be_assigned=False, can_serve_tables=False, can_receive_kitchen_orders=False, can_receive_bar_orders=True))

        await session.commit()