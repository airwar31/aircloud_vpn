#!/bin/bash

echo "🔒 Настройка HTTPS для AirCloud VPN"
echo "=================================="

# Получаем IP сервера
SERVER_IP=$(curl -4 -s ifconfig.me)
echo "🌍 IP сервера: $SERVER_IP"

# Вариант 1: Самоподписанный сертификат (быстро)
echo "📜 Создаем самоподписанный SSL сертификат..."
openssl req -x509 -newkey rsa:4096 -keyout ssl/private.key -out ssl/cert.pem -days 365 -nodes -subj "/C=RU/ST=Moscow/L=Moscow/O=AirCloud/CN=$SERVER_IP"

# Создаем папку для SSL
mkdir -p ssl

# Вариант 2: Let's Encrypt (для домена)
echo "🔧 Для Let's Encrypt нужен домен. Установка certbot:"
echo "sudo apt update && sudo apt install certbot"
echo "sudo certbot certonly --standalone -d yourdomain.com"

# Обновляем docker-compose для HTTPS
cat > docker-compose-https.yml << EOF
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: aircloud-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-https.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - aircloud-bot
    networks:
      - aircloud-network

  aircloud-bot:
    build: .
    container_name: aircloud-vpn-bot
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - BOT_TOKEN=7717019733:AAE8ElbxXYUTeoLct8s185m8aMA6lwx_mns
      - ADMIN_IDS=1262543088
      - YOOKASSA_SHOP_ID=1127420
      - YOOKASSA_SECRET_KEY=test_5ed7HCB8W7xTWQm4WjSjrSi_gNjI5lvh42-j-1Ts5Zc
      - XRAY_SERVER_IP=$SERVER_IP
      - XRAY_SERVER_PORT=443
      - DATABASE_PATH=/app/data/aircloud_vpn.db
    networks:
      - aircloud-network

networks:
  aircloud-network:
    driver: bridge
EOF

# Создаем конфиг Nginx с HTTPS
cat > nginx-https.conf << EOF
events {
    worker_connections 1024;
}

http {
    # HTTP -> HTTPS редирект
    server {
        listen 80;
        server_name $SERVER_IP;
        return 301 https://\$server_name\$request_uri;
    }

    # HTTPS сервер
    server {
        listen 443 ssl http2;
        server_name $SERVER_IP;

        # SSL сертификаты
        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/private.key;

        # SSL настройки
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Проксирование к боту
        location / {
            proxy_pass http://aircloud-bot:8000;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
    }
}
EOF

echo ""
echo "✅ HTTPS настроен!"
echo "📋 Варианты запуска:"
echo ""
echo "1️⃣ С самоподписанным сертификатом:"
echo "   docker-compose -f docker-compose-https.yml up -d"
echo ""
echo "2️⃣ С Let's Encrypt (нужен домен):"
echo "   sudo certbot certonly --standalone -d yourdomain.com"
echo "   cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem"
echo "   cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/private.key"
echo "   docker-compose -f docker-compose-https.yml up -d"
echo ""
echo "🌐 HTTPS будет доступен по адресу: https://$SERVER_IP"