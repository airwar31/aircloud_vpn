# ⚡ Quick Start: Deploy VK → NL (5 шагов)

## 1️⃣ Подготовка ключей (локально)

```bash
# Генерируем Reality ключи
xray x25519

# Сохраняем Private и Public keys!
```

---

## 2️⃣ VK Сервер (243.x.x.x)

```bash
ssh root@243.x.x.x
cd /opt && git clone https://github.com/yourusername/aircloud_vpn.git
cd aircloud_vpn/docker-configs

# Создаем .env с ключами и адресами
cat > .env << 'EOF'
VK_SERVER=243.x.x.x
VK_PUBLIC_IP=243.x.x.x
NL_SERVER=85.239.56.174
NL_DOMAIN=nl.vpn.example.com
VK_PRIVATE_KEY=XXXX...  # Reality private key
VK_PUBLIC_KEY=YYYY...    # Reality public key
UUID_DOUBLE=550e8400-e29b-41d4-a716-446655440000
UUID_SINGLE=550e8400-e29b-41d4-a716-446655440001
BOT_TOKEN=123456...
EOF

# Обновляем vk-server/config.json
# - Замените REPLACE_WITH_PRIVATE_KEY на Reality private key
# - Замените REPLACE_WITH_UUID_DOUBLE на UUID_DOUBLE
# - Замените "address": "nl-server" на "address": "85.239.56.174"

# Запускаем
docker-compose build vk-server
docker-compose up -d vk-server
docker-compose logs -f vk-server  # Проверяем логи

# Проверка: netstat -tlnp | grep 443
```

---

## 3️⃣ NL Сервер (85.239.56.174)

```bash
ssh root@85.239.56.174
cd /opt && git clone https://github.com/yourusername/aircloud_vpn.git
cd aircloud_vpn/docker-configs

# Тот же .env файл как на VK!
cat > .env << 'EOF'
VK_SERVER=243.x.x.x
VK_PUBLIC_IP=243.x.x.x
NL_SERVER=85.239.56.174
NL_DOMAIN=nl.vpn.example.com
VK_PRIVATE_KEY=XXXX...
VK_PUBLIC_KEY=YYYY...
UUID_DOUBLE=550e8400-e29b-41d4-a716-446655440000
UUID_SINGLE=550e8400-e29b-41d4-a716-446655440001
BOT_TOKEN=123456...
EOF

# Получаем SSL сертификат
DOMAIN=nl.vpn.example.com
certbot certonly --standalone -d $DOMAIN --email admin@example.com --agree-tos

# Копируем сертификаты
mkdir -p nl-server/certs
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nl-server/certs/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nl-server/certs/
chmod 644 nl-server/certs/privkey.pem

# Обновляем nl-server/config.json
# - "serverName": "nl.vpn.example.com"
# - Обновите оба UUID (DOUBLE и SINGLE)

# Запускаем NL + Bot
docker-compose build
docker-compose up -d
docker-compose ps  # Должны быть 3 контейнера в Up

# Проверка: netstat -tlnp | grep -E '443|8443'
```

---

## 4️⃣ Проверка связи VK → NL

```bash
# На NL сервере
docker-compose logs nl-server | grep -i "inbound\|listening"

# На VK сервере
docker-compose logs vk-server | grep -i "outbound\|success"
```

---

## 5️⃣ Тестирование VPN

### Double Tunnel:
1. Получите конфиг из бота: `/start` → `/buy`
2. Импортируйте VLESS ссылку в клиент
3. Проверьте IP на ipinfo.io → **должен быть из Нидерландов**

### Single Tunnel:
1. Получите single конфиг из бота
2. Подключитесь к `85.239.56.174:8445` (внешний порт)
3. Проверьте IP → **85.239.56.174** ✓

---

## ✅ Done!

```
VK (243.x.x.x:443) → маршрутизирует → NL (85.239.56.174)
                                       ├─ 443/8444 (double)
                                       └─ 8443/8445 (single)
```
