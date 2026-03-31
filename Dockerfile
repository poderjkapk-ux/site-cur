# Dockerfile

# --- Этап 1: Базовый образ ---
FROM python:3.11-slim

# --- Налаштування змінних оточення ---
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# --- Этап 2: Настройка рабочей директории ---
WORKDIR /app

# --- Этап 3: Установка системних залежностей ---
# ДОБАВЛЕНО: Установка tzdata для поддержки часовых поясов
RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

# --- Этап 4: Установка Python залежностей ---
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Этап 5: Копирование кода ---
COPY . .

# --- Этап 6: Запуск ---
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]