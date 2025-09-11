#!/usr/bin/env python3
"""
Скрипт запуска VPN бота
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

try:
    from bot import main
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что установлены все зависимости: pip install -r requirements.txt")
    sys.exit(1)

def check_env_file():
    """Проверка наличия файла .env"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Файл .env не найден!")
        print("📝 Скопируйте .env.example в .env и заполните настройки:")
        print("   cp .env.example .env")
        return False
    return True

def main_wrapper():
    """Обертка для запуска бота"""
    print("🚀 Запуск VPN Telegram бота...")
    
    if not check_env_file():
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_wrapper()