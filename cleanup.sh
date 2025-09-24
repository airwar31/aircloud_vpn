#!/bin/bash

# Скрипт очистки VPN системы
# Удаляет всех клиентов из Xray и очищает базу данных

echo "🧹 Скрипт очистки VPN системы"
echo "⚠️  ВНИМАНИЕ: Это действие удалит ВСЕ данные!"

# Проверка наличия Python скрипта
if [ ! -f "cleanup.py" ]; then
    echo "❌ Файл cleanup.py не найден!"
    exit 1
fi

# Запрос подтверждения
read -p "Вы уверены? Введите 'YES' для подтверждения: " confirm
if [ "$confirm" != "YES" ]; then
    echo "❌ Очистка отменена"
    exit 0
fi

# Дополнительное подтверждение
read -p "Последнее предупреждение! Введите 'CONFIRM' для продолжения: " confirm2
if [ "$confirm2" != "CONFIRM" ]; then
    echo "❌ Очистка отменена"
    exit 0
fi

echo "🚀 Запуск очистки..."

# Запуск Python скрипта
if python3 cleanup.py; then
    echo "✅ Очистка завершена успешно!"
else
    echo "❌ Ошибка при выполнении очистки"
    exit 1
fi