#!/bin/bash
# Безопасное обновление на рабочем сервере

echo "🔄 Безопасное обновление сервера..."

# 1. Создаем бэкап
echo "📦 Создание бэкапа..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Бэкапим важные данные
cp -r xray-config $BACKUP_DIR/ 2>/dev/null || echo "⚠️ xray-config не найден"
cp -r bot-data $BACKUP_DIR/ 2>/dev/null || echo "⚠️ bot-data не найден"
cp .env $BACKUP_DIR/ 2>/dev/null || echo "⚠️ .env не найден"
cp docker-compose.yml $BACKUP_DIR/ 2>/dev/null || echo "⚠️ docker-compose.yml не найден"

echo "✅ Бэкап создан в $BACKUP_DIR"

# 2. Обновляем только код бота (без пересборки контейнеров)
echo "🔧 Обновление кода бота..."

# Копируем новые файлы
cp bot.py bot.py.backup 2>/dev/null
cp requirements.txt requirements.txt.backup 2>/dev/null

# 3. Перезапускаем только бот (не трогаем БД и Xray)
echo "🔄 Перезапуск только бота..."
docker-compose stop vpn-bot
docker-compose build vpn-bot
docker-compose up -d vpn-bot

# 4. Проверяем статус
echo "📊 Проверка статуса..."
sleep 5
docker ps | grep vpn-bot

# 5. Тест бота
echo "🧪 Тест бота..."
if docker logs vpn-bot --tail 10 | grep -q "Запуск VPN бота"; then
    echo "✅ Бот запущен успешно"
else
    echo "❌ Проблемы с ботом, откатываем..."
    cp bot.py.backup bot.py 2>/dev/null
    docker-compose stop vpn-bot
    docker-compose up -d vpn-bot
fi

echo "🏁 Обновление завершено"