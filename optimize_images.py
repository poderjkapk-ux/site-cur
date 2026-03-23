import asyncio
import os
import sys
from dotenv import load_dotenv

# Завантажуємо змінні оточення
load_dotenv()

from models import async_session_maker, Product
import inventory_models  # Важливо для коректної роботи SQLAlchemy

from sqlalchemy import select
from PIL import Image

# Налаштування оптимізації
MAX_SIZE = (800, 800)
QUALITY = 80
TARGET_FORMAT = "WEBP"

async def optimize_existing_images():
    async with async_session_maker() as session:
        result = await session.execute(select(Product).where(Product.image_url.is_not(None)))
        products = result.scalars().all()
        
        print(f"Знайдено {len(products)} товарів з фото. Перевірка шляхів та оптимізація...")
        
        optimized_count = 0
        fixed_path_count = 0
        skipped = 0
        errors = 0

        for product in products:
            if not product.image_url:
                continue

            original_url = product.image_url
            is_changed = False

            # --- ЕТАП 1: Виправлення слешів (Windows -> Linux/Web) ---
            if "\\" in product.image_url:
                product.image_url = product.image_url.replace("\\", "/")
                is_changed = True
                fixed_path_count += 1
                # print(f"🔧 Шлях виправлено: {product.name}")

            # Перевіряємо, чи існує файл (Python на Windows розуміє і прямі слеші /)
            if not os.path.exists(product.image_url):
                # Спробуємо знайти файл, якщо шлях був записаний "криво"
                # (наприклад, якщо в БД /, а на диску Windows хоче \)
                windows_path = product.image_url.replace("/", "\\")
                if os.path.exists(windows_path):
                    # Файл є, працюємо з ним
                    current_file_path = windows_path
                else:
                    # print(f"⚠️ Файл не знайдено: {product.image_url}")
                    continue
            else:
                current_file_path = product.image_url

            # --- ЕТАП 2: Конвертація у WebP (якщо це ще не WebP) ---
            if not product.image_url.lower().endswith('.webp'):
                try:
                    with Image.open(current_file_path) as img:
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        
                        img.thumbnail(MAX_SIZE)
                        
                        directory = os.path.dirname(current_file_path)
                        filename_no_ext = os.path.splitext(os.path.basename(current_file_path))[0]
                        new_filename = f"{filename_no_ext}.webp"
                        new_file_path = os.path.join(directory, new_filename)
                        
                        # Зберігаємо
                        img.save(new_file_path, format=TARGET_FORMAT, quality=QUALITY, optimize=True)
                    
                    # Оновлюємо посилання в БД (обов'язково з правильними слешами)
                    product.image_url = new_file_path.replace("\\", "/")
                    is_changed = True
                    optimized_count += 1
                    
                    # Видаляємо старий файл, якщо ім'я змінилося
                    if current_file_path != new_file_path:
                        try:
                            os.remove(current_file_path)
                        except Exception as e:
                            print(f"Не вдалося видалити старий файл: {e}")

                    print(f"✅ Оптимізовано: {product.name}")

                except Exception as e:
                    errors += 1
                    print(f"❌ Помилка обробки {product.name}: {e}")
            else:
                skipped += 1

            # Якщо ми виправили шлях АБО оптимізували фото -> зберігаємо в БД
            if is_changed:
                session.add(product)

        await session.commit()
        
        print("-" * 30)
        print(f"🏁 Готово!")
        print(f"Виправлено шляхів (слешів): {fixed_path_count}")
        print(f"Оптимізовано (конвертовано): {optimized_count}")
        print(f"Вже були WebP: {skipped}")
        print(f"Помилок: {errors}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(optimize_existing_images())