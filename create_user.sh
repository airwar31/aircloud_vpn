#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Создание нового пользователя VPN ===${NC}"

# Проверяем, запущен ли контейнер
CONTAINER_STATUS=$(docker-compose ps -q aircloud-vpn)

if [ -z "$CONTAINER_STATUS" ]; then
    echo -e "${RED}Контейнер не запущен!${NC}"
    echo -e "${YELLOW}Для запуска выполните: docker-compose up -d${NC}"
    exit 1
fi

# Запрашиваем имя пользователя
read -p "Введите имя пользователя (email): " EMAIL

if [ -z "$EMAIL" ]; then
    echo -e "${RED}Имя пользователя не может быть пустым!${NC}"
    exit 1
fi

# Запрашиваем срок действия подписки
read -p "Введите срок действия подписки в днях [30]: " DAYS
DAYS=${DAYS:-30}

# Создаем пользователя
echo -e "${YELLOW}Создаем пользователя ${EMAIL} на ${DAYS} дней...${NC}"

# Выполняем команду в контейнере
RESULT=$(docker-compose exec -T aircloud-vpn python -c "import asyncio, json; from xray_api import XrayAPI; result = asyncio.run(XrayAPI().create_user('${EMAIL}', ${DAYS}, 100)); print(json.dumps(result))")

# Проверяем результат
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при создании пользователя!${NC}"
    exit 1
fi

# Выводим информацию о пользователе
echo -e "${GREEN}Пользователь успешно создан!${NC}"
echo -e "${YELLOW}Данные пользователя:${NC}"
echo $RESULT | python -m json.tool

# Извлекаем ссылку для подключения
LINK=$(echo $RESULT | python -c "import sys, json; print(json.load(sys.stdin)['link'])")

echo -e "${GREEN}Ссылка для подключения:${NC}"
echo -e "${YELLOW}${LINK}${NC}"

# Сохраняем ссылку в файл
echo $LINK > "user_${EMAIL}.txt"
echo -e "${GREEN}Ссылка сохранена в файл user_${EMAIL}.txt${NC}"