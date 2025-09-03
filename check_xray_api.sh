#!/bin/bash

echo "🔍 ПРОВЕРКА XRAY API КОМАНД"
echo "=========================="

echo "📋 Доступные команды xray api:"
xray help api

echo ""
echo "🧪 Тест добавления пользователя:"
echo '{"id":"test-uuid","email":"test@test.com","flow":"xtls-rprx-vision"}' | xray api adi vless-in

echo ""
echo "📊 Список пользователей:"
xray api inbounduser vless-in