#!/bin/bash

echo "🚀 БЫСТРЫЙ ЗАПУСК AIRCLOUD VPN"
echo "============================="

# Проверяем root права
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт от root: sudo bash quick_start.sh"
    exit 1
fi

# Проверяем .env файл
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл на основе .env.example"
    exit 1
fi

echo "1️⃣ Установка Xray..."
bash start_secure.sh

echo ""
echo "2️⃣ Запуск бота..."
docker-compose up -d --build

echo ""
echo "3️⃣ Проверка статуса..."
sleep 5

echo "📊 Статус Xray:"
systemctl status xray --no-pager -l | head -10

echo ""
echo "📊 Статус бота:"
docker-compose ps

echo ""
echo "✅ Запуск завершен!"
echo "📋 Проверьте логи: docker-compose logs -f aircloud-bot"
echo "🔧 Управление: systemctl status xray"