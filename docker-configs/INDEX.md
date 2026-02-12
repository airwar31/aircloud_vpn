# 📚 НАВИГАЦИЯ ПО DOCKER-КОНФИГАМ

## 🎯 ВЫБЕРИ СВОЙ ПУТЬ

### 1️⃣ **Я в спешке, хочу быстро развернуть (5 мин)**
→ Читай: [QUICKSTART.md](QUICKSTART.md)
```bash
bash deploy.sh
```

### 2️⃣ **Я хочу разобраться как это работает (20 мин)**
→ Читай: [README.md](README.md)
- Архитектура
- Каждый контейнер
- Управление

### 3️⃣ **Я разворачиваю на production сервер (1 час)**
→ Читай: [DEPLOYMENT.md](DEPLOYMENT.md)
- Пошаговое развертывание
- SSL сертификаты
- Troubleshooting
- Масштабирование

### 4️⃣ **Мне нужны файлы конфигов**
→ Смотри папки:
```
vk-server/         # config.json для промежуточного сервера
nl-server/         # config.json для конечного сервера
bot/               # Dockerfile для бота
```

---

## 🗂️ СТРУКТУРА ФАЙЛОВ

```
docker-configs/
│
├── 📄 КОНФИГУРАЦИОННЫЕ ФАЙЛЫ
│   ├── docker-compose.yml       ⭐ Главный файл оркестрации
│   ├── .env.example             📝 Переменные окружения
│   └── .env                     🔐 Реальные переменные (создаётся из .example)
│
├── 📁 VK SERVER (Промежуточный)
│   ├── Dockerfile               # Ubuntu + Xray
│   └── config.json              # VLESS на 443 и 8443
│
├── 📁 NL SERVER (Конечный)
│   ├── Dockerfile               # Ubuntu + Xray + Certbot
│   ├── config.json              # VLESS с TLS на 443
│   └── entrypoint.sh            # Скрипт для SSL сертификатов
│
├── 📁 BOT (Telegram)
│   ├── Dockerfile               # Python 3.11 + pip
│   ├── vpn_bot.py              # Основной файл бота
│   ├── config.py               # Конфиги VPN планов
│   ├── *.py                    # Остальные модули
│   └── requirements.txt        # Зависимости Python
│
├── 📖 ДОКУМЕНТАЦИЯ
│   ├── QUICKSTART.md           # Быстрый старт (5 мин)
│   ├── README.md               # Подробная инструкция (20 мин)
│   ├── DEPLOYMENT.md           # Production развертывание (1+ час)
│   ├── INDEX.md               # Этот файл
│   └── TROUBLESHOOTING.md     # Решение проблем
│
├── 🔧 СКРИПТЫ
│   ├── deploy.sh              # Автоматическое развертывание
│   └── copy-bot-files.sh      # Копирование файлов бота
│
└── 📋 ДРУГОЕ
    ├── .gitignore
    └── LICENSE
```

---

## 🚀 БЫСТРЫЕ КОМАНДЫ

### Развертывание
```bash
cd docker-configs/
bash deploy.sh
```

### Управление
```bash
docker-compose ps              # Статус
docker-compose logs -f         # Логи
docker-compose restart         # Перезагрузка
docker-compose down            # Остановка
```

### Отладка
```bash
docker-compose exec vk-server bash      # SSH в ВК контейнер
docker-compose exec nl-server bash      # SSH в NL контейнер
docker-compose exec vpn-bot bash        # SSH в бот
docker-compose logs vk-server           # Логи ВК
```

---

## 📊 АРХИТЕКТУРА

```
         ┌─────────────────┐
         │   Telegram      │
         │   Пользователь  │
         └────────┬────────┘
                  │ BOT_TOKEN
                  ↓
         ┌─────────────────┐
         │  vpn-bot        │ Docker контейнер (Python)
         └────┬───────┬────┘
              │       │
         ┌────▼─┐  ┌──▼────┐
         │  VK  │  │  NL   │
         │Server│  │Server │
         │:443  │  │:443   │
         │:8443 │  │       │
         └──────┘  └───────┘
            ↑        ↑
            └────────┘
          Xray (VLESS)
          Docker сеть

【 Обычный VPN 】
Клиент → VK:8443 → Интернет

【 Двойной туннель 】
Клиент → VK:443 → NL:443 → Интернет
```

---

## 🔐 КЛЮЧЕВЫЕ ПЕРЕМЕННЫЕ

| Переменная | Где найти | Где установить |
|-----------|----------|----------------|
| `BOT_TOKEN` | @BotFather в Telegram | `.env` |
| `VK_PRIVATE_KEY` | `xray x25519` | `.env` (авто-генерируется) |
| `YOOKASSA_SHOP_ID` | Личный кабинет ЮKassa | `.env` |
| `NL_DOMAIN` | Ваш домен | `.env` |

---

## 🎯 ЭТАПЫ РАЗВЕРТЫВАНИЯ

### 1. Подготовка (5 мин)
```bash
cd docker-configs
cp .env.example .env
nano .env  # Отредактируйте
```

### 2. Копирование файлов (1 мин)
```bash
bash copy-bot-files.sh
```

### 3. Запуск (2 мин)
```bash
docker-compose up -d
```

### 4. SSL сертификат (5-10 мин)
```bash
# Запросить Let's Encrypt сертификат для NL сервера
```

### 5. Тестирование (5 мин)
```bash
# Подключиться с клиента и проверить IP
```

---

## 📞 КАНАЛЫ ПОДДЕРЖКИ

### Документация
- 📖 **Полная инструкция:** `DEPLOYMENT.md`
- ⚡ **Быстрый старт:** `QUICKSTART.md`
- 📚 **FAQ:** `README.md`

### Логи
```bash
docker-compose logs -f          # Все логи
docker-compose logs vk-server   # Логи ВК
docker-compose logs nl-server   # Логи NL
docker-compose logs vpn-bot     # Логи бота
```

### Помощь
```bash
# Проверить статус
docker-compose ps

# Проверить ошибки
docker-compose logs | grep -i error

# Перезагрузить все
docker-compose restart
```

---

## ✅ ЧЕКЛИСТ ГОТОВНОСТИ

- [ ] Docker установлен: `docker --version`
- [ ] Docker Compose установлен: `docker-compose --version`
- [ ] `.env` файл отредактирован
- [ ] Получены Reality ключи
- [ ] Файлы бота скопированы
- [ ] `docker-compose up -d` выполнен успешно
- [ ] Все контейнеры в статусе "Up": `docker-compose ps`
- [ ] SSL сертификат на NL сервере
- [ ] Тест подключения пройден ✅

---

## 🎉 ГОТОВО!

### Для новичков:
```bash
# 1. Читайте QUICKSTART.md
# 2. Выполняйте команды по шагам
# 3. Смотрите логи если что не работает
```

### Для опытных:
```bash
# 1. docker-compose up -d
# 2. Получить сертификат
# 3. Готово!
```

---

**Последнее обновление:** Февраль 2026  
**Версия:** 1.0  
**Статус:** ✅ Готово в боевых условиях
