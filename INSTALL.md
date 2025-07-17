# Инструкция по установке AirCloud VPN на базе Xray

## Требования
- Сервер с Ubuntu 20.04 или новее
- Доменное имя (опционально)
- Открытый порт 443 (или другой порт, который вы хотите использовать)

## Шаг 1: Установка Xray

```bash
# Обновляем систему
sudo apt update
sudo apt upgrade -y

# Устанавливаем необходимые пакеты
sudo apt install -y curl socat jq

# Устанавливаем Xray
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

# Создаем директории для логов и конфигурации
sudo mkdir -p /var/log/xray
sudo mkdir -p /etc/xray
sudo chown -R nobody:nogroup /var/log/xray
```

## Шаг 2: Настройка Xray

```bash
# Копируем шаблон конфигурации
sudo cp config.template.json /etc/xray/config.template.json

# Создаем пустой файл конфигурации
sudo touch /etc/xray/config.json
sudo chown nobody:nogroup /etc/xray/config.json
```

## Шаг 3: Установка Python и зависимостей

```bash
# Устанавливаем Python и pip
sudo apt install -y python3 python3-pip python3-venv

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

## Шаг 4: Настройка базы данных

```bash
# Инициализируем базу данных
python create_db.py
```

## Шаг 5: Настройка файла .env

```bash
# Копируем пример файла .env
cp .env.example .env

# Редактируем файл .env
nano .env
```

Заполните следующие параметры в файле .env:
- BOT_TOKEN - токен вашего Telegram бота (получите у @BotFather)
- VPN_SERVER_ADDRESS - IP-адрес или домен вашего сервера
- ADMIN_IDS - список ID администраторов (через запятую)
- YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY (если используете ЮKassa)

## Шаг 6: Настройка Reality для Xray

```bash
# Активируем виртуальное окружение, если оно не активировано
source venv/bin/activate

# Запускаем скрипт для настройки Reality
python -c "import asyncio; from xray_api import XrayAPI; asyncio.run(XrayAPI().setup_reality())"
```

## Шаг 7: Настройка systemd для автозапуска бота

Создайте файл службы systemd:

```bash
sudo nano /etc/systemd/system/aircloud-vpn.service
```

Добавьте следующее содержимое:

```ini
[Unit]
Description=AirCloud VPN Telegram Bot
After=network.target xray.service

[Service]
Type=simple
User=nobody
Group=nogroup
WorkingDirectory=/path/to/aircloud_vpn
ExecStart=/path/to/aircloud_vpn/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Замените `/path/to/aircloud_vpn` на фактический путь к директории проекта.

Активируйте и запустите службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aircloud-vpn
sudo systemctl start aircloud-vpn
```

## Шаг 8: Проверка работы

```bash
# Проверяем статус Xray
sudo systemctl status xray

# Проверяем статус бота
sudo systemctl status aircloud-vpn

# Проверяем логи Xray
sudo journalctl -u xray -f

# Проверяем логи бота
sudo journalctl -u aircloud-vpn -f
```

## Настройка для работы с веб-хуками (опционально)

Если вы хотите использовать веб-хуки вместо long polling, вам потребуется:

1. Настроить Nginx или другой веб-сервер
2. Получить SSL-сертификат (например, с помощью Let's Encrypt)
3. Изменить метод запуска бота в файле main.py с `main()` на `main_webhook()`

## Обновление

Для обновления системы выполните:

```bash
# Обновляем код
git pull

# Активируем виртуальное окружение
source venv/bin/activate

# Обновляем зависимости
pip install -r requirements.txt

# Перезапускаем службы
sudo systemctl restart xray
sudo systemctl restart aircloud-vpn
```

## Устранение неполадок

### Проблема: Xray не запускается

Проверьте логи:
```bash
sudo journalctl -u xray -f
```

Убедитесь, что конфигурация корректна:
```bash
xray -test -config /etc/xray/config.json
```

### Проблема: Бот не отвечает

Проверьте логи:
```bash
sudo journalctl -u aircloud-vpn -f
```

Убедитесь, что токен бота правильный и бот запущен:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

### Проблема: Не работает Reality

Убедитесь, что порт 443 открыт:
```bash
sudo ufw status
```

Если порт закрыт, откройте его:
```bash
sudo ufw allow 443/tcp
```