# AirCloud VPN

Telegram-бот для продажи и управления VPN-подключениями на базе Xray с Reality.

## Особенности

- Быстрая и простая установка через Docker
- Поддержка протокола VLESS с Reality
- Интеграция с Telegram-ботом для управления подписками
- Интеграция с ЮKassa для приема платежей
- Автоматическое создание и продление подписок

## Требования

- Сервер с Linux (рекомендуется Ubuntu 20.04 или новее)
- Открытый порт 443 (или другой порт, который вы хотите использовать)
- Docker и Docker Compose

## Быстрая установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/aircloud_vpn.git
   cd aircloud_vpn
   ```

2. Запустите скрипт установки:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Отредактируйте файл `.env` с вашими настройками:
   ```bash
   nano .env
   ```

4. Проверьте, что сервис работает:
   ```bash
   docker-compose logs -f
   ```

## Ручная установка

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/aircloud_vpn.git
   cd aircloud_vpn
   ```

2. Создайте файл `.env` из примера:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Создайте директории для данных и логов:
   ```bash
   mkdir -p data logs
   ```

4. Соберите и запустите контейнеры:
   ```bash
   docker-compose up -d
   ```

## Настройка

В файле `.env` необходимо указать следующие параметры:

- `BOT_TOKEN` - токен вашего Telegram бота (получите у @BotFather)
- `VPN_SERVER_ADDRESS` - IP-адрес или домен вашего сервера
- `ADMIN_IDS` - список ID администраторов (через запятую)
- `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` (если используете ЮKassa)

## Обновление

Для обновления проекта выполните:

```bash
chmod +x update.sh
./update.sh
```

## Управление

- Запуск: `docker-compose up -d`
- Остановка: `docker-compose down`
- Перезапуск: `docker-compose restart`
- Просмотр логов: `docker-compose logs -f`

## Устранение неполадок

### Проблема: Контейнер не запускается

Проверьте логи:
```bash
docker-compose logs -f
```

### Проблема: Бот не отвечает

Убедитесь, что токен бота правильный и бот запущен:
```bash
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getMe
```

### Проблема: Не работает Reality

Убедитесь, что порт 443 открыт на сервере:
```bash
sudo ufw status
```

Если порт закрыт, откройте его:
```bash
sudo ufw allow 443/tcp
```