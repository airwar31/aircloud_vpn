#!/bin/bash

# Скрипт для копирования файлов бота в папку docker-configs/bot

echo "📋 Копирую файлы бота в docker-configs/bot..."

# Копируем основные модули
cp *.py docker-configs/bot/ 2>/dev/null || true

# Копируем requirements
cp requirements.txt docker-configs/bot/ 2>/dev/null || true

# Копируем папки (если есть)
cp -r certs docker-configs/bot/ 2>/dev/null || true

echo "✅ Файлы скопированы!"
echo ""
echo "Содержимое docker-configs/bot/:"
ls -la docker-configs/bot/
