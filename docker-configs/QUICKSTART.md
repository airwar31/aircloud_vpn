# 🚀 БЫСТРАЯ СПРАВКА

## 📁 СТРУКТУРА

```
docker-configs/
├── vk-server/           # Промежуточный (Россия, Reality)
├── nl-server/           # Конечный (Нидерланды, TLS)
├── bot/                 # Telegram бот
├── docker-compose.yml   # Оркестрация
└── .env.example        # Переменные
```

---

## ⚡ ОДНА КОМАНДА ДЛЯ РАЗВЕРТЫВАНИЯ

```bash
cd docker-configs
bash deploy.sh
```

---

## 📝 ПРЕЖДЕ ЧЕМ ЗАПУСКАТЬ

1. **Установите Docker:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
bash get-docker.sh
```

2. **Отредактируйте .env:**
```bash
cp .env.example .env
nano .env

# Найдите и обновите:
BOT_TOKEN=your-telegram-token
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
```

3. **Скопируйте файлы бота:**
```bash
bash copy-bot-files.sh
```

---

## 🔧 ОСНОВНЫЕ КОМАНДЫ

```bash
# Запустить
docker-compose up -d

# Остановить
docker-compose down

# Логи
docker-compose logs -f

# Статус
docker-compose ps

# Перезагрузить
docker-compose restart

# Удалить всё
docker-compose down -v
```

---

## 🔐 SSL СЕРТИФИКАТ

```bash
# Для NL сервера нужен сертификат Let's Encrypt:
docker-compose exec nl-server bash

# Внутри контейнера:
certbot certonly --standalone -d nl.vpn.example.com
cp /etc/letsencrypt/*/nl.vpn.example.com/* /etc/xray/certs/
```

---

## ✅ ПРОВЕРКА

```bash
# Статус контейнеров
docker-compose ps

# Логи ошибок
docker-compose logs | grep -i error

# Тест подключения
# 1. Импортируйте VLESS link в V2RayNG/Clash
# 2. Подключитесь
# 3. Откройте ipinfo.io
# 4. Должен быть IP Нидерландов для двойного туннеля ✅
```

---

## 📊 АРХИТЕКТУРА

```
【 ОБЫЧНЫЙ VPN 】
Клиент → VK:8443 → Интернет

【 ДВОЙНОЙ ТУННЕЛЬ 】
Клиент → VK:443 → NL:443 → Интернет (видит IP Нидерландов)
```

---

## 🆘 ПОМОЩЬ

Полная документация:
- `README.md` - подробно о каждом контейнере
- `DEPLOYMENT.md` - шаг за шагом развертывание

Логи:
```bash
docker-compose logs vk-server   # ВК сервер
docker-compose logs nl-server   # NL сервер
docker-compose logs vpn-bot     # Бот
```

---

**Тремя командами в production:**
```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

✅ **Ready to go!**
