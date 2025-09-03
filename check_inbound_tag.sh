#!/bin/bash

echo "🔍 ПРОВЕРКА ТЕГА INBOUND"
echo "======================="

CONFIG_PATH="/usr/local/etc/xray/config.json"

if [ -f "$CONFIG_PATH" ]; then
    echo "📋 Найденные теги inbound:"
    grep -o '"tag"[[:space:]]*:[[:space:]]*"[^"]*"' "$CONFIG_PATH"
    
    echo ""
    echo "🎯 Правильный тег для использования:"
    grep -A 5 -B 5 '"protocol"[[:space:]]*:[[:space:]]*"vless"' "$CONFIG_PATH" | grep '"tag"'
else
    echo "❌ Конфиг не найден: $CONFIG_PATH"
fi