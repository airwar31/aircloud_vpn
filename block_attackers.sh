#!/bin/bash
# Блокировка атакующих IP адресов

echo "🛡️ Блокировка атакующих IP..."

# Список атакующих IP из логов
ATTACK_IPS=(
    "90.151.171.108"
    "90.151.171.106" 
    "196.251.81.30"
    "185.242.226.58"
    "96.126.104.20"
    "199.45.155.66"
    "167.94.138.206"
    "167.94.145.99"
)

# Блокируем каждый IP
for ip in "${ATTACK_IPS[@]}"; do
    echo "🚫 Блокируем $ip"
    iptables -I INPUT -s $ip -j DROP 2>/dev/null || echo "⚠️ Не удалось заблокировать $ip"
done

# Ограничиваем подключения к портам
echo "🔒 Настройка ограничений подключений..."
iptables -A INPUT -p tcp --dport 8080 -m connlimit --connlimit-above 10 -j DROP 2>/dev/null
iptables -A INPUT -p tcp --dport 8444 -m connlimit --connlimit-above 50 -j DROP 2>/dev/null

# Блокируем подозрительные запросы
echo "🔍 Блокировка подозрительных запросов..."
iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP 2>/dev/null
iptables -A INPUT -p tcp ! --syn -m state --state NEW -j DROP 2>/dev/null

echo "✅ Блокировка завершена"
echo "📊 Текущие правила:"
iptables -L INPUT -n | head -20