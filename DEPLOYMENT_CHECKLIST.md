# ✅ Checklist: Проверка перед запуском

## Pre-Deployment (до развертывания)

- [ ] Reality ключи сгенерированы: `xray x25519`
  - [ ] Private key сохранен
  - [ ] Public key сохранен
- [ ] IP адреса известны:
  - [ ] VK сервер IP: `_______________`
  - [ ] NL сервер IP: `_______________`
- [ ] Доменное имя готово:
  - [ ] Домен: `_______________`
  - [ ] DNS A запись указывает на NL IP
- [ ] Порты открыты в firewall:
  - [ ] VK: 443 (входящий)
  - [ ] NL: 443, 8443 (входящие)

---

## VK Сервер (Россия)

### Подготовка

- [ ] SSH доступ работает
- [ ] Docker установлен: `docker --version`
- [ ] Docker Compose установлен: `docker-compose --version`
- [ ] Git установлен: `git --version`
- [ ] Проект клонирован в `/opt/aircloud_vpn`

### Конфигурация

- [ ] .env файл создан в `docker-configs/`
- [ ] .env содержит:
  - [ ] `VK_PRIVATE_KEY=XXXXXXX...`
  - [ ] `VK_PUBLIC_KEY=YYYYYYY...`
  - [ ] `UUID_DOUBLE=550e8400...`
  - [ ] `NL_SERVER=85.239.56.174`
  - [ ] `NL_DOMAIN=nl.vpn.example.com`
  - [ ] `BOT_TOKEN=123456...`

### vk-server/config.json

- [ ] Строка `"privateKey": "XXXXXXX..."` обновлена (Reality ключ)
- [ ] Строка `"id": "550e8400..."` обновлена (UUID_DOUBLE)
- [ ] Строка `"address": "nl-server"` отсутствует или изменена на NL IP
  - Проверьте outbound section: `"address": "85.239.56.174"`

### Запуск

- [ ] Собрана образ: `docker-compose build vk-server` (без ошибок)
- [ ] Контейнер запущен: `docker-compose up -d vk-server` (без ошибок)
- [ ] Контейнер в состоянии Up: `docker-compose ps` (STATUS: Up x minutes)
- [ ] Логи нормальные: `docker-compose logs vk-server | tail -10`
  - [ ] Нет Error/Exception
  - [ ] Есть строка про listening/started
- [ ] Порт слушает:
  - [ ] `netstat -tlnp | grep 443` показывает 0.0.0.0:443

---

## NL Сервер (Нидерланды)

### Подготовка

- [ ] SSH доступ работает
- [ ] Docker установлен
- [ ] Docker Compose установлен
- [ ] Git установлен
- [ ] Проект клонирован в `/opt/aircloud_vpn`

### SSL Сертификат (критично!)

- [ ] Домен DNS A запись указывает на NL IP (проверьте `nslookup nl.vpn.example.com`)
- [ ] Certbot установлен: `certbot --version`
- [ ] SSL сертификат получен:
  ```bash
  certbot certonly --standalone -d nl.vpn.example.com \
    --email admin@example.com --agree-tos
  ```
- [ ] Сертификаты существуют:
  - [ ] `/etc/letsencrypt/live/nl.vpn.example.com/fullchain.pem`
  - [ ] `/etc/letsencrypt/live/nl.vpn.example.com/privkey.pem`
- [ ] Сертификаты скопированы:
  - [ ] `nl-server/certs/fullchain.pem` существует
  - [ ] `nl-server/certs/privkey.pem` существует
- [ ] Права на файлы:
  - [ ] `chmod 644 nl-server/certs/privkey.pem`

### Конфигурация

- [ ] .env файл создан (КОП'я с VK сервера, но отредактированный):
  - [ ] `VK_SERVER=243.x.x.x`
  - [ ] `VK_PRIVATE_KEY=XXXX...` (ТОЧНО ТАКОЙ ЖЕ как на VK!)
  - [ ] `VK_PUBLIC_KEY=YYYY...` (ТОЧНО ТАКОЙ ЖЕ как на VK!)
  - [ ] `UUID_DOUBLE=550e8400...` (ТОЧНО ТАКОЙ ЖЕ как на VK!)
  - [ ] `UUID_SINGLE=550e8400...` (ТОЧНО ТАКОЙ ЖЕ как на VK!)
  - [ ] `NL_SERVER=85.239.56.174`
  - [ ] `NL_DOMAIN=nl.vpn.example.com`
  - [ ] `BOT_TOKEN=123456...` (ТОЧНО ТАКОЙ ЖЕ как на VK!)

### nl-server/config.json

- [ ] Строка `"serverName": "nl.vpn.example.com"` обновлена
- [ ] Оба UUID обновлены:
  - [ ] Double инбаунд: `"id": "550e8400-e29b-41d4-a716-446655440000"`
  - [ ] Single инбаунд: `"id": "550e8400-e29b-41d4-a716-446655440001"`
- [ ] Пути к сертификатам корректны:
  - [ ] `"certificateFile": "/etc/xray/certs/fullchain.pem"`
  - [ ] `"keyFile": "/etc/xray/certs/privkey.pem"`

### Запуск

- [ ] Собраны образы: `docker-compose build` (все 3 образа: vk-server, nl-server, vpn-bot)
- [ ] Контейнеры запущены: `docker-compose up -d`
- [ ] Все 3 контейнера в состоянии Up:
  ```bash
  docker-compose ps
  # STATUS: Up x minutes для всех 3
  ```
- [ ] Логи Xray на NL нормальные:
  - [ ] `docker-compose logs nl-server | tail -20`
  - [ ] Нет Error про сертификаты
  - [ ] Есть про listening на 443 и 8443
- [ ] Порты слушают:
  - [ ] `netstat -tlnp | grep 443` показывает 0.0.0.0:443
  - [ ] `netstat -tlnp | grep 8443` показывает 0.0.0.0:8443
- [ ] Логи бота:
  - [ ] `docker-compose logs vpn-bot | head -20`
  - [ ] Нет ошибок про подключение к БД
  - [ ] Бот готов получать сообщения

---

## Тестирование связи VK ↔ NL

### Проверка 1: Может ли VK достичь NL?

```bash
# На VK сервере
docker-compose exec vk-server curl -I https://85.239.56.174:443

# Должно быть:
# HTTP/1.1 200 OK  (или похожее)
# НЕ должно быть: Connection refused, Timeout
```

- [ ] Результат: OK / Error `_______________`

### Проверка 2: Логи показывают успешное подключение?

```bash
# На NL сервере
docker-compose logs nl-server | grep -i "accept\|inbound\|client"

# На VK сервере
docker-compose logs vk-server | grep -i "success\|outbound\|connected"
```

- [ ] Видны логи подключений

### Проверка 3: Xray инправсил правила?

```bash
# На NL сервере
docker-compose exec nl-server xray -test -config /etc/xray/config.json

# Должно быть:
# "The config is valid"
```

- [ ] Конфиг валиден

---

## Тестирование VPN

### Test 1: Double Tunnel

- [ ] Запустите бота: `/start`
- [ ] Заказьте подписку: `/buy` → выберите Double
- [ ] Получили VLESS ссылку
- [ ] Импортировали в клиент (V2RayNG, Clash и т.д.)
- [ ] Подключились
- [ ] Проверили IP на ipinfo.io:
  - [ ] IP из Нидерландов: ✅
  - [ ] Не ваш обычный IP: ✅
  - [ ] Не IP VK сервера: ✅

### Test 2: Single Tunnel

- [ ] Заказьте подписку: `/buy` → выберите Single
- [ ] Получили VLESS ссылку (должна быть на порт 8445 или 85.239.56.174:8443)
- [ ] Импортировали в клиент
- [ ] Подключились
- [ ] Проверили IP:
  - [ ] IP: 85.239.56.174 ✅
  - [ ] Такой же как в Double: ✅

---

## Финальная проверка

```bash
# На VK сервере
docker-compose ps
# Должно быть: vk-xray-server  Up

# На NL сервере
docker-compose ps
# Должны быть: nl-xray-server  Up
#             vpn-telegram-bot  Up
```

| Пункт | VK | NL | Bot |
|-------|----|----|-----|
| Docker Up | ✅ | ✅ | ✅ |
| Порты слушают | 443 | 443, 8443 | - |
| Логи OK | ✅ | ✅ | ✅ |
| SSL Cert | ❌ | ✅ | - |
| VPN работает | - | ✅ | - |

---

## Если что-то не работает

### VK контейнер не стартует

```bash
docker-compose logs vk-server
# Проверьте:
# - Reality ключ правильный?
# - UUID уникальный?
# - NL адрес правильный?
```

### NL контейнер не стартует

```bash
docker-compose logs nl-server
# Проверьте:
# - SSL сертификаты в place?
# - Пути к сертификатам правильные?
# - UUID правильные?
# - serverName совпадает с доменом?
```

### VPN не работает

```bash
# На NL проверьте логи
docker-compose logs nl-server | grep -i error

# Тестируйте подключение
curl -I https://85.239.56.174:8444 --insecure
```

### Нет подключения VK → NL

```bash
# На VK проверьте DNS работает
nslookup 85.239.56.174
# или
ping 85.239.56.174

# Проверьте firewall на NL и VK
sudo ufw status
```

---

**✅ Все пункты отмечены → Система готова! 🚀**
