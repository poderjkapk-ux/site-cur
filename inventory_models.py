# inventory_models.py
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text
from datetime import datetime
from models import Base, Product  # Импортируем Base и Product из основного файла models.py

# --- СПРАВОЧНИКИ ---

class Unit(Base):
    """Единицы измерения (кг, л, шт)"""
    __tablename__ = 'units'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(20), unique=True)
    is_weighable: Mapped[bool] = mapped_column(sa.Boolean, default=True) # Можно ли делить (кг - да, банка - нет)

class Warehouse(Base):
    """Склады и Производственные цеха"""
    __tablename__ = 'warehouses'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    
    # Флаг: является ли склад производственным цехом (Кухня/Бар), где готовят, но не хранят продукты
    is_production: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    # Склад списания
    # Если это цех (is_production=True), тут указываем ID реального склада, откуда списывать ингредиенты
    linked_warehouse_id: Mapped[int | None] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    
    # Связь для удобного доступа к родительскому складу
    linked_warehouse: Mapped["Warehouse"] = relationship("Warehouse", remote_side=[id], foreign_keys=[linked_warehouse_id])
    
    # Явно указываем foreign_keys для stocks, чтобы избежать конфликтов
    stocks: Mapped[list["Stock"]] = relationship("Stock", back_populates="warehouse", foreign_keys="Stock.warehouse_id")

class Supplier(Base):
    """Контрагенты (Поставщики)"""
    __tablename__ = 'suppliers'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    phone: Mapped[str] = mapped_column(sa.String(50), nullable=True)
    contact_person: Mapped[str] = mapped_column(sa.String(100), nullable=True)
    comment: Mapped[str] = mapped_column(sa.String(255), nullable=True)

class Ingredient(Base):
    """Ингредиенты (Сырье: Мука, Томаты, Мясо) ИЛИ Полуфабрикаты (Тесто, Соус)"""
    __tablename__ = 'ingredients'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    unit_id: Mapped[int] = mapped_column(sa.ForeignKey('units.id'))
    
    # Текущая себестоимость (обновляется при приходе или производстве)
    current_cost: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0.00)
    
    # --- Флаг полуфабриката ---
    is_semi_finished: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    unit: Mapped["Unit"] = relationship("Unit")
    stocks: Mapped[list["Stock"]] = relationship("Stock", back_populates="ingredient")
    
    # Связь с рецептом (если это П/Ф)
    recipe_components: Mapped[list["IngredientRecipeItem"]] = relationship(
        "IngredientRecipeItem", 
        foreign_keys="IngredientRecipeItem.parent_ingredient_id",
        back_populates="parent_ingredient", 
        cascade="all, delete-orphan"
    )

class IngredientRecipeItem(Base):
    """Состав полуфабриката: Из чего состоит П/Ф"""
    __tablename__ = 'ingredient_recipe_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Родитель (П/Ф, который мы готовим, напр. "Тесто")
    parent_ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'), nullable=False)
    
    # Ребенок (Сырье, напр. "Мука")
    child_ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'), nullable=False)
    
    gross_amount: Mapped[float] = mapped_column(sa.Numeric(10, 3)) # Сколько нужно сырья
    
    parent_ingredient: Mapped["Ingredient"] = relationship("Ingredient", foreign_keys=[parent_ingredient_id], back_populates="recipe_components")
    child_ingredient: Mapped["Ingredient"] = relationship("Ingredient", foreign_keys=[child_ingredient_id])

class Modifier(Base):
    """Модификаторы (Добавки к блюдам: Сыр, Сироп, Молоко)"""
    __tablename__ = 'modifiers'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100))
    price: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0.00) # Цена продажи
    
    # Привязка к ингредиенту для списания со склада
    ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'), nullable=True)
    ingredient_qty: Mapped[float] = mapped_column(sa.Numeric(10, 3), default=0.000) # Сколько списывать
    
    # Склад списания для модификатора
    warehouse_id: Mapped[int | None] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[warehouse_id])

# --- ТЕХНОЛОГИЧЕСКИЕ КАРТЫ ---

class TechCard(Base):
    """Технологическая карта блюда (Связь Продукт -> Набор ингредиентов)"""
    __tablename__ = 'tech_cards'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(sa.ForeignKey('products.id'), unique=True)
    
    # Инструкция (технология приготовления) для повара
    cooking_method: Mapped[str] = mapped_column(sa.Text, nullable=True) 
    
    product: Mapped["Product"] = relationship("Product")
    components: Mapped[list["TechCardItem"]] = relationship("TechCardItem", back_populates="tech_card", cascade="all, delete-orphan")

class TechCardItem(Base):
    """Строка технологической карты (Ингредиент + количество)"""
    __tablename__ = 'tech_card_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tech_card_id: Mapped[int] = mapped_column(sa.ForeignKey('tech_cards.id'))
    ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'))
    
    gross_amount: Mapped[float] = mapped_column(sa.Numeric(10, 3)) # Брутто
    net_amount: Mapped[float] = mapped_column(sa.Numeric(10, 3))   # Нетто
    
    # Флаг: Только для доставки/самовивозу
    is_takeaway: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    tech_card: Mapped["TechCard"] = relationship("TechCard", back_populates="components")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")

# --- ПРАВИЛА АВТО-СПИСАНИЯ (УПАКОВКА) ---

class AutoDeductionRule(Base):
    """
    Правила для автоматического списания расходников (упаковка, пакеты, приборы)
    в зависимости от типа заказа (Доставка, Самовывоз, В зале).
    """
    __tablename__ = 'auto_deduction_rules'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Тип заказа, при котором срабатывает правило:
    # 'delivery', 'pickup', 'in_house', 'all'
    trigger_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    
    # Что списывать
    ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'), nullable=False)
    quantity: Mapped[float] = mapped_column(sa.Numeric(10, 3), default=1.000)
    
    # Откуда списывать
    warehouse_id: Mapped[int] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=False)
    
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[warehouse_id])

# --- СКЛАДСКОЙ УЧЕТ ---

class Stock(Base):
    """Остатки на складах"""
    __tablename__ = 'stocks'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(sa.ForeignKey('warehouses.id'))
    ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'))
    quantity: Mapped[float] = mapped_column(sa.Numeric(10, 3), default=0.000)
    
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stocks", foreign_keys=[warehouse_id])
    ingredient: Mapped["Ingredient"] = relationship("Ingredient", back_populates="stocks")

class InventoryDoc(Base):
    """Документ движения (Накладная)"""
    __tablename__ = 'inventory_docs'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Типы: supply (приход), transfer (перемещение), writeoff (списание), deduction (авто-списание по чеку), return (возврат)
    doc_type: Mapped[str] = mapped_column(sa.String(20)) 
    
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.now)
    
    # Флаг: проведен ли документ (повлиял ли он на остатки)
    is_processed: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=text("false"))
    
    supplier_id: Mapped[int | None] = mapped_column(sa.ForeignKey('suppliers.id'), nullable=True)
    source_warehouse_id: Mapped[int | None] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    target_warehouse_id: Mapped[int | None] = mapped_column(sa.ForeignKey('warehouses.id'), nullable=True)
    
    comment: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    # Если это списание на основе продажи, здесь будет ID заказа
    linked_order_id: Mapped[int | None] = mapped_column(sa.ForeignKey('orders.id'), nullable=True) 
    
    # Сумма, которая была оплачена из кассы за эту накладную (для учета расходов)
    paid_amount: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0.00, server_default=text("0.00"))
    
    items: Mapped[list["InventoryDocItem"]] = relationship("InventoryDocItem", back_populates="doc", cascade="all, delete-orphan")
    
    supplier: Mapped["Supplier"] = relationship("Supplier")
    source_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    target_warehouse: Mapped["Warehouse"] = relationship("Warehouse", foreign_keys=[target_warehouse_id])

class InventoryDocItem(Base):
    """Позиция в накладной"""
    __tablename__ = 'inventory_doc_items'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(sa.ForeignKey('inventory_docs.id'))
    ingredient_id: Mapped[int] = mapped_column(sa.ForeignKey('ingredients.id'))
    quantity: Mapped[float] = mapped_column(sa.Numeric(10, 3))
    price: Mapped[float] = mapped_column(sa.Numeric(10, 2), default=0.00) # Цена закупки (для прихода)
    
    doc: Mapped["InventoryDoc"] = relationship("InventoryDoc", back_populates="items")
    ingredient: Mapped["Ingredient"] = relationship("Ingredient")