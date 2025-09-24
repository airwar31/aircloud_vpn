#!/usr/bin/env python3
"""Скрипт для обновления проекта с сохранением данных"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def update_project():
    """Обновление проекта"""
    print("🔄 Начинаем обновление проекта...")
    
    # 1. Проверяем наличие важных файлов
    important_files = ['.env', 'config.py', 'database.py']
    missing_files = [f for f in important_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Отсутствуют важные файлы: {missing_files}")
        return False
    
    # 2. Создаем резервную копию
    print("📦 Создание резервной копии...")
    try:
        exec(open('backup_script.py').read())
    except Exception as e:
        print(f"⚠️  Ошибка создания бэкапа: {e}")
    
    # 3. Обновляем зависимости
    print("📥 Обновление зависимостей...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'], 
                      check=True)
        print("✅ Зависимости обновлены")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка обновления зависимостей: {e}")
        return False
    
    # 4. Проверяем конфигурацию
    print("🔧 Проверка конфигурации...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['BOT_TOKEN', 'YOOKASSA_SHOP_ID', 'YOOKASSA_SECRET_KEY', 
                        'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Отсутствуют переменные окружения: {missing_vars}")
            return False
        
        print("✅ Конфигурация корректна")
        
    except Exception as e:
        print(f"❌ Ошибка проверки конфигурации: {e}")
        return False
    
    # 5. Тестируем подключение к БД
    print("🗄️  Проверка подключения к БД...")
    try:
        import database
        db = database.Database()
        # Простой тест подключения
        print("✅ Подключение к БД успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False
    
    print("🎉 Обновление завершено успешно!")
    print("\n📋 Следующие шаги:")
    print("1. Перезапустите бота: python bot.py")
    print("2. Проверьте работу основных функций")
    print("3. Мониторьте логи на предмет ошибок")
    
    return True

if __name__ == "__main__":
    success = update_project()
    sys.exit(0 if success else 1)