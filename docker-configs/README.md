# 🐳 DOCKER РАЗВЕРТЫВАНИЕ VPN СЕРВИСА

## 📁 СТРУКТУРА

```
docker-configs/
├── vk-server/                # Промежуточный сервер (ВК)
│   ├── Dockerfile           # Ubuntu + Xray
│   └── config.json          # Конфиг для двойного туннеля и обычного VPN
├── nl-server/               # Конечный сервер (Нидерланды)
│   ├── Dockerfile
│   ├── config.json
│   └── entrypoint.sh        # Скрипт для работы с SSL сертификатами
├── bot/                     # Telegram бот
│   └── Dockerfile
├── docker-compose.yml       # Оркестрация всех сервисов
├── .env.example             # Переменные окружения (копируйте в .env)
└── README.md               # Этот файл
```

---

## 🚀 БЫСТРЫЙ СТАРТ

### 1️⃣ Подготовка

```bash
cd docker-configs

# Копируем пример конфига
cp .env.example .env

# Редактируем .env с вашими значениями
nano .env
```

**Важные переменные в .env:**
```
BOT_TOKEN=                  # Ваш токен Telegram бота
YOOKASSA_SHOP_ID=          # ID магазина ЮKassa
YOOKASSA_SECRET_KEY=       # Secret key ЮKassa
VK_PRIVATE_KEY=            # Reality приватный ключ (сгенерируйте!)
```

---

### 2️⃣ Генерируем Reality ключи (один раз)

```bash
docker run --rm xray/xray:latest x25519

# Вывод:
# Private key: XXXXX...
# Public key: XXXXX...

# Копируйте private key в VK_PRIVATE_KEY в .env файле
```

---

### 3️⃣ Запускаем контейнеры

```bash
# Сборка и запуск
docker-compose up -d

# Проверка статуса
docker-compose ps

# Логи
docker-compose logs -f vk-server
docker-compose logs -f nl-server
docker-compose logs -f vpn-bot
```

---

## 🔧 АРХИТЕКТУРА

### Топология сети:

```
┌─────────────┐
│  Telegram   │
│  Клиент     │
└──────┬──────┘
       │ BOT_TOKEN
       ↓
┌──────────────────┐
│  vpn-bot         │ (python:3.11)
│  (Docker)        │
└──────┬───────────┘
       │
    ┌──┴──┐
    │     │
    ↓     ↓
┌────────┐  ┌────────┐
│ VK     │  │  NL    │
│Server  │  │Server  │
│443     │  │443     │
│8443    │  │        │
└────────┘  └────────┘
    ↑           ↑
    └─ Xray ────┘
      (VLESS)
```

### Маршруты трафика:

```
【 ОБЫЧНЫЙ VPN 】
Клиент → VK:8443 (Reality) → Интернет
         (вход в отдельный порт)

【 ДВОЙНОЙ ТУННЕЛЬ 】
Клиент → VK:443 (Reality) → NL:443 (TLS) → Интернет
         (цепь через оба сервера)
```

---

## 📝 КОНФИГУРАЦИЯ СЕРВИСОВ

### VK Server (Промежуточный)

- **Образ:** Ubuntu 22.04 + Xray
- **Порты:**
  - `443` - двойной туннель (цепь к NL)
  - `8443` - обычный VPN (прямой выход)
- **Сеть:** vpn-network
- **Конфиг:** config.json (автоматически копируется)

### NL Server (Конечный)

- **Образ:** Ubuntu 22.04 + Xray + Certbot
- **Порт:** `8444` (проксируется как 443 внутри контейнера)
- **SSL:** Автоматически ожидает сертификаты в `/etc/xray/certs/`
- **Скрипт входа:** Проверяет наличие сертификатов, генерирует самоподписанные если нужно
- **Том:** xray-certs (для хранения сертификатов)

### VPN Bot

- **Образ:** Python 3.11 + зависимости
- **Зависимости:** From requirements.txt в bot/
- **Переменные окружения:** From .env файла
- **Том:** shared-db (для БД Sqlite)

---

## 🔐 ПОЛУЧЕНИЕ SSL СЕРТИФИКАТА (для NL сервера)

### Вариант 1: Let's Encrypt (рекомендуется)

```bash
# На хосте (пока контейнеры запущены)
docker-compose exec nl-server certbot certonly --standalone \
    -d nl.vpn.example.com \
    --agree-tos \
    -m admin@example.com

# Сертификаты будут в контейнере по пути:
# /etc/letsencrypt/live/nl.vpn.example.com/fullchain.pem
# /etc/letsencrypt/live/nl.vpn.example.com/privkey.pem

# Скопируйте их в том xray-certs
docker exec nl-server cp /etc/letsencrypt/live/nl.vpn.example.com/fullchain.pem /etc/xray/certs/
docker exec nl-server cp /etc/letsencrypt/live/nl.vpn.example.com/privkey.pem /etc/xray/certs/
docker exec nl-server chown nobody:nogroup /etc/xray/certs/*
```

### Вариант 2: Самоподписанный сертификат (тестирование)

```bash
# Автоматически генерируется при запуске, если сертификата нет
# Будет в /etc/xray/certs/ внутри контейнера
```

---

## 📊 УПРАВЛЕНИЕ КОНТЕЙНЕРАМИ

### Запуск/Остановка

```bash
# Запустить все
docker-compose up -d

# Остановить все
docker-compose down

# Перезагрузить определенный сервис
docker-compose restart vk-server

# Обновить (перестроить образы)
docker-compose up -d --build
```

### Мониторинг

```bash
# Статус всех контейнеров
docker-compose ps

# Логи в реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f vk-server

# Последние 50 строк
docker-compose logs --tail=50 vpn-bot
```

### Отладка

```bash
# Зайти в контейнер
docker-compose exec vk-server bash

# Проверить конфиг Xray
docker-compose exec vk-server cat /etc/xray/config.json

# Проверить порты
docker-compose exec vk-server netstat -tuln
```

---

## 🌍 РАЗВЕРТЫВАНИЕ НА НЕСКОЛЬКО СЕРВЕРОВ

### Вариант А: Все в одном контейнере (dev/small)

```bash
# Текущая конфигурация
docker-compose up -d
```

### Вариант Б: Разные хосты (prod/large)

**На хосте 1 (ВК сервер):**
```bash
# Копируем только VK конфиг
docker build -t vk-xray:latest ./vk-server
docker run -d \
    -p 443:443 \
    -p 8443:8443 \
    --name vk-server \
    vk-xray:latest
```

**На хосте 2 (NL сервер):**
```bash
docker build -t nl-xray:latest ./nl-server
docker run -d \
    -p 443:443 \
    -v xray-certs:/etc/xray/certs \
    --name nl-server \
    nl-xray:latest
```

**На хосте 3 (Бот):**
```bash
docker build -t vpn-bot:latest ./bot
docker run -d \
    -e BOT_TOKEN="..." \
    -e VK_SERVER="vk.example.com" \
    -e NL_SERVER="nl.example.com" \
    --name vpn-bot \
    vpn-bot:latest
```

---

## 🛠️ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

| Переменная | Описание | Пример |
|-----------|---------|--------|
| BOT_TOKEN | Токен Telegram бота | 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew |
| YOOKASSA_SHOP_ID | ID магазина | 123456 |
| YOOKASSA_SECRET_KEY | Secret ключ | test_AbCdEfGhIjKlMnOpQrStUvWxYz |
| VK_SERVER | Домен/IP ВК сервера | localhost, vk.vpn.example.com |
| NL_SERVER | Домен/IP NL сервера | localhost, nl.vpn.example.com |
| VK_PRIVATE_KEY | Reality приватный ключ | ПОЛУЧЕННЫЙ ИЗ x25519 |

---

## ✅ ПРОВЕРКА РАБОТОСПОСОБНОСТИ

```bash
# 1. Проверяем статус контейнеров
docker-compose ps

# Должны быть в состоянии "Up"

# 2. Проверяем порты
netstat -tuln | grep -E "443|8443"

# 3. Логи VK сервера
docker-compose logs vk-server

# Должны видеть "Xray started successfully"

# 4. Тест подключения (из клиента)
# Используйте сгенерированные VLESS links для подключения
# Проверьте на ipinfo.io какой выходит IP
```

---

## 🚨 РЕШЕНИЕ ПРОБЛЕМ

### Проблема: "Connection refused"
```bash
# Проверьте, запущены ли контейнеры
docker-compose ps

# Перезагрузите
docker-compose restart vk-server nl-server
```

### Проблема: "Certificate verification failed"
```bash
# Проверьте сертификаты в NL контейнере
docker-compose exec nl-server ls -la /etc/xray/certs/

# Скопируйте сертификаты вручную
docker-compose exec nl-server certbot renew
```

### Проблема: "No such file or directory: config.json"
```bash
# Убедитесь, что конфиги есть в папках
ls -la ./vk-server/config.json
ls -la ./nl-server/config.json

# Они должны быть перед docker-compose up
```

---

## 📦 ТРЕБОВАНИЯ

- Docker 20.10+
- Docker Compose 1.29+
- Python 3.11 (для локальной разработки)
- 2GB RAM минимум для контейнеров

---

## 🎯 БЫСТРЫЕ КОМАНДЫ

```bash
# Полная переделишка (пересоздать все с нуля)
docker-compose down -v && docker-compose up -d

# Просмотр активных процессов в контейнерах
docker-compose top

# Удалить неиспользуемые образы
docker image prune -a

# Проверить использование ресурсов
docker stats

# Вывести IP адреса контейнеров
docker-compose exec vk-server hostname -I
docker-compose exec nl-server hostname -I
```

---

**Готово! Система развернута в контейнерах** 🎉
