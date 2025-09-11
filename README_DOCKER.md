# 🐳 VPN Telegram Bot с Xray в Docker

Telegram бот для продажи VPN ключей с собственным Xray сервером в контейнере.

## 🚀 Быстрый старт

### 1. Подготовка
```bash
git clone <repository-url>
cd vpn-bot
cp .env.example .env
```

### 2. Настройка переменных окружения
Отредактируйте `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
SERVER_IP=your_server_ip
XRAY_API_URL=http://xray-api:8080
```

### 3. Запуск
```bash
chmod +x start.sh
./start.sh
```

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │────│   Xray API      │
│   (Python)      │    │   (Flask)       │
└─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   Xray Core     │
                       │   (VPN Server)  │
                       └─────────────────┘
```

## 📦 Контейнеры

- **xray-api**: Xray сервер + API для управления
- **vpn-bot**: Telegram бот

## 🔧 Управление

### Просмотр логов
```bash
# Все логи
docker-compose logs -f

# Только бот
docker-compose logs -f vpn-bot

# Только Xray
docker-compose logs -f xray-api
```

### Перезапуск
```bash
docker-compose restart
```

### Остановка
```bash
docker-compose down
```

### Обновление
```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

## 📊 Мониторинг

### Статистика бота
```bash
docker-compose exec vpn-bot python admin.py stats
```

### Проверка Xray API
```bash
curl http://localhost:8080/health
```

## 🔒 Безопасность

### Настройка файрвола
```bash
# Разрешить только необходимые порты
ufw allow 22    # SSH
ufw allow 443   # VPN
ufw deny 8080   # API только внутри Docker
ufw enable
```

### SSL сертификат (рекомендуется)
Для продакшена настройте SSL сертификат для порта 443.

## 🐛 Решение проблем

### Контейнер не запускается
```bash
docker-compose logs <service-name>
```

### Проблемы с сетью
```bash
docker network ls
docker network inspect vpn-bot_vpn-network
```

### Очистка
```bash
# Удалить все контейнеры и данные
docker-compose down -v
docker system prune -a
```

## 📈 Масштабирование

Для высоких нагрузок можно запустить несколько экземпляров:

```yaml
# docker-compose.yml
services:
  xray-api:
    deploy:
      replicas: 2
  
  vpn-bot:
    deploy:
      replicas: 3
```

## 🔄 Резервное копирование

```bash
# Создание бэкапа
docker-compose exec vpn-bot cp /app/data/vpn_bot.db /app/data/backup_$(date +%Y%m%d).db

# Восстановление
docker cp backup.db container_name:/app/data/vpn_bot.db
```