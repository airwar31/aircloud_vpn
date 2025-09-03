#!/bin/bash

echo "🔄 Перезагрузка Xray после добавления пользователей"
echo "================================================="

# Проверяем статус
echo "📊 Текущий статус Xray:"
systemctl status xray --no-pager -l | head -5

echo ""
echo "🔄 Перезагружаем Xray..."
systemctl reload xray

sleep 2

echo ""
echo "✅ Новый статус:"
systemctl status xray --no-pager -l | head -5

echo ""
echo "👥 Проверяем пользователей в конфиге:"
grep -c '"email"' /usr/local/etc/xray/config.json
echo "Всего пользователей в конфиге"