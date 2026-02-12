FROM ubuntu:22.04

# Установка Certbot и Xray
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    certbot \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray
RUN bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) install

# Создаем директории
RUN mkdir -p /etc/xray/certs

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
