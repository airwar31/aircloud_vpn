#!/bin/bash
# Проверка сохранности данных после обновления

echo "🔍 Проверка сохранности данных..."

# 1. Проверяем Docker volumes
echo "📁 Docker volumes:"
docker volume ls | grep -E "(xray-config|bot-data)"

# 2. Проверяем контейнеры
echo "🐳 Статус контейнеров:"
docker-compose ps

# 3. Проверяем подключение к БД
echo "🗄️ Тест подключения к MySQL:"
docker-compose exec vpn-bot python -c "
from database_mysql import db
try:
    stats = db.get_stats()
    print(f'✅ БД работает: {stats.get(\"total_users\", 0)} пользователей')
except Exception as e:
    print(f'❌ Ошибка БД: {e}')
" 2>/dev/null || echo "⚠️ Не удалось проверить БД"

# 4. Проверяем Xray API
echo "🔗 Тест Xray API:"
curl -s http://localhost:8080/health | grep -q "healthy" && echo "✅ Xray API работает" || echo "❌ Xray API недоступен"

# 5. Проверяем логи бота
echo "📝 Последние логи бота:"
docker logs vpn-bot --tail 5

echo "🏁 Проверка завершена"