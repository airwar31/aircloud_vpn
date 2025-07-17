# Инструкция по использованию Docker для AirCloud VPN

## Установка Docker и Docker Compose

### Ubuntu/Debian

```bash
# Установка Docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt update
sudo apt install -y docker-ce

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

### CentOS/RHEL

```bash
# Установка Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавление текущего пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

## Запуск AirCloud VPN

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourusername/aircloud_vpn.git
   cd aircloud_vpn
   ```

2. Создайте файл `.env` из примера:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Настройте параметры в файле `.env`:
   ```
   BOT_TOKEN=ваш_токен_бота
   VPN_SERVER_ADDRESS=ваш_ip_адрес
   ADMIN_IDS=ваш_telegram_id
   ```

4. Запустите контейнеры:
   ```bash
   docker-compose up -d
   ```

## Управление контейнерами

### Просмотр логов

```bash
# Просмотр всех логов
docker-compose logs -f

# Просмотр последних 100 строк логов
docker-compose logs --tail=100 -f
```

### Перезапуск контейнеров

```bash
docker-compose restart
```

### Остановка контейнеров

```bash
docker-compose down
```

### Обновление контейнеров

```bash
# Получение последних изменений
git pull

# Пересборка и запуск контейнеров
docker-compose up --build -d
```

## Управление пользователями

### Создание нового пользователя

```bash
./create_user.sh
```

### Просмотр списка пользователей

```bash
docker-compose exec aircloud-vpn python -c "import asyncio; from xray_api import XrayAPI; users = asyncio.run(XrayAPI().get_users()); print(users)"
```

## Резервное копирование

### Резервное копирование базы данных

```bash
docker-compose exec aircloud-vpn cp /app/aircloud_vpn.db /app/data/backup_$(date +%Y%m%d).db
```

### Резервное копирование конфигурации Xray

```bash
docker-compose exec aircloud-vpn cp /etc/xray/config.json /app/data/xray_config_$(date +%Y%m%d).json
```

## Устранение неполадок

### Проверка статуса контейнера

```bash
docker-compose ps
```

### Проверка статуса Xray

```bash
docker-compose exec aircloud-vpn service xray status
```

### Проверка открытых портов

```bash
docker-compose exec aircloud-vpn netstat -tulpn | grep xray
```

### Перезапуск Xray

```bash
docker-compose exec aircloud-vpn service xray restart
```

### Просмотр логов Xray

```bash
docker-compose exec aircloud-vpn cat /var/log/xray/error.log
```