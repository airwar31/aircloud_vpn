# 🚀 AirCloud VPN - Простой запуск

## Быстрый старт

### 1. Загрузите файлы на сервер
```bash
# Создайте папку
mkdir /root/aircloud-vpn
cd /root/aircloud-vpn

# Загрузите сюда все файлы проекта
```

### 2. Запустите проект
```bash
# Сделайте скрипт исполняемым
chmod +x start.sh

# Запустите
./start.sh
```

### 3. Готово!
Бот запущен с предустановленными настройками:
- **Telegram Bot Token**: уже настроен
- **Admin ID**: уже настроен  
- **ЮKassa**: тестовые ключи
- **VPN сервер**: 5.129.224.166:443
- **Reality ключи**: уже вставлены

## Управление

```bash
# Просмотр логов
docker-compose -f docker-compose-simple.yml logs -f

# Перезапуск
docker-compose -f docker-compose-simple.yml restart

# Остановка
docker-compose -f docker-compose-simple.yml down
```

## Что настроено автоматически

✅ **Telegram бот** - готов к работе  
✅ **ЮKassa** - тестовые платежи  
✅ **VPN сервер** - подключен к 5.129.224.166  
✅ **Reality ключи** - настроены  
✅ **База данных** - автоматически создается  
✅ **Тарифы** - настроены (99₽, 249₽, 499₽, 999₽)  

## Файлы для запуска

Нужны только эти файлы:
- `main.py` - основной код бота
- `database.py` - работа с БД
- `xray_api.py` - VPN конфигурации
- `config.py` - настройки
- `admin_panel.py` - админ панель
- `device_monitor.py` - мониторинг устройств
- `payments/yookassa_integration.py` - платежи
- `utils.py` - утилиты
- `plans.json` - тарифы
- `requirements.txt` - зависимости
- `Dockerfile` - образ Docker
- `docker-compose-simple.yml` - запуск
- `start.sh` - скрипт запуска

**Всё остальное удалено для упрощения!** 🚀