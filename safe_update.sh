#!/bin/bash

PROJECT_DIR="/path/to/your/aircloud_vpn"
REPO_URL="https://github.com/your-repo/aircloud_vpn.git"

cd $PROJECT_DIR

echo "1. Остановка сервисов..."
docker-compose down

echo "2. Создание бэкапа..."
./update_backup.sh

echo "3. Сохранение критических файлов..."
cp .env .env.backup
cp -r logs logs.backup

echo "4. Обновление кода..."
git stash  # Сохраняем локальные изменения
git pull origin main

echo "5. Восстановление конфигурации..."
cp .env.backup .env
cp -r logs.backup/* logs/ 2>/dev/null || true

echo "6. Обновление зависимостей..."
docker-compose build --no-cache

echo "7. Запуск обновленных сервисов..."
docker-compose up -d

echo "8. Проверка статуса..."
sleep 10
docker-compose ps

echo "Обновление завершено!"
echo "Проверьте работу бота и при необходимости откатитесь: git stash pop"