FROM ubuntu:22.04

# Установка зависимостей и Xray
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка Xray
RUN bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) install

# Копируем конфиг
COPY config.json /etc/xray/config.json

# Устанавливаем права доступа
RUN chown -R nobody:nogroup /etc/xray

# Открываем порты
EXPOSE 443 8443

# Запускаем Xray
CMD ["/usr/local/bin/xray", "-c", "/etc/xray/config.json"]
