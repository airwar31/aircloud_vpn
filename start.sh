#!/bin/bash

echo "🚀 Автоматическая установка AirCloud VPN + Xray"
echo "======================================================"

# Устанавливаем Xray на сервер
echo "📦 Устанавливаем Xray..."
if ! command -v xray &> /dev/null; then
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
    echo "✅ Xray установлен"
else
    echo "✅ Xray уже установлен"
fi

# Открываем порт 443
echo "🔓 Открываем порт 443..."
ufw allow 443 2>/dev/null || iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || echo "⚠️  Не удалось открыть порт автоматически"

# Генерируем Reality ключи
echo "🔑 Генерируем Reality ключи..."
KEYS=$(xray x25519)
PRIVATE_KEY=$(echo "$KEYS" | grep "Private key:" | cut -d' ' -f3)
PUBLIC_KEY=$(echo "$KEYS" | grep "Public key:" | cut -d' ' -f3)

echo "🔐 Private: $PRIVATE_KEY"
echo "🔑 Public: $PUBLIC_KEY"

# Получаем IP сервера
SERVER_IP=$(curl -4 -s ifconfig.me || curl -4 -s ipinfo.io/ip || curl -4 -s icanhazip.com)
echo "🌍 Сервер IP: $SERVER_IP"

# Создаем конфигурацию Xray
echo "🔧 Создаем конфигурацию Xray..."
cat > /usr/local/etc/xray/config.json << EOF
{
    "log": {
        "loglevel": "info"
    },
    "api": {
        "tag": "api",
        "services": ["HandlerService", "StatsService"]
    },
    "stats": {},
    "inbounds": [
        {
            "listen": "127.0.0.1",
            "port": 10085,
            "protocol": "dokodemo-door",
            "settings": {
                "address": "127.0.0.1"
            },
            "tag": "api"
        },
        {
            "tag": "vless-in",
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "google.com:443",
                    "serverNames": ["google.com"],
                    "privateKey": "$PRIVATE_KEY",
                    "shortIds": [""]
                }
            },
            "sniffing": {
                "enabled": true,
                "destOverride": ["http", "tls", "quic"],
                "routeOnly": true
            }
        }
    ],
    "outbounds": [
        {
            "tag": "direct",
            "protocol": "freedom"
        }
    ],
    "routing": {
        "rules": [
            {
                "type": "field",
                "inboundTag": ["api"],
                "outboundTag": "api"
            }
        ]
    }
}
EOF

# Генерируем несколько UUID для пользователей
echo "🔑 Генерируем UUID для пользователей..."
UUID1=$(xray uuid)
UUID2=$(xray uuid)
UUID3=$(xray uuid)
UUID4=$(xray uuid)
UUID5=$(xray uuid)

echo "UUID1: $UUID1"
echo "UUID2: $UUID2"
echo "UUID3: $UUID3"
echo "UUID4: $UUID4"
echo "UUID5: $UUID5"

# Сохраняем UUID в файл для бота
cat > uuid_pool.txt << EOF
$UUID1
$UUID2
$UUID3
$UUID4
$UUID5
EOF

# Обновляем конфигурацию с пулом пользователей
cat > /usr/local/etc/xray/config.json << EOF
{
    "log": {
        "loglevel": "info"
    },
    "api": {
        "tag": "api",
        "services": ["HandlerService", "StatsService"]
    },
    "stats": {},
    "inbounds": [
        {
            "listen": "127.0.0.1",
            "port": 10085,
            "protocol": "dokodemo-door",
            "settings": {
                "address": "127.0.0.1"
            },
            "tag": "api"
        },
        {
            "tag": "vless-in",
            "port": 443,
            "protocol": "vless",
            "settings": {
                "clients": [
                    {
                        "id": "$UUID1",
                        "email": "user1@aircloud.vpn",
                        "flow": "xtls-rprx-vision"
                    },
                    {
                        "id": "$UUID2",
                        "email": "user2@aircloud.vpn",
                        "flow": "xtls-rprx-vision"
                    },
                    {
                        "id": "$UUID3",
                        "email": "user3@aircloud.vpn",
                        "flow": "xtls-rprx-vision"
                    },
                    {
                        "id": "$UUID4",
                        "email": "user4@aircloud.vpn",
                        "flow": "xtls-rprx-vision"
                    },
                    {
                        "id": "$UUID5",
                        "email": "user5@aircloud.vpn",
                        "flow": "xtls-rprx-vision"
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "dest": "google.com:443",
                    "serverNames": ["google.com"],
                    "privateKey": "$PRIVATE_KEY",
                    "shortIds": [""]
                }
            },
            "sniffing": {
                "enabled": true,
                "destOverride": ["http", "tls", "quic"],
                "routeOnly": true
            }
        }
    ],
    "outbounds": [
        {
            "tag": "direct",
            "protocol": "freedom"
        }
    ],
    "routing": {
        "rules": [
            {
                "type": "field",
                "inboundTag": ["api"],
                "outboundTag": "api"
            }
        ]
    }
}
EOF

# Обновляем код бота с новыми ключами
echo "🤖 Обновляем конфигурацию бота..."
sed -i "s/4J6HNMExjUwdktWwR5Bo3rrjY3raBIGvFBHyQK86kQU/$PUBLIC_KEY/g" xray_api.py
sed -i "s/127.0.0.1/$SERVER_IP/g" docker-compose.yml

# Копируем данные для бота
cp uuid_pool.txt data/
echo "$PUBLIC_KEY" > data/public_key.txt

echo "🔑 Сохранено для бота:"
echo "- UUID пул: $(wc -l < uuid_pool.txt) пользователей"
echo "- Public Key: $PUBLIC_KEY"

# Запускаем Xray
echo "🚀 Запускаем Xray..."
systemctl enable xray
systemctl restart xray

# Создаем папки для бота
mkdir -p data

# Запускаем бота
echo "🤖 Запускаем бота..."
docker-compose up -d --build aircloud-bot

echo ""
echo "✅ Установка завершена!"
echo "🌍 VPN сервер: $SERVER_IP:443"
echo "🔑 Public Key: $PUBLIC_KEY"

# Ждем запуска бота и синхронизируем UUID
echo "🔄 Ожидание запуска бота..."
sleep 15

echo "🔄 Синхронизация UUID с Xray..."
if [ -f "data/uuid_pool.txt" ]; then
    # Читаем UUID из пула
    UUID1=$(sed -n '1p' data/uuid_pool.txt 2>/dev/null || echo "")
    UUID2=$(sed -n '2p' data/uuid_pool.txt 2>/dev/null || echo "")
    UUID3=$(sed -n '3p' data/uuid_pool.txt 2>/dev/null || echo "")
    UUID4=$(sed -n '4p' data/uuid_pool.txt 2>/dev/null || echo "")
    UUID5=$(sed -n '5p' data/uuid_pool.txt 2>/dev/null || echo "")
    
    if [ ! -z "$UUID1" ]; then
        echo "🔑 Обновление конфига Xray..."
        
        # Обновляем конфиг Xray
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
        
        # Перезапускаем Xray
        systemctl restart xray
        echo "✅ UUID синхронизированы!"
    else
        echo "⚠️  UUID пул пуст, повторите через минуту"
    fi
else
    echo "⚠️  Файл UUID пула не найден, повторите через минуту"
fi

echo ""
echo "📋 Проверка Xray: systemctl status xray"
echo "📋 Проверка бота: docker-compose logs -f aircloud-bot"