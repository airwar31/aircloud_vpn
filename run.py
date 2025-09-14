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
    """Проверка наличия переменных окружения"""
    import os
    required_vars = ['BOT_TOKEN', 'YOOKASSA_SHOP_ID', 'YOOKASSA_SECRET_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("📝 Проверьте файл .env или переменные окружения")
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