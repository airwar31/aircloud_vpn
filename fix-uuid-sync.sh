#!/bin/bash

echo "🔧 Исправление синхронизации UUID"
echo "================================"

# Ждем создания файла UUID в контейнере
echo "⏳ Ожидание создания UUID пула..."
for i in {1..30}; do
    if docker exec aircloud-vpn-bot test -f /app/data/uuid_pool.txt; then
        echo "✅ UUID пул найден в контейнере!"
        break
    fi
    echo "Попытка $i/30..."
    sleep 2
done

# Копируем UUID из контейнера
echo "📋 Копирование UUID из контейнера..."
docker cp aircloud-vpn-bot:/app/data/uuid_pool.txt ./data/uuid_pool.txt 2>/dev/null

if [ -f "data/uuid_pool.txt" ]; then
    echo "✅ UUID пул скопирован!"
    echo "📋 UUID в пуле:"
    cat -n data/uuid_pool.txt
    
    # Читаем UUID
    UUID1=$(sed -n '1p' data/uuid_pool.txt)
    UUID2=$(sed -n '2p' data/uuid_pool.txt)
    UUID3=$(sed -n '3p' data/uuid_pool.txt)
    UUID4=$(sed -n '4p' data/uuid_pool.txt)
    UUID5=$(sed -n '5p' data/uuid_pool.txt)
    
    echo ""
    echo "🔧 Обновление конфигурации Xray..."
    
    # Создаем временный Python скрипт
    cat > /tmp/update_xray_config.py << EOF
import json

config_path = '/usr/local/etc/xray/config.json'

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Находим vless-in inbound и обновляем клиентов
    for inbound in config['inbounds']:
        if inbound.get('tag') == 'vless-in':
            inbound['settings']['clients'] = [
                {'id': '$UUID1', 'email': 'user1@aircloud.vpn', 'flow': 'xtls-rprx-vision'},
                {'id': '$UUID2', 'email': 'user2@aircloud.vpn', 'flow': 'xtls-rprx-vision'},
                {'id': '$UUID3', 'email': 'user3@aircloud.vpn', 'flow': 'xtls-rprx-vision'},
                {'id': '$UUID4', 'email': 'user4@aircloud.vpn', 'flow': 'xtls-rprx-vision'},
                {'id': '$UUID5', 'email': 'user5@aircloud.vpn', 'flow': 'xtls-rprx-vision'}
            ]
            print(f'Добавлено {len(inbound["settings"]["clients"])} пользователей')
            break
    
    # Сохраняем обновленный конфиг
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print('✅ Конфигурация обновлена')
    
except Exception as e:
    print(f'❌ Ошибка: {e}')
EOF
    
    # Выполняем обновление
    python3 /tmp/update_xray_config.py
    
    # Перезапускаем Xray
    echo "🔄 Перезапуск Xray..."
    systemctl restart xray
    
    echo ""
    echo "✅ Синхронизация завершена!"
    echo "🎯 Тестовый токен с первым UUID:"
    
    # Получаем публичный ключ
    PUBLIC_KEY=$(docker exec aircloud-vpn-bot cat /app/data/public_key.txt 2>/dev/null || echo "tDjEY1qV0yAQAcCAnYU6v_UjU1KtSsGGC94XJ5uWlzc")
    SERVER_IP=$(curl -4 -s ifconfig.me)
    
    echo "vless://$UUID1@$SERVER_IP:443?type=tcp&security=reality&pbk=$PUBLIC_KEY&fp=chrome&sni=google.com&sid=&flow=xtls-rprx-vision#TestToken"
    
else
    echo "❌ Не удалось получить UUID пул"
    echo "🔄 Попробуйте перезапустить бота: docker-compose restart aircloud-bot"
fi