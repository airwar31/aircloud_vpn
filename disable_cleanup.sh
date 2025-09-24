#!/bin/bash
# Временное отключение cleanup-service

echo "⏸️ Отключение cleanup-service..."

# Останавливаем и удаляем контейнер
docker-compose stop cleanup-service
docker-compose rm -f cleanup-service

# Показываем статус остальных сервисов
echo "📊 Статус остальных сервисов:"
docker-compose ps

echo "✅ cleanup-service отключен"
echo "ℹ️ Основные сервисы (бот, xray, nginx) продолжают работать"