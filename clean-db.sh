#!/bin/bash

echo "🗑️ Очистка базы данных AirCloud VPN"
echo "=================================="

# Останавливаем бота
echo "⏹️ Остановка бота..."
docker-compose stop aircloud-bot

# Удаляем базу данных
echo "🗑️ Удаление базы данных..."
rm -f data/aircloud_vpn.db
rm -f data/*.db
rm -f data/*.sqlite
rm -f data/*.sqlite3

# Удаляем UUID пул и ключи
echo "🗑️ Удаление UUID пула и ключей..."
rm -f data/uuid_pool.txt
rm -f data/public_key.txt
rm -f data/test_user.txt

# Удаляем логи
echo "🗑️ Удаление логов..."
rm -f data/*.log
rm -f *.log

# Показываем что осталось
echo ""
echo "📋 Содержимое папки data:"
ls -la data/ 2>/dev/null || echo "Папка data пуста или не существует"

echo ""
echo "✅ База данных и связанные файлы удалены!"
echo "🚀 Для перезапуска с чистой БД: docker-compose up -d"