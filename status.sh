#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Статус AirCloud VPN ===${NC}"

# Проверяем статус контейнера
CONTAINER_STATUS=$(docker-compose ps -q aircloud-vpn)

if [ -z "$CONTAINER_STATUS" ]; then
    echo -e "${RED}Контейнер не запущен!${NC}"
    echo -e "${YELLOW}Для запуска выполните: docker-compose up -d${NC}"
    exit 1
fi

echo -e "${GREEN}Контейнер запущен${NC}"

# Проверяем логи контейнера
echo -e "${YELLOW}Последние логи:${NC}"
docker-compose logs --tail=20 aircloud-vpn

# Проверяем статус Xray
echo -e "${YELLOW}Статус Xray:${NC}"
docker-compose exec aircloud-vpn service xray status

# Проверяем открытые порты
echo -e "${YELLOW}Открытые порты:${NC}"
docker-compose exec aircloud-vpn netstat -tulpn | grep xray

echo -e "${GREEN}Для просмотра полных логов используйте: docker-compose logs -f${NC}"