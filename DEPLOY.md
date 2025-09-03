# Запуск AirCloud VPN на сервере

## 1. Подготовка сервера

```bash
# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Устанавливаем Docker Compose
apt install docker-compose -y

# Клонируем проект
git clone <your-repo> /root/aircloud_vpn
cd /root/aircloud_vpn
```

## 2. Настройка переменных

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем переменные
nano .env
```

Заполните обязательные переменные:
```env
BOT_TOKEN=your_telegram_bot_token
XRAY_SERVER_IP=your_server_ip
XRAY_SERVER_PORT=443
XRAY_INBOUND_TAG=vless-in
DATABASE_URL=sqlite:///data/bot.db
```

## 3. Установка и запуск Xray

```bash
# Запускаем установку Xray
bash start_secure.sh
```

## 4. Запуск бота

```bash
# Запускаем бота в Docker
docker-compose up -d --build

# Проверяем логи
docker-compose logs -f aircloud-bot
```

## 5. Проверка работы

```bash
# Статус Xray
systemctl status xray

# Статус бота
docker-compose ps

# Логи бота
docker-compose logs aircloud-bot
```

## Команды управления

```bash
# Остановить бота
docker-compose down

# Перезапустить бота
docker-compose restart

# Обновить бота
git pull
docker-compose up -d --build

# Перезапустить Xray
systemctl restart xray
```