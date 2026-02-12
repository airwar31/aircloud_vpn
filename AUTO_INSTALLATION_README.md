# 📚 АВТОМАТИЧЕСКАЯ УСТАНОВКА - ПОЛНЫЙ ГАЙД

## 🎯 Что было создано

Создан полный набор скриптов и документации для автоматической установки проекта на двух серверах:

### 📝 Документы:
1. **install-vk.sh** - Автоматический скрипт установки на VK сервер
2. **install-nl.sh** - Автоматический скрипт установки на NL сервер
3. **INSTALLATION_DATA_GUIDE.md** - Подробное объяснение каждого требуемого параметра
4. **QUICK_INSTALLATION.md** - Пошаговая инструкция быстрого старта

---

## 🚀 ТРИ СПОСОБА УСТАНОВКИ

### Способ 1️⃣: САМЫЙ БЫСТРЫЙ (рекомендуется)

```bash
# На VK сервере
ssh root@<VK_IP>
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-vk.sh
chmod +x install-vk.sh
./install-vk.sh

# На NL сервере (после VK)
ssh root@<NL_IP>
wget https://raw.githubusercontent.com/your-username/aircloud_vpn/main/install-nl.sh
chmod +x install-nl.sh
./install-nl.sh
```

**Время:** ~10 минут на сервер  
**Сложность:** НИЗКАЯ (просто ответить на вопросы)

---

### Способ 2️⃣: ПОШАГОВЫЙ (для понимания)

Следи руководство [QUICK_INSTALLATION.md](QUICK_INSTALLATION.md) шаг за шагом

**Время:** ~30 минут  
**Сложность:** СРЕДНЯЯ (нужно вводить команды вручную)

---

### Способ 3️⃣: РУЧНОЙ (полная гибкость)

Устанавливай вручную, используя шаги из скриптов. Смотри содержимое install-vk.sh и install-nl.sh

**Время:** ~1 час  
**Сложность:** ВЫСОКАЯ (нужно понимать что делаешь)

---

## 📋 НЕОБХОДИМЫЕ ДАННЫЕ

### Где их взять

Полный гайд в файле [INSTALLATION_DATA_GUIDE.md](INSTALLATION_DATA_GUIDE.md). Там описано ГДЕ И КАК получить каждый параметр:

| Параметр | Что это | Где получить |
|----------|---------|--------------|
| **VK_IP** | IP VK сервера | `curl -s https://api.ipify.org` на VK |
| **NL_IP** | IP NL сервера | `curl -s https://api.ipify.org` на NL |
| **NL_DOMAIN** | Домен (дл SSL) | Регистратор домена + DNS A запись |
| **BOT_TOKEN** | Telegram бот токен | @BotFather в Telegram |
| **YOOKASSA_SHOP_ID** | ID магазина | https://yookassa.ru кабинет |
| **YOOKASSA_SECRET_KEY** | Ключ YooKassa | https://yookassa.ru кабинет |
| **VK_PRIVATE_KEY** | Reality ключ | `xray x25519` на VK сервере |
| **VK_PUBLIC_KEY** | Reality публичный ключ | Результат `xray x25519` |
| **UUID_DOUBLE** | ID двойного туннеля | `uuidgen` или автогенерация в скрипте |
| **UUID_SINGLE** | ID одиночного туннеля | `uuidgen` или автогенерация в скрипте |
| **ADMIN_ID** | Твой Telegram ID | @userinfobot в Telegram |

---

## ⚙️ КРАТКИЙ ЧЕКЛИСТ

### Перед установкой:

```
Локальная машина:
□ Домен зарегистрирован
□ DNS A запись настроена на NL IP
□ BOT_TOKEN получен от @BotFather
□ YooKassa аккаунт активирован
□ ADMIN_ID (свой Telegram ID) известен

VK сервер:
□ Ubuntu 22.04+ установлена
□ SSH доступ работает
□ Интернет есть
□ Порты开放: 22 (SSH), 443 (Xray)

NL сервер:
□ Ubuntu 22.04+ установлена
□ SSH доступ работает
□ Интернет есть
□ Домен указывает на этот IP
□ Порты откры: 22 (SSH), 443/8443 (Xray)
```

### Во время установки:

```
□ Запустить install-vk.sh на VK
  (ответить на вопросы про данные)
  
□ Запустить install-nl.sh на NL
  (ответить на вопросы про данные)
  (сертификат получится автоматически)

□ Проверить что все контейнеры Up:
  docker-compose ps
  
□ Проверить логи на ошибки:
  docker-compose logs | grep -i error
```

### После установки:

```
□ Тестировать VPN через бота
□ Проверить IP при подключении
□ Убедиться что double и single работают
□ Настроить мониторинг/резервные копии
□ Документировать все учетные данные
```

---

## 🏗️ ЧТО ДЕЛАЕТ КАЖДЫЙ СКРИПТ

### install-vk.sh (на VK сервере)

```bash
#!/bin/bash
export install-vk.sh

1. ✅ Проверяет требования (root, Ubuntu, интернет)
2. ✅ Устанавливает Docker, Docker Compose, Git, Xray
3. ✅ Клонирует проект из репозитория
4. ✅ Генерирует Reality ключи (xray x25519)
5. ✅ Создает .env файл с твоими данными
6. ✅ Конфигурирует Xray (заменяет UUID и ключи)
7. ✅ Настраивает Firewall (открывает порты 22, 443)
8. ✅ Устанавливает Fail2Ban (DDoS защита)
9. ✅ Собирает Docker образ (docker-compose build)
10. ✅ Запускает контейнер (docker-compose up -d)
11. ✅ Проверяет статус и выводит логи
12. ✅ Выводит полезные команды для отладки
```

**Время:** ~5 минут  
**Результат:** VK сервер готов к работе

---

### install-nl.sh (на NL сервере)

```bash
#!/bin/bash
export install-nl.sh

1. ✅ Проверяет требования
2. ✅ Устанавливает Docker, Docker Compose, Git, Certbot
3. ✅ Клонирует проект
4. ✅ Получает SSL сертификат от Let's Encrypt
5. ✅ Копирует сертификаты в контейнер
6. ✅ Создает .env файл
7. ✅ Конфигурирует Xray на NL (оба inbound'а)
8. ✅ Настраивает Firewall (порты 22, 443, 8443)
9. ✅ Устанавливает Fail2Ban
10. ✅ Собирает Docker образы (nl-server + vpn-bot)
11. ✅ Запускает оба контейнера
12. ✅ Проверяет конфигурацию и выводит статус
```

**Время:** ~8 минут (включая получение SSL)  
**Результат:** NL сервер + Bot готовы к работе

---

## 💾 СТРУКТУРА ПРОЕКТА ПОСЛЕ УСТАНОВКИ

```
/opt/aircloud_vpn/
├── docker-configs/
│   ├── .env              ← Твои реальные значения
│   ├── .env.example      ← Шаблон для .env
│   ├── docker-compose.yml
│   ├── vk-server/
│   │   ├── Dockerfile
│   │   ├── config.json   ← Заполнен твоими UUID и ключом
│   │   └── core_vpn/
│   ├── nl-server/
│   │   ├── Dockerfile
│   │   ├── config.json   ← Заполнен твоими UUID
│   │   ├── certs/        ← SSL сертификаты (получены автоматически)
│   │   │   ├── fullchain.pem
│   │   │   └── privkey.pem
│   │   └── bot_app/
│   │       ├── requirements.txt
│   │       ├── bot.py
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── tunnel_manager.py
│   │       └── [остальные файлы]
│   └── backups/
│       └── <YYYYMMDD_HHMMSS>/  ← Автоматический бэкап перед изменениями
│
└── [остальные файлы проекта]
```

---

## 🔐 БЕЗОПАСНОСТЬ

### Что скрипты делают для защиты:

✅ **Firewall (UFW)**
- Открывают только нужные порты
- Лимитируют SSH (max 6 попыток за 30 сек)

✅ **Fail2Ban**
- Автоматически банит после 3 неудачных SSH попыток
- Защита от DDoS

✅ **SSH Hardening**
- Скрипты рекомендуют отключить root логин
- Рекомендуют использовать только SSH ключи

✅ **SSL сертификаты**
- Автоматически получаются от Let's Encrypt
- Автоматически обновляются через Certbot

---

## 🚨 ВОЗМОЖНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### "Permission denied" при запуске скрипта

```bash
chmod +x install-vk.sh
chmod +x install-nl.sh
# Попробуй снова
./install-vk.sh
```

### "Command not found: docker-compose"

```bash
# Переинсталлируем Docker Compose
/usr/local/bin/docker-compose --version
# или
docker --version  # Docker должен быть
```

### "Could not resolve host: github.com"

```bash
# Проверь интернет
ping 8.8.8.8

# Проверь DNS
cat /etc/resolv.conf
# Должно быть nameserver 8.8.8.8 или похожее
```

### "E: Unable to locate package certbot"

```bash
apt-get update
apt-get install -y certbot
```

### SSL сертификат не получен

```bash
# Проверь что домен указывает на NL IP
nslookup nl.vpn.example.com
# Должен вернуть NL IP

# Проверь что порт 443 открыт
telnet nl.vpn.example.com 443
# "Connected" = OK

# Попробуй вручную
certbot certonly --standalone -d nl.vpn.example.com \
  --email admin@example.com --agree-tos
```

### Docker контейнер не стартует

```bash
# Посмотри логи
docker-compose logs <service>

# Проверь конфиг
docker-compose exec <service> xray -test -config /etc/xray/config.json

# Перестартуй
docker-compose restart <service>
```

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

После успешной установки:

### На VK сервере:
- ✅ Контейнер `vk-xray-server` в состоянии Up
- ✅ Порт 443 слушает (netstat показывает LISTEN)
- ✅ Логи показывают "listening on port 443"
- ✅ Тест конфига пройден (xray -test)

### На NL сервере:
- ✅ Контейнер `nl-xray-server` в состоянии Up
- ✅ Контейнер `vpn-telegram-bot` в состоянии Up
- ✅ Порты 443 и 8443 слушают
- ✅ SSL сертификат в `/etc/xray/certs/`
- ✅ Бот отвечает на `/start` команду в Telegram
- ✅ Логи показывают "listening on port 443" и "listening on port 8443"

### VPN функциональность:
- ✅ Single VPN подключается к NL:8443
- ✅ Double VPN подключается через VK:443 → NL:443
- ✅ Оба показывают одинаковый exit IP (NL IP)
- ✅ Bot генерирует конфиги для обоих типов
- ✅ Платежи обрабатываются через YooKassa

---

## 🎓 ДАЛЬНЕЙШЕЕ ОБУЧЕНИЕ

После успешной установки изучи:

1. **SAFE_UPDATE_GUIDE.md** - Как безопасно обновлять
2. **SECURITY_HARDENING_GUIDE.md** - Как укрепить защиту
3. **DEPLOYMENT_GUIDE_TWO_SERVERS.md** - Детальное объяснение архитектуры

---

## 📞 ПОДДЕРЖКА

### Если что-то не работает:

1. Проверь все данные в [INSTALLATION_DATA_GUIDE.md](INSTALLATION_DATA_GUIDE.md)
2. Следуй [QUICK_INSTALLATION.md](QUICK_INSTALLATION.md) пошагово
3. Смотри логи: `docker-compose logs | grep -i error`
4. Проверь firewall: `ufw status`
5. Проверь конфиг: `xray -test -config config.json`

---

## 🎉 ИТОГО

Два простых шага к готовой VPN системе:

```bash
# Шаг 1: На VK
ssh root@<VK_IP>
wget https://...install-vk.sh
chmod +x install-vk.sh
./install-vk.sh

# Шаг 2: На NL
ssh root@<NL_IP>
wget https://...install-nl.sh
chmod +x install-nl.sh
./install-nl.sh

# Готово! 🚀
```

**Бот будет доступен в Telegram сразу после установки NL сервера.**

---

**Удачи с установкой! 🌟**
