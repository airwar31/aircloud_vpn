import asyncio
import logging
from session_manager import SessionManager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DeviceMonitor:
    """Мониторинг устройств и автоматическая блокировка при превышении лимита"""
    
    def __init__(self, check_interval: int = 60):
        self.session_manager = SessionManager()
        self.check_interval = check_interval
        self.running = False
    
    async def start_monitoring(self):
        """Запуск мониторинга"""
        self.running = True
        logger.info("Запущен мониторинг устройств")
        
        while self.running:
            try:
                await self.check_all_users()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Ошибка в мониторинге устройств: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.running = False
        logger.info("Остановлен мониторинг устройств")
    
    async def check_all_users(self):
        """Проверка всех пользователей на превышение лимита устройств"""
        import sqlite3
        
        conn = sqlite3.connect("aircloud_vpn.db")
        cursor = conn.cursor()
        
        try:
            # Получаем всех пользователей с активными подписками
            cursor.execute('''
                SELECT xray_uuid, devices FROM subscriptions 
                WHERE is_active = TRUE AND xray_uuid IS NOT NULL
            ''')
            
            subscriptions = cursor.fetchall()
            
            for xray_uuid, max_devices in subscriptions:
                await self.check_user_devices(xray_uuid, max_devices)
                
        except Exception as e:
            logger.error(f"Ошибка проверки пользователей: {e}")
        finally:
            conn.close()
    
    async def check_user_devices(self, xray_uuid: str, max_devices: int):
        """Проверка конкретного пользователя"""
        try:
            # Получаем активные сессии пользователя
            sessions = await self.session_manager.get_active_sessions(xray_uuid)
            current_devices = len(sessions)
            
            if current_devices > max_devices:
                logger.warning(f"Пользователь {xray_uuid[:8]}... превысил лимит: {current_devices}/{max_devices}")
                
                # Блокируем и уведомляем
                await self.session_manager._notify_user_limit_exceeded(
                    xray_uuid, current_devices, max_devices
                )
            
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя {xray_uuid[:8]}...: {e}")

# Глобальный экземпляр монитора
device_monitor = DeviceMonitor()

async def start_device_monitoring():
    """Запуск мониторинга устройств в фоновом режиме"""
    await device_monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(start_device_monitoring())