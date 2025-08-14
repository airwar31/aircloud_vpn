FROM python:3.11-slim

WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем папку для данных
RUN mkdir -p /app/data

EXPOSE 8000

# Запускаем бота
CMD ["python", "main.py"]