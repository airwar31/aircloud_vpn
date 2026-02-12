# 🐳 ПОЛНАЯ ИНСТРУКЦИЯ РАЗВЕРТЫВАНИЯ

## 📋 СОДЕРЖИМОЕ

```
docker-configs/
├── vk-server/                   # Промежуточный сервер (Россия)
│   ├── Dockerfile              
│   └── config.json              # Два порта: 443 (цепь) + 8443 (выход)
│
├── nl-server/                   # Конечный сервер (Нидерланды)
│   ├── Dockerfile
│   ├── config.json
│   └── entrypoint.sh           # Работа с SSL сертификатами
│
├── bot/                         # Telegram бот
│   └── Dockerfile
│
├── docker-compose.yml           # Оркестрация сервисов
├── .env.example                 # Переменные окружения (шаблон)
│
├── deploy.sh                    # Скрипт для быстрого развертывания
├── copy-bot-files.sh           # Копирование файлов бота
│
└── README.md                    # Подробная документация
```

---

## 🚀 БЫСТРОЕ РАЗВЕРТЫВАНИЕ (5 минут)

### На локальной машине (тестирование):

```bash
cd docker-configs
chmod +x deploy.sh
./deploy.sh

# Ответьте на вопросы
```

### На боевом сервере (production):

```bash
# 1. Скопируйте папку docker-configs на боевой сервер
scp -r docker-configs/ root@your-server:/opt/

# 2. Подключитесь к серверу
ssh root@your-server

# 3. Перейдите в папку
cd /opt/docker-configs

# 4. Отредактируйте .env
nano .env
# - Установите BOT_TOKEN
# - Установите YOOKASSA_* значения
# - Установите реальные домены serversов

# 5. Запустите развертывание
chmod +x deploy.sh
./deploy.sh
```

---

## 🔧 ШАГИ РАЗВЕРТЫВАНИЯ

### Шаг 1: Подготовка окружения

```bash
cd docker-configs

# Копируем файлы бота в папку bot/
bash copy-bot-files.sh

# Проверяем структуру
tree docker-configs/
# или
find . -type f -name "*.json" -o -name "Dockerfile"
```

### Шаг 2: Конфигурация переменных

```bash
# Копируем шаблон
cp .env.example .env

# Редактируем с вашими значениями
nano .env

# Важные переменные:
# BOT_TOKEN - токен вашего Telegram бота
# YOOKASSA_SHOP_ID - ID вашего магазина в ЮKassa
# YOOKASSA_SECRET_KEY - Secret key ЮKassa
# VK_PRIVATE_KEY - Reality ключ (сгенерируется автоматически)
```

### Шаг 3: Генерируем Reality ключи (один раз!)

```bash
# Способ 1: Автоматически через скрипт deploy.sh
./deploy.sh

# Способ 2: Вручную
docker run --rm xray/xray:latest x25519

# Выведет:
# Private key: XXXXXXXXXXXXXXXXXXXXX
# Public key: YYYYYYYYYYYYYYYYYYYYYY

# Скопируйте Private key в .env файл (переменная VK_PRIVATE_KEY)
```

### Шаг 4: Запуск контейнеров

```bash
# Способ 1: Автоматически
./deploy.sh

# Способ 2: Вручную
docker-compose up -d

# Способ 3: С перестройкой образов
docker-compose up -d --build
```

### Шаг 5: Проверка статуса

```bash
# Проверяем, запущены ли контейнеры
docker-compose ps

# Должно быть:
# CONTAINER ID   IMAGE                STATUS              PORTS
# xxx            vpn-service_vk-...   Up 2 minutes        0.0.0.0:443->443/tcp
# xxx            vpn-service_nl-...   Up 2 minutes        0.0.0.0:8444->443/tcp
# xxx            vpn-service_bot...   Up 2 minutes

# Проверяем логи
docker-compose logs -f --tail=50
```

---

## 🔐 НАСТРОЙКА SSL СЕРТИФИКАТА (для NL сервера)

### Вариант 1: Let's Encrypt (РЕКОМЕНДУЕТСЯ)

```bash
# Остановить контейнер NL временно (если использует порт 443)
docker-compose stop nl-server

# Получить сертификат
docker run --rm -it \
    -p 443:443 \
    -v xray-certs:/etc/xray/certs \
    ubuntu:22.04 bash

# Внутри контейнера:
apt-get update && apt-get install -y certbot
certbot certonly --standalone \
    -d nl.vpn.example.com \
    --agree-tos \
    -m admin@example.com

# Копируем сертификаты
cp /etc/letsencrypt/live/nl.vpn.example.com/fullchain.pem /etc/xray/certs/
cp /etc/letsencrypt/live/nl.vpn.example.com/privkey.pem /etc/xray/certs/
exit

# Запускаем контейнер обратно
docker-compose up -d nl-server
```

### Вариант 2: Скопировать существующий сертификат

```bash
# Если у вас уже есть сертификат на хосте:
docker cp /path/to/cert.pem container_id:/etc/xray/certs/fullchain.pem
docker cp /path/to/key.pem container_id:/etc/xray/certs/privkey.pem

# Установить права доступа
docker-compose exec nl-server chown -R nobody:nogroup /etc/xray/certs
docker-compose exec nl-server chmod 600 /etc/xray/certs/privkey.pem
```

---

## 📊 СТРУКТУРА СЕТЕЙ И ПОРТОВ

### Веб-Порты (снаружи контейнеров):

```
VK Server:
├── 443:443      → ВК контейнер порт 443 (двойной туннель)
└── 8443:8443    → ВК контейнер порт 8443 (обычный VPN)

NL Server:
└── 8444:443     → NL контейнер порт 443 (внутри контейнера!)

Telegram Bot:
└── Внутренняя коммуникация через Docker сеть vpn-network
```

### Внутренние DNS имена (внутри Docker сети):

```
VK Server: vk-server:443 (для NL)
NL Server: nl-server:443 (для VK)
Bot может обращаться к обоим по этим именам
```

---

## 🐳 ОСНОВНЫЕ КОМАНДЫ

### Управление контейнерами

```bash
# Запустить все
docker-compose up -d

# Остановить все
docker-compose down

# Перезагрузить
docker-compose restart

# Перестроить образы
docker-compose build

# Удалить все (включая данные!)
docker-compose down -v
```

### Просмотр логов

```bash
# Все сервисы в реальном времени
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f vk-server

# Последние N строк
docker-compose logs --tail=100 vpn-bot

# С временными метками
docker-compose logs -f -t
```

### Доступ в контейнер

```bash
# Интерактивный shell
docker-compose exec vk-server bash
docker-compose exec nl-server bash
docker-compose exec vpn-bot bash

# Выполнить команду
docker-compose exec vk-server cat /etc/xray/config.json
docker-compose exec nl-server netstat -tuln
```

---

## ✅ ПРОВЕРКА РАБОТОСПОСОБНОСТИ

### Шаг 1: Проверить, запущены ли контейнеры

```bash
docker-compose ps

# Все должны быть в статусе "Up"
```

### Шаг 2: Проверить порты

```bash
# На Linux/Mac
netstat -tuln | grep -E "443|8443|8444"

# На Windows
netstat -ano | findstr ":443 :8443 :8444"
```

### Шаг 3: Проверить логи

```bash
# VK сервер должен вывести "Xray started"
docker-compose logs vk-server | grep -i "xray\|config\|started"

# NL сервер должен вывести "Xray started"
docker-compose logs nl-server | grep -i "xray\|config\|started"

# Бот должен подключиться к Telegram
docker-compose logs vpn-bot | grep -i "telegram\|started\|connected"
```

### Шаг 4: Тест подключения (из клиента)

```bash
# 1. Откройте V2RayNG или Clash
# 2. Импортируйте VLESS link (двойной туннель):
vless://YOUR-UUID@your-vk-server:443?security=reality&...

# 3. Подключитесь
# 4. Откройте ipinfo.io
# 5. Должен быть IP Нидерландов! ✅
```

---

## 🚨 РЕШЕНИЕ ПРОБЛЕМ

### Проблема: Контейнеры не запускаются

```bash
# Проверьте логи
docker-compose logs

# Проверьте, есть ли конфиги
ls -la vk-server/config.json nl-server/config.json bot/Dockerfile

# Пересоздайте все
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Проблема: Порты уже в использовании

```bash
# Найдите процесс
lsof -i :443  # или netstat -tuln | grep 443

# Завершите его или меняйте порты в docker-compose.yml
# Например, измените "443:443" на "8443:443"
```

### Проблема: "Connection refused" при подключении

```bash
# Проверьте firewall
sudo ufw status
sudo ufw allow 443/tcp
sudo ufw allow 8443/tcp
sudo ufw allow 8444/tcp

# Проверьте конфиги
docker-compose exec vk-server cat /etc/xray/config.json
docker-compose exec nl-server cat /etc/xray/config.json
```

### Проблема: "TLS certificate verification failed"

```bash
# На NL сервере проверьте сертификаты
docker-compose exec nl-server ls -la /etc/xray/certs/

# Должны быть fullchain.pem и privkey.pem

# Если пусто, получите сертификат (смотрите раздел SSL выше)
```

---

## 🔄 ОБНОВЛЕНИЕ КОДА

```bash
# 1. Остановите контейнеры
docker-compose down

# 2. Обновите файлы бота
bash copy-bot-files.sh

# 3. Пересоберите образ бота
docker-compose build bot

# 4. Запустите снова
docker-compose up -d bot
```

---

## 📈 МАСШТАБИРОВАНИЕ

### Добавить еще один NL сервер:

```yaml
# В docker-compose.yml добавьте:
nl-server-2:
    image: nl-xray:latest
    ports:
      - "8445:443"
    volumes:
      - ./nl-server/config.json:/etc/xray/config.json:ro
      - xray-certs-2:/etc/xray/certs
```

### Использовать внешние серверы:

```bash
# Просто не добавляйте их в docker-compose.yml
# Вместо этого установите Xray напрямую на хосты

# И обновите .env:
VK_SERVER=your-vk-server.com
NL_SERVER=your-nl-server.com
```

---

## 💾 BACKUP И ВОССТАНОВЛЕНИЕ

### Backup данных

```bash
# Backup БД бота
docker cp $(docker-compose ps -q vpn-bot):/shared /backup/vpn-db-$(date +%Y%m%d).bak

# Backup конфигов
tar czf backup-configs-$(date +%Y%m%d).tar.gz vk-server/ nl-server/ bot/

# Backup сертификатов
docker cp $(docker-compose ps -q nl-server):/etc/xray/certs /backup/certs-$(date +%Y%m%d).bak
```

### Восстановление

```bash
# Восстановить БД
docker cp /backup/vpn-db-XXX.bak/shared $(docker-compose ps -q vpn-bot):/

# Восстановить конфиги
tar xzf backup-configs-XXX.tar.gz

# Восстановить сертификаты
docker cp /backup/certs-XXX.bak $(docker-compose ps -q nl-server):/etc/xray/certs
```

---

## 🎯 ЧЕКЛИСТ РАЗВЕРТЫВАНИЯ

- [ ] Docker и Docker Compose установлены
- [ ] .env файл создан и заполнен
- [ ] Reality ключи сгенерированы
- [ ] Файлы бота скопированы в docker-configs/bot/
- [ ] docker-compose up -d успешно запущен
- [ ] Все контейнеры в статусе "Up"
- [ ] SSL сертификат на NL сервере
- [ ] Тест подключения с клиента успешен
- [ ] IP выходит правильный (Нидерланды для двойного)
- [ ] Бот отвечает на команды Telegram

---

## 📞 ПОДДЕРЖКА

Логи всегда в помощь:
```bash
docker-compose logs -f
```

Текущий статус:
```bash
docker-compose ps
docker stats
```

Перезагрузить все:
```bash
docker-compose restart
```

---

**Готово! 🎉 Система развернута в Docker контейнерах и готока к бою!**
