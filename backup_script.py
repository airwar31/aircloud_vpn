#!/usr/bin/env python3
"""Скрипт для создания резервной копии БД и конфигурации"""

import os
import shutil
from datetime import datetime
import subprocess

def create_backup():
    """Создание резервной копии"""
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Копируем конфигурационные файлы
    config_files = ['.env', 'config.py', 'database.py']
    for file in config_files:
        if os.path.exists(file):
            shutil.copy2(file, backup_dir)
            print(f"✅ Скопирован {file}")
    
    # Экспорт БД (если MySQL доступен локально)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_host = os.getenv('DB_HOST')
        db_user = os.getenv('DB_USER') 
        db_pass = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')
        
        dump_file = os.path.join(backup_dir, f"{db_name}_backup.sql")
        cmd = f"mysqldump -h {db_host} -u {db_user} -p{db_pass} {db_name} > {dump_file}"
        
        print(f"📦 Создание дампа БД: {dump_file}")
        # subprocess.run(cmd, shell=True, check=True)
        print("⚠️  Для создания дампа БД выполните команду вручную:")
        print(cmd)
        
    except Exception as e:
        print(f"❌ Ошибка экспорта БД: {e}")
    
    print(f"✅ Резервная копия создана в папке: {backup_dir}")

if __name__ == "__main__":
    create_backup()