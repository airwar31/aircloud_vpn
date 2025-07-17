#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Обновление AirCloud VPN ===${NC}"

# Останавливаем контейнеры
echo -e "${YELLOW}Останавливаем контейнеры...${NC}"
docker-compose down

# Получаем последние изменения из репозитория
echo -e "${YELLOW}Получаем последние изменения...${NC}"
git pull

# Пересобираем и запускаем контейнеры
echo -e "${GREEN}Пересобираем и запускаем контейнеры...${NC}"
docker-compose up --build -d

echo -e "${GREEN}AirCloud VPN успешно обновлен и запущен!${NC}"
echo -e "${GREEN}Для просмотра логов используйте: docker-compose logs -f${NC}"