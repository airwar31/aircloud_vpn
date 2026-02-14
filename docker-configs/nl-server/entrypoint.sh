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
        -subj "/C=NL/ST=Netherlands/L=Amsterdam/O=VPN/CN=85.239.56.174"
    
    chown -R nobody:nogroup /etc/xray/certs
    chmod 600 /etc/xray/certs/privkey.pem
fi

# Генерируем UUID для single tunnel если еще не заменены
echo "Preparing Xray configuration..."
if grep -q "REPLACE_WITH_UUID_SINGLE" /etc/xray/config.json; then
    SINGLE_UUID=$(cat /proc/sys/kernel/random/uuid)
    sed -i "s/REPLACE_WITH_UUID_SINGLE/$SINGLE_UUID/g" /etc/xray/config.json
    echo "Generated Single Tunnel UUID: $SINGLE_UUID"
fi

if grep -q "REPLACE_WITH_UUID_DOUBLE" /etc/xray/config.json; then
    DOUBLE_UUID=$(cat /proc/sys/kernel/random/uuid)
    sed -i "s/REPLACE_WITH_UUID_DOUBLE/$DOUBLE_UUID/g" /etc/xray/config.json
    echo "Generated Double Tunnel UUID: $DOUBLE_UUID"
fi

# Запускаем Xray
echo "Starting Xray..."
/usr/local/bin/xray -c /etc/xray/config.json
