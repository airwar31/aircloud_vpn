#!/usr/bin/env python3
"""
Скрипт для запуска мониторинга устройств
"""

import asyncio
import logging
from device_monitor import DeviceMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Основная функция запуска мониторинга"""
    monitor = DeviceMonitor()
    
    try:
        print("🚀 Запуск мониторинга устройств...")
        await monitor.start()
    except KeyboardInterrupt:
        print("\n⏹️ Получен сигнал остановки")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await monitor.cleanup()
        print("✅ Мониторинг остановлен")

if __name__ == "__main__":
    asyncio.run(main())