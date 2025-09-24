#!/bin/bash
# Горячее исправление YooKassa без перезапуска всех сервисов

echo "🔥 Горячее исправление YooKassa..."

# 1. Бэкап текущего бота
cp bot.py bot.py.old

# 2. Применяем только исправление YooKassa (уже в файле)
echo "✅ Исправление YooKassa уже применено в bot.py"

# 3. Перезапускаем только контейнер бота
echo "🔄 Перезапуск бота..."
docker-compose restart vpn-bot

# 4. Блокируем атакующие IP
echo "🛡️ Блокировка атак..."
ATTACK_IPS=("90.151.171.108" "90.151.171.106" "196.251.81.30")
for ip in "${ATTACK_IPS[@]}"; do
    iptables -I INPUT -s $ip -j DROP 2>/dev/null && echo "🚫 Заблокирован $ip"
done

# 5. Проверяем статус
echo "📊 Статус сервисов:"
docker-compose ps

echo "✅ Горячее исправление завершено"