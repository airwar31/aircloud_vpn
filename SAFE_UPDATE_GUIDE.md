# 🔄 Безопасное обновление на двух серверах

## 🎯 Стратегия обновления

**Главное правило:** Никогда не трогаем работающие конфиги без бэкапа!

```
ПОСЛЕДОВАТЕЛЬНОСТЬ:
1. Бэкапируем ВСЕ конфиги (VK и NL)
2. Обновляем файлы с git pull
3. Перезапускаем контейнеры (по одному!)
4. Проверяем логи
5. Тестируем VPN
6. Если всё OK → готово
7. Если ошибка → откатываем из бэкапа
```

---

## 📥 ШАГ 1: Бэкап на обоих серверах

### На VK сервере:

```bash
ssh root@243.x.x.x
cd /opt/aircloud_vpn/docker-configs

# Создаем папку для бэкапов
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Бэкапируем конфиги
cp -r vk-server/config.json $BACKUP_DIR/vk-config.json.bak
cp .env $BACKUP_DIR/.env.bak
cp docker-compose.yml $BACKUP_DIR/docker-compose.yml.bak

# Проверяем что всё скопировалось
ls -la $BACKUP_DIR/

# Выводим путь к бэкапу (может пригодиться)
echo "Backup directory: /opt/aircloud_vpn/docker-configs/$BACKUP_DIR"
```

### На NL сервере:

```bash
ssh root@85.239.56.174
cd /opt/aircloud_vpn/docker-configs

# Создаем папку для бэкапов
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

# Бэкапируем конфиги
cp -r nl-server/config.json $BACKUP_DIR/nl-config.json.bak
cp -r nl-server/certs $BACKUP_DIR/certs.bak
cp -r nl-server/bot_app $BACKUP_DIR/bot_app.bak
cp .env $BACKUP_DIR/.env.bak
cp docker-compose.yml $BACKUP_DIR/docker-compose.yml.bak

# Проверяем
ls -la $BACKUP_DIR/

# Выводим путь
echo "Backup directory: /opt/aircloud_vpn/docker-configs/$BACKUP_DIR"
```

---

## 🔄 ШАГ 2: Обновление файлов

### На VK сервере:

```bash
cd /opt/aircloud_vpn

# Проверяем что нет несохраненных изменений
git status

# Если есть локальные изменения (не из гайда выше)
# git stash

# Обновляем
git pull origin main

# Проверяем что изменилось
git log --oneline -5
```

### На NL сервере:

```bash
cd /opt/aircloud_vpn

# Проверяем статус
git status

# Обновляем
git pull origin main
```

---

## 🔍 ШАГ 3: Проверка новых файлов

### Что изменилось?

```bash
git diff HEAD~1..HEAD --name-only

# Должны быть обновлены:
# - docker-configs/vk-server/config.json (удален port 8443)
# - docker-configs/nl-server/config.json (добавлен port 8443)
# - docker-configs/nl-server/bot_app/tunnel_manager.py (single → NL)
# - docker-configs/nl-server/bot_app/xray_double_tunnel.py (новый метод)
# - docker-configs/nl-server/Dockerfile (EXPOSE 443 8443)
# - docker-configs/docker-compose.yml (port 8445)
```

### Проверим что конфиги синтаксически верны:

```bash
# На VK
cd /opt/aircloud_vpn/docker-configs
docker-compose exec vk-server xray -test -config /etc/xray/config.json

# На NL
docker-compose exec nl-server xray -test -config /etc/xray/config.json

# Должно быть: "The config is valid"
```

---

## 🚀 ШАГ 4: Обновление контейнеров

### Вариант А: Если контейнеры работают (рекомендуется)

#### На VK сервере:

```bash
cd /opt/aircloud_vpn/docker-configs

# Собираем новый образ (без остановки текущего)
docker-compose build vk-server

# Плавно заменяем контейнер (zero-downtime update)
docker-compose up -d vk-server

# Проверяем статус
docker-compose ps

# Смотрим логи (новый контейнер должен стартовать без ошибок)
docker-compose logs -f vk-server

# Жми Ctrl+C когда увидишь что стартовал нормально (через 5-10 сек)
```

#### На NL сервере:

```bash
cd /opt/aircloud_vpn/docker-configs

# Собираем образы (все 3, но более критичны nl-server и vpn-bot)
docker-compose build nl-server vpn-bot

# Начинаем с Xray (без бота)
docker-compose up -d nl-server

# Ждем 10 сек чтобы Xray стартовал
sleep 10

# Проверяем логи Xray
docker-compose logs nl-server | tail -20

# Если OK → обновляем бота
docker-compose up -d vpn-bot

# Финальная проверка
docker-compose ps
```

### Вариант Б: Если нужен restart (downtime неизбежен)

```bash
# Если что-то совсем сломалось

# На VK:
cd /opt/aircloud_vpn/docker-configs
docker-compose restart vk-server

# На NL:
docker-compose restart
```

---

## ✅ ШАГ 5: Проверка после обновления

### На VK сервере:

```bash
# Проверяем что контейнер Up
docker-compose ps | grep vk-server

# Проверяем logи (должны быть OK)
docker-compose logs vk-server | tail -20

# Проверяем что сервис слушает
netstat -tlnp | grep 443

# Тест подключения (с другой машины)
telnet 243.x.x.x 443
# (должно быть: Connected/Escape character is '^]')
# (жми Ctrl+] потом quit)
```

### На NL сервере:

```bash
# Проверяем все 3 контейнера
docker-compose ps

# Логи Xray
docker-compose logs nl-server | tail -20
# Должны быть строки про listening на 443 и 8443

# Логи бота
docker-compose logs vpn-bot | tail -10
# Должно быть про успешный старт

# Проверяем порты
netstat -tlnp | grep -E '443|8443'

# Тесты подключения
telnet 85.239.56.174 443
telnet 85.239.56.174 8443
# Оба должны быть Connected
```

---

## 🧪 ШАГ 6: Функциональное тестирование

### Проверяем что Double и Single работают

```bash
# Отправь боту команду /start
# Затем /buy → выбери Double Tunnel

# Импортируй конфиг в клиент и проверь:
# 1. Подключается ли?
# 2. Какой IP выходит? (должен быть NL, 85.239.56.174)

# Затем закажи Single Tunnel
# Проверь:
# 1. Подключается?
# 2. IP тот же (85.239.56.174)?
```

---

## ⚠️ ШАГ 7: Откат при проблемах

Если что-то за***alось и нужно откатить:

### На VK сервере:

```bash
cd /opt/aircloud_vpn/docker-configs

# Находим последний бэкап
ls -la backups/

# Допустим последний: backups/20260212_143022
BACKUP_DIR="backups/20260212_143022"

# Восстанавливаем конфиг
cp $BACKUP_DIR/vk-config.json.bak vk-server/config.json

# Откатываем git
git checkout HEAD -- .

# Перезапускаем контейнер
docker-compose restart vk-server

# Проверяем логи
docker-compose logs vk-server | tail -20
```

### На NL сервере:

```bash
cd /opt/aircloud_vpn/docker-configs

# Находим бэкап
BACKUP_DIR="backups/20260212_143022"

# Восстанавливаем
cp $BACKUP_DIR/nl-config.json.bak nl-server/config.json
cp -r $BACKUP_DIR/bot_app/* nl-server/bot_app/ 2>/dev/null

# Откатываем git
git checkout HEAD -- .

# Перезапускаем
docker-compose restart

# Проверяем
docker-compose ps
```

---

## 📋 Полная процедура обновления (скопипейсти)

### Для нетерпеливых (copy-paste всё сразу):

#### На VK:
```bash
ssh root@243.x.x.x << 'EOFVK'
cd /opt/aircloud_vpn/docker-configs
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
cp -r vk-server/config.json $BACKUP_DIR/vk-config.json.bak
cp .env $BACKUP_DIR/.env.bak
cd /opt/aircloud_vpn
git pull origin main
cd docker-configs
docker-compose build vk-server
docker-compose up -d vk-server
echo "✅ VK обновлен"
docker-compose logs vk-server | tail -10
EOFVK
```

#### На NL:
```bash
ssh root@85.239.56.174 << 'EOFNL'
cd /opt/aircloud_vpn/docker-configs
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
cp -r nl-server/config.json $BACKUP_DIR/nl-config.json.bak
cp -r nl-server/bot_app $BACKUP_DIR/bot_app.bak
cp .env $BACKUP_DIR/.env.bak
cd /opt/aircloud_vpn
git pull origin main
cd docker-configs
docker-compose build nl-server vpn-bot
docker-compose up -d nl-server
sleep 10
docker-compose up -d vpn-bot
echo "✅ NL обновлен"
docker-compose ps
EOFNL
```

---

## 🔔 Важные моменты

1. **Бэкап ПЕРЕД обновлением** - без исключений!
2. **git pull только если ты владелец репо** - иначе обновь файлы вручную
3. **Проверь синтаксис конфигов** - `xray -test -config` спасает жизни
4. **Обновляй VK первым** затем NL - в таком порядке!
5. **Не обновляй .env** - там твои приватные ключи!
6. **После обновления тестируй оба типа VPN** - и double и single

---

## 🚨 Если контейнер не стартует

```bash
# Проверяем ошибку
docker-compose logs nl-server 2>&1 | grep -i error

# Типичные ошибки:
# - "permission denied" → chmod 644 certs/privkey.pem
# - "config is invalid" → проверь JSON через xray -test
# - "cannot connect to NL" → проверь firewall/ip

# Откатываем
git checkout HEAD -- .
cp backups/LATEST/nl-config.json.bak nl-server/config.json
docker-compose restart nl-server
```

---

## ✅ Финальный чеклист

Перед обновлением:
- [ ] Сделал бэкап на VK
- [ ] Сделал бэкап на NL
- [ ] Проверил git status (нет локальных изменений)

После обновления:
- [ ] VK контейнер Up
- [ ] NL контейнер Up
- [ ] Bot контейнер Up
- [ ] Нет ошибок в логах
- [ ] Порты 443 и 8443 слушают
- [ ] Double Tunnel подключается
- [ ] Single Tunnel подключается
- [ ] IP правильный (85.239.56.174)

**Всё готово! 🎉**
