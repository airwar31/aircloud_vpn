# 🚀 AIRCLOUD VPN v2.0 - БЫСТРЫЙ СТАРТ С ПЛАТЕЖНОЙ СИСТЕМОЙ

## ⚡ За 5 минут до первого платежа:

### 1️⃣ Клонируйте и подготовьте:
```bash
cd deploy/nl-server
cp .env.example .env
```

### 2️⃣ Получите YooKassa ключи:
- Перейти на https://yookassa.ru/
- Зарегистрируйте магазин
- Скопируйте Shop ID и Secret Key в .env

### 3️⃣ Добавьте крипто адреса (опционально):
```bash
# В .env файле заполните:
CRYPTO_WALLETS_USDT_ETH=0xYourAddress
CRYPTO_WALLETS_TON=EQxxx...
```

### 4️⃣ Установите зависимости:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt requirements-payments.txt
```

### 5️⃣ Запустите:
```bash
python MAIN_BOT_EXAMPLE.py
```

**✅ Готово! Бот запустился и готов принимать платежи!**

---

## 🧪 Первый тест платежа:

1. Отправьте команду `/pay` боту
2. Выберите: **Базовый туннель** → **1 месяц** → **YooKassa**
3. Используйте тестовую карту:
   - Номер: `4111 1111 1111 1111`
   - Дата: `12/34`
   - CVC: `123`
4. ✅ После платежа получите VLESS ссылку

---

## 📚 Документация по порядку:

1. **Для быстрого старта:**
   - Этот файл (вы здесь ✅)

2. **Для детальной документации:**
   - [PAYMENT_SYSTEM_STRUCTURE.md](PAYMENT_SYSTEM_STRUCTURE.md) - архитектура
   - [PAYMENT_INTEGRATION.md](PAYMENT_INTEGRATION.md) - техническая инструкция
   - [MAIN_BOT_EXAMPLE.py](MAIN_BOT_EXAMPLE.py) - полный пример кода

3. **Для отладки и запуска:**
   - [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md) - полное руководство

---

## 🎯 Основные файлы платежной системы:

```
bot_app/
├── yookassa_payment.py      # YooKassa API клиент
├── payment_handler.py       # Основная логика платежей
├── bot_payment.py          # Telegram UI для платежей
├── crypto_payment.py       # Криптовалютные платежи
└── webhook_handler.py      # Вебхуки от YooKassa
```

---

## 💳 Поддерживаемые платежи:

| Способ | Статус | Комиссия | Скорость |
|--------|--------|----------|----------|
| 💳 YooKassa | ✅ Готов | 2.5% | 1-3 мин |
| ⭐ Telegram Stars | ✅ Готов | 0% | <1 сек |
| 🪙 USDT/USDC/TON | ✅ Готов | 1% | 5-10 мин |

---

## 🔧 Основные переменные .env:

```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...

# YooKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Криптовалюты (опционально)
CRYPTO_WALLETS_USDT_ETH=0x...
CRYPTO_WALLETS_TON=EQ...

# Вебхук (для YooKassa)
WEBHOOK_HOST=https://yourdomain.com
WEBHOOK_ENABLED=true
```

---

## 🛠️ Решение частых проблем:

### ❌ Боттекст не запускается
**Решение:**
```bash
# Проверьте токен
python -c "import aiogram"  # Если error - установите: pip install aiogram

# Проверьте интернет
curl https://api.telegram.org/bot123456:ABC.../getMe
```

### ❌ YooKassa платежи не работают
**Решение:**
```bash
# Убедитесь, что:
1. YOOKASSA_SHOP_ID и SECRET_KEY правильные
2. Это PRODUCTION ключи (не test!)
3. Магазин активирован на yookassa.ru

# Проверьте логи:
grep "YooKassa" logs/bot.log
```

### ❌ Вебхук не работает
**Решение:**
```bash
# Проверьте, что используется HTTPS:
WEBHOOK_HOST=https://yourdomain.com  # ❌ ДА (https)
WEBHOOK_HOST=http://yourdomain.com   # ❌ НЕТ (http не работает!)

# Проверьте сертификат:
openssl s_client -connect yourdomain.com:8080
```

---

## 📝 Быстрая команда для инициализации БД:

```bash
python -c "
from bot_app.database import Database
import asyncio

async def init():
    db = Database('bot.db')
    await db.init()
    print('✅ Database initialized')

asyncio.run(init())
"
```

---

## 🎓 Запуск в разных окружениях:

### Локально (разработка):
```bash
python MAIN_BOT_EXAMPLE.py
```

### Docker (production):
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### systemd (Linux):
```bash
sudo systemctl start aircloud-bot
```

---

## 🔍 Проверка работоспособности:

```bash
# Проверить, что бот онлайн:
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверить, что вебхук здоров:
curl -s "https://yourdomain.com:8080/health"

# Проверить БД:
sqlite3 bot.db "SELECT COUNT(*) FROM users;"
```

---

## 📊 Мониторинг в реальном времени:

```bash
# Смотреть логи платежей:
tail -f logs/bot.log | grep "Payment"

# Смотреть все ошибки:
tail -f logs/bot.log | grep "ERROR"

# Проверить статистику платежей:
sqlite3 bot.db "SELECT payment_method, COUNT(*) FROM orders GROUP BY payment_method;"
```

---

## 🚨 Важно перед продакшеном:

- [ ] Заполнить все переменные в .env
- [ ] Получить HTTPS сертификат (Let's Encrypt)
- [ ] Установить YooKassa вебхук в личном кабинете
- [ ] Протестировать все 3 способа оплаты
- [ ] Проверить логирование и мониторинг
- [ ] Сделать резервную копию БД
- [ ] Включить ENABLE_BLOCKCHAIN_MONITOR если нужен крипто

---

## 💡 Советы для использования:

1. **Чтобы быстро отладить платежи:**
   - Используйте `TEST_MODE=true` в .env
   - Смотрите логи: `tail -f logs/bot.log`
   - Проверяйте БД: `sqlite3 bot.db ".tables"`

2. **Для мониторинга блокчейна:**
   - Установите `ENABLE_BLOCKCHAIN_MONITOR=true`
   - Добавьте API ключи (Etherscan, BscScan, TON)
   - Проверяйте баланс крипто кошельков

3. **Для безопасности:**
   - Никогда не коммитьте .env в Git
   - Используйте длинные пароли для 3xui
   - Регулярно меняйте Secret Key в YooKassa

---

## 🎯 Что это дает вам:

✅ **Полная автоматизация:** платеж → активация → VLESS ссылка
✅ **3 способа оплаты:** для разных пользователей
✅ **Мониторинг крипто:** автоматическое обнаружение платежей в блокчейне
✅ **Production-ready:** все обработано, все залогировано
✅ **Русский интерфейс:** для российского рынка
✅ **Двойной туннель:** VK → NL через 3xui

---

## 📞 Помощь и поддержка:

- **Документация YooKassa:** https://yookassa.ru/docs
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **3xui документация:** https://github.com/MhammadAli/X-UI
- **Логи приложения:** `logs/bot.log`

---

## 🎉 Готовы к старту?

```bash
# 1. Клонируйте
cd deploy/nl-server

# 2. Подготовьте .env
cp .env.example .env
# ... заполните YooKassa ключи ...

# 3. Установите
pip install -r requirements.txt requirements-payments.txt

# 4. Запустите
python MAIN_BOT_EXAMPLE.py

# 5. Откройте бот в Telegram и напишите /pay
```

**✨ Готово! Первый платеж вы получите за 5 минут!**

---

*Версия: 2.0*
*Дата: 2024*
*Язык интерфейса: Русский*
*Автор: AirCloud Team*
