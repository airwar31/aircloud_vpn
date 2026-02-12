#!/bin/bash

# Ждем пока сертификаты будут готовы
echo "Waiting for SSL certificates..."
for i in {1..30}; do
    if [ -f /etc/xray/certs/fullchain.pem ] && [ -f /etc/xray/certs/privkey.pem ]; then
        echo "SSL certificates found!"
        chown -R nobody:nogroup /etc/xray/certs
        chmod 600 /etc/xray/certs/privkey.pem
        break
    fi
    echo "Attempt $i/30: Waiting for certificates..."
    sleep 5
done

# Если сертификаты не найдены, генерируем самоподписанные (для тестирования)
if [ ! -f /etc/xray/certs/fullchain.pem ]; then
    echo "Generating self-signed certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/xray/certs/privkey.pem \
        -out /etc/xray/certs/fullchain.pem \
        -subj "/C=NL/ST=Netherlands/L=Amsterdam/O=VPN/CN=nl.vpn.example.com"
    
    chown -R nobody:nogroup /etc/xray/certs
    chmod 600 /etc/xray/certs/privkey.pem
fi

# Запускаем Xray
echo "Starting Xray..."
/usr/local/bin/xray -c /etc/xray/config.json
