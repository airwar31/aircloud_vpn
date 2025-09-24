#!/bin/bash

# Скрипт запуска VPN бота с Xray в контейнерах

echo "🚀 Запуск VPN бота с Xray..."

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Скопируйте .env.example в .env и заполните настройки:"
    echo "   cp .env.example .env"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен!"
    exit 1
fi

# Создание необходимых директорий
mkdir -p xray-config xray-logs bot-data

# Запуск контейнеров
echo "📦 Запуск контейнеров..."
if docker-compose up -d; then
    echo "✅ Контейнеры запущены успешно"
else
    echo "❌ Ошибка запуска контейнеров"
    exit 1
fi

# Проверка статуса
echo "✅ Проверка статуса контейнеров..."
if docker-compose ps; then
    echo "📊 Статус контейнеров получен"
else
    echo "❌ Ошибка получения статуса"
    exit 1
fi

echo "🎉 VPN бот запущен!"
echo "📊 Для просмотра логов: docker-compose logs -f"
echo "⏹️ Для остановки: docker-compose down"