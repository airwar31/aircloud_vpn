#!/bin/bash

echo "🔍 ПРОВЕРКА ПОСЛЕ ПЕРЕЗАПУСКА"
echo "============================="

UUID="54ff5eb8-6458-4b61-ba68-26a704929fe4"

echo "1️⃣ Статус Xray:"
systemctl status xray --no-pager -l | head -10

echo ""
echo "2️⃣ Ошибки в логах Xray:"
journalctl -u xray -n 10 --no-pager | grep -i error

echo ""
echo "3️⃣ Пользователь в конфиге:"
if grep -q "$UUID" /usr/local/etc/xray/config.json; then
    echo "✅ Найден в конфиге"
else
    echo "❌ НЕ найден в конфиге"
fi

echo ""
echo "4️⃣ Проверка синтаксиса конфига:"
xray test -config /usr/local/etc/xray/config.json

echo ""
echo "5️⃣ Порт 443:"
netstat -tlnp | grep :443