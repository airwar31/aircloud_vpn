#!/bin/bash

echo "🚀 Безопасная установка AirCloud VPN + Xray"
echo "======================================================"

# Проверяем наличие переменных окружения
if [ -z "$XRAY_SERVER_IP" ] || [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: Не заданы обязательные переменные окружения"
    echo "Создайте файл .env на основе .env.example"
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

# Генерируем UUID для пула
echo "🔑 Генерируем UUID для пула..."
mkdir -p data
for i in {1..5}; do
    xray uuid >> data/uuid_pool.txt
done

# Сохраняем публичный ключ
echo "$PUBLIC_KEY" > data/public_key.txt

echo "🔑 Сохранено для бота:"
echo "- UUID пул: $(wc -l < data/uuid_pool.txt) пользователей"
echo "- Public Key: $PUBLIC_KEY"

# Запускаем Xray
echo "🚀 Запускаем Xray..."
systemctl enable xray
systemctl restart xray

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