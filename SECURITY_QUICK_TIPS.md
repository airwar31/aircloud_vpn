# 🚀 Security Tips: Быстрая защита

## 1️⃣ Сразу после развертывания (5 минут)

```bash
# На обоих серверах

# Firewall (блокируем всё кроме нужного)
sudo ufw default deny incoming
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp        # VK
sudo ufw allow 8443/tcp       # NL только
sudo ufw limit 22/tcp
sudo ufw enable

# Fail2ban (защита от бруфорса)
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Docker auto-restart (важно!)
# Добавь в docker-compose.yml: restart: always
docker-compose up -d
```

---

## 2️⃣ SSH Hardening (3 минуты)

```bash
# Запрещаем root логин
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Только ключи, без паролей
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Перезагружаем SSH
sudo systemctl restart sshd

# Генерируем ключ если не будет SSH доступа
# ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
```

---

## 3️⃣ Xray Rate Limiting (в config.json)

```json
"connLimit": {
  "conns": 5000,        // Max total connections
  "connsPerIP": 100     // Max per single IP
}
```

**Что делает:**
- 5000 клиентов макс одновременно
- Один IP может иметь максимум 100 соединений (защита от abuse)

---

## 4️⃣ Мониторинг DDoS в реальном времени

```bash
# Смотрим в реальном времени топ IP которые подключаются
watch 'netstat -tnp 2>/dev/null | grep ESTABLISHED | awk '"'"'{print $5}'"'"' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10'

# Смотрим бан-листы Fail2ban
sudo fail2ban-client status sshd

# Смотрим заблокированные IP
sudo iptables -L -n | grep -i drop
```

---

## 5️⃣ Быстрая диагностика если что-то за***ллось

```bash
# 1. Контейнеры запущены?
docker-compose ps

# 2. Порты слушают?
netstat -tlnp | grep -E '443|8443'

# 3. Ошибки в логах?
docker-compose logs nl-server 2>&1 | grep -i error

# 4. Fail2ban банит?
sudo fail2ban-client status

# 5. Firewall блокирует?
sudo ufw status verbose
```

---

## 6️⃣ Если под DDoS атакой прямо сейчас

```bash
# 1. Смотрим откуда идет трафик
watch 'netstat -tnp | grep :443 | awk '"'"'{print $5}'"'"' | cut -d: -f1 | sort | uniq -c | sort -rn'

# 2. Блокируем конкретный IP через UFW
sudo ufw deny from 1.2.3.4

# 3. Включаем Rate Limit на порт
sudo iptables -A INPUT -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j DROP

# 4. Перезагружаем контейнеры
docker-compose restart

# 5. Звоним провайдеру если не помогает
# Они включат DDoS mitigation на уровне ISP
```

---

## 7️⃣ Регулярно проверяй

```bash
# Еженедельно
- docker-compose logs | grep -i error
- sudo fail2ban-client status
- netstat -tlnp | grep -vE '127|docker|LISTEN'

# Ежемесячно
- apt update && apt upgrade -y docker.io
- certbot renew --dry-run
- Backup конфиги
```

---

## ⚠️ Главное

| Что | Почему | Как |
|-----|--------|-----|
| **UFW на port 22** | SSH攻击 = root компромисс | `ufw limit 22` |
| **Fail2ban** | Автоматический ban bruteforce | `systemctl enable fail2ban` |
| **Rate limit в Xray** | Защита от abuse одного IP | `connsPerIP: 100` |
| **restart: always** | При DDoS контейнер упадет → auto-restart | В docker-compose.yml |
| **Только SSH ключи** | От паролей пароли менее безопасны | `PasswordAuthentication no` |
| **Мониторь логи** | Рано узнаешь об атаке | `docker-compose logs -f` |

---

## ✅ Список для Paranoid Mode (максимальная защита)

```bash
# На каждом сервере

# 1. Двойной брандмауэр
sudo ufw enable
sudo ufw limit 22/tcp

# 2. Fail2ban с агрессивными параметрами
# maxretry = 2
# bantime = 86400 (1 день)

# 3. Отключить все сервисы кроме SSH и Xray
sudo systemctl disable apache2 nginx postfix mysql

# 4. Включить SELinux (если CentOS) или AppArmor (Ubuntu)
sudo apt install -y apparmor

# 5. Регулярное резервное копирование
0 2 * * * /usr/local/bin/backup.sh

# 6. Мониторинг от 24/7 сервиса (опционально)
# NewRelic, DataDog, или самодельный скрипт

# 7. Логирование всего
# Audit logs
# Docker logs
# Xray logs
```

---

## 🎯 Минимальная защита (для начинающих):

```bash
sudo ufw enable
sudo ufw limit 22/tcp
sudo apt install -y fail2ban
docker-compose restart
# Готово!
```

**Это закроет 90% простых атак. Остальное - DDoS protection от ISP.**
