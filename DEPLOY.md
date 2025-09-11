# 🚀 Инструкция по развертыванию VPN бота

## 📋 Подготовка сервера

### 1. Обновление системы (Ubuntu/Debian)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git nginx -y
```

### 2. Создание пользователя для бота
```bash
sudo useradd -m -s /bin/bash vpnbot
sudo usermod -aG sudo vpnbot
su - vpnbot
```

## 📦 Установка бота

### 1. Клонирование репозитория
```bash
cd /home/vpnbot
git clone <your-repository-url> vpn-bot
cd vpn-bot
```

### 2. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настройка конфигурации
```bash
cp .env.example .env
nano .env
```

Заполните все необходимые переменные:
```env
BOT_TOKEN=your_telegram_bot_token
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
X_UI_URL=http://localhost:54321
X_UI_USERNAME=admin
X_UI_PASSWORD=your_password
```

## 🔧 Настройка X-UI панели

### 1. Установка X-UI (если еще не установлена)
```bash
bash <(curl -Ls https://raw.githubusercontent.com/vaxilu/x-ui/master/install.sh)
```

### 2. Настройка inbound'а
1. Откройте веб-панель X-UI: `http://your-server-ip:54321`
2. Войдите с учетными данными
3. Создайте inbound с протоколом VLESS или VMess
4. Убедитесь, что inbound активен

## 🤖 Настройка systemd сервиса

### 1. Копирование файла сервиса
```bash
sudo cp vpn-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/vpn-bot.service
```

Отредактируйте пути в файле:
```ini
WorkingDirectory=/home/vpnbot/vpn-bot
ExecStart=/home/vpnbot/vpn-bot/venv/bin/python /home/vpnbot/vpn-bot/run.py
```

### 2. Запуск сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable vpn-bot
sudo systemctl start vpn-bot
sudo systemctl status vpn-bot
```

## 🌐 Настройка Nginx (для webhook)

### 1. Создание конфигурации Nginx
```bash
sudo nano /etc/nginx/sites-available/vpn-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /yookassa/webhook {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Активация конфигурации
```bash
sudo ln -s /etc/nginx/sites-available/vpn-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Установка SSL сертификата (рекомендуется)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

## 🔗 Настройка webhook в ЮKassa

### 1. Запуск webhook сервера
```bash
cd /home/vpnbot/vpn-bot
source venv/bin/activate
gunicorn -w 4 -b 127.0.0.1:5000 webhook:app --daemon
```

### 2. Настройка webhook в личном кабинете ЮKassa
1. Войдите в личный кабинет ЮKassa
2. Перейдите в раздел "Настройки" → "Уведомления"
3. Добавьте URL: `https://your-domain.com/yookassa/webhook`
4. Выберите события: `payment.succeeded`

## 📊 Мониторинг и логи

### 1. Просмотр логов бота
```bash
sudo journalctl -u vpn-bot -f
```

### 2. Просмотр статистики
```bash
cd /home/vpnbot/vpn-bot
source venv/bin/activate
python admin.py all
```

### 3. Очистка истекших ключей (добавить в cron)
```bash
crontab -e
```

Добавить строку:
```
0 2 * * * /home/vpnbot/vpn-bot/venv/bin/python /home/vpnbot/vpn-bot/admin.py cleanup
```

## 🔒 Безопасность

### 1. Настройка файрвола
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 54321  # X-UI панель
sudo ufw enable
```

### 2. Ограничение доступа к X-UI
Рекомендуется настроить доступ к X-UI панели только с определенных IP адресов.

### 3. Регулярные обновления
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Обновление зависимостей Python
cd /home/vpnbot/vpn-bot
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## 🐛 Решение проблем

### Бот не запускается
```bash
# Проверка статуса
sudo systemctl status vpn-bot

# Просмотр логов
sudo journalctl -u vpn-bot -n 50

# Перезапуск
sudo systemctl restart vpn-bot
```

### Ошибки подключения к X-UI
```bash
# Проверка доступности X-UI
curl http://localhost:54321

# Проверка логов X-UI
sudo journalctl -u x-ui -n 50
```

### Проблемы с webhook
```bash
# Проверка работы Flask приложения
curl http://localhost:5000/health

# Проверка конфигурации Nginx
sudo nginx -t
```

## 📈 Масштабирование

### Для высоких нагрузок:
1. Используйте PostgreSQL вместо SQLite
2. Настройте Redis для кеширования
3. Используйте несколько инстансов бота с балансировщиком нагрузки
4. Мониторьте производительность с помощью Prometheus + Grafana

### Резервное копирование:
```bash
# Создание бэкапа базы данных
cp /home/vpnbot/vpn-bot/vpn_bot.db /backup/vpn_bot_$(date +%Y%m%d_%H%M%S).db

# Автоматическое резервное копирование (добавить в cron)
0 3 * * * cp /home/vpnbot/vpn-bot/vpn_bot.db /backup/vpn_bot_$(date +\%Y\%m\%d_\%H\%M\%S).db
```

## ✅ Проверка работоспособности

1. Отправьте `/start` боту в Telegram
2. Выберите тарифный план
3. Проведите тестовый платеж
4. Убедитесь, что VPN ключ создается корректно
5. Проверьте подключение с помощью созданного ключа

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи всех сервисов
2. Убедитесь в правильности конфигурации
3. Проверьте доступность всех внешних сервисов (ЮKassa, Telegram API, X-UI)
4. Обратитесь к документации соответствующих сервисов