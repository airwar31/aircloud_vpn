#!/bin/bash

echo "🔄 Синхронизация пользователей с Xray"
echo "===================================="

# Читаем UUID из пула бота
if [ -f "data/uuid_pool.txt" ]; then
    echo "📋 UUID из пула бота:"
    cat -n data/uuid_pool.txt
    
    # Читаем все UUID
    UUID1=$(sed -n '1p' data/uuid_pool.txt)
    UUID2=$(sed -n '2p' data/uuid_pool.txt)
    UUID3=$(sed -n '3p' data/uuid_pool.txt)
    UUID4=$(sed -n '4p' data/uuid_pool.txt)
    UUID5=$(sed -n '5p' data/uuid_pool.txt)
    
    echo ""
    echo "🔧 Обновление конфигурации Xray..."
    
    # Обновляем конфиг Xray с актуальными UUID
    python3 -c "
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
            break
    
    # Сохраняем обновленный конфиг
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print('✅ Конфигурация обновлена')
    
except Exception as e:
    print(f'❌ Ошибка: {e}')
"
    
    # Перезагружаем Xray
    echo "🔄 Перезагрузка Xray..."
    systemctl reload xray
    
    echo ""
    echo "✅ Синхронизация завершена!"
    echo "📋 Проверка:"
    echo "journalctl -u xray --no-pager -n 5"
    
else
    echo "❌ Файл data/uuid_pool.txt не найден"
    echo "Запустите сначала: docker-compose restart aircloud-bot"
fi