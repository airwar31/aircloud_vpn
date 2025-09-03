#!/bin/bash

echo "🚀 Запуск сервиса автоматической перезагрузки Xray"
echo "================================================="

# Запускаем сервис в фоне
nohup python3 xray_reload_service.py > reload_service.log 2>&1 &

echo "✅ Сервис запущен на порту 9999"
echo "📋 Логи: tail -f reload_service.log"

# Проверяем, что сервис работает
sleep 2
if curl -s http://127.0.0.1:9999/ >/dev/null 2>&1; then
    echo "✅ Сервис доступен"
else
    echo "❌ Сервис недоступен"
fi