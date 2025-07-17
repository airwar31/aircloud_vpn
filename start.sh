#!/bin/bash

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo "Файл .env не найден. Копируем из .env.example..."
    cp .env.example .env
    echo "Пожалуйста, отредактируйте файл .env перед запуском."
    exit 1
fi

# Создаем директории для данных и логов
mkdir -p data
mkdir -p logs

# Запускаем контейнеры
docker-compose up -d

echo "AirCloud VPN запущен!"
echo "Для просмотра логов используйте: docker-compose logs -f"