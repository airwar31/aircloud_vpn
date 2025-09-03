#!/bin/bash

echo "🚀 ПОЛНЫЙ ЗАПУСК AIRCLOUD VPN"
echo "============================="

# 1. Остановить всё
echo "1️⃣ Остановка старых процессов..."
docker-compose down 2>/dev/null
pkill -f xray_reload_service 2>/dev/null
pkill -f xray_user_service 2>/dev/null

# 2. Запуск Xray (если не запущен)
echo "2️⃣ Проверка Xray..."
if ! systemctl is-active --quiet xray; then
    systemctl start xray
    echo "✅ Xray запущен"
else
    echo "✅ Xray уже работает"
fi

# 3. Запуск сервиса перезагрузки
echo "3️⃣ Запуск сервиса перезагрузки..."
nohup python3 xray_reload_service.py > reload.log 2>&1 &
sleep 2

# Проверка сервиса
if curl -s http://127.0.0.1:9998/ >/dev/null 2>&1; then
    echo "✅ Сервис перезагрузки работает"
else
    echo "❌ Сервис перезагрузки не запустился"
fi

# 4. Запуск бота
echo "4️⃣ Запуск бота..."
docker-compose up -d --build

# 5. Проверка статуса
echo "5️⃣ Проверка статуса..."
sleep 3

echo ""
echo "📊 СТАТУС СЕРВИСОВ:"
echo "==================="
echo "Xray: $(systemctl is-active xray)"
echo "Бот: $(docker-compose ps --services --filter status=running)"
echo "Сервис перезагрузки: $(curl -s http://127.0.0.1:9998/ >/dev/null 2>&1 && echo 'работает' || echo 'не работает')"

echo ""
echo "📋 ЛОГИ:"
echo "========"
echo "Бот: docker-compose logs -f aircloud-bot"
echo "Xray: journalctl -u xray -f"
echo "Сервис: tail -f reload.log"