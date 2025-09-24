#!/bin/bash

# Скрипт для бэкапа перед обновлением
BACKUP_DIR="/backup/$(date +%Y%m%d_%H%M%S)"
PROJECT_DIR="/path/to/your/aircloud_vpn"

echo "Создание бэкапа в $BACKUP_DIR..."
mkdir -p $BACKUP_DIR

# Бэкап базы данных
docker exec aircloud_vpn_bot python3 backup_script.py

# Бэкап конфигурации
cp $PROJECT_DIR/.env $BACKUP_DIR/
cp -r $PROJECT_DIR/logs $BACKUP_DIR/
cp -r /etc/xray $BACKUP_DIR/xray_config

# Бэкап Docker volumes (если используются)
docker run --rm -v aircloud_vpn_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/volumes.tar.gz -C /data .

echo "Бэкап завершен: $BACKUP_DIR"