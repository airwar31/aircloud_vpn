#!/bin/bash

echo "🔍 ДИАГНОСТИКА VPN ПРОБЛЕМЫ"
echo "=========================="

UUID="44524a54-bf42-4864-9b6c-7691bef1853e"

echo "1️⃣ Проверяем пользователя в конфиге:"
if grep -q "$UUID" /usr/local/etc/xray/config.json; then
    echo "✅ Пользователь найден в конфиге"
    grep -A 3 -B 1 "$UUID" /usr/local/etc/xray/config.json
else
    echo "❌ Пользователь НЕ найден в конфиге"
fi

echo ""
echo "2️⃣ Проверяем Reality ключи:"
grep -A 10 '"realitySettings"' /usr/local/etc/xray/config.json

echo ""
echo "3️⃣ Статус Xray:"
systemctl status xray --no-pager -l | head -10

echo ""
echo "4️⃣ Последние логи Xray:"
journalctl -u xray -n 5 --no-pager

echo ""
echo "5️⃣ Генерируем тестовый токен:"
SERVER_IP=$(curl -4 -s ifconfig.me)
PUBLIC_KEY=$(grep '"publicKey"' /usr/local/etc/xray/config.json | cut -d'"' -f4)

echo "vless://$UUID@$SERVER_IP:443?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=chrome&sni=google.com&sid=&flow=xtls-rprx-vision#TestUser"