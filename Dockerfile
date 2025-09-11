FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray
RUN curl -L https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip \
    && unzip xray.zip \
    && mv xray /usr/local/bin/ \
    && chmod +x /usr/local/bin/xray \
    && rm xray.zip

# Создание рабочей директории
WORKDIR /app

# Копирование файлов
COPY requirements.txt .
COPY xray_api.py .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Создание директории для конфигурации
RUN mkdir -p /etc/xray

# Переменные окружения
ENV SERVER_IP=YOUR_SERVER_IP
ENV FLASK_APP=xray_api.py

# Открытие портов
EXPOSE 8080 443

# Запуск
CMD ["python", "xray_api.py"]