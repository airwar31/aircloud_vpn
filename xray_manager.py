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
        self.api_url = api_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def add_client(self, email: str, plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Добавление клиента"""
        try:
            client_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=plan["days"])
            
            client_data = {
                "email": email,
                "id": client_id,
                "traffic_limit": plan["traffic"] * 1024 * 1024 * 1024,  # В байтах
                "expires_at": expires_at.isoformat(),
                "enable": True
            }
            
            async with self.session.post(
                f"{self.api_url}/api/clients",
                json=client_data
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
                    logger.error(f"Ошибка добавления клиента: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            return None
            
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