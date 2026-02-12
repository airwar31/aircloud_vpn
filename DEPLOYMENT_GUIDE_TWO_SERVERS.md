# 🚀 Гайд развертывания на двух серверах: VK + NL

## 📋 Требования

### VK Сервер (Россия)
- ✅ Ubuntu 22.04 LTS
- ✅ Публичный IP (пусть `243.x.x.x` - вместо x подставь свой)
- ✅ Открыты порты: **443** (входящий)
- ✅ 1 GB RAM минимум
- ✅ 10 GB свободного места
- ✅ Docker + Docker Compose установлены

### NL Сервер (Нидерланды)  
- ✅ Ubuntu 22.04 LTS
- ✅ Публичный IP (пусть `85.239.56.174`)
- ✅ Открыты порты: **443, 8443** (входящие)
- ✅ 2 GB RAM минимум
- ✅ 20 GB свободного места
- ✅ Docker + Docker Compose установлены
- ✅ Домен, указывающий на этот IP (для SSL)

---

## 🔑 ШАГ 1: Подготовка ключей (локально, перед развертыванием)

### 1.1 Генерируем Reality ключи

```bash
# На локальной машине (Windows/Mac/Linux)
xray x25519
```

**Результат:**
```
Private key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
Public key:  YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
```

**Сохраняем оба!** ⚠️

---

## 🖥️ ШАГ 2: Развертывание на VK сервере

### 2.1 Подключаемся к VK серверу

```bash
ssh root@243.x.x.x
```

### 2.2 Клонируем проект

```bash
cd /opt
git clone https://github.com/yourusername/aircloud_vpn.git
cd aircloud_vpn/docker-configs
```

### 2.3 Создаем .env файл

```bash
cat > .env << 'EOF'
# VK Server (Russia)
VK_SERVER=243.x.x.x
VK_PUBLIC_IP=243.x.x.x

# NL Server (Netherlands)
NL_SERVER=85.239.56.174
NL_DOMAIN=nl.vpn.example.com

# Reality Keys (получены на шаге 1)
VK_PRIVATE_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
VK_PUBLIC_KEY=YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY

# UUIDs (можешь сгенерировать через uuidgen)
UUID_DOUBLE=550e8400-e29b-41d4-a716-446655440000
UUID_SINGLE=550e8400-e29b-41d4-a716-446655440001

# Bot
BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_XXXXXXXXXXXXXXXXXXXXXXXXXXX

# Timezone
TZ=UTC
EOF
```

### 2.4 Обновляем VK config.json

Откройте `vk-server/config.json` и замените:

```json
"privateKey": "REPLACE_WITH_PRIVATE_KEY"
↓
"privateKey": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

"id": "REPLACE_WITH_UUID_DOUBLE"
↓
"id": "550e8400-e29b-41d4-a716-446655440000"
```

**Также обновите адрес NL сервера:**

```json
"address": "nl-server"
↓
"address": "85.239.56.174"  // или домен: nl.vpn.example.com
```

### 2.5 Собираем и запускаем VK контейнер

```bash
docker-compose build vk-server
docker-compose up -d vk-server

# Проверяем статус
docker-compose ps
docker-compose logs -f vk-server
```

**Должно быть:**
```
vk-xray-server    Up    0.0.0.0:443->443/tcp
```

### 2.6 Проверяем, работает ли VK

```bash
# Проверяем что Xray слушает порт 443
netstat -tlnp | grep 443

# Смотрим логи
docker-compose logs vk-server | tail -20
```

✅ **VK сервер готов!**

---

## 🌍 ШАГ 3: Развертывание на NL сервере

### 3.1 Подключаемся к NL серверу

```bash
ssh root@85.239.56.174
```

### 3.2 Клонируем проект

```bash
cd /opt
git clone https://github.com/yourusername/aircloud_vpn.git
cd aircloud_vpn/docker-configs
```

### 3.3 Создаем .env файл (точно такой же!)

```bash
cat > .env << 'EOF'
# VK Server (Russia)
VK_SERVER=243.x.x.x
VK_PUBLIC_IP=243.x.x.x

# NL Server (Netherlands)
NL_SERVER=85.239.56.174
NL_DOMAIN=nl.vpn.example.com

# Reality Keys
VK_PRIVATE_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
VK_PUBLIC_KEY=YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY

# UUIDs (ДОЛЖНЫ СОВПАДАТЬ С VK!)
UUID_DOUBLE=550e8400-e29b-41d4-a716-446655440000
UUID_SINGLE=550e8400-e29b-41d4-a716-446655440001

# Bot
BOT_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_XXXXXXXXXXXXXXXXXXXXXXXXXXX

TZ=UTC
EOF
```

### 3.4 Получаем SSL сертификат (Let's Encrypt)

**Важно!** Домен должен быть направлен на этот IP (в DNS)

```bash
# Укажите ваш домен
DOMAIN=nl.vpn.example.com

# Получаем сертификат
certbot certonly --standalone -d $DOMAIN --email admin@example.com --agree-tos

# Проверяем что сертификат получен
ls -la /etc/letsencrypt/live/$DOMAIN/
```

**Результат:**
```
/etc/letsencrypt/live/nl.vpn.example.com/
├── fullchain.pem
├── privkey.pem
└── ...
```

### 3.5 Копируем сертификаты в docker volume

```bash
# Создаем директорию
mkdir -p nl-server/certs

# Копируем сертификаты
cp /etc/letsencrypt/live/nl.vpn.example.com/fullchain.pem nl-server/certs/
cp /etc/letsencrypt/live/nl.vpn.example.com/privkey.pem nl-server/certs/
```

### 3.6 Обновляем NL config.json

```json
"serverName": "nl.vpn.example.com"  ← проверьте что верно
"certificateFile": "/etc/xray/certs/fullchain.pem"
"keyFile": "/etc/xray/certs/privkey.pem"

"id": "REPLACE_WITH_UUID_DOUBLE"
↓
"id": "550e8400-e29b-41d4-a716-446655440000"

"id": "REPLACE_WITH_UUID_SINGLE"
↓
"id": "550e8400-e29b-41d4-a716-446655440001"
```

### 3.7 Собираем и запускаем NL контейнеры

```bash
# Собираем образы
docker-compose build nl-server

# Запускаем NL сервер
docker-compose up -d nl-server

# Проверяем
docker-compose ps
docker-compose logs -f nl-server
```

**Должно быть:**
```
nl-xray-server    Up    0.0.0.0:8444->443/tcp, 0.0.0.0:8445->8443/tcp
```

### 3.8 Даем права на сертификаты

```bash
# Чтобы контейнер мог читать сертификаты
chmod 644 nl-server/certs/privkey.pem
chmod 644 nl-server/certs/fullchain.pem
```

### 3.9 Проверяем NL

```bash
# Проверяем что порты слушают
netstat -tlnp | grep -E '443|8443'

# Смотрим логи
docker-compose logs nl-server | tail -20

# Тест подключения (с локальной машины)
openssl s_client -connect 85.239.56.174:8444
```

✅ **NL сервер готов!**

---

## 🤖 ШАГ 4: Запуск Telegram Bot (на NL сервере)

### 4.1 Копируем bot файлы

Убедитесь что в `nl-server/bot_app/` находятся все 16 файлов бота:
```bash
ls -la nl-server/bot_app/ | wc -l
# Должно быть минимум 16 файлов
```

### 4.2 Собираем и запускаем бот

```bash
# Собираем образ бота
docker-compose build vpn-bot

# Запускаем всю связку (VK + NL + Bot)
docker-compose up -d

# Проверяем статус
docker-compose ps
```

**Должно быть:**
```
vk-xray-server     Up
nl-xray-server     Up
vpn-telegram-bot   Up
```

### 4.3 Проверяем логи бота

```bash
docker-compose logs vpn-bot | tail -50

# Должно быть что-то типа:
# [INFO] Bot started successfully!
# [INFO] Listening for messages...
```

---

## 🧪 ШАГ 5: Тестирование

### 5.1 Генерируем тестовый конфиг

Отправьте боту команду `/start`, затем `/buy` и выберите подписку.

### 5.2 Тестируем Double Tunnel

Получите VLESS ссылку из бота:
- Первый хоп: `vless://UUID@243.x.x.x:443?security=reality...`
- Второй хоп: `vless://UUID@85.239.56.174:8444?security=tls...`

Импортируйте в клиента (V2RayNG, Clash и т.д.) и тестируйте подключение.

```bash
# Проверяем на ipinfo.io (должен быть IP Нидерландов)
curl ipinfo.io
```

### 5.3 Тестируем Single Tunnel

Получите ссылку для Single:
- `vless://UUID@85.239.56.174:8445?security=tls...`

Должен видеть IP: **85.239.56.174** ✅

---

## 📊 Финальная проверка

| Компонент | VK Сервер | NL Сервер |
|-----------|-----------|-----------|
| **Xray слушает** | Port 443 | Port 443, 8443 |
| **Docker запущен** | ✅ | ✅ |
| **Логи нормальные** | ✅ | ✅ |
| **Бот подключен** | - | ✅ |
| **SSL сертификат** | ❌ | ✅ |

---

## 🔧 Команды для отладки

### На VK сервере:

```bash
# Перезапуск
docker-compose restart vk-server

# Логи в реальном времени
docker-compose logs -f vk-server

# Вход в контейнер
docker-compose exec vk-server bash

# Проверить конфиг Xray
docker-compose exec vk-server cat /etc/xray/config.json
```

### На NL сервере:

```bash
# Перезапуск всего
docker-compose restart

# Логи бота
docker-compose logs -f vpn-bot

# Логи Xray на NL
docker-compose logs -f nl-server

# Проверить сертификаты
docker-compose exec nl-server ls -la /etc/xray/certs/
```

---

## ⚠️ Важные моменты

1. **UUIDs должны совпадать** на VK и NL - одинаковые UUID_DOUBLE и UUID_SINGLE
2. **Домен NL** должен указывать на IP сервера (проверьте DNS)
3. **SSL сертификат** обновляется автоматически (Certbot)
4. **Порты** должны быть открыты в firewall обоих серверов
5. **Private Key** должен быть одинаковый на VK (для Reality)

---

## 🚀 Выводы

```
✅ VK сервер (243.x.x.x:443)
   └─ Маршрутизирует double tunnel в NL

✅ NL сервер (85.239.56.174)
   ├─ Port 443 (8444 публично) - для double tunnel
   ├─ Port 8443 (8445 публично) - для single tunnel
   └─ Telegram Bot управляет подписками

✅ Оба типа VPN выходят через NL с IP 85.239.56.174
```

**Готово! 🎉**
