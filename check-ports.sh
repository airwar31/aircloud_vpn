#!/bin/bash

echo "🔍 Проверка портов и сети"
echo "========================"

# Проверяем что порт 443 открыт
echo "📡 Проверка порта 443:"
netstat -tulpn | grep :443 || echo "Порт 443 не слушается"

# Проверяем IP forwarding
echo ""
echo "🌐 IP forwarding:"
cat /proc/sys/net/ipv4/ip_forward

# Проверяем firewall
echo ""
echo "🔥 Firewall (ufw):"
ufw status || echo "ufw не установлен"

echo ""
echo "🔥 Firewall (iptables):"
iptables -L INPUT | head -5

# Открываем порт 443 если нужно
echo ""
echo "🔓 Открываем порт 443..."
ufw allow 443/tcp 2>/dev/null || echo "ufw недоступен"
iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || echo "iptables недоступен"

# Включаем IP forwarding
echo ""
echo "🔄 Включаем IP forwarding..."
echo 1 > /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo "Нет прав для изменения"

echo ""
echo "✅ Проверка завершена"