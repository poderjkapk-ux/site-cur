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

async def update_database_schema():
    """
    Додає нові необхідні колонки до таблиць бази даних.
    """
    print(f"🔄 Підключення до бази даних...")
    
    # Створення двигуна SQLAlchemy
    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.begin() as conn:
            print("🛠 Оновлення структури таблиць...")
            
            # Додаємо колонку comment до таблиці orders (з попередніх оновлень)
            sql_query1 = text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS comment VARCHAR(500);")
            await conn.execute(sql_query1)
            print("✅ Колонку 'comment' перевірено/додано до таблиці 'orders'.")
            
            # Додаємо нову колонку restify_is_active до таблиці settings
            sql_query2 = text("ALTER TABLE settings ADD COLUMN IF NOT EXISTS restify_is_active BOOLEAN DEFAULT FALSE;")
            await conn.execute(sql_query2)
            print("✅ Колонку 'restify_is_active' перевірено/додано до таблиці 'settings'.")
            
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
    asyncio.run(update_database_schema())