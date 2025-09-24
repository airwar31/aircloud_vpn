#!/bin/bash
# Быстрое исправление проблемы с MYSQL_PASSWORD

echo "🔧 Исправление проблемы с cleanup-service..."

# 1. Останавливаем проблемный сервис
echo "⏹️ Остановка cleanup-service..."
docker-compose stop cleanup-service

# 2. Проверяем .env файл
echo "🔍 Проверка .env файла..."
if grep -q "MYSQL_PASSWORD" .env; then
    echo "✅ MYSQL_PASSWORD найден в .env"
else
    echo "❌ MYSQL_PASSWORD отсутствует в .env"
    echo "Добавляем MYSQL_PASSWORD..."
    echo "MYSQL_PASSWORD=1%)aD)Gz={E}+v" >> .env
fi

# 3. Перезапускаем только cleanup-service
echo "🔄 Перезапуск cleanup-service..."
docker-compose up -d cleanup-service

# 4. Проверяем статус
echo "📊 Проверка статуса..."
sleep 3
docker logs cleanup-service --tail 5

echo "✅ Исправление завершено"