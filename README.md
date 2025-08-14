# 🚀 AirCloud VPN Bot

Простой Telegram бот для продажи VPN подписок.

## Быстрый запуск

### 1. Загрузите файлы на сервер
```bash
mkdir /root/aircloud-vpn
cd /root/aircloud-vpn
# Загрузите все файлы проекта
```

### 2. Запустите
```bash
chmod +x start.sh
./start.sh
```

### 3. Готово!
Бот запущен с настройками:
- 🤖 **Telegram**: готов к работе
- 💳 **ЮKassa**: тестовые платежи  
- 🔐 **VPN**: подключен к серверу
- 📱 **Тарифы**: 99₽, 249₽, 499₽, 999₽

## Управление

```bash
# Логи
docker-compose logs -f

# Перезапуск
docker-compose restart

# Остановка
docker-compose down
```

## Файлы проекта

**Основные:**
- `main.py` - бот
- `database.py` - БД
- `xray_api.py` - VPN
- `config.py` - настройки
- `admin_panel.py` - админка
- `payments/yookassa_integration.py` - платежи

**Запуск:**
- `docker-compose.yml` - конфигурация
- `Dockerfile` - образ
- `start.sh` - запуск
- `requirements.txt` - зависимости

**Всё готово к работе!** 🎉