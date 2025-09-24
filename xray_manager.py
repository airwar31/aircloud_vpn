import json
import uuid
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class XrayManager:
    """Менеджер для управления Xray через API"""
    
    def __init__(self, api_url: str = "http://localhost:8080"):
        # Проверяем и очищаем URL
        if not api_url or not api_url.startswith(('http://', 'https://')):
            raise ValueError("Invalid API URL provided")
        self.api_url = api_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def add_client(self, email: str, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Добавление клиента"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            client_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=plan["days"])
            
            client_data = {
                "email": email,
                "id": client_id,
                "expires_at": expires_at.isoformat(),
                "enable": True
            }
            
            async with self.session.post(
                f"{self.api_url}/api/clients",
                json=client_data,
                headers={'Content-Type': 'application/json'}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {
                        "email": email,
                        "id": client_id,
                        "config": result.get("config"),
                        "expires_at": expires_at
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Ошибка добавления клиента: {resp.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            return None
            
    async def restore_client(self, email: str, config: str, days: int) -> bool:
        """Восстановление существующего клиента"""
        try:
            # Извлекаем UUID из конфигурации
            import re
            uuid_match = re.search(r'vless://([^@]+)@', config)
            if not uuid_match:
                logger.error(f"Не удалось извлечь UUID из конфигурации")
                return False
                
            client_id = uuid_match.group(1)
            expires_at = datetime.now() + timedelta(days=days)
            
            client_data = {
                "email": email,
                "id": client_id,  # Используем существующий UUID
                "expires_at": expires_at.isoformat(),
                "enable": True
            }
            
            async with self.session.post(
                f"{self.api_url}/api/clients",
                json=client_data
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Клиент {email} восстановлен в Xray")
                    return True
                else:
                    logger.error(f"Ошибка восстановления клиента: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка восстановления клиента: {e}")
            return False
            
    async def extend_client(self, email: str, current_expires_at: datetime, days: int) -> bool:
        """Продление срока действия существующего клиента"""
        try:
            # Добавляем дни к существующей дате истечения
            new_expires_at = current_expires_at + timedelta(days=days)
            
            update_data = {
                "expires_at": new_expires_at.isoformat(),
                "enable": True
            }
            
            async with self.session.put(
                f"{self.api_url}/api/clients/{email}",
                json=update_data
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Клиент {email} продлен в Xray до {new_expires_at}")
                    return True
                else:
                    logger.error(f"Ошибка продления клиента: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка продления клиента: {e}")
            return False
            
    async def remove_client(self, email: str) -> bool:
        """Удаление клиента"""
        try:
            async with self.session.delete(f"{self.api_url}/api/clients/{email}") as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Ошибка удаления клиента: {e}")
            return False
            
    async def get_client_stats(self, email: str) -> Optional[Dict[str, Any]]:
        """Получение статистики клиента"""
        try:
            async with self.session.get(f"{self.api_url}/api/clients/{email}/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None