# 🛡️ Защита от DDoS и кибератак

## 📊 Виды атак которые могут быть

| Атака | Где | Как защиться |
|-------|-----|--------------|
| **DDoS (Layer 3/4)** | На ports 443/8443 | Firewall, Rate limit, ISP protection |
| **Layer 7 DDoS** | HTTP flood на бот API | Nginx reverse proxy, fail2ban |
| **Port scan** | Все порты | UFW firewall, fail2ban |
| **Brute force SSH** | SSH 22 | SSH keys only, fail2ban, change port |
| **Xray exploit** | Protocol exploit | Keep Xray updated |
| **Bot spam** | Telegram API commands | Rate limit in code |
| **Certificate ACME** | SSL validation attack | Monitor certbot logs |

---

## 🔥 ШАГ 1: Firewall (UFW)

### На VK сервере:

```bash
ssh root@243.x.x.x

# Проверяем статус
sudo ufw status

# Если не установлен
sudo apt update && sudo apt install -y ufw

# Начальные правила
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Открываем только нужные порты
sudo ufw allow 22/tcp          # SSH
sudo ufw allow 443/tcp         # Xray double tunnel
sudo ufw limit 22/tcp          # Limit SSH (max 6 попыток за 30 сек)

# Включаем UFW
sudo ufw enable

# Проверяем
sudo ufw status verbose
```

**Результат должен быть:**
```
22/tcp (v6)                LIMIT       Anywhere (v6)
443/tcp (v6)               ALLOW       Anywhere (v6)
```

### На NL сервере:

```bash
ssh root@85.239.56.174

# То же самое
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8443/tcp
sudo ufw limit 22/tcp
sudo ufw enable

# Проверяем
sudo ufw status verbose
```

**Результат:**
```
22/tcp                      LIMIT       Anywhere
443/tcp                     ALLOW       Anywhere
8443/tcp                    ALLOW       Anywhere
```

---

## 🚨 ШАГ 2: Fail2Ban (защита от brute-force)

### На обоих серверах:

```bash
# Установка
sudo apt update && sudo apt install -y fail2ban

# Стартуем
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Проверяем
sudo systemctl status fail2ban
```

### Конфигурируем SSH защиту:

```bash
# Создаем локальный конфиг
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Редактируем
sudo nano /etc/fail2ban/jail.local

# Ищем [sshd] секцию и изменяем:
```

**Рекомендуемые параметры:**
```ini
[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3          # 3 неудачных попытки
findtime = 600        # За 10 минут
bantime = 3600        # Банить на 1 час
```

```bash
# Перезагружаем fail2ban
sudo systemctl restart fail2ban

# Проверяем статус
sudo fail2ban-client status sshd
```

### Добавляем защиту для Xray (DDoS on 443):

```bash
# Создаем новый jail для Xray
sudo nano /etc/fail2ban/jail.d/xray.conf

# Вставляем:
```

```ini
[xray-ddos]
enabled = true
port = 443,8443
logpath = /var/log/syslog
maxretry = 100          # 100 пакетов в секунду
findtime = 10           # За 10 сек
bantime = 600           # Банить на 10 минут
action = iptables-multiport[name=xray, port="443,8443"]
```

```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status xray-ddos
```

---

## 📍 ШАГ 3: Rate Limiting (в Xray config)

### На VK сервере (vk-server/config.json):

Добавляем в inbound для port 443:

```json
"inbounds": [
  {
    "port": 443,
    "protocol": "vless",
    "tag": "double-tunnel-in",
    "settings": {
      "clients": [
        {
          "id": "UUID",
          "level": 0
        }
      ],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "www.google.com:443",
        "xver": 0,
        "privateKey": "KEY",
        "maxTimeDiff": 0,
        "handshake": 29,
        "maxConcurrentConns": 5000
      }
    },
    "sniffing": {
      "enabled": true,
      "destOverride": ["http", "tls"]
    }
  }
]
```

**Важная строка:** `"maxConcurrentConns": 5000` - максимум 5000 одновременных соединений

### На NL сервере (nl-server/config.json):

Добавляем для двух inbound'ов:

```json
"inbounds": [
  {
    "port": 443,
    "tag": "double-tunnel-in",
    "protocol": "vless",
    "settings": {
      "clients": [
        {
          "id": "UUID",
          "level": 0
        }
      ],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "tcp",
      "security": "tls",
      "tlsSettings": {
        "alpn": ["h2", "http/1.1"],
        "certificates": [
          {
            "certificateFile": "/etc/xray/certs/fullchain.pem",
            "keyFile": "/etc/xray/certs/privkey.pem"
          }
        ]
      }
    },
    "sniffing": {
      "enabled": true,
      "destOverride": ["http", "tls"]
    },
    "connLimit": {
      "conns": 5000,
      "connsPerIP": 100
    }
  },
  {
    "port": 8443,
    "tag": "single-tunnel-in",
    "protocol": "vless",
    "settings": {
      "clients": [
        {
          "id": "UUID",
          "level": 0
        }
      ],
      "decryption": "none"
    },
    "streamSettings": {
      "network": "tcp",
      "security": "tls",
      "tlsSettings": {
        "alpn": ["h2", "http/1.1"],
        "certificates": [
          {
            "certificateFile": "/etc/xray/certs/fullchain.pem",
            "keyFile": "/etc/xray/certs/privkey.pem"
          }
        ]
      }
    },
    "sniffing": {
      "enabled": true,
      "destOverride": ["http", "tls"]
    },
    "connLimit": {
      "conns": 5000,
      "connsPerIP": 100
    }
  }
]
```

**Важные параметры:**
- `conns`: 5000 max total connections
- `connsPerIP`: 100 max connections per IP

Проверяем синтаксис:
```bash
docker-compose exec nl-server xray -test -config /etc/xray/config.json
# "The config is valid"
```

---

## 🤖 ШАГ 4: Telegram Bot Rate Limiting

### Редактируем bot.py на NL сервере:

```bash
ssh root@85.239.56.174
nano /opt/aircloud_vpn/docker-configs/nl-server/bot_app/bot.py
```

**Добавляем в начало бота (после импортов):**

```python
from collections import defaultdict
from time import time

# Rate limiting
user_requests = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 30
MAX_REQUESTS_PER_HOUR = 500

def rate_limit_check(user_id: int) -> bool:
    """Проверяем лимит запросов пользователя"""
    now = time()
    
    # Очищаем старые запросы (старше часа)
    user_requests[user_id] = [t for t in user_requests[user_id] 
                               if now - t < 3600]
    
    # Проверяем лимит за час
    if len(user_requests[user_id]) > MAX_REQUESTS_PER_HOUR:
        return False
    
    # Проверяем лимит за минуту
    last_minute = [t for t in user_requests[user_id] if now - t < 60]
    if len(last_minute) > MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Добавляем текущий запрос
    user_requests[user_id].append(now)
    return True

# В каждый обработчик команд добавляем проверку:
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not rate_limit_check(message.from_user.id):
        await message.reply("⏱️ Вы отправляете слишком много команд. Попробуйте позже.")
        return
    
    # Остальной код...
```

---

## 📝 ШАГ 5: Мониторинг и логирование

### Включаем логирование в Docker

На обоих серверах создаем logging конфиг:

```bash
sudo nano /etc/docker/daemon.json
```

**Добавляем:**
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3",
    "labels": "service"
  }
}
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### Проверяем логи:

```bash
# Логи конкретного контейнера
docker-compose logs -f nl-server

# Последние 100 строк
docker-compose logs --tail 100 nl-server

# С временными метками
docker-compose logs -f -t nl-server

# Grep для ошибок
docker-compose logs nl-server 2>&1 | grep -i error
```

---

## 🔍 ШАГ 6: Мониторинг атак (Fail2Ban)

### Проверяем бан-листы:

```bash
# Проверяем sshd
sudo fail2ban-client status sshd
# Результат:
# |- Filter
# |  |- Currently failed: 2
# |  |- Total failed: 5
# |  `- File list: /var/log/auth.log
# `- Actions
#    `- iptables-multiport[name=sshd, port=ssh]
#       |- Currently banned: 1
#       |- Total banned: 1
#       `- IP list: 192.168.1.100

# Проверяем Xray DDoS
sudo fail2ban-client status xray-ddos

# Смотрим в реальном времени
sudo tail -f /var/log/fail2ban.log | grep -i ban
```

### Скрипт для мониторинга DDoS в реальном времени:

```bash
# Создаем скрипт
cat > ~/monitor_attacks.sh << 'EOF'
#!/bin/bash

echo "=== Real-time Attack Monitor ==="
while true; do
    clear
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Network Activity:"
    echo ""
    
    # Заблокированные IP
    echo "--- Blocked by Fail2Ban ---"
    sudo fail2ban-client status sshd 2>/dev/null | grep "IP list"
    
    # Соединения на 443/8443
    echo ""
    echo "--- Active Connections ---"
    netstat -tnp 2>/dev/null | grep -E '443|8443' | wc -l
    
    # Топ источников
    echo ""
    echo "--- Top Source IPs ---"
    netstat -tnp 2>/dev/null | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10
    
    # Очищаем экран через 5 сек
    sleep 5
done
EOF

chmod +x ~/monitor_attacks.sh

# Запускаем
~/monitor_attacks.sh
```

---

## 🚀 ШАГ 7: Auto-restart контейнеров

Если контейнер упадет от DDoS - автоматически перезапускаем:

```bash
# Редактируем docker-compose.yml
nano docker-configs/docker-compose.yml

# Добавляем к каждому сервису restart policy:
```

```yaml
services:
  vk-server:
    image: xray/xray:latest
    container_name: vk-xray-server
    restart: always  # ← ДОБАВЛЯЕМ
    ports:
      - "443:443"
    # ...

  nl-server:
    image: xray/xray:latest
    container_name: nl-xray-server
    restart: always  # ← ДОБАВЛЯЕМ
    ports:
      - "8444:443"
      - "8445:8443"
    # ...

  vpn-bot:
    build:
      context: ./nl-server
      dockerfile: Dockerfile.bot
    restart: always  # ← ДОБАВЛЯЕМ
    # ...
```

---

## 🌐 ШАГ 8: DDoS защита через CDN/ISP

### Вариант 1: Cloudflare Proxy (для бота)

Если у тебя есть домен с Cloudflare:

```bash
# Меняем DNS на Cloudflare nameservers
# Включаем Proxy в Cloudflare:
# - DNS запись: example.com → 85.239.56.174
# - Включаем "Proxied" (оранжевая облако)
# - Включаем DDoS protection
```

### Вариант 2: Запрос у ISP

Свяжись с провайдером:
- Запроси "DDoS mitigation service"
- Обычно включено в dedicated server плане
- Просят указать публичный IP

### Вариант 3: Tercet/Yandex Cloud Protection

Если сервер на Yandex Cloud:

```bash
# На NL сервере (Yandex):
# Идешь в Yandex Cloud Console → Network → Security Group
# Добавляешь правило:
# - Direction: Ingress
# - Protocol: TCP
# - Ports: 443, 8443
# - CIDR block: 0.0.0.0/0
# - Включаешь DDoS protection
```

---

## 🔐 ШАГ 9: SSH Hardening

### На обоих серверах:

```bash
sudo nano /etc/ssh/sshd_config

# Делаешь следующие изменения:
```

```bash
# Откл root логин
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Откл password auth (только keys)
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Переносим SSH на нестандартный port (опционально)
sed -i 's/#Port 22/Port 2222/' /etc/ssh/sshd_config

# Откл X11 forwarding
sed -i 's/X11Forwarding yes/X11Forwarding no/' /etc/ssh/sshd_config

# Лимит auth attempts
sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config

# Перезагружаем
sudo systemctl restart sshd
```

---

## ✅ Финальный Checklist Защиты

- [ ] **Firewall (UFW)**
  - [ ] SSH on 22/tcp with limit
  - [ ] 443/tcp allow
  - [ ] 8443/tcp allow (NL только)
  - [ ] All other ports deny

- [ ] **Fail2Ban**
  - [ ] sshd jail enabled
  - [ ] xray-ddos jail enabled
  - [ ] Maxretry = 3 для SSH, 100 для DDoS
  - [ ] Bantime = 3600 для SSH, 600 для DDoS

- [ ] **Xray Rate Limiting**
  - [ ] maxConcurrentConns в config.json
  - [ ] connLimit параметры установлены
  - [ ] Конфиг протестирован (`xray -test`)

- [ ] **Bot Rate Limiting**
  - [ ] rate_limit_check функция добавлена
  - [ ] MAX_REQUESTS_PER_MINUTE = 30
  - [ ] MAX_REQUESTS_PER_HOUR = 500

- [ ] **Logging и Мониторинг**
  - [ ] Docker logging конфигурирован
  - [ ] Fail2ban логи проверяются
  - [ ] Monitor скрипт готов

- [ ] **Auto-restart**
  - [ ] restart: always в docker-compose.yml
  - [ ] Все 3 сервиса покрыты

- [ ] **SSH Hardening**
  - [ ] PermitRootLogin no
  - [ ] PasswordAuthentication no
  - [ ] MaxAuthTries 3
  - [ ] X11Forwarding no

- [ ] **DDoS Protection**
  - [ ] ISP mitigation активирована (если доступна)
  - [ ] CDN/Cloudflare настроена (для бота)
  - [ ] Firewall rules проверены

---

## 🌀 Полная команда для быстрой защиты

### На VK сервере:

```bash
ssh root@243.x.x.x << 'EOF'
sudo apt update && sudo apt install -y ufw fail2ban

# UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw limit 22/tcp
sudo ufw enable

# Fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# SSH hardening
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config
sudo systemctl restart sshd

echo "✅ VK защищен"
EOF
```

### На NL сервере:

```bash
ssh root@85.239.56.174 << 'EOF'
sudo apt update && sudo apt install -y ufw fail2ban

# UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8443/tcp
sudo ufw limit 22/tcp
sudo ufw enable

# Fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# SSH hardening
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#MaxAuthTries 6/MaxAuthTries 3/' /etc/ssh/sshd_config
sudo systemctl restart sshd

echo "✅ NL защищен"
EOF
```

---

## 📊 После всего этого:

```
✅ UFW блокирует ненужные порты
✅ Fail2ban банит после 3 неудачных SSH попыток
✅ Fail2ban банит при DDoS на 443/8443
✅ Xray ограничивает соединения per IP
✅ Bot rate-limit защищает от spam
✅ SSH работает только с ключами
✅ Контейнеры автоматически перезагружаются
✅ Все логируется и мониторится

Система в боеготовности! 🛡️
```

**Помни:**防
