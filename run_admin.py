#!/usr/bin/env python3
"""
Скрипт запуска админ панели VPN бота
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

try:
    from admin_panel import main
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что установлены все зависимости: pip install -r requirements.txt")
    sys.exit(1)

def main_wrapper():
    """Обертка для запуска админ панели"""
    print("🔧 Запуск админ панели VPN бота...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Админ панель остановлена пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_wrapper()