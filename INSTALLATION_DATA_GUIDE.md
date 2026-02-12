# 📋 РУКОВОДСТВО: НЕОБХОДИМЫЕ ДАННЫЕ ДЛЯ АВТОМАТИЧЕСКОЙ УСТАНОВКИ

## 🎯 Краткий обзор

Для развертывания проекта на двух серверах нужны определенные данные. Это руководство объясняет, какие данные нужны и как их получить.

---

## 📊 Таблица необходимых данных

| Данные | Где получить | Формат | Нужно знать |
|--------|--------------|--------|------------|
| VK Server IP | Провайдер | Числа:Числа.Числа.Числа | Публичный IP VK сервера |
| NL Server IP | Провайдер | Числа:Числа.Числа.Числа | Публичный IP NL сервера |
| NL Domain | DNS / Регистратор | example.com | Домен, указывающий на NL IP |
| BOT_TOKEN | Telegram BotFather | 123456789:ABCxyz123... | Telegram бот |
| YOOKASSA_SHOP_ID | YooKassa кабинет | Числа | ID магазина для платежей |
| YOOKASSA_SECRET_KEY | YooKassa кабинет | Строка | Ключ для платежей |
| VK_PRIVATE_KEY | Генерируется | 88 символов | Reality приватный ключ |
| VK_PUBLIC_KEY | Генерируется | 88 символов | Reality публичный ключ |
| UUID_DOUBLE | Генерируется или существует | UUID формат | ID для double tunnel |
| UUID_SINGLE | Генерируется или существует | UUID формат | ID для single tunnel |
| ADMIN_ID | Telegram аккаунт | Числа (9-10 цифр) | Telegram ID админа |

---

## 🔍 ШАГ ЗА ШАГОМ: ГДЕ НАЙТИ КАЖДОЕ ЗНАЧЕНИЕ

### 1️⃣ **VK Server IP** (Публичный IP VK сервера)

#### Как получить:
```bash
# На VK сервере выполни:
curl -s https://api.ipify.org
# или
hostname -I
```

#### Пример:
```
89.208.86.167
```

#### Где использовать:
- В скрипте install-vk.sh
- В .env файле (VK_SERVER)

---

### 2️⃣ **NL Server IP** (Публичный IP NL сервера)

#### Как получить:
```bash
# На NL сервере выполни:
curl -s https://api.ipify.org
```

#### Пример:
```
85.239.56.174
```

#### Где использовать:
- В скрипте install-nl.sh
- В .env файле (NL_SERVER)

---

### 3️⃣ **NL Domain** (Домен для NL сервера)

#### Что это:
Доменное имя, которое указывает на NL сервер. Нужно для SSL сертификата.

#### Как получить:
1. Зарегистрируй домен (Namecheap, GoDaddy, 1и1 и т.д.)
2. В DNS запись добавь A record:
   ```
   Name:  nl.vpn
   Type:  A
   Value: 85.239.56.174  (IP NL сервера)
   ```
3. Подожди 5-15 минут чтобы DNS распространился

#### Проверка:
```bash
nslookup nl.vpn.example.com
# или
dig nl.vpn.example.com
```

#### Пример:
```
nl.vpn.example.com
```

#### Где использовать:
- В скрипте install-nl.sh
- В .env файле (NL_DOMAIN)
- В nl-server/config.json (serverName)

---

### 4️⃣ **BOT_TOKEN** (Telegram Bot Token)

#### Что это:
Уникальный токен для твоего Telegram бота. Нужен для подключения бота к Telegram.

#### Как получить:
1. Откройте @BotFather в Telegram
2. Напишите `/start`
3. Напишите `/newbot`
4. Дайте боту имя (например "AirCloud VPN Bot")
5. Дайте боту username (например "aircloud_vpn_bot")
6. Копируйте токен, который вам выдал BotFather

#### Пример:
```
123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi
```

#### Где использовать:
- В .env файле (BOT_TOKEN)
- ОДИНАКОВЫЙ на VK и NL!

---

### 5️⃣ **YOOKASSA_SHOP_ID** (ID магазина YooKassa)

#### Что это:
ID авторизованного магазина в системе платежей YooKassa (для приема платежей).

#### Как получить:
1. Зарегистрируйтесь на https://yookassa.ru
2. Авторизуйтесь в личном кабинете
3. Перейдите в "Мой магазин" → "Интеграция"
4. Найдите "Shop ID" (обычно это число типа 123456)

#### Пример:
```
1125955
```

#### Где использовать:
- В .env файле (YOOKASSA_SHOP_ID)
- ОДИНАКОВЫЙ на VK и NL!

---

### 6️⃣ **YOOKASSA_SECRET_KEY** (Секретный ключ YooKassa)

#### Что это:
Приватный ключ для аутентификации API YooKassa. ХРАНИ В СЕКРЕТЕ!

#### Как получить:
1. В личном кабинете YooKassa → "Интеграция"
2. Найди "API-ключ"
3. Скопируй его (обычно начинается с "live_" или "test_")

#### Пример:
```
live_-bVWPswAIpvcSf4F6hic4jAxVN-b1efMMuMySSiZMYk
```

#### Где использовать:
- В .env файле (YOOKASSA_SECRET_KEY)
- ОДИНАКОВЫЙ на VK и NL!
- **НИКОГДА не выкладывай в открытый код!**

---

### 7️⃣ **VK_PRIVATE_KEY** (Reality Приватный ключ)

#### Что это:
Криптографический ключ для обфускации Reality протокола на VK сервере.

#### Как получить:
1. На VK сервере выполни:
   ```bash
   xray x25519
   ```
2. Скопируй строку после "Private key:"

#### Пример:
```
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (88 символов)
```

#### Где использовать:
- В .env файле (VK_PRIVATE_KEY)
- В vk-server/config.json
- ТОЛЬКО на VK сервере!

#### Важно:
```bash
# Генерируется командой:
xray x25519

# Результат:
Private key: <КОПИРУЙ ЭТО>
Public key:  <И ЭТО ДЛЯ ПРОВЕРКИ>
```

---

### 8️⃣ **VK_PUBLIC_KEY** (Reality Публичный ключ)

#### Что это:
Публичная часть Reality ключа (для проверки).

#### Как получить:
Генерируется вместе с Private key:
```bash
xray x25519
```

#### Пример:
```
YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY (88 символов)
```

#### Где использовать:
- В .env файле (VK_PUBLIC_KEY)
- Для информации (не обязателен в config.json)

---

### 9️⃣ **UUID_DOUBLE** (ID для двойного туннеля)

#### Что это:
Уникальный идентификатор для users двойного туннеля (VK → NL).

#### Как получить:
Генерируется автоматически скриптом или вручную:
```bash
uuidgen
# или
python3 -c "import uuid; print(uuid.uuid4())"
```

#### Пример:
```
550e8400-e29b-41d4-a716-446655440000
```

#### Где использовать:
- В .env файле
- В vk-server/config.json (inbound settings)
- В nl-server/config.json (inbound settings)
- ОДИНАКОВЫЙ на VK и NL!

---

### 🔟 **UUID_SINGLE** (ID для одиночного туннеля)

#### Что это:
Уникальный идентификатор для users одиночного туннеля (только NL).

#### Как получить:
```bash
uuidgen
```

#### Пример:
```
550e8400-e29b-41d4-a716-446655440001
```

#### Где использовать:
- В .env файле
- В nl-server/config.json (port 8443 inbound)
- ОДИНАКОВЫЙ на VK и NL!

---

### 1️⃣1️⃣ **ADMIN_ID** (Telegram ID админа)

#### Что это:
Твой личный Telegram ID. Нужен для админских команд бота.

#### Как получить:
1. Отправь боту @userinfobot сообщение /start
2. Бот выдаст твой ID (число)

#### Или вручную:
1. Создай тестового бота
2. Отправь ему сообщение
3. В логах будет твой ID

#### Пример:
```
1262543088
```

#### Где использовать:
- В .env файле (ADMIN_IDS)
- В обоих скриптах (install-vk.sh и install-nl.sh)

---

## 🔐 ПОСЛЕДОВАТЕЛЬНОСТЬ ПОЛУЧЕНИЯ ДАННЫХ

```
1. Подготовка (НЕ на серверах):
   ✅ Зарегистрировать домен (nl.vpn.example.com)
   ✅ Получить BOT_TOKEN от @BotFather
   ✅ Получить YOOKASSA данные
   ✅ Получить свой ADMIN_ID

2. VK сервер:
   ✅ Получить IP (curl -s https://api.ipify.org)
   ✅ Сгенерировать Reality ключи (xray x25519)
   ✅ Запустить install-vk.sh

3. NL сервер:
   ✅ Получить IP
   ✅ Получить SSL сертификат (автоматично в скрипте)
   ✅ Запустить install-nl.sh

4. Проверка:
   ✅ Тестировать подключение через бота
```

---

## 📝 ФОРМАТ И ПРИМЕРЫ

### Reality ключи (VK_PRIVATE_KEY, VK_PUBLIC_KEY)
```
Длина: ровно 88 символов
Формат: base64
Пример: aaBBccDDeeFFggHHiiJJkkLLmmNNooPPqqRRssTTuuVVwwXXyyZZaabbccddeeFFgg==
```

### UUID (UUID_DOUBLE, UUID_SINGLE)
```
Формат: 550e8400-e29b-41d4-a716-446655440000
Команда: uuidgen
Валидизация: https://www.uuidvalidator.net/
```

### IP адреса (VK_SERVER, NL_SERVER)
```
Формат: XXX.XXX.XXX.XXX
Пример: 89.208.86.167
```

### Telegram ID (ADMIN_ID)
```
Формат: целое число (9-10 цифр)
Пример: 1262543088
Как проверить: @userinfobot
```

### Domain (NL_DOMAIN)
```
Формат: example.com или sub.example.com
Пример: nl.vpn.example.com
DNS: A record должен указывать на NL_SERVER IP
```

---

## ✅ ЧЕКЛИСТ ПЕРЕД УСТАНОВКОЙ

### На локальной машине:
- [ ] Домен зарегистрирован
- [ ] DNS A запись указывает на NL IP
- [ ] BOT_TOKEN получен от @BotFather
- [ ] YOOKASSA аккаунт создан
- [ ] ADMIN_ID получен

### На VK сервере:
- [ ] Ubuntu 22.04+ установлена
- [ ] SSH доступ работает
- [ ] Публичный IP известен
- [ ] Порт 22 открыт (для SSH)
- [ ] Порт 443 открыт (для Xray)
- [ ] curl доступен (для скрипта)

### На NL сервере:
- [ ] Ubuntu 22.04+ установлена
- [ ] SSH доступ работает
- [ ] Публичный IP известен
- [ ] Домен настроен на этот IP
- [ ] Порты 22, 443, 8443 открыты
- [ ] curl доступен

---

## 🚀 БЫСТРЫЙ СТАРТ С ДАННЫМИ

### Скопируй и заполни эту форму:

```bash
# 🎯 Данные для УСТАНОВКИ

# Сервер VK (Россия)
export VK_IP=XX.XXX.XXX.XXX
export VK_PRIVATE_KEY="ВСТАВЬ_СЮДА_88_СИМВОЛА"

# Сервер NL (Нидерланды)
export NL_IP=XX.XXX.XXX.XXX
export NL_DOMAIN="nl.vpn.example.com"

# Telegram
export BOT_TOKEN="123456789:ABCxyz..."
export ADMIN_ID=1234567890

# YooKassa
export YOOKASSA_SHOP_ID=123456
export YOOKASSA_SECRET_KEY="live_xxxxx"

# UUIDs
export UUID_DOUBLE=$(uuidgen)
export UUID_SINGLE=$(uuidgen)

# 📋 Вывод для проверки:
echo "VK_IP: $VK_IP"
echo "NL_IP: $NL_IP"
echo "NL_DOMAIN: $NL_DOMAIN"
echo "BOT_TOKEN: ***СКРЫТО***"
echo "ADMIN_ID: $ADMIN_ID"
echo "UUID_DOUBLE: $UUID_DOUBLE"
echo "UUID_SINGLE: $UUID_SINGLE"
```

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### БЕЗОПАСНОСТЬ:
1. **НИКОГДА не выкладывай:**
   - YOOKASSA_SECRET_KEY
   - VK_PRIVATE_KEY
   - BOT_TOKEN
   - .env файл

2. **Храни в безопасности:**
   - Сделай backup .env файла
   - Сохраняй все ключи локально
   - Используй .env.example как шаблон

3. **Регулярно проверяй:**
   - SSH ключи (без паролей)
   - Firewall правила
   - SSL сертификаты (автообновление)

### ДОМЕН:
- Убедись что DNS распространился (`nslookup` должен найти)
- Используй HTTPS для домена (Certbot получит cert автоматически)
- При обновлении IP - обнови DNS запись

### НОВЫЕ КЛЮЧИ:
- Reality ключи - генерируются один раз при установке
- UUID можно использовать повторно между клиентами
- BOT_TOKEN привязан к конкретному боту (не менять)

---

## 🔗 ПОЛЕЗНЫЕ ССЫЛКИ

- **Telegram BotFather:** https://t.me/BotFather
- **YooKassa:** https://yookassa.ru
- **Сгенерировать UUID:** https://www.uuidgenerator.net/
- **Проверить Telegram ID:** @userinfobot
- **Проверить IP:** https://api.ipify.org
- **Проверить домен:** https://www.nslookup.io/

---

**Когда все данные готовы → запускай install-vk.sh и install-nl.sh! 🚀**
