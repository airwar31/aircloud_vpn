#!/bin/bash

# Скрипт для генерации самоподписанного сертификата

echo "🔐 Генерация SSL сертификата..."

# Создание директорий
if ! mkdir -p /etc/ssl/certs /etc/ssl/private; then
    echo "❌ Ошибка создания директорий"
    exit 1
fi

# Генерация приватного ключа
if ! openssl genrsa -out /etc/ssl/private/key.pem 2048; then
    echo "❌ Ошибка генерации ключа"
    exit 1
fi

# Генерация сертификата
if ! openssl req -new -x509 -key /etc/ssl/private/key.pem -out /etc/ssl/certs/cert.pem -days 365 -subj "/C=US/ST=CA/L=San Francisco/O=Google Inc/CN=www.google.com"; then
    echo "❌ Ошибка генерации сертификата"
    exit 1
fi

# Установка прав доступа
if ! chmod 600 /etc/ssl/private/key.pem || ! chmod 644 /etc/ssl/certs/cert.pem; then
    echo "❌ Ошибка установки прав доступа"
    exit 1
fi

echo "✅ SSL сертификат создан"