#!/bin/bash

# Скрипт для генерации самоподписанного сертификата

echo "🔐 Генерация SSL сертификата..."

# Создание директорий
mkdir -p /etc/ssl/certs /etc/ssl/private

# Генерация приватного ключа
openssl genrsa -out /etc/ssl/private/key.pem 2048

# Генерация сертификата
openssl req -new -x509 -key /etc/ssl/private/key.pem -out /etc/ssl/certs/cert.pem -days 365 -subj "/C=US/ST=CA/L=San Francisco/O=Google Inc/CN=www.google.com"

# Установка прав доступа
chmod 600 /etc/ssl/private/key.pem
chmod 644 /etc/ssl/certs/cert.pem

echo "✅ SSL сертификат создан"