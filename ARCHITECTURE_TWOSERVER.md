# Архитектура двух-серверной системы

## 🏗️ Общая архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ПОЛЬЗОВАТЕЛИ                                 │
│                                                                      │
│  Telegram │ VPN Клиенты (Reality)  │ VPN Клиенты (TLS)             │
└─────────┬─────────────────┬──────────────────────┬──────────────────┘
          │                 │                      │
          │                 │                      │
          ▼                 ▼                      ▼
    ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐
    │ TELEGRAM    │  │ VK СЕРВЕР    │  │   NL СЕРВЕР        │
    │ API         │  │ 243.x.x.x    │  │   89.x.x.x         │
    │ (@BotFather)│  │              │  │                    │
    └──────┬──────┘  └──────┬───────┘  └────────┬───────────┘
           │                │                   │
           │                │                   │
           ▼                ▼                   ▼
    ┌──────────────────────────────────────────────────┐
    │          DOCKER COMPOSE СЕТЬ (vpn-network)      │
    │                                                  │
    │  ┌─────────────────┐   ┌────────────────────┐  │
    │  │  VK CONTAINER   │   │  NL CONTAINER      │  │
    │  │                 │   │                    │  │
    │  │ :443 (Reality)  │──→│ :443 (TLS)         │  │
    │  │ :8443 (VLESS)   │   │                    │  │
    │  │                 │   │ 📌 BOT РАБОТАЕТ    │  │
    │  │ XRAY            │   │    ЗДЕСЬ           │  │
    │  │ ├─ Inbound      │   │                    │  │
    │  │ │  ├─ :443      │   │ XRAY               │  │
    │  │ │  │  └→ Reality│   │ ├─ Inbound         │  │
    │  │ │  └─ :8443     │   │ │  └─ TLS на :443  │  │
    │  │ │     └→ VLESS  │   │ ├─ Outbound        │  │
    │  │ │                │   │ │  └─ Direct       │  │
    │  │ ├─ Routing       │   │                    │  │
    │  │ │  ├─ :443       │   │ TELEGRAM BOT       │  │
    │  │ │  │  └→ Forward │───┘ ├─ vpn_bot.py     │  │
    │  │ │  │     to NL   │     ├─ admin_panel.py │  │
    │  │ │  └─ :8443      │     ├─ webhook.py     │  │
    │  │ │     └→ Direct  │     └─ database.py    │  │
    │  │ │        exit    │                        │  │
    │  │ └─ Outbound      │     УВЕДОМЛЕНИЯ       │  │
    │  │    └─ Direct     │     ├─ notify.py      │  │
    │  │       (:8443)    │     └─ monitoring.py  │  │
    │  │                 │                        │  │
    │  └─────────────────┘    ┌────────────────┐  │  │
    │           │             │ SHARED VOLUMES │ │  │
    │           │             ├ shared-db      │ │  │
    │           │             ├ xray-certs     │ │  │
    │           └─────────────→ (SSL для NL)   │ │  │
    │                          └────────────────┘  │  │
    └──────────────────────────────────────────────┘
    
    🔗 Docker Network: vpn-network
    📦 Volumes: 
       - xray-certs (SSL сертификаты)
       - shared-db (SQLite база)
```

---

## 📌 Назначение каждого сервера

### VK Сервер (Россия) - Маршрутизатор

**IP**: `243.x.x.x` или домен `vk.vpn.example.com`

**Открытые порты (публичные)**:
- **:443** — VLESS + Reality для двойного туннеля
- **:8443** — VLESS для одиночного VPN

**Функции**:
```
1. Принимает подключения от клиентов на портах 443 и 8443
2. Маршрутизирует трафик:
   - :443 → Forward to nl-server:443 (двойной туннель)
   - :8443 → Direct exit через провайдера (одиночный VPN)
```

**Установленные компоненты**:
- Xray (маршрутизатор трафика)
- xray_manager.py (управление процессом)
- xray_api.py (API для управления)
- config.json (правила маршрутизации)

**Минимальные требования**:
- CPU: 1 ядро
- RAM: 512 МБ
- Сеть: 100 МБит/с+

---

### NL Сервер (Нидерланды) - Выход + Бот

**IP**: `89.x.x.x` или домен `nl.vpn.example.com`

**Открытые порты (публичные)**:
- **:443** — VLESS + TLS (конец двойного туннеля)

**Внутренние порты (Docker сеть)**:
- **:9090** — API Webhook для платежей
- **:9091** — API для генерации конфигов

**Функции**:
```
1. Xray:
   - Получает форвард с VK сервера (:443)
   - TLS шифрование входящего трафика (от VK)
   - Direct выход в интернет (для usuarios)

2. Telegram Bot:
   - Обрабатывает команды пользователей (/start, /buy, /key)
   - Генерирует VLESS конфиги для клиентов
   - Управляет БД пользователей и ключей
   - Обрабатывает платежи через Yookassa (webhook)
   - Отправляет уведомления об истечении подписок
   - Админ панель для управления системой
```

**Установленные компоненты**:
- Xray (выход трафика)
- Python 3.11 приложение (bot)
- vpn_bot.py (основной бот)
- admin_panel.py (администрирование)
- database.py (SQLite БД)
- webhook.py (платежи)
- notify_expiring.py (уведомления)
- tunnel_manager.py (генерация конфигов)
- monitoring.py (мониторинг нагрузки)

**Минимальные требования**:
- CPU: 2 ядра
- RAM: 1-2 ГБ
- Хранилище: 5 ГБ+ (для БД и кешей)
- Сеть: 250+ МБит/с

---

## 🔀 Поток трафика

### Сценарий 1: ДВОЙНОЕ ТУННЕЛИРОВАНИЕ (Double Tunnel)

```
┌─────────────┐
│   ПОЛЬЗОВАТЕЛЬ     │
│ 192.168.1.100      │
└────────┬────────┘
         │
         │ Xray Client Config:
         │ - Outbound: VLESS → VK:443 (Reality)
         │ - Inbound: SOCKS5 на :1080
         │
         ▼
    ┌────────────────────┐
    │   Шифр 1: Reality  │
    │    VK:443 ← Клиент │◄─ Зашифровано Real
    └─────────┬──────────┘
              │
              │ Через интернет (публичные IP)
              │
              ▼
    ┌────────────────────────────────────────┐
    │         VK SERVER (243.x.x.x)          │
    │                                        │
    │  :443 (Reality + VLESS)                │
    │  ├─ Распознает подключение             │
    │  ├─ Маршрутизирует в docker-network   │
    │  └─ Форвардит на nl-server:443         │
    └────────────┬─────────────────────────┘
                 │
                 │ Docker Network (внутренне)
                 │
                 ▼
    ┌────────────────────────────────────────┐
    │      NL SERVER (docker-network)        │
    │                                        │
    │  :443 (TLS + VLESS - прием)            │
    │  ├─ Принимает форвард от VK            │
    │  ├─ Применяет TLS (второе шифрование) │
    │  └─ Выходит в интернет через eth0     │
    │                                        │
    │  ✅ Трафик пользователя в интернете   │
    │     Виден как из NL (89.x.x.x)        │
    └────────────────────────────────────────┘
                 │
                 │ Интернет
                 │
                 ▼
              САЙТЫ
          vpn-test.com → Видит IP 89.x.x.x ✅
```

### Сценарий 2: ОДИНОЧНЫЙ VPN (Single VPN)

```
┌─────────────┐
│   ПОЛЬЗОВАТЕЛЬ     │
│ 192.168.1.100      │
└────────┬────────┘
         │
         │ Xray Client Config:
         │ - Outbound: VLESS → VK:8443 (Reality)
         │ - Inbound: SOCKS5 на :1080
         │
         ▼
    ┌────────────────────┐
    │   Шифр 1: Reality  │
    │  VK:8443 ← Клиент  │◄─ Зашифровано
    └─────────┬──────────┘
              │
              │ Через интернет (публичные IP)
              │
              ▼
    ┌────────────────────────────────────────┐
    │         VK SERVER (243.x.x.x)          │
    │                                        │
    │  :8443 (Reality + VLESS)               │
    │  ├─ Распознает подключение             │
    │  ├─ Маршрутизирует как Direct exit    │
    │  └─ Выходит в интернет через eth0     │
    │                                        │
    │  ✅ Трафик пользователя в интернете  │
    │     Виден как из России (243.x.x.x)   │
    └────────────────────────────────────────┘
              │
              │ Интернет
              │
              ▼
           САЙТЫ
      vpn-test.com → Видит IP 243.x.x.x ✅
```

---

## 📊 Распределение данных

### VK Сервер сохраняет:
- `config.json` — Маршруты трафика (не меняется в runtime)
- Логи xray (может быть очищено)

### NL Сервер сохраняет:
- **shared-db/vpn_users.db**:
  - Пользователи системы
  - Активные подписки
  - VPN ключи
  - Истории платежей
  
- **xray-certs/**:
  - SSL сертификат (Let's Encrypt)
  - Приватный ключ
  - Промежуточные сертификаты

- **Логи**: 
  - Telegram bot logs
  - Xray logs
  - Ошибки платежей

---

## 🔄 Синхронизация между серверами

### Как VK узнает про пользователя NL?

```
1. Пользователь в NL Telegram /start
   └→ Бот создает запись в shared-db

2. Пользователь вводит команду /buy
   └→ Бот генерирует VLESS конфиг через tunnel_manager.py
      └→ Конфиг содержит: VK:443 (для double) или VK:8443 (для single)

3. Клиент подключается к VK:443 или VK:8443
   └→ VK не знает про пользователя, но:
      - По подключению узнает тип трафика (Reality)
      - Правильно маршрутизирует (по порту)
```

### Синхронизация при обновлении тарифов:

```
1. Администратор меняет цены в config.py
2. Копирует config.py в docker-configs/nl-server/bot_app/
3. Перестраивает образ: docker-compose build nl-server
4. Перезагружает контейнер: docker-compose up -d nl-server

VK сервер НЕ нужно перезагружать (он не смотрит config.py)
```

---

## 📋 Файлы в каждом контейнере

### VK Container (`docker-configs/vk-server/`)

```
Dockerfile                    ← Инструкции сборки
config.json                   ← Маршруты (443→forward, 8443→direct)
core_vpn/
├── xray_manager.py
├── xray_api.py
└── xray_api_fixed.py

Во время запуска:
/etc/xray/config.json         ← Скопирован из config.json
/var/log/xray/                ← Логи Xray
```

### NL Container (`docker-configs/nl-server/`)

```
Dockerfile                    ← Инструкции сборки
entrypoint.sh                 ← Запуск (SSL + Xray + Bot)
config.json                   ← Параметры Xray TLS
requirements.txt              ← Python pip зависимости
requirements-bot.txt          ← Доп. зависимости

bot_app/                      ← 📌 ОСНОВНОЕ ПРИЛОЖЕНИЕ
├── vpn_bot.py                ← Главный файл бота
├── bot.py
├── admin_panel.py
├── admin.py
├── admin_methods.py
├── webhook.py
├── notify_expiring.py
├── config.py                 ← Конфиг (цены, API)
├── database.py               ← SQLite БД
├── tunnel_manager.py         ← Генерация конфигов
├── xray_double_tunnel.py     ← VLESS ссылки
├── double_tunnel_utils.py
├── double_tunnel_docs.py
├── sync_keys.py
├── monitoring.py
└── user_agreement.txt

Во время запуска:
/app/data/vpn_users.db        ← SQLite БД
/etc/xray/config.json         ← Скопирован из config.json
/etc/xray/certs/              ← SSL сертификат (volume)
/var/log/xray/                ← Логи Xray
/app/bot.log                  ← Логи Bot
```

---

## ✅ Связность между контейнерами

```
docker-compose setup:

service "vk-server"
  ├─ ports: 0.0.0.0:443 → 443/tcp (Reality)
  ├─ ports: 0.0.0.0:8443 → 8443/tcp (VLESS)
  ├─ networks: vpn-network 
  │  └─ DNS: vk-server (может обращаться nl-server из конфига)
  └─ volumes: нет (stateless)

service "nl-server"
  ├─ ports: 0.0.0.0:8444 → 443/tcp (внутренний PORT)
  ├─ networks: vpn-network
  │  └─ DNS: nl-server (бот обращается к локальному localhost)
  ├─ volumes:
  │  ├─ xray-certs:/etc/xray/certs (SSL persistence)
  │  └─ shared-db:/app/data (БД persistence)
  └─ environment: BOT_TOKEN, YOOKASSA_SHOP_ID, etc.
```

При запуске NL контейнера бот может обращаться:
- `nl-server` (в конфигах туннелей внешний адрес)
- `vk-server` (в конфигах маршрутизации)

---

## 🚀 Итоговая структура для развертывания

```
На разработочной машине (Linux/Mac/Windows):
───────────────────────────────────────────
aircloud_vpn/                           ← Корневая папка проекта
├── docker-configs/
│   ├── vk-server/
│   │   ├── Dockerfile                 ← docker build
│   │   ├── config.json                ← Конфиг маршрутизации
│   │   └── core_vpn/
│   │       ├── xray_manager.py        ← Скопировано
│   │       ├── xray_api.py            ← Скопировано
│   │       └── xray_api_fixed.py      ← Скопировано
│   │
│   ├── nl-server/
│   │   ├── Dockerfile                 ← docker build
│   │   ├── config.json                ← TLS конфиг
│   │   ├── entrypoint.sh              ← Запуск сript
│   │   ├── requirements.txt           ← pip install
│   │   ├── requirements-bot.txt       ← pip install
│   │   └── bot_app/                   ← 📌 ГЛАВНАЯ ПАПКАБота
│   │       ├── vpn_bot.py             ← Скопировано
│   │       ├── bot.py                 ← Скопировано
│   │       ├── admin_panel.py         ← Скопировано
│   │       ├── admin.py               ← Скопировано
│   │       ├── admin_methods.py       ← Скопировано
│   │       ├── webhook.py             ← Скопировано
│   │       ├── notify_expiring.py     ← Скопировано
│   │       ├── config.py              ← Скопировано (ГЛАВНЫЙ)
│   │       ├── database.py            ← Скопировано
│   │       ├── tunnel_manager.py      ← Скопировано
│   │       ├── xray_double_tunnel.py  ← Скопировано
│   │       ├── double_tunnel_utils.py ← Скопировано
│   │       └── [еще файлы]            ← Скопировано
│   │
│   ├── docker-compose.yml              ← docker-compose up -d
│   ├── .env.example                    ← cp & nano .env
│   ├── deploy.sh                       ← bash deploy.sh
│   ├── prepare-files.sh                ← bash prepare-files.sh
│   └── README.md

│
└── [Остальные корневые файлы для разработки]
    (не нужны в docker-configs)
```

Готово! 📦
