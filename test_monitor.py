#!/usr/bin/env python3
"""
Тест системы мониторинга устройств
"""

import asyncio
import logging
from device_monitor import DeviceMonitor
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_device_monitoring():
    """Тест мониторинга устройств"""
    
    print("🧪 Тестирование системы мониторинга устройств...")
    
    # Создаем экземпляр монитора
    monitor = DeviceMonitor()
    
    try:
        # Тест 1: Проверка получения статистики Xray
        print("\n1️⃣ Тестирование получения статистики Xray...")
        stats = await monitor.get_xray_stats()
        print(f"   Получено подключений: {len(stats)}")
        for email, connections in stats.items():
            print(f"   - {email}: {connections} устройств")
        
        # Тест 2: Проверка базы данных
        print("\n2️⃣ Тестирование базы данных...")
        
        # Получаем тестовых пользователей
        test_users = db.get_all_users()[:3]  # Первые 3 пользователя
        
        if not test_users:
            print("   ⚠️ Нет пользователей в базе данных для тестирования")
            return
            
        for user in test_users:
            vpn_keys = db.get_user_vpn_keys(user['telegram_id'])
            print(f"   - Пользователь {user['telegram_id']}: {len(vpn_keys)} ключей")
            
            for key in vpn_keys:
                print(f"     * {key['email']}: лимит {key.get('device_limit', 1)} устройств")
        
        # Тест 3: Симуляция превышения лимита
        print("\n3️⃣ Симуляция превышения лимита...")
        
        if test_users and len(test_users) > 0:
            test_user = test_users[0]
            user_keys = db.get_user_vpn_keys(test_user['telegram_id'])
            
            if user_keys:
                test_key = user_keys[0]
                print(f"   Отправка тестового уведомления пользователю {test_user['telegram_id']}")
                
                # Отправляем тестовое уведомление
                await monitor.send_warning(
                    user_id=test_user['telegram_id'],
                    email=test_key['email'],
                    active=3,  # Симулируем 3 активных устройства
                    allowed=test_key.get('device_limit', 1)
                )
                print("   ✅ Тестовое уведомление отправлено")
            else:
                print("   ⚠️ У тестового пользователя нет VPN ключей")
        
        # Тест 4: Проверка логики мониторинга
        print("\n4️⃣ Тестирование логики мониторинга...")
        await monitor.check_device_limits()
        print("   ✅ Проверка лимитов завершена")
        
        print("\n✅ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        logger.error(f"Ошибка тестирования: {e}")
        
    finally:
        await monitor.cleanup()

async def main():
    """Главная функция"""
    await test_device_monitoring()

if __name__ == "__main__":
    asyncio.run(main())