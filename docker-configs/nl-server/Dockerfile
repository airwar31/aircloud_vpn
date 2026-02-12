FROM ubuntu:22.04

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray (без systemd требирования)
RUN mkdir -p /usr/local/bin && \
    curl -L https://github.com/XTLS/Xray-core/releases/download/v24.12.31/Xray-linux-64.zip -o /tmp/xray.zip && \
    cd /tmp && unzip -q xray.zip && \
    mv /tmp/xray /usr/local/bin/xray && \
    chmod +x /usr/local/bin/xray && \
    rm -f /tmp/*.zip /tmp/xray* && \
    mkdir -p /etc/xray/certs

# Копируем конфиг
COPY config.json /etc/xray/config.json
COPY entrypoint.sh /entrypoint.sh

# Даем права на исполнение
RUN chmod +x /entrypoint.sh

# Устанавливаем права доступа
RUN chown -R nobody:nogroup /etc/xray

# Открываем порты (443 for double-tunnel, 8443 for single tunnel)
EXPOSE 443 8443

# Запускаем скрипт входа
ENTRYPOINT ["/entrypoint.sh"]
