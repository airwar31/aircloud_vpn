# 🚀 БЫСТРЫЙ СТАРТ: ПОШАГОВАЯ УСТАНОВКА

## 📋 Предварительные требования

Перед началом убедись что у тебя есть:

- ✅ **2 сервера** (VK Russia + NL Netherlands) с Ubuntu 22.04+
- ✅ **SSH доступ** к обоим серверам
- ✅ **Доменное имя** (для NL сервера)
- ✅ **Telegram бот токен** (от @BotFather)
- ✅ **YooKassa аккаунт** (для платежей)
- ✅ Все данные из [INSTALLATION_DATA_GUIDE.md](INSTALLATION_DATA_GUIDE.md)

---

## 🎯 ФАЗА 1: ПОДГОТОВКА (на локальной машине)

### Шаг 1.1: Подготовь данные

Заполни эту информацию:

```bash
# Запиши эти значения
VK_IP = ???                           # IP VK сервера
NL_IP = ???                           # IP NL сервера
DOMAIN = nl.vpn.example.com           # Твой домен
BOT_TOKEN = 123456:ABC...             # От @BotFather
ADMIN_ID = 1234567890                 # Твой Telegram ID
YOOKASSA_SHOP_ID = ???                # ID магазина YooKassa
YOOKASSA_SECRET_KEY = live_???        # Ключ YooKassa
```

### Шаг 1.2: Настрой DNS

Если ты еще не настроил DNS для домена:

```bash
# Зайди в управление DNS у регистратора (Namecheap, GoDaddy и т.д.)
# Добавь A запись:
Hostname: nl.vpn
Type: A
Value: <NL_IP>
TTL: 3600

# Подожди 5-15 минут чтобы DNS распространился
# Проверь: nslookup nl.vpn.example.com
```

---

## 🖥️ ФАЗА 2: УСТАНОВКА VK СЕРВЕРА

### Шаг 2.1: Генерируем Reality ключи (на VK)

```bash
# Подключись к VK серверу
ssh root@<VK_IP>

# Сгенерируй Reality ключи
xray x25519

# Результат выглядит так:
# Private key: XXXXX...  <- ЗАПИШИ ЭТО (VK_PRIVATE_KEY)
# Public key:  YYYYY...  <- ЗАПИШИ ЭТО (VK_PUBLIC_KEY)
```

### Шаг 2.2: Загрузи скрипт установки на VK

```bash
# На локальной машине
scp install-vk.sh root@<VK_IP>:/root/

# Или скачай напрямую на VK сервер
ssh root@<VK_IP>
cd /root
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-vk.sh
chmod +x install-vk.sh
```

### Шаг 2.3: Запусти установку на VK

```bash
# На VK сервере
./install-vk.sh

# Скрипт попросит ввести данные:
VK IP: <ENTER - автоматический или указать>
NL IP: <ввести NL_IP>
NL Domain: nl.vpn.example.com
BOT_TOKEN: <вставить>
YOOKASSA_SHOP_ID: <вставить>
YOOKASSA_SECRET_KEY: <вставить>
ADMIN_ID: <вставить>
VK_PRIVATE_KEY: <вставить ключ из шага 2.1>

# Генеривать новые Reality ключи? y (да, если их нет)
# Генеривать новые UUID? new (да, для новой установки)

# Ждем завершения (~3 минуты)
```

### Шаг 2.4: Проверь VK сервер

```bash
# На VK сервере
docker-compose ps
# Должно быть:
# vk-xray-server    Up

# Проверь логи
docker-compose logs vk-server | tail -20
# Не должно быть ERROR или Exception

# Проверь порты
netstat -tlnp | grep 443
# 0.0.0.0:443 должен быть LISTEN
```

### Шаг 2.5: Сохрани данные

После успешной установки VK сервера:

```bash
# На VK сервере, вывод UUID и ключей:
cat /opt/aircloud_vpn/docker-configs/.env | grep UUID
cat /opt/aircloud_vpn/docker-configs/.env | grep VK_PRIVATE_KEY

# Запиши эти значения для NL сервера:
UUID_DOUBLE = ???
UUID_SINGLE = ???
VK_PRIVATE_KEY = ???
```

---

## 🌍 ФАЗА 3: УСТАНОВКА NL СЕРВЕРА

### Шаг 3.1: Загрузи скрипт на NL

```bash
# На локальной машине
scp install-nl.sh root@<NL_IP>:/root/

# Или скачай напрямую
ssh root@<NL_IP>
cd /root
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-nl.sh
chmod +x install-nl.sh
```

### Шаг 3.2: Запусти установку на NL

```bash
# На NL сервере
./install-nl.sh

# Скрипт попросит ввести данные:
Domain: nl.vpn.example.com
Email (for Let's Encrypt): admin@example.com
VK IP: <VK_IP>
NL IP: <ENTER - автоматический>
BOT_TOKEN: <такой же как на VK>
YOOKASSA_SHOP_ID: <такой же как на VK>
YOOKASSA_SECRET_KEY: <такой же как на VK>
ADMIN_ID: <такой же как на VK>

# Ждем получения SSL сертификата и установки (~5 минут)
```

### Шаг 3.3: Проверь NL сервер

```bash
# На NL сервере
docker-compose ps
# Должно быть 3 сервиса:
# nl-xray-server          Up
# vpn-telegram-bot        Up

# Проверь логи Xray
docker-compose logs nl-server | tail -20
# Ищи строки про listening на 443 и 8443

# Проверь логи бота
docker-compose logs vpn-bot | tail -20
# Должно быть про Bot started successfully

# Проверь SSL сертификат
ls -la /opt/aircloud_vpn/docker-configs/nl-server/certs/
# fullchain.pem и privkey.pem должны быть

# Проверь конфиг
docker-compose exec nl-server xray -test -config /etc/xray/config.json
# "The config is valid"
```

---

## 🧪 ФАЗА 4: ТЕСТИРОВАНИЕ

### Шаг 4.1: Проверь подключение между серверами

```bash
# На NL сервере
docker-compose logs nl-server | grep -i "accept\|inbound"
# Должны быть логи о принятых соединениях

# На VK сервере
docker-compose logs vk-server | grep -i "outbound\|connected"
# Должны быть логи об исходящих соединениях
```

### Шаг 4.2: Тестирование VPN через бота

```bash
# 1. Найди своего бота в Telegram (по BOT_TOKEN)
# 2. Напиши боту /start
# 3. Выбери примерку:
#    - Single VPN: прямое подключение на NL
#    - Double VPN: VK → NL цепь

# 4. Получи конфиг и импортируй в VPN клиент (V2RayNG, Clash и т.д.)
# 5. Проверь подключение
```

### Шаг 4.3: Проверь IP адрес

```bash
# При подключении через VPN проверь IP:
# На телефоне/ПК перейди на https://ipinfo.io
# Должен быть IP Netherlands (85.239.56.174 или похожий)
```

---

## 📋 ТАБЛИЦА СИНХРОНИЗАЦИИ ДАННЫХ

Эти данные должны быть **ОДИНАКОВЫМИ** на VK и NL:

| Параметр | VK | NL | Статус |
|----------|----|----|--------|
| BOT_TOKEN | ✅ | ✅ | Одинаков |
| YOOKASSA_SHOP_ID | ✅ | ✅ | Одинаков |
| YOOKASSA_SECRET_KEY | ✅ | ✅ | Одинаков |
| UUID_DOUBLE | ✅ | ✅ | Одинаков |
| UUID_SINGLE | ✅ | ✅ | Одинаков |
| ADMIN_ID | ✅ | ✅ | Одинаков |

Эти данные **РАЗНЫЕ**:

| Параметр | VK | NL |
|----------|----|----|
| VK_PRIVATE_KEY | ✅ Используется | — |
| VK_SERVER | ✅ Это сервер | Адрес VK |
| NL_SERVER | Адрес NL | ✅ Это сервер |
| NL_DOMAIN | — | ✅ Используется |

---

## 🔧 ПОЛЕЗНЫЕ КОМАНДЫ ПОСЛЕ УСТАНОВКИ

### Мониторинг:

```bash
# На любом сервере
cd /opt/aircloud_vpn/docker-configs

# Статус всех контейнеров
docker-compose ps

# Логи в реальном времени
docker-compose logs -f vk-server    # На VK
docker-compose logs -f nl-server    # На NL
docker-compose logs -f vpn-bot      # На NL

# Перезагрузка контейнера
docker-compose restart vk-server    # На VK
docker-compose restart nl-server    # На NL
docker-compose restart vpn-bot      # На NL

# Остановка/запуск
docker-compose stop
docker-compose up -d
```

### Обновление:

```bash
cd /opt/aircloud_vpn

# Получить новую версию
git pull origin main

# Пересобрать контейнеры
cd docker-configs
docker-compose build
docker-compose up -d
```

### Отладка:

```bash
# На VK сервере
docker-compose exec vk-server xray -test -config /etc/xray/config.json

# На NL сервере
docker-compose exec nl-server xray -test -config /etc/xray/config.json

# Проверить подключение к порту
telnet 85.239.56.174 443
telnet 85.239.56.174 8443

# Проверить логи Xray
docker-compose exec nl-server tail -f /var/log/xray/access.log
```

---

## ⚠️ ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК

### Контейнер не стартует:

```bash
# Проверь логи
docker-compose logs <service>

# Проверь конфиг
docker-compose exec <service> xray -test -config /etc/xray/config.json

# Перестроим контейнер
docker-compose down <service>
docker-compose build <service>
docker-compose up -d <service>
```

### Нет подключения между серверами:

```bash
# Проверь firewall
ufw status verbose

# Проверь что порты открыты
netstat -tlnp | grep -E '443|8443'

# Проверь DNS с VK сервера
nslookup <NL_DOMAIN>
ping <NL_IP>
```

### SSL сертификат не получен:

```bash
# На NL сервере
certbot renew --dry-run

# Проверь logs Certbot
cat /var/log/letsencrypt/letsencrypt.log
```

### .env файл испорчен после установки:

```bash
# Восстанови из бэкапа
cp /opt/aircloud_vpn/docker-configs/backups/*/. env.bak /opt/aircloud_vpn/docker-configs/.env

# Или переделай вручную
cp /opt/aircloud_vpn/docker-configs/.env.example /opt/aircloud_vpn/docker-configs/.env
# Заполни значения вручную
nano /opt/aircloud_vpn/docker-configs/.env
```

---

## ✅ ФИНАЛЬНЫЙ ЧЕКЛИСТ

Перед тем как считать установку завершенной:

- [ ] VK сервер запущен (`docker-compose ps` показывает Up)
- [ ] NL сервер запущен (`docker-compose ps` показывает Up)
- [ ] Bot запущен (`docker-compose ps` показывает Up)
- [ ] Нет ошибок в логах VK (`docker-compose logs vk-server` без ERROR)
- [ ] Нет ошибок в логах NL (`docker-compose logs nl-server` без ERROR)
- [ ] Нет ошибок в логах Bot (`docker-compose logs vpn-bot` без ERROR)
- [ ] SSL сертификат получен (`ls nl-server/certs/`)
- [ ] Конфиги валидны (xray -test пройден)
- [ ] Firewall правилаправильны (порты 22, 443, 8443 открыты)
- [ ] Bot отвечает на сообщения в Telegram
- [ ] Single VPN подключается и показывает правильный IP
- [ ] Double VPN подключается и показывает правильный IP

---

## 🎉 ГОТОВО!

Если все пункты чеклиста выполнены → система работает! 

**Теперь:**
1. Оповести пользователей о доступности VPN
2. Начать прием платежей через YooKassa
3. Мониторить логи сервера

**Успехов! 🚀**
