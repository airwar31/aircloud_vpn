#!/bin/bash

echo "🚀 Безопасная установка AirCloud VPN + Xray"
echo "======================================================"

# Загружаем переменные окружения из .env файла
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Переменные окружения загружены из .env"
else
    echo "❌ Файл .env не найден"
    echo "Создайте файл .env на основе .env.example"
    exit 1
fi

# Проверяем наличие обязательных переменных
if [ -z "$XRAY_SERVER_IP" ] || [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: Не заданы обязательные переменные окружения"
    echo "Проверьте файл .env"
    exit 1
fi

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
                "clients": [
                    {
                        "id": "00000000-0000-0000-0000-000000000000",
                        "email": "admin@aircloud.vpn",
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

# Создаем директорию для данных
echo "📁 Создаем директорию для данных..."
mkdir -p data

# Сохраняем публичный ключ
echo "$PUBLIC_KEY" > data/public_key.txt

echo "🔑 Сохранено для бота:"
echo "- Public Key: $PUBLIC_KEY"
echo "- UUID будут генерироваться уникально для каждого пользователя"

# Запускаем Xray
echo "🚀 Запускаем Xray..."
systemctl enable xray
systemctl restart xray

# Создаем скрипт для добавления пользователей
cat > /usr/local/bin/add_user_to_xray.py << 'SCRIPT_EOF'
#!/usr/bin/env python3
import json
import sys
import os

def add_user_to_config(user_uuid, email):
    config_path = '/usr/local/etc/xray/config.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        for inbound in config.get('inbounds', []):
            if inbound.get('tag') == 'vless-in':
                clients = inbound.get('settings', {}).get('clients', [])
                
                for client in clients:
                    if client.get('id') == user_uuid:
                        print(f"User {email} already exists")
                        return True
                
                new_client = {
                    "id": user_uuid,
                    "email": email,
                    "flow": "xtls-rprx-vision"
                }
                clients.append(new_client)
                
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"User {email} added")
                return True
        
        return False
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)
    
    user_uuid = sys.argv[1]
    email = sys.argv[2]
    
    if add_user_to_config(user_uuid, email):
        os.system("systemctl reload xray")
SCRIPT_EOF

chmod +x /usr/local/bin/add_user_to_xray.py

# Устанавливаем сервис для добавления пользователей
echo "🌐 Устанавливаем сервис добавления пользователей..."
cp xray_user_service.py /root/
cp xray-user-service.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable xray-user-service
systemctl start xray-user-service

# Запускаем бота с переменными окружения
echo "🤖 Запускаем бота..."
export PUBLIC_KEY="$PUBLIC_KEY"
docker-compose up -d --build aircloud-bot

echo ""
echo "✅ Установка завершена!"
echo "🌍 VPN сервер: $XRAY_SERVER_IP:443"
echo "🔑 Public Key: $PUBLIC_KEY"
echo ""
echo "📋 Проверка Xray: systemctl status xray"
echo "📋 Проверка бота: docker-compose logs -f aircloud-bot"