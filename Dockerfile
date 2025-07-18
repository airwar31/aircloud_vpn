FROM python:3.10-slim

WORKDIR /app

# Установка необходимых пакетов
RUN apt-get update && apt-get install -y \
    curl \
    socat \
    jq \
    unzip \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray напрямую
RUN mkdir -p /tmp/xray && \
    curl -L -o /tmp/xray/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip /tmp/xray/xray.zip -d /tmp/xray && \
    mv /tmp/xray/xray /usr/local/bin/ && \
    mv /tmp/xray/geosite.dat /usr/local/bin/ && \
    mv /tmp/xray/geoip.dat /usr/local/bin/ && \
    chmod +x /usr/local/bin/xray && \
    rm -rf /tmp/xray

# Создание директорий для логов и конфигурации
RUN mkdir -p /var/log/xray && \
    mkdir -p /etc/xray && \
    chown -R nobody:nogroup /var/log/xray

# Копирование файлов проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копирование шаблона конфигурации
RUN mkdir -p /etc/xray && \
    cp config.template.json /etc/xray/config.template.json && \
    cp config.template.json /etc/xray/config.json && \
    chmod 644 /etc/xray/config.json

# Запуск скрипта для настройки Reality (при первом запуске)
RUN mkdir -p /app/data
VOLUME /app/data

# Запуск Xray и бота
CMD ["sh", "-c", "nohup /usr/local/bin/xray -config /etc/xray/config.json > /var/log/xray/access.log 2> /var/log/xray/error.log & sleep 2 && python main.py"]