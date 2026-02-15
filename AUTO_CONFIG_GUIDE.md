# 🔧 АВТОМАТИЧЕСКАЯ КОНФИГУРАЦИЯ REALITY И TLS

## 📋 Описание

Два Python скрипта для автоматического получения конфигурации из 3xui панелей:

1. **init_reality_config.py** - получает Reality параметры с VK сервера
2. **init_tls_config.py** - получает TLS параметры с NL сервера

---

## 🚀 Быстрый старт

### Шаг 1: Убедиться что 3xui панели запущены

**VK сервер:**
```bash
ssh root@89.208.86.167
docker ps | grep xray  # должен быть контейнер 3xui
```

**NL сервер:**
```bash
ssh root@85.239.56.174
docker ps | grep xray  # должен быть контейнер 3xui
```

### Шаг 2: Заполнить .env файлы

**VK сервер (.env):**
```env
VK_XRAY_HOST=89.208.86.167
VK_XRAY_PORT=54321
VK_XRAY_USERNAME=ваш_логин_админа
VK_XRAY_PASSWORD=ваш_пароль_админа
```

**NL сервер (.env):**
```env
NL_SERVER_IP=85.239.56.174
NL_SERVER_PORT=8443  # или где запущена 3xui
NL_SERVER_USERNAME=ваш_логин_админа
NL_SERVER_PASSWORD=ваш_пароль_админа
```

### Шаг 3: Запустить скрипты

**Для VK сервера (получить Reality конфиг):**
```bash
cd deploy/vk-server

# Установить зависимости (если нужны)
pip install aiohttp

# Запустить скрипт (он прочитает .env автоматически)
python init_reality_config.py

# Или с явными параметрами:
python init_reality_config.py \
  --host 89.208.86.167 \
  --port 54321 \
  --username admin \
  --password password \
  --inbound-id 1 \
  --env .env
```

**Для NL сервера (получить TLS конфиг):**
```bash
cd deploy/nl-server

# Запустить скрипт
python init_tls_config.py

# Или с явными параметрами:
python init_tls_config.py \
  --host 85.239.56.174 \
  --port 8443 \
  --username admin \
  --password password \
  --inbound-id 0 \
  --env .env
```

### Шаг 4: Проверить результат

**VK сервер (.env):**
```env
# После запуска скрипта будут заполнены:
REALITY_PUBLIC_KEY=abc123...
REALITY_SHORT_ID=shortID
REALITY_FINGERPRINT=chrome
REALITY_SNI=dl.google.com
```

**NL сервер (.env):**
```env
# После запуска скрипта будут заполнены:
NL_TLS_SERVER_NAME=example.com
NL_TLS_ALPN=h2,http/1.1
NL_TLS_CERTIFICATE_FILE=/path/to/cert
NL_TLS_KEY_FILE=/path/to/key
```

---

## 📖 Использование скриптов в боте

### Автоматический запуск при инициализации бота

Добавьте в main.py вашего бота:

```python
import asyncio
import os
import sys

async def initialize_configs():
    """Инициализировать конфигурацию при первом запуске"""
    
    # Проверяем наличие необходимых значений в .env
    if not os.getenv("REALITY_PUBLIC_KEY") or os.getenv("REALITY_PUBLIC_KEY") == "PUBLIC_KEY_FROM_PANEL":
        logger.info("Получаю Reality конфигурацию с VK сервера...")
        
        from init_reality_config import XrayRealityConfigurator
        
        try:
            async with XrayRealityConfigurator(
                host=os.getenv("VK_XRAY_HOST"),
                port=int(os.getenv("VK_XRAY_PORT")),
                username=os.getenv("VK_XRAY_USERNAME"),
                password=os.getenv("VK_XRAY_PASSWORD"),
                env_path=".env"
            ) as configurator:
                await configurator.configure(inbound_id=1)
        except Exception as e:
            logger.warning(f"Не удалось получить Reality конфиг: {e}")
    
    if not os.getenv("NL_TLS_SERVER_NAME") or os.getenv("NL_TLS_SERVER_NAME") == "example.com":
        logger.info("Получаю TLS конфигурацию с NL сервера...")
        
        from init_tls_config import XrayTLSConfigurator
        
        try:
            async with XrayTLSConfigurator(
                host=os.getenv("NL_SERVER_IP"),
                port=int(os.getenv("NL_SERVER_PORT")),
                username=os.getenv("NL_SERVER_USERNAME"),
                password=os.getenv("NL_SERVER_PASSWORD"),
                env_path=".env"
            ) as configurator:
                await configurator.configure(inbound_id=0)
        except Exception as e:
            logger.warning(f"Не удалось получить TLS конфиг: {e}")

async def main():
    # Инициализируем конфигурацию
    await initialize_configs()
    
    # Остальной код...
```

---

## 🔍 Параметры скриптов

### init_reality_config.py

| Параметр | Описание | По умолчанию |
|----------|---------|--------------|
| `--host` | IP адрес VK сервера | `VK_XRAY_HOST` из .env |
| `--port` | Порт 3xui панели | `VK_XRAY_PORT` из .env |
| `--username` | Логин админа | `VK_XRAY_USERNAME` из .env |
| `--password` | Пароль админа | `VK_XRAY_PASSWORD` из .env |
| `--env` | Путь к .env файлу | `.env` |
| `--inbound-id` | ID inbound'а | `1` (входная точка VK) |

### init_tls_config.py

| Параметр | Описание | По умолчанию |
|----------|---------|--------------|
| `--host` | IP адрес NL сервера | `NL_SERVER_IP` из .env |
| `--port` | Порт 3xui панели | `NL_SERVER_PORT` из .env |
| `--username` | Логин админа | `NL_SERVER_USERNAME` из .env |
| `--password` | Пароль админа | `NL_SERVER_PASSWORD` из .env |
| `--env` | Путь к .env файлу | `.env` |
| `--inbound-id` | ID inbound'а | `0` (основная входная точка NL) |

---

## 🆘 Решение проблем

### Ошибка: "Не удалось подключиться"
```bash
# Проверьте, что сервер доступен
ping 89.208.86.167
ping 85.239.56.174

# Проверьте, что 3xui панель запущена
curl http://89.208.86.167:54321/api/inbounds
```

### Ошибка: "Ошибка авторизации"
```bash
# Убедитесь, что пароль правильный
# Попробуйте залогиниться в 3xui вручную через браузер
# http://89.208.86.167:54321

# Обновите .env с правильными credentials
```

### Ошибка: "Reality конфигурация не найдена"
```bash
# Проверьте, что inbound с ID 1 существует и использует Reality
# В 3xui выберите Inbound -> посмотрите Protocol
# Должен быть VLESS с Reality
```

### Ошибка: "TLS конфигурация не найдена"
```bash
# Убедитесь, что у inbound с ID 0 настроен TLS
# В 3xui: Inbound -> Stream Settings -> TLS
```

---

## 📝 Что скрипты делают

### init_reality_config.py:

1. Подключается к 3xui VK сервера
2. Авторизуется с помощью username/password
3. Получает конфигурацию inbound'а
4. Извлекает Reality параметры:
   - `publicKey`
   - `shortIds`
   - `fingerprint`
   - `serverName`
5. Обновляет .env файл с этими значениями

### init_tls_config.py:

1. Подключается к 3xui NL сервера
2. Авторизуется с помощью username/password
3. Получает конфигурацию inbound'а
4. Извлекает TLS параметры:
   - `serverName`
   - `alpn`
   - `certificateFile`
   - `keyFile`
5. Обновляет .env файл с этими значениями

---

## 🔐 Безопасность

- Скрипты используют HTTPS где возможно
- Не сохраняют пароли (используют только для авторизации)
- Пароли берутся из .env, который не должен коммититься в Git
- Все запросы проходят внутри вашей сети

---

## 🎯 Когда использовать

✅ **Используйте скрипты когда:**
- Вы впервые настраиваете сервера
- Вы изменили конфигурацию в 3xui панели
- Вы переносите конфигурацию на другой сервер
- Вы хотите автоматизировать процесс

❌ **Не используйте когда:**
- У вас нет доступа к 3xui панели
- 3xui панель не запущена
- Вы предпочитаете вводить значения вручную

---

## 📚 Дополнительно

Скрипты используют:
- `aiohttp` - асинхронные HTTP запросы
- `asyncio` - асинхронное программирование
- Встроенный Python `json` для парсинга ответов

**Требуемые зависимости:**
```bash
pip install aiohttp
```

---

## 💡 Советы

1. **Запустите скрипты сразу после развертывания 3xui:**
   ```bash
   # На VK сервере
   python init_reality_config.py
   
   # На NL сервере
   python init_tls_config.py
   ```

2. **Используйте явные параметры для скриптов в CI/CD:**
   ```bash
   python init_reality_config.py \
     --host $VK_HOST \
     --port $VK_PORT \
     --username $VK_USER \
     --password $VK_PASS
   ```

3. **Проверяйте логи:**
   ```
   ✅ означает успешное выполнение
   ❌ означает ошибку
   ⚠️  означает предупреждение
   ```

---

**Готово! Теперь конфигурация填充автоматически! 🚀**
