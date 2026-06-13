FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего кода (будет перезаписано volume в docker-compose для hot-reload)
COPY . .

EXPOSE 8000

# Запуск с hot-reload для разработки
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]