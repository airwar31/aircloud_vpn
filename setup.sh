#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Установка AirCloud VPN ===${NC}"

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker не установлен. Устанавливаем...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose не установлен. Устанавливаем...${NC}"
    curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Проверяем наличие файла .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}Файл .env не найден. Копируем из .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Пожалуйста, отредактируйте файл .env:${NC}"
    echo -e "${YELLOW}nano .env${NC}"
    read -p "Нажмите Enter после редактирования файла .env..."
fi

# Создаем директории для данных и логов
mkdir -p data
mkdir -p logs

# Собираем и запускаем контейнеры
echo -e "${GREEN}Собираем и запускаем контейнеры...${NC}"
docker-compose up --build -d

echo -e "${GREEN}AirCloud VPN успешно установлен и запущен!${NC}"
echo -e "${GREEN}Для просмотра логов используйте: docker-compose logs -f${NC}"
echo -e "${GREEN}Для остановки: docker-compose down${NC}"
echo -e "${GREEN}Для перезапуска: docker-compose restart${NC}"