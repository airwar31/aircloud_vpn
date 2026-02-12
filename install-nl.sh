#!/bin/bash

################################################################################
# 🇳🇱 NL СЕРВЕР - АВТОМАТИЧЕСКАЯ УСТАНОВКА
# Установите быт на NL (Netherlands) сервер
################################################################################

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/aircloud_vpn"
DOCKER_CONFIGS_DIR="${PROJECT_DIR}/docker-configs"

echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🚀 NL СЕРВЕР - УСТАНОВКА И КОНФИГУРАЦИЯ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

################################################################################
# 1. ПРОВЕРКА ТРЕБОВАНИЙ
################################################################################

echo -e "\n${YELLOW}📋 Проверка требований...${NC}"

# Проверка root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Этот скрипт должен быть запущен от root${NC}"
   exit 1
fi

# Проверка ОС
if [[ ! -f /etc/os-release ]]; then
    echo -e "${RED}❌ Не поддерживаемая ОС${NC}"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    echo -e "${RED}❌ Требуется Ubuntu (найдена: $ID)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Ubuntu 22.04+ подтверждена${NC}"

# Проверка интернета
if ! ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${RED}❌ Нет интернет соединения${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Интернет доступен${NC}"

################################################################################
# 2. УСТАНОВКА DOCKER И ЗАВИСИМОСТЕЙ
################################################################################

echo -e "\n${YELLOW}📦 Установка Docker и зависимостей...${NC}"

# Обновляем пакеты
apt-get update > /dev/null 2>&1
apt-get upgrade -y > /dev/null 2>&1

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⏳ Установка Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh > /dev/null 2>&1
    sh get-docker.sh > /dev/null 2>&1
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker установлен${NC}"
else
    echo -e "${GREEN}✅ Docker уже установлен${NC}"
fi

# Установка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⏳ Установка Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose > /dev/null 2>&1
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✅ Docker Compose установлен${NC}"
else
    echo -e "${GREEN}✅ Docker Compose уже установлен${NC}"
fi

# Установка Git
if ! command -v git &> /dev/null; then
    apt-get install -y git > /dev/null 2>&1
    echo -e "${GREEN}✅ Git установлен${NC}"
else
    echo -e "${GREEN}✅ Git уже установлен${NC}"
fi

# Установка Certbot (для SSL)
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}⏳ Установка Certbot...${NC}"
    apt-get install -y certbot > /dev/null 2>&1
    echo -e "${GREEN}✅ Certbot установлен${NC}"
else
    echo -e "${GREEN}✅ Certbot уже установлен${NC}"
fi

################################################################################
# 3. КЛОНИРОВАНИЕ ПРОЕКТА
################################################################################

echo -e "\n${YELLOW}📥 Клонирование проекта...${NC}"

if [ -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}⏳ Обновление репозитория...${NC}"
    cd "$PROJECT_DIR"
    git pull origin main > /dev/null 2>&1
    echo -e "${GREEN}✅ Репозиторий обновлен${NC}"
else
    echo -e "${YELLOW}⏳ Клонирование репозитория...${NC}"
    git clone https://github.com/your-username/aircloud_vpn.git "$PROJECT_DIR" > /dev/null 2>&1
    echo -e "${GREEN}✅ Репозиторий клонирован${NC}"
fi

cd "$DOCKER_CONFIGS_DIR"

################################################################################
# 4. ПОЛУЧЕНИЕ SSL СЕРТИФИКАТА
################################################################################

echo -e "\n${YELLOW}🔐 SSL сертификат (Let's Encrypt)...${NC}"

read -p "Домен для SSL сертификата (например nl.vpn.example.com): " DOMAIN

# Проверяем DNS
echo -e "${YELLOW}⏳ Проверяем DNS...${NC}"
if ! nslookup "$DOMAIN" &> /dev/null; then
    echo -e "${YELLOW}⚠️  DNS не разрешается. Убедитесь, что DNS настроен правильно.${NC}"
    read -p "Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Получаем сертификат
if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    echo -e "${YELLOW}⏳ Получаем SSL сертификат...${NC}"
    read -p "Email для трвоги Let's Encrypt: " LETSENCRYPT_EMAIL
    
    certbot certonly --standalone -d "$DOMAIN" --email "$LETSENCRYPT_EMAIL" --agree-tos --non-interactive > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ SSL сертификат получен${NC}"
    else
        echo -e "${RED}❌ Ошибка при получении сертификата${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ SSL сертификат уже существует${NC}"
fi

# Копируем сертификаты
echo -e "${YELLOW}⏳ Копируем сертификаты...${NC}"
mkdir -p nl-server/certs
cp /etc/letsencrypt/live/"$DOMAIN"/fullchain.pem nl-server/certs/
cp /etc/letsencrypt/live/"$DOMAIN"/privkey.pem nl-server/certs/
chmod 644 nl-server/certs/privkey.pem

echo -e "${GREEN}✅ Сертификаты скопированны${NC}"

################################################################################
# 5. СОЗДАНИЕ .ENV ФАЙЛА
################################################################################

echo -e "\n${YELLOW}⚙️  Конфигурация .env...${NC}"

if [ -f .env ]; then
    echo -e "${YELLOW}⏳ Файл .env уже существует${NC}"
    read -p "Переписать? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✅ Пропускаем создание .env${NC}"
    else
        cp .env.example .env
        echo -e "${GREEN}✅ .env переписан из шаблона${NC}"
    fi
else
    cp .env.example .env
    echo -e "${GREEN}✅ .env создан из шаблона${NC}"
fi

# Запрашиваем данные для конфигурации
echo -e "\n${BLUE}Заполните данные для конфигурации:${NC}"

read -p "VK Server IP address: " VK_IP
read -p "NL Server IP address [текущий IP]: " NL_IP
NL_IP=${NL_IP:-$(curl -s https://api.ipify.org)}

read -p "BOT_TOKEN (из .env от VK сервера): " BOT_TOKEN
read -p "YOOKASSA_SHOP_ID (из .env от VK сервера): " YOOKASSA_SHOP_ID
read -p "YOOKASSA_SECRET_KEY (из .env от VK сервера): " YOOKASSA_SECRET_KEY
read -p "ADMIN_ID (Telegram ID админа): " ADMIN_ID

# Обновляем .env
sed -i "s|VK_SERVER=.*|VK_SERVER=${VK_IP}|" .env
sed -i "s|NL_SERVER=.*|NL_SERVER=${NL_IP}|" .env
sed -i "s|NL_DOMAIN=.*|NL_DOMAIN=${DOMAIN}|" .env
sed -i "s|BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|" .env
sed -i "s|YOOKASSA_SHOP_ID=.*|YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}|" .env
sed -i "s|YOOKASSA_SECRET_KEY=.*|YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}|" .env
sed -i "s|ADMIN_IDS=.*|ADMIN_IDS=${ADMIN_ID}|" .env

echo -e "${GREEN}✅ .env обновлен${NC}"

################################################################################
# 6. КОНФИГУРАЦИЯ NL CONFIG.JSON
################################################################################

echo -e "\n${YELLOW}🔧 Конфигурация Xray...${NC}"

# Обновляем serverName в config.json
sed -i "s|nl.vpn.example.com|${DOMAIN}|g" nl-server/config.json

# Обновляем VK адрес
sed -i "s|address\": \"vk-server\"|address\": \"${VK_IP}\"|g" nl-server/config.json

echo -e "${GREEN}✅ Xray конфигурирован${NC}"

################################################################################
# 7. НАСТРОЙКА FIREWALL
################################################################################

echo -e "\n${YELLOW}🔐 Настройка Firewall...${NC}"

if ! command -v ufw &> /dev/null; then
    apt-get install -y ufw > /dev/null 2>&1
fi

ufw default deny incoming > /dev/null 2>&1
ufw default allow outgoing > /dev/null 2>&1
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1
ufw allow 8443/tcp > /dev/null 2>&1
ufw limit 22/tcp > /dev/null 2>&1

# Включаем UFW
echo "y" | ufw enable > /dev/null 2>&1

echo -e "${GREEN}✅ Firewall настроен (порты 22, 443, 8443 открыты)${NC}"

################################################################################
# 8. УСТАНОВКА FAIL2BAN
################################################################################

echo -e "\n${YELLOW}🛡️  Установка Fail2Ban...${NC}"

if ! command -v fail2ban-client &> /dev/null; then
    apt-get install -y fail2ban > /dev/null 2>&1
else
    echo -e "${GREEN}✅ Fail2Ban уже установлен${NC}"
fi

systemctl start fail2ban > /dev/null 2>&1
systemctl enable fail2ban > /dev/null 2>&1

echo -e "${GREEN}✅ Fail2Ban активирован${NC}"

################################################################################
# 9. СБОРКА И ЗАПУСК КОНТЕЙНЕРОВ
################################################################################

echo -e "\n${YELLOW}🐳 Сборка Docker образов...${NC}"

docker-compose build nl-server vpn-bot

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Контейнеры собраны успешно${NC}"
else
    echo -e "${RED}❌ Ошибка при сборке контейнеров${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🚀 Запуск контейнеров...${NC}"

docker-compose up -d nl-server

sleep 5

docker-compose up -d vpn-bot

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Контейнеры запущены${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске контейнеров${NC}"
    exit 1
fi

################################################################################
# 10. ПРОВЕРКА СТАТУСА
################################################################################

echo -e "\n${YELLOW}✅ Проверка статуса...${NC}"

sleep 3

docker-compose ps

echo -e "\n${YELLOW}📋 Проверка логов NL сервера...${NC}"

docker-compose logs nl-server | tail -20

echo -e "\n${YELLOW}📋 Проверка логов бота...${NC}"

docker-compose logs vpn-bot | tail -20

################################################################################
# 11. ПРОВЕРКА КОНФИГА
################################################################################

echo -e "\n${YELLOW}🔍 Проверка конфигурации Xray...${NC}"

docker-compose exec nl-server xray -test -config /etc/xray/config.json

################################################################################
# 12. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ УСТАНОВКА NL СЕРВЕРА ЗАВЕРШЕНА!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}📋 Сохраненная конфигурация:${NC}"
echo -e "${BLUE}VK Server IP:        ${YELLOW}${VK_IP}${NC}"
echo -e "${BLUE}NL Server IP:        ${YELLOW}${NL_IP}${NC}"
echo -e "${BLUE}Domain:              ${YELLOW}${DOMAIN}${NC}"
echo -e "${BLUE}SSL Certificate:     ${YELLOW}✅ Let's Encrypt${NC}"
echo -e "${BLUE}BOT_TOKEN:           ${YELLOW}***СКРЫТО***${NC}"

echo -e "\n${YELLOW}🔗 Полезные команды:${NC}"
echo -e "${BLUE}# Смотреть логи:${NC}"
echo -e "  docker-compose logs -f nl-server"
echo -e "  docker-compose logs -f vpn-bot"
echo -e "\n${BLUE}# Проверить статус:${NC}"
echo -e "  docker-compose ps"
echo -e "\n${BLUE}# Перезапустить:${NC}"
echo -e "  docker-compose restart nl-server"
echo -e "  docker-compose restart vpn-bot"
echo -e "\n${BLUE}# Тестировать конфиг:${NC}"
echo -e "  docker-compose exec nl-server xray -test -config /etc/xray/config.json"

echo -e "\n${YELLOW}📊 Тестирование VPN:${NC}"
echo -e "${BLUE}1. Дождитесь полного запуска бота (см. логи выше)${NC}"
echo -e "${BLUE}2. Отправьте /start боту (${YELLOW}@your_bot${BLUE})${NC}"
echo -e "${BLUE}3. Выберите подписку (single или double tunnel)${NC}"
echo -e "${BLUE}4. Импортируйте конфиг в VPN клиент${NC}"
echo -e "${BLUE}5. Проверьте подключение${NC}"

echo -e "\n${YELLOW}⚠️  ОБНОВЛЕНИЕ SSL СЕРТИФИКАТА:${NC}"
echo -e "${BLUE}Сертификаты автоматически обновляются через Certbot${NC}"
echo -e "${BLUE}Проверить автообновление:${NC}"
echo -e "  certbot renew --dry-run"

echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
