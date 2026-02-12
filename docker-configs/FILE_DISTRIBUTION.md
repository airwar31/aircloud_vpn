# Распределение файлов по сервисам

## VK Сервер (Россия) - Порты 443 (chain) и 8443 (direct)

Директория: `docker-configs/vk-server/`

### Файлы для копирования из корня проекта:

```bash
# Копировать в vk-server/core_vpn/
xray_manager.py           # Управление процессом xray
xray_api.py               # API для взаимодействия
xray_api_fixed.py         # Исправленная версия API
```

### Файлы уже в docker-configs/vk-server/:

```
config.json              # Конфиг маршрутизации (443→NL, 8443→direct)
Dockerfile              # Ubuntu 22.04 + Xray (скрипт установки)
```

### Команда копирования:

```bash
cp xray_manager.py docker-configs/vk-server/core_vpn/
cp xray_api.py docker-configs/vk-server/core_vpn/
cp xray_api_fixed.py docker-configs/vk-server/core_vpn/
```

---

## NL Сервер (Нидерланды) - Порт 443 TLS + Telegram Bot

Директория: `docker-configs/nl-server/`

### 📌 Файлы бота (обязательно копировать):

```bash
# Копировать в nl-server/bot_app/
vpn_bot.py              # Основной Telegram бот
bot.py                  # Дополнительные функции
admin_panel.py          # Админ панель
admin.py                # Админ команды
admin_methods.py        # Методы администратора
webhook.py              # Вебхук платежей Yookassa
notify_expiring.py      # Уведомления об истечении

# Утилиты и конфиг
config.py               # Конфигурация (ГЛАВНЫЙ файл)
database.py             # SQLite БД
tunnel_manager.py       # Генерация konфигов
xray_double_tunnel.py   # VLESS ссылки и Clash
double_tunnel_utils.py  # Утилиты туннелей
double_tunnel_docs.py   # Документация для пользователей
sync_keys.py            # Синхронизация ключей
monitoring.py           # Мониторинг
user_agreement.txt      # Пользовательское соглашение
```

### Файлы уже в docker-configs/nl-server/:

```
config.json             # Конфиг Xray (TLS на 443)
entrypoint.sh           # Инициализация (SSL + Xray + Bot)
Dockerfile              # Ubuntu 22.04 + Python + Xray + Certbot
requirements.txt        # Python зависимости
requirements-bot.txt    # Доп. зависимости бота
```

### Команда копирования:

```bash
# Основные файлы бота
cp vpn_bot.py docker-configs/nl-server/bot_app/
cp bot.py docker-configs/nl-server/bot_app/
cp admin_panel.py docker-configs/nl-server/bot_app/
cp admin.py docker-configs/nl-server/bot_app/
cp admin_methods.py docker-configs/nl-server/bot_app/
cp webhook.py docker-configs/nl-server/bot_app/
cp notify_expiring.py docker-configs/nl-server/bot_app/

# Конфиг и БД
cp config.py docker-configs/nl-server/bot_app/
cp database.py docker-configs/nl-server/bot_app/

# Утилиты туннелей
cp tunnel_manager.py docker-configs/nl-server/bot_app/
cp xray_double_tunnel.py docker-configs/nl-server/bot_app/
cp double_tunnel_utils.py docker-configs/nl-server/bot_app/
cp double_tunnel_docs.py docker-configs/nl-server/bot_app/
cp sync_keys.py docker-configs/nl-server/bot_app/
cp monitoring.py docker-configs/nl-server/bot_app/
cp user_agreement.txt docker-configs/nl-server/bot_app/
```

---

## Оптимизированный скрипт копирования

Создайте `docker-configs/prepare-files.sh`:

```bash
#!/bin/bash

echo "📦 Копирование файлов на VK сервер..."
mkdir -p docker-configs/vk-server/core_vpn
cp xray_manager.py docker-configs/vk-server/core_vpn/
cp xray_api.py docker-configs/vk-server/core_vpn/
cp xray_api_fixed.py docker-configs/vk-server/core_vpn/

echo "📦 Копирование файлов на NL сервер (BOT)..."
mkdir -p docker-configs/nl-server/bot_app
cp vpn_bot.py docker-configs/nl-server/bot_app/
cp bot.py docker-configs/nl-server/bot_app/
cp admin_panel.py docker-configs/nl-server/bot_app/
cp admin.py docker-configs/nl-server/bot_app/
cp admin_methods.py docker-configs/nl-server/bot_app/
cp webhook.py docker-configs/nl-server/bot_app/
cp notify_expiring.py docker-configs/nl-server/bot_app/
cp config.py docker-configs/nl-server/bot_app/
cp database.py docker-configs/nl-server/bot_app/
cp tunnel_manager.py docker-configs/nl-server/bot_app/
cp xray_double_tunnel.py docker-configs/nl-server/bot_app/
cp double_tunnel_utils.py docker-configs/nl-server/bot_app/
cp double_tunnel_docs.py docker-configs/nl-server/bot_app/
cp sync_keys.py docker-configs/nl-server/bot_app/
cp monitoring.py docker-configs/nl-server/bot_app/
cp user_agreement.txt docker-configs/nl-server/bot_app/

echo "✅ Все файлы скопированы успешно!"
echo ""
echo "📊 Структура:"
echo "   VK сервер (Россия): docker-configs/vk-server/"
echo "   NL сервер (Нидерланды): docker-configs/nl-server/bot_app/"
```

Использование:

```bash
bash docker-configs/prepare-files.sh
```

---

## 📋 Таблица зависимостей файлов

### VK Сервер требует:
- ✅ xray_manager.py
- ✅ xray_api.py (или xray_api_fixed.py)
- ✅ config.json (жестко в docker-configs/vk-server/)

### NL Сервер требует:
- ✅ vpn_bot.py (основной), зависит от:
  - bot.py, admin_panel.py, admin.py
  - config.py (конфиг)
  - database.py (БД)
  - webhook.py (платежи)
- ✅ tunnel_manager.py, xray_double_tunnel.py (генерация конфигов)
- ✅ notify_expiring.py (фоновые задачи)
- ✅ monitoring.py (мониторинг)
- ✅ config.json (жестко в docker-configs/nl-server/)

---

## 🔄 Синхронизация config.py

⚠️ **ВАЖНО**: `config.py` находится в `docker-configs/nl-server/bot_app/` но определяет параметры для:
- VPN тарифы
- API ключи
- Параметры сетей
- Хосты серверов (VK и NL адреса/IP)

**При обновлении config.py**:
1. Отредактируйте в корне проекта
2. Скопируйте в `docker-configs/nl-server/bot_app/config.py`
3. Перестройте образ NL: `docker-compose build nl-server`

---

## 🚀 Быстрое развертывание

```bash
# 1. Подготовить файлы
bash docker-configs/prepare-files.sh

# 2. Перейти в docker-configs
cd docker-configs

# 3. Создать .env из шаблона
cp .env.example .env

# 4. Отредактировать .env
nano .env

# 5. Собрать образы
docker-compose build

# 6. Запустить сервисы
docker-compose up -d

# 7. Проверить статус
docker-compose ps
```

---

## ✅ Чек-лист перед развертыванием

- [ ] Файлы скопированы: `bash docker-configs/prepare-files.sh`
- [ ] .env заполнен реальными значениями
- [ ] VK_PRIVATE_KEY получен от: `xray x25519`
- [ ] BOT_TOKEN от @BotFather
- [ ] YOOKASSA_SHOP_ID и YOOKASSA_API_KEY готовы
- [ ] Домены готовы (NL домен для SSL)
- [ ] Порты 443, 8443 открыты на VK
- [ ] Порт 443 (8444 в docker-compose) открыт на NL
