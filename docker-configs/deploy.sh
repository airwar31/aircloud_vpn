#!/bin/bash

# 🚀 Скрипт развертывания VPN сервиса в Docker контейнерах

set -e

echo "================================"
echo "🚀 VPN Service Docker Deploy"
echo "================================"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

echo "✅ Docker найден"
echo ""

# Проверка .env файла
if [ ! -f .env ]; then
    echo "📋 Копирую .env.example в .env..."
    cp .env.example .env
    echo "⚠️  Отредактируйте .env с вашими значениями перед продолжением"
    echo "   Особенно важны: BOT_TOKEN, YOOKASSA_*, VK_PRIVATE_KEY"
    read -p "Готовы продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Генерируем Reality ключи если нужно
if grep -q "ВАШЕ_РЕАЛЬНОЕ_ЗНАЧЕНИЕ_КЛЮЧА" .env; then
    echo "🔑 Генерирую Reality ключи..."
    
    # Создаем временный контейнер для генерации ключей
    KEYS=$(docker run --rm xray/xray:latest x25519 2>&1)
    PRIVATE_KEY=$(echo "$KEYS" | grep "Private key:" | awk '{print $3}')
    PUBLIC_KEY=$(echo "$KEYS" | grep "Public key:" | awk '{print $3}')
    
    echo "Private Key: $PRIVATE_KEY"
    echo "Public Key: $PUBLIC_KEY"
    echo ""
    
    # Обновляем .env файл
    sed -i "s/ВАШЕ_РЕАЛЬНОЕ_ЗНАЧЕНИЕ_КЛЮЧА/$PRIVATE_KEY/" .env
    
    echo "✅ Reality ключи сгенерированы и добавлены в .env"
    echo ""
fi

# Сборка образов
echo "🔨 Сборка Docker образов..."
docker-compose build

echo ""
echo "🚀 Запуск контейнеров..."
docker-compose up -d

echo ""
echo "⏳ Ожидание запуска сервисов (15 секунд)..."
sleep 15

# Проверка статуса
echo ""
echo "📊 Статус контейнеров:"
docker-compose ps

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📋 Доступные команды:"
echo "  docker-compose logs -f vk-server  # Логи ВК сервера"
echo "  docker-compose logs -f nl-server  # Логи NL сервера"
echo "  docker-compose logs -f vpn-bot    # Логи бота"
echo "  docker-compose ps                 # Статус контейнеров"
echo "  docker-compose down               # Остановить все"
echo ""
echo "📌 Следующие шаги:"
echo "  1. Получите SSL сертификат для NL сервера (Let's Encrypt)"
echo "  2. Обновите конфиги с реальными UUID и IP адресами"
echo "  3. Протестируйте подключение через мобильное приложение"
echo ""
