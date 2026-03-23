# Dockerfile

# --- Этап 1: Базовый образ ---
FROM python:3.11-slim

# --- Налаштування змінних оточення ---
# Запобігає створенню .pyc файлів
ENV PYTHONDONTWRITEBYTECODE=1
# Запобігає буферизації виводу (логів)
ENV PYTHONUNBUFFERED=1
# Порт за замовчуванням
ENV PORT=8000

# --- Этап 2: Настройка рабочей директории ---
WORKDIR /app

# --- Этап 3: Установка системних залежностей (якщо потрібно для Pillow/asyncpg) ---
# Зазвичай для asyncpg та Pillow вистачає binary wheels, але про всяк випадок:
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# --- Этап 4: Установка Python залежностей ---
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Этап 5: Копирование кода ---
# Копіюємо весь код проекту (враховуючи .dockerignore)
COPY . .

# --- Этап 6: Запуск ---
EXPOSE 8000

# Запускаємо uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]