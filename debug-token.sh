#!/bin/bash

echo "🔍 Диагностика VPN токенов"
echo "=========================="

# Проверяем конфигурацию Xray
echo "📋 Проверка конфигурации Xray:"
if [ -f "/usr/local/etc/xray/config.json" ]; then
    echo "✅ Конфиг найден"
    
    # Извлекаем публичный ключ из конфига
    PUBLIC_KEY_IN_CONFIG=$(grep -o '"privateKey": "[^"]*"' /usr/local/etc/xray/config.json | cut -d'"' -f4)
    echo "🔐 Private Key в конфиге: $PUBLIC_KEY_IN_CONFIG"
    
    # Генерируем публичный ключ из приватного
    if command -v xray &> /dev/null; then
        ACTUAL_PUBLIC_KEY=$(echo "$PUBLIC_KEY_IN_CONFIG" | xray x25519 -i)
        echo "🔑 Соответствующий Public Key: $ACTUAL_PUBLIC_KEY"
        
        # Сохраняем актуальный публичный ключ
        echo "$ACTUAL_PUBLIC_KEY" > data/public_key.txt
        echo "💾 Публичный ключ сохранен в data/public_key.txt"
    fi
    
    # Проверяем количество пользователей в конфиге
    USER_COUNT=$(grep -c '"id":' /usr/local/etc/xray/config.json)
    echo "👥 Пользователей в конфиге: $USER_COUNT"
    
    # Показываем первого пользователя
    FIRST_UUID=$(grep -o '"id": "[^"]*"' /usr/local/etc/xray/config.json | head -1 | cut -d'"' -f4)
    echo "🆔 Первый UUID: $FIRST_UUID"
    
else
    echo "❌ Конфиг Xray не найден!"
fi

echo ""
echo "🌐 Проверка сети:"
SERVER_IP=$(curl -4 -s ifconfig.me)
echo "📍 Внешний IP: $SERVER_IP"

# Проверяем доступность порта 443
if nc -z localhost 443 2>/dev/null; then
    echo "✅ Порт 443 открыт"
else
    echo "❌ Порт 443 недоступен"
fi

echo ""
echo "🔄 Статус Xray:"
systemctl status xray --no-pager -l

echo ""
echo "📝 Последние логи Xray:"
journalctl -u xray --no-pager -n 10

echo ""
echo "🎯 Тестовый токен:"
if [ -f "data/uuid_pool.txt" ] && [ -f "data/public_key.txt" ]; then
    TEST_UUID=$(head -1 data/uuid_pool.txt)
    PUBLIC_KEY=$(cat data/public_key.txt)
    
    TEST_TOKEN="vless://$TEST_UUID@$SERVER_IP:443?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=chrome&sni=google.com&sid=&flow=xtls-rprx-vision#TestToken"
    
    echo "$TEST_TOKEN"
    echo ""
    echo "📱 Попробуйте этот токен в VPN приложении"
else
    echo "❌ Файлы с данными не найдены"
fi