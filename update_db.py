import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Завантаження змінних з .env файлу
load_dotenv()

# Отримання URL бази даних
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Помилка: Не знайдено DATABASE_URL у файлі .env")
    sys.exit(1)

async def add_comment_column():
    """
    Додає колонку 'comment' до таблиці 'orders', якщо вона ще не існує.
    """
    print(f"🔄 Підключення до бази даних...")
    
    # Створення двигуна SQLAlchemy
    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.begin() as conn:
            print("🛠 Перевірка структури таблиці 'orders'...")
            
            # SQL-запит для додавання колонки. 
            # IF NOT EXISTS гарантує, що помилки не буде, якщо колонка вже є.
            sql_query = text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS comment VARCHAR(500);")
            
            await conn.execute(sql_query)
            print("✅ Успішно! Колонку 'comment' додано до таблиці 'orders' (або вона вже була).")
            
    except Exception as e:
        print(f"❌ Виникла помилка при оновленні бази даних:\n{e}")
    finally:
        await engine.dispose()
        print("🏁 Роботу скрипта завершено.")

if __name__ == "__main__":
    # Налаштування для Windows, щоб уникнути помилок EventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Запуск асинхронної функції
    asyncio.run(add_comment_column())