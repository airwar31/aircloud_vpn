#!/bin/bash

# Скрипт подготовки файлов для развертывания на серверы
# Копирует файлы из корня проекта в структуру docker-configs

set -e  # Выход при ошибке

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Подготовка файлов для развертывания Docker контейнеров   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Переменные путей
DOCKER_CONFIG_DIR="docker-configs"
VK_SERVER_DIR="${DOCKER_CONFIG_DIR}/vk-server"
NL_SERVER_DIR="${DOCKER_CONFIG_DIR}/nl-server"
NL_BOT_APP_DIR="${NL_SERVER_DIR}/bot_app"
VK_CORE_VPN_DIR="${VK_SERVER_DIR}/core_vpn"

# Проверяем наличие docker-configs
if [ ! -d "${DOCKER_CONFIG_DIR}" ]; then
    echo -e "${RED}❌ Ошибка: директория ${DOCKER_CONFIG_DIR} не найдена${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Начинаем копирование файлов...${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# VK СЕРВЕР (Россия) - Xray маршрутизатор
# ═══════════════════════════════════════════════════════════════

echo -e "${BLUE}[1/2] VK Сервер (Россия)${NC}"
echo "─────────────────────────────────────────────────────────"

# Создаем директорию если не существует
mkdir -p "${VK_CORE_VPN_DIR}"

# Проверяем наличие файлов
if [ ! -f "xray_manager.py" ]; then
    echo -e "${YELLOW}⚠️  xray_manager.py не найден в корне${NC}"
else
    cp -v xray_manager.py "${VK_CORE_VPN_DIR}/"
    echo -e "${GREEN}✅ xray_manager.py${NC}"
fi

if [ ! -f "xray_api.py" ]; then
    echo -e "${YELLOW}⚠️  xray_api.py не найден в корне${NC}"
else
    cp -v xray_api.py "${VK_CORE_VPN_DIR}/"
    echo -e "${GREEN}✅ xray_api.py${NC}"
fi

if [ ! -f "xray_api_fixed.py" ]; then
    echo -e "${YELLOW}⚠️  xray_api_fixed.py не найден в корне${NC}"
else
    cp -v xray_api_fixed.py "${VK_CORE_VPN_DIR}/"
    echo -e "${GREEN}✅ xray_api_fixed.py${NC}"
fi

echo ""
echo -e "${GREEN}✓ VK сервер готов (Xray файлы скопированы)${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# NL СЕРВЕР (Нидерланды) - Xray выход + Telegram Bot
# ═══════════════════════════════════════════════════════════════

echo -e "${BLUE}[2/2] NL Сервер (Нидерланды) - 📌 TELEGRAM BOT${NC}"
echo "─────────────────────────────────────────────────────────"

# Создаем директорию если не существует
mkdir -p "${NL_BOT_APP_DIR}"

# Основные файлы бота
BOT_FILES=(
    "vpn_bot.py"
    "bot.py"
    "admin_panel.py"
    "admin.py"
    "admin_methods.py"
    "webhook.py"
    "notify_expiring.py"
)

# Конфиг и БД
CONFIG_FILES=(
    "config.py"
    "database.py"
)

# Утилиты туннелей
TUNNEL_FILES=(
    "tunnel_manager.py"
    "xray_double_tunnel.py"
    "double_tunnel_utils.py"
    "double_tunnel_docs.py"
)

# Дополнительные утилиты
UTIL_FILES=(
    "sync_keys.py"
    "monitoring.py"
    "user_agreement.txt"
)

# Копируем файлы бота
echo -e "${YELLOW}📝 Копируем основные файлы бота:${NC}"
for file in "${BOT_FILES[@]}"; do
    if [ ! -f "${file}" ]; then
        echo -e "${RED}   ❌ ${file} не найден${NC}"
    else
        cp -v "${file}" "${NL_BOT_APP_DIR}/"
        echo -e "${GREEN}   ✅ ${file}${NC}"
    fi
done

echo ""
echo -e "${YELLOW}⚙️  Копируем конфигурацию и БД:${NC}"
for file in "${CONFIG_FILES[@]}"; do
    if [ ! -f "${file}" ]; then
        echo -e "${RED}   ❌ ${file} не найден${NC}"
    else
        cp -v "${file}" "${NL_BOT_APP_DIR}/"
        echo -e "${GREEN}   ✅ ${file}${NC}"
    fi
done

echo ""
echo -e "${YELLOW}🔗 Копируем утилиты туннелей:${NC}"
for file in "${TUNNEL_FILES[@]}"; do
    if [ ! -f "${file}" ]; then
        echo -e "${RED}   ❌ ${file} не найден${NC}"
    else
        cp -v "${file}" "${NL_BOT_APP_DIR}/"
        echo -e "${GREEN}   ✅ ${file}${NC}"
    fi
done

echo ""
echo -e "${YELLOW}🛠️  Копируем дополнительные утилиты:${NC}"
for file in "${UTIL_FILES[@]}"; do
    if [ ! -f "${file}" ]; then
        echo -e "${RED}   ❌ ${file} не найден${NC}"
    else
        cp -v "${file}" "${NL_BOT_APP_DIR}/"
        echo -e "${GREEN}   ✅ ${file}${NC}"
    fi
done

echo ""
echo -e "${GREEN}✓ NL сервер готов (BOT файлы скопированы)${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# Итоговая информация
# ═══════════════════════════════════════════════════════════════

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            ✅ Подготовка завершена успешно!              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Структура проекта:${NC}"
echo ""
echo "docker-configs/"
echo "├── vk-server/               ← Сервер России (маршрутизатор трафика)"
echo "│   ├── Dockerfile"
echo "│   ├── config.json          (443→forward, 8443→direct)"
echo "│   └── core_vpn/"
echo "│       ├── xray_manager.py   ✓ Скопировано"
echo "│       ├── xray_api.py       ✓ Скопировано"
echo "│       └── xray_api_fixed.py ✓ Скопировано"
echo ""
echo "└── nl-server/               ← Сервер Нидерландов (BOT + выход)"
echo "    ├── Dockerfile"
echo "    ├── config.json          (TLS на :443)"
echo "    ├── entrypoint.sh"
echo "    ├── requirements.txt"
echo "    └── bot_app/             📌 TELEGRAM BOT"
echo "        ├── vpn_bot.py        ✓ Скопировано"
echo "        ├── bot.py            ✓ Скопировано"
echo "        ├── admin_panel.py    ✓ Скопировано"
echo "        ├── admin.py          ✓ Скопировано"
echo "        ├── admin_methods.py  ✓ Скопировано"
echo "        ├── webhook.py        ✓ Скопировано"
echo "        ├── notify_expiring.py ✓ Скопировано"
echo "        ├── config.py         ✓ Скопировано"
echo "        ├── database.py       ✓ Скопировано"
echo "        ├── tunnel_manager.py ✓ Скопировано"
echo "        ├── xray_double_tunnel.py ✓ Скопировано"
echo "        ├── double_tunnel_utils.py ✓ Скопировано"
echo "        ├── sync_keys.py      ✓ Скопировано"
echo "        ├── monitoring.py     ✓ Скопировано"
echo "        └── user_agreement.txt ✓ Скопировано"
echo ""

echo -e "${BLUE}🚀 Следующие шаги:${NC}"
echo ""
echo "1. Перейти в docker-configs:"
echo "   ${YELLOW}cd docker-configs${NC}"
echo ""
echo "2. Создать .env файл:"
echo "   ${YELLOW}cp .env.example .env${NC}"
echo "   ${YELLOW}nano .env${NC}"
echo ""
echo "3. Заполнить переменные окружения:"
echo "   ${YELLOW}BOT_TOKEN${NC} = Токен от @BotFather"
echo "   ${YELLOW}YOOKASSA_SHOP_ID${NC} = ID магазина YooKassa"
echo "   ${YELLOW}YOOKASSA_API_KEY${NC} = API ключ YooKassa"
echo "   ${YELLOW}VK_PRIVATE_KEY${NC} = Ключ от: xray x25519"
echo "   ${YELLOW}VK_PUBLIC_KEY${NC} = Публичный ключ"
echo "   ${YELLOW}NL_DOMAIN${NC} = Домен сервера NL (для SSL)"
echo ""
echo "4. Собрать Docker образы:"
echo "   ${YELLOW}docker-compose build${NC}"
echo ""
echo "5. Запустить контейнеры:"
echo "   ${YELLOW}docker-compose up -d${NC}"
echo ""
echo "6. Проверить статус:"
echo "   ${YELLOW}docker-compose ps${NC}"
echo ""
echo "7. Смотреть логи:"
echo "   ${YELLOW}docker-compose logs -f nl-server${NC}"
echo ""

echo -e "${GREEN}✨ Готово к развертыванию!${NC}"
echo ""
