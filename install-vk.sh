#!/bin/bash

################################################################################
# 🇷🇺 VK СЕРВЕР - АВТОМАТИЧЕСКАЯ УСТАНОВКА
# Установите бот на вас VK (Russia) сервер
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
echo -e "${GREEN}🚀 VK СЕРВЕР - УСТАНОВКА И КОНФИГУРАЦИЯ${NC}"
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

# Установка Xray (для тестирования ключей)
if ! command -v xray &> /dev/null; then
    echo -e "${YELLOW}⏳ Установка Xray...${NC}"
    bash <(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh) install > /dev/null 2>&1
    echo -e "${GREEN}✅ Xray установлен${NC}"
else
    echo -e "${GREEN}✅ Xray уже установлен${NC}"
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
# 4. ГЕНЕРАЦИЯ REALITY КЛЮЧЕЙ (если нужны)
################################################################################

echo -e "\n${YELLOW}🔑 Reality ключи...${NC}"

read -p "Хотите сгенерировать новые Reality ключи? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏳ Генерируем Reality ключи...${NC}"
    KEYS=$(xray x25519)
    PRIVATE_KEY=$(echo "$KEYS" | grep "Private key:" | awk '{print $NF}')
    PUBLIC_KEY=$(echo "$KEYS" | grep "Public key:" | awk '{print $NF}')
    echo -e "${GREEN}✅ Ключи сгенерированы:${NC}"
    echo -e "${BLUE}Private Key: ${YELLOW}${PRIVATE_KEY}${NC}"
    echo -e "${BLUE}Public Key:  ${YELLOW}${PUBLIC_KEY}${NC}"
else
    echo -e "${YELLOW}⏳ Используйте существующие ключи из .env${NC}"
fi

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

read -p "VK Server IP address [текущий IP]: " VK_IP
VK_IP=${VK_IP:-$(curl -s https://api.ipify.org)}

read -p "NL Server IP address: " NL_IP
read -p "NL Domain (например nl.vpn.example.com): " NL_DOMAIN
read -p "BOT_TOKEN (Telegram Bot Token): " BOT_TOKEN
read -p "YOOKASSA_SHOP_ID: " YOOKASSA_SHOP_ID
read -p "YOOKASSA_SECRET_KEY: " YOOKASSA_SECRET_KEY
read -p "ADMIN_ID (Telegram ID админа): " ADMIN_ID
read -p "VK_PRIVATE_KEY (Real Reality ключ): " VK_PRIVATE_KEY

# Обновляем .env
sed -i "s|VK_SERVER=.*|VK_SERVER=${VK_IP}|" .env
sed -i "s|NL_SERVER=.*|NL_SERVER=${NL_IP}|" .env
sed -i "s|NL_DOMAIN=.*|NL_DOMAIN=${NL_DOMAIN}|" .env
sed -i "s|BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|" .env
sed -i "s|YOOKASSA_SHOP_ID=.*|YOOKASSA_SHOP_ID=${YOOKASSA_SHOP_ID}|" .env
sed -i "s|YOOKASSA_SECRET_KEY=.*|YOOKASSA_SECRET_KEY=${YOOKASSA_SECRET_KEY}|" .env
sed -i "s|ADMIN_IDS=.*|ADMIN_IDS=${ADMIN_ID}|" .env
sed -i "s|VK_PRIVATE_KEY=.*|VK_PRIVATE_KEY=${VK_PRIVATE_KEY}|" .env

echo -e "${GREEN}✅ .env обновлен${NC}"

################################################################################
# 6. КОНФИГУРАЦИЯ XRAY
################################################################################

echo -e "\n${YELLOW}🔧 Конфигурация Xray...${NC}"

# Генерируем UUID если нужны новые
read -p "Хотите использовать существующие UUID или сгенерировать новые? (new/existing): " UUID_CHOICE

if [[ "$UUID_CHOICE" == "new" ]]; then
    UUID_DOUBLE=$(uuidgen | tr '[:upper:]' '[:lower:]')
    UUID_SINGLE=$(uuidgen | tr '[:upper:]' '[:lower:]')
    echo -e "${GREEN}✅ UUID сгенерированы:${NC}"
    echo -e "${BLUE}UUID_DOUBLE: ${YELLOW}${UUID_DOUBLE}${NC}"
    echo -e "${BLUE}UUID_SINGLE: ${YELLOW}${UUID_SINGLE}${NC}"
    
    sed -i "s|REPLACE_WITH_UUID_DOUBLE|${UUID_DOUBLE}|g" vk-server/config.json
    sed -i "s|REPLACE_WITH_UUID_SINGLE|${UUID_SINGLE}|g" vk-server/config.json
    sed -i "s|REPLACE_WITH_UUID_DOUBLE|${UUID_DOUBLE}|g" nl-server/config.json
    sed -i "s|REPLACE_WITH_UUID_SINGLE|${UUID_SINGLE}|g" nl-server/config.json
    
    # Сохраняем в .env
    sed -i "s|UUID_DOUBLE=.*|UUID_DOUBLE=${UUID_DOUBLE}|" .env
    sed -i "s|UUID_SINGLE=.*|UUID_SINGLE=${UUID_SINGLE}|" .env
else
    echo -e "${YELLOW}⏳ Используйте UUID из .env${NC}"
fi

# Обновляем Private Key в config
sed -i "s|REPLACE_WITH_PRIVATE_KEY|${VK_PRIVATE_KEY}|g" vk-server/config.json
sed -i "s|nl-server|${NL_IP}|g" vk-server/config.json

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
ufw limit 22/tcp > /dev/null 2>&1

# Включаем UFW
echo "y" | ufw enable > /dev/null 2>&1

echo -e "${GREEN}✅ Firewall настроен (порты 22, 443 открыты)${NC}"

################################################################################
# 8. УСТАНОВKA FAIL2BAN
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

docker-compose build vk-server

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ VK контейнер собран успешно${NC}"
else
    echo -e "${RED}❌ Ошибка при сборке VK контейнера${NC}"
    exit 1
fi

echo -e "\n${YELLOW}🚀 Запуск контейнеров...${NC}"

docker-compose up -d vk-server

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ VK сервер запущен${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске VK сервера${NC}"
    exit 1
fi

################################################################################
# 10. ПРОВЕРКА СТАТУСА
################################################################################

echo -e "\n${YELLOW}✅ Проверка статуса...${NC}"

sleep 3

docker-compose ps

echo -e "\n${YELLOW}📋 Проверка логов...${NC}"

docker-compose logs vk-server | tail -20

################################################################################
# 11. ФИНАЛЬНАЯ ИНФОРМАЦИЯ
################################################################################

echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ УСТАНОВКА VK СЕРВЕРА ЗАВЕРШЕНА!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}📋 Сохраненная конфигурация:${NC}"
echo -e "${BLUE}VK Server IP:        ${YELLOW}${VK_IP}${NC}"
echo -e "${BLUE}NL Server IP:        ${YELLOW}${NL_IP}${NC}"
echo -e "${BLUE}NL Domain:           ${YELLOW}${NL_DOMAIN}${NC}"
echo -e "${BLUE}BOT_TOKEN:           ${YELLOW}***СКРЫТО***${NC}"
echo -e "${BLUE}VK_PRIVATE_KEY:      ${YELLOW}***СКРЫТО***${NC}"

echo -e "\n${YELLOW}🔗 Полезные команды:${NC}"
echo -e "${BLUE}# Смотреть логи:${NC}"
echo -e "  docker-compose logs -f vk-server"
echo -e "\n${BLUE}# Проверить статус:${NC}"
echo -e "  docker-compose ps"
echo -e "\n${BLUE}# Перезапустить сервер:${NC}"
echo -e "  docker-compose restart vk-server"
echo -e "\n${BLUE}# Тестировать конфиг:${NC}"
echo -e "  docker-compose exec vk-server xray -test -config /etc/xray/config.json"

echo -e "\n${YELLOW}⚠️  СЛЕДУЮЩИЕ ШАГИ:${NC}"
echo -e "${BLUE}1. Установите NL сервер, используя install-nl.sh${NC}"
echo -e "${BLUE}2. Передайте ${YELLOW}VK_PUBLIC_KEY${BLUE} на NL сервер${NC}"
echo -e "${BLUE}3. Проверьте подключение на NL сервере${NC}"

echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
