#!/bin/bash

# Скрипт для запуска очистки внутри Docker контейнера

echo "🧹 Запуск очистки VPN системы в контейнере"

# Проверяем, запущены ли контейнеры
if ! docker ps | grep -q "vpn-bot"; then
    echo "❌ Контейнер vpn-bot не запущен!"
    echo "Запустите систему командой: docker-compose up -d"
    exit 1
fi

echo "📦 Найден контейнер vpn-bot"

# Запрашиваем подтверждение
read -p "⚠️  Это удалит ВСЕ данные! Введите 'YES' для подтверждения: " confirm
if [ "$confirm" != "YES" ]; then
    echo "❌ Очистка отменена"
    exit 0
fi

# Дополнительное подтверждение
read -p "Последнее предупреждение! Введите 'CONFIRM' для продолжения: " confirm2
if [ "$confirm2" != "CONFIRM" ]; then
    echo "❌ Очистка отменена"
    exit 0
fi

echo "🚀 Запуск очистки в контейнере..."

# Выполняем очистку в контейнере
if docker exec vpn-bot python cleanup.py; then
    echo "✅ Очистка завершена успешно!"
    echo "🔄 Рекомендуется перезапустить контейнеры:"
    echo "   docker-compose restart"
else
    echo "❌ Ошибка при выполнении очистки"
    exit 1
fi