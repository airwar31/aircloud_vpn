#!/bin/bash

echo "🔑 Генерация тестового VPN токена"
echo "================================"

# Читаем тестовый UUID
if [ -f "test_user.txt" ]; then
    source test_user.txt
    echo "📋 Тестовый UUID: $TEST_UUID"
else
    echo "❌ Файл test_user.txt не найден"
    exit 1
fi

# Получаем IP сервера
SERVER_IP=$(curl -4 -s ifconfig.me)
echo "🌍 IP сервера: $SERVER_IP"

# Читаем публичный ключ из xray_api.py
PUBLIC_KEY=$(grep 'reality_public_key = ' xray_api.py | cut -d'"' -f2)
echo "🔐 Public Key: $PUBLIC_KEY"

# Генерируем тестовый токен
TEST_TOKEN="vless://$TEST_UUID@$SERVER_IP:443?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=chrome&sni=google.com&sid=&flow=xtls-rprx-vision#TestUser"

echo ""
echo "🎯 ТЕСТОВЫЙ VPN ТОКЕН:"
echo "======================"
echo "$TEST_TOKEN"
echo ""
echo "📱 Скопируйте этот токен и добавьте в VPN приложение"
echo "🔄 Попробуйте подключиться"
echo ""
echo "📋 Если подключение работает - проблема в API добавлении пользователей"
echo "📋 Если не работает - проблема в конфигурации Reality"