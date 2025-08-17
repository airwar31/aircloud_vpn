#!/bin/bash

echo "⏰ Настройка автоматического продления SSL"
echo "========================================"

# Создаем скрипт автопродления
cat > /usr/local/bin/aircloud-ssl-renew.sh << 'EOF'
#!/bin/bash

# Логирование
LOG_FILE="/var/log/aircloud-ssl-renew.log"
echo "$(date): Начало проверки сертификатов" >> $LOG_FILE

# Продление сертификатов
certbot renew --quiet >> $LOG_FILE 2>&1

# Проверяем успешность
if [ $? -eq 0 ]; then
    echo "$(date): Сертификаты проверены/обновлены" >> $LOG_FILE
    
    # Копируем сертификаты в проект
    DOMAIN="yourdomain.com"  # Замените на ваш домен
    PROJECT_DIR="/root/aircloud-vpn"
    
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $PROJECT_DIR/ssl/cert.pem
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $PROJECT_DIR/ssl/private.key
        chmod 644 $PROJECT_DIR/ssl/cert.pem
        chmod 600 $PROJECT_DIR/ssl/private.key
        
        # Перезапускаем сервисы
        cd $PROJECT_DIR
        docker-compose restart nginx
        systemctl reload xray
        
        echo "$(date): Сервисы перезапущены" >> $LOG_FILE
    fi
else
    echo "$(date): ОШИБКА при обновлении сертификатов" >> $LOG_FILE
fi
EOF

# Делаем скрипт исполняемым
chmod +x /usr/local/bin/aircloud-ssl-renew.sh

# Добавляем в crontab (проверка каждый день в 3:00)
echo "📅 Настройка cron задачи..."
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/local/bin/aircloud-ssl-renew.sh") | crontab -

# Добавляем в systemd timer (альтернатива cron)
cat > /etc/systemd/system/aircloud-ssl-renew.service << EOF
[Unit]
Description=AirCloud SSL Certificate Renewal
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/aircloud-ssl-renew.sh
User=root
EOF

cat > /etc/systemd/system/aircloud-ssl-renew.timer << EOF
[Unit]
Description=Run AirCloud SSL renewal daily
Requires=aircloud-ssl-renew.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Активируем systemd timer
systemctl daemon-reload
systemctl enable aircloud-ssl-renew.timer
systemctl start aircloud-ssl-renew.timer

echo ""
echo "✅ Автоматическое продление настроено!"
echo ""
echo "📋 Настроено:"
echo "• Cron задача: каждый день в 3:00"
echo "• Systemd timer: ежедневно"
echo "• Логи: /var/log/aircloud-ssl-renew.log"
echo ""
echo "🔍 Проверка статуса:"
echo "• crontab -l"
echo "• systemctl status aircloud-ssl-renew.timer"
echo "• tail -f /var/log/aircloud-ssl-renew.log"
echo ""
echo "🧪 Тестовый запуск:"
echo "/usr/local/bin/aircloud-ssl-renew.sh"