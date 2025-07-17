import os
import logging
import subprocess
import json
from datetime import datetime, timedelta
from xray_config import XrayConfig

logger = logging.getLogger(__name__)

class XrayAPI:
    """API для управления Xray и пользователями"""
    
    def __init__(self, config_path="/etc/xray/config.json"):
        self.config_path = config_path
        self.xray_config = XrayConfig(config_path=config_path)
    
    async def restart_xray(self):
        """Перезапуск сервиса Xray"""
        try:
            # Используем systemctl для перезапуска сервиса
            result = subprocess.run(["systemctl", "restart", "xray"], 
                                   check=True, 
                                   capture_output=True, 
                                   text=True)
            
            if result.returncode == 0:
                logger.info("Xray успешно перезапущен")
                return True
            else:
                logger.error(f"Ошибка при перезапуске Xray: {result.stderr}")
                return False
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка при перезапуске Xray: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при перезапуске Xray: {str(e)}")
            return False
    
    async def create_user(self, email=None, days=30, traffic_limit_gb=100):
        """Создание нового пользователя VPN"""
        try:
            # Генерируем имя пользователя, если не указано
            if not email:
                email = f"tg_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Добавляем пользователя в конфигурацию
            user_data = self.xray_config.add_user(email, days, traffic_limit_gb)
            
            if user_data:
                # Перезапускаем Xray для применения изменений
                if await self.restart_xray():
                    return user_data
                else:
                    # Если перезапуск не удался, удаляем пользователя
                    self.xray_config.remove_user(user_data["uuid"])
                    return None
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя VPN: {str(e)}")
            return None
    
    async def delete_user(self, user_uuid):
        """Удаление пользователя VPN"""
        try:
            # Удаляем пользователя из конфигурации
            if self.xray_config.remove_user(user_uuid):
                # Перезапускаем Xray для применения изменений
                if await self.restart_xray():
                    return True
                else:
                    logger.error("Пользователь удален из конфигурации, но Xray не удалось перезапустить")
                    return False
            else:
                return False
        
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя VPN: {str(e)}")
            return False
    
    async def get_users(self):
        """Получение списка всех пользователей"""
        try:
            return self.xray_config.get_users()
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
            return []
    
    async def setup_reality(self, dest="dl.google.com:443", server_names=None):
        """Настройка Reality для Xray"""
        try:
            result = self.xray_config.setup_reality(dest, server_names)
            
            if result:
                # Перезапускаем Xray для применения изменений
                if await self.restart_xray():
                    return result
                else:
                    logger.error("Reality настроен, но Xray не удалось перезапустить")
                    return None
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при настройке Reality: {str(e)}")
            return None
    
    async def get_xray_status(self):
        """Получение статуса сервиса Xray"""
        try:
            # Используем systemctl для проверки статуса сервиса
            result = subprocess.run(["systemctl", "is-active", "xray"], 
                                   capture_output=True, 
                                   text=True)
            
            status = result.stdout.strip()
            
            if status == "active":
                return {"status": "active", "message": "Xray работает"}
            else:
                # Получаем дополнительную информацию о статусе
                status_result = subprocess.run(["systemctl", "status", "xray"], 
                                             capture_output=True, 
                                             text=True)
                
                return {
                    "status": status,
                    "message": "Xray не работает",
                    "details": status_result.stdout
                }
        
        except Exception as e:
            logger.error(f"Ошибка при получении статуса Xray: {str(e)}")
            return {"status": "unknown", "message": f"Ошибка: {str(e)}"}
    
    async def get_traffic_stats(self):
        """Получение статистики трафика (заглушка)"""
        # В реальном коде здесь должен быть запрос к API Xray для получения статистики
        # Для примера возвращаем заглушку
        return {
            "total_upload": 0,
            "total_download": 0,
            "users": {}
        }