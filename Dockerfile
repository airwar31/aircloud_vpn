FROM python:3.10-slim

WORKDIR /app

# Установка необходимых пакетов
RUN apt-get update && apt-get install -y \
    curl \
    socat \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray
RUN curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh | bash -s -- install

# Создание директорий для логов и конфигурации
RUN mkdir -p /var/log/xray && \
    mkdir -p /etc/xray && \
    chown -R nobody:nogroup /var/log/xray

# Копирование файлов проекта
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Копирование шаблона конфигурации
RUN cp config.template.json /etc/xray/config.template.json && \
    touch /etc/xray/config.json && \
    chown nobody:nogroup /etc/xray/config.json

# Запуск скрипта для настройки Reality (при первом запуске)
RUN mkdir -p /app/data
VOLUME /app/data

# Запуск Xray и бота
CMD ["sh", "-c", "service xray start && python main.py"]