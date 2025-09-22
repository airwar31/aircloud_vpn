FROM python:3.11-slim

# Настройка DNS для исправления проблем с резолвингом
RUN echo 'nameserver 8.8.8.8' > /etc/resolv.conf

# Установка системных зависимостей с альтернативными зеркалами
RUN apt-get update --fix-missing || true && \
    apt-get install -y --no-install-recommends \
    wget \
    unzip \
    procps \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* || true

# Установка Xray
RUN wget -O xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip \
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