FROM ubuntu:22.04

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray (без systemd требирования)
RUN mkdir -p /usr/local/bin && \
    curl -L https://github.com/XTLS/Xray-core/releases/download/v24.12.31/Xray-linux-64.zip -o /tmp/xray.zip && \
    cd /tmp && unzip -q xray.zip && \
    mv /tmp/xray /usr/local/bin/xray && \
    chmod +x /usr/local/bin/xray && \
    rm -f /tmp/*.zip /tmp/xray* && \
    mkdir -p /etc/xray

# Копируем конфиг
COPY config.json /etc/xray/config.json

# Устанавливаем права доступа
RUN chown -R nobody:nogroup /etc/xray

# Открываем порты
EXPOSE 443 8443

# Запускаем Xray
CMD ["/usr/local/bin/xray", "-c", "/etc/xray/config.json"]
