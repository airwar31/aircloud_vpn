# 📦 АВТОМАТИЧЕСКАЯ УСТАНОВКА - ПОЛНЫЙ ПАКЕТ

## 🎁 Что в комплекте

```
✅ 2 Bash скрипта для автоматической установки
✅ 4 Подробных гайда с объяснениями
✅ Готовые команды copy-paste
✅ Чеклисты для проверки
```

---

## 📂 СОЗДАННЫЕ ФАЙЛЫ

### 🚀 Скрипты установки:

| Файл | Для | Время | Использование |
|------|-----|-------|----------------|
| **install-vk.sh** | VK сервер | ~5 мин | `./install-vk.sh` |
| **install-nl.sh** | NL сервер | ~8 мин | `./install-nl.sh` |

### 📚 Документация:

| Файл | Описание | Когда читать |
|------|---------|--------------|
| **AUTO_INSTALLATION_README.md** | 🎯 ГЛАВНЫЙ ФАЙЛ - начни отсюда | ВСЕ |
| **INSTALLATION_DATA_GUIDE.md** | 📋 Где получить каждый параметр | ПЕРЕД установкой |
| **QUICK_INSTALLATION.md** | ⚡ Пошаговый старт | ЕСЛИ устанавливаешь вручную |
| **SAFE_UPDATE_GUIDE.md** | 🔄 Как обновлять без проблем | ПОТОМ (для обновлений) |
| **SECURITY_HARDENING_GUIDE.md** | 🛡️ Усиление защиты | ПОТОМ (для безопасности) |
| **DEPLOYMENT_GUIDE_TWO_SERVERS.md** | 📖 Подробное объяснение | ЕСЛИ нужно понимать детали |

---

## 🎯 ПОРЯДОК ИСПОЛЬЗОВАНИЯ

```
1. ПРОЧИТАТЬ:
   └─ AUTO_INSTALLATION_README.md (2 мин)

2. ПОДГОТОВИТЬ:
   └─ Собрать все данные из INSTALLATION_DATA_GUIDE.md (15 мин)

3. УСТАНОВИТЬ VK:
   ├─ Загрузить install-vk.sh на VK сервер
   ├─ Запустить: ./install-vk.sh
   └─ Ответить на вопросы (5 мин)

4. УСТАНОВИТЬ NL:
   ├─ Загрузить install-nl.sh на NL сервер
   ├─ Запустить: ./install-nl.sh
   └─ Ответить на вопросы (8 мин)

5. ПРОТЕСТИРОВАТЬ:
   ├─ Проверить что контейнеры запущены
   ├─ Тестировать VPN через бота
   └─ Готово! 🎉
```

---

## 🚀 САМЫЙ БЫСТРЫЙ СПОСОБ (5 минут)

### ШАГ 1️⃣ Подготовь данные:

```bash
# Запиши эти значения (из INSTALLATION_DATA_GUIDE.md):

VK_IP = X.X.X.X              # curl -s https://api.ipify.org на VK
NL_IP = X.X.X.X              # curl -s https://api.ipify.org на NL
DOMAIN = nl.vpn.example.com   # Твой домен (DNS настроен)
BOT_TOKEN = 123...            # От @BotFather
YOOKASSA_SHOP_ID = 123        # От https://yookassa.ru
YOOKASSA_SECRET_KEY = live_   # От https://yookassa.ru
ADMIN_ID = 1234567890         # От @userinfobot
```

### ШАГ 2️⃣ На VK сервере:

```bash
ssh root@<VK_IP>

# Генерируем Reality ключи (ЗАПИШИ результат!)
xray x25519
# Private key: XXXX <- COPY THIS
# Public key:  YYYY

# Загружаем скрипт
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-vk.sh
chmod +x install-vk.sh

# Запускаем (отвечаем на вопросы)
./install-vk.sh

# ~ 5 минут ждем...
```

### ШАГ 3️⃣ На NL сервере:

```bash
ssh root@<NL_IP>

# Загружаем скрипт
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-nl.sh
chmod +x install-nl.sh

# Запускаем (отвечаем на вопросы - используем ТАКИЕ ЖЕ как на VK)
./install-nl.sh

# ~ 8 минут ждем...
```

### ШАГ 4️⃣ Проверяем:

```bash
# На оба сервере:
docker-compose ps
# Должны быть Up все контейнеры

# Тестируем VPN:
# 1. Находим бота в Telegram
# 2. /start
# 3. Выбираем подписку
# 4. Подключаемся
# 5. Проверяем IP (должен быть NL IP)
```

---

## 📋 НУЖНЫЕ ДАННЫЕ - КРАТКАЯ СПРАВКА

### ОДИН РАЗ копируешь эти данные для ОБОИХ серверов:

```env
# Telegram
BOT_TOKEN=123456789:ABCxyz123...
ADMIN_IDS=1262543088

# YooKassa
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=live_xxxxx

# UUIDs (генерируются один раз)
UUID_DOUBLE=550e8400-e29b-41d4-a716-446655440000
UUID_SINGLE=550e8400-e29b-41d4-a716-446655440001
```

### РАЗНЫЕ для каждого сервера:

```env
# VK сервер
VK_SERVER=89.208.86.167
VK_PRIVATE_KEY=XXXX...  (из xray x25519)

# NL сервер
NL_SERVER=85.239.56.174
NL_DOMAIN=nl.vpn.example.com
LETSENCRYPT_EMAIL=admin@example.com  (для SSL)
```

---

## ✅ КОГДА ГОТОВО

После завершения обоих скриптов **АВТОМАТИЧЕСКИ**:

```
✅ Docker установлен и работает
✅ Проект клонирован из Git
✅ Reality ключи сгенерированы (VK)
✅ SSL сертификаты получены (NL)
✅ .env файл создан и заполнен
✅ Xray конфиги обновлены
✅ Firewall настроен
✅ Fail2Ban активирован
✅ Контейнеры собраны и запущены
✅ Все проверено и готово к использованию
```

---

## 🔗 СВЯЗЬ МЕЖДУ ДОКУМЕНТАМИ

```
AUTO_INSTALLATION_README.md (СТАРТ)
     │
     ├─→ INSTALLATION_DATA_GUIDE.md
     │   (Где получить каждый параметр)
     │
     ├─→ install-vk.sh (Скрипт)
     │   (Автоматический, копи-паста)
     │
     ├─→ install-nl.sh (Скрипт)
     │   (Автоматический, копи-паста)
     │
     ├─→ QUICK_INSTALLATION.md
     │   (Если не используешь скрипты)
     │
     └─→ DEPLOYMENT_GUIDE_TWO_SERVERS.md
         (Для понимания архитектуры)
         
ПОТОМ:
     ├─→ SAFE_UPDATE_GUIDE.md (Как обновлять)
     └─→ SECURITY_HARDENING_GUIDE.md (Укрепить защиту)
```

---

## 🎓 УРОВНИ СЛОЖНОСТИ

| Уровень | Описание | Файл | Время |
|---------|---------|------|-------|
| 🟢 **НОВИЧОК** | Просто запустить скрипты | install-vk.sh + install-nl.sh | 15 мин |
| 🟡 **СРЕДНИЙ** | Понимать что делается | QUICK_INSTALLATION.md | 30 мин |
| 🔴 **ПРОДВИНУТЫЙ** | Полное понимание | DEPLOYMENT_GUIDE_TWO_SERVERS.md | 2 часа |

---

## 🚨 ВАЖНЫЕ ЗАМЕЧАНИЯ

### БЕЗОПАСНОСТЬ:
```
⚠️ НИКОГДА не выкладывай публично:
  - .env файл
  - BOT_TOKEN
  - YOOKASSA_SECRET_KEY
  - VK_PRIVATE_KEY
  
✅ ЭТО ИНФОРМАЦИЯ ДОЛЖНА БЫТЬ В .env (локально)
```

### СИНХРОНИЗАЦИЯ:
```
ОДИНАКОВЫЕ на VK и NL:
  ✅ BOT_TOKEN
  ✅ YOOKASSA данные
  ✅ UUID_DOUBLE
  ✅ UUID_SINGLE
  ✅ ADMIN_ID

РАЗНЫЕ:
  ✅ VK_IP vs NL_IP
  ✅ VK_PRIVATE_KEY (только на VK)
  ✅ NL_DOMAIN (только на NL)
```

### ПОРЯДОК:
```
1. СНАЧАЛА VK сервер
2. ПОТОМ NL сервер
3. НЕЛЬЗЯ наоборот!
```

---

## 📞 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

1. **Скрипт не запускается**
   ```bash
   chmod +x install-vk.sh
   chmod +x install-nl.sh
   ```

2. **Нет интернета на сервере**
   ```bash
   ping 8.8.8.8
   cat /etc/resolv.conf  # Проверь DNS
   ```

3. **Docker не устанавливается**
   ```bash
   apt-get update
   apt-get install -y docker.io
   ```

4. **Контейнер не стартует**
   ```bash
   docker-compose logs <service> | grep -i error
   docker-compose exec <service> xray -test -config /etc/xray/config.json
   ```

5. **SSL сертификат не получен**
   ```bash
   nslookup nl.vpn.example.com  # Должен раз Resolve
   certbot certonly --standalone -d nl.vpn.example.com \
     --email admin@example.com --agree-tos
   ```

Все ошибки описаны в [AUTO_INSTALLATION_README.md](AUTO_INSTALLATION_README.md)

---

## 📊 ОБЩАЯ СТАТИСТИКА

```
📝 Документов создано: 4
🚀 Скриптов создано: 2
⏱️ Общее время установки: ~15 минут
🎯 Сложность освоения: НИЗКАЯ
🔧 Требуется ручной ввод: МИН (только ответы на вопросы)
✅ Автоматизация: MAX (все остальное делают скрипты)
```

---

## 🎉 ГОТОВО!

Теперь ты имеешь полный набор для автоматического развертывания. 

### Начни отсюда:
1. Прочитай [AUTO_INSTALLATION_README.md](AUTO_INSTALLATION_README.md)
2. Собери данные из [INSTALLATION_DATA_GUIDE.md](INSTALLATION_DATA_GUIDE.md)
3. Запусти скрипты

**Все остальное сделают скрипты! 🤖**

---

**Удачи с установкой! 🚀**
