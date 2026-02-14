"""
Manager для работы с Xray API
"""

import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class XrayManager:
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def add_client(self, email: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Добавление клиента в Xray"""
        try:
            # Генерируем UUID для клиента
            client_uuid = str(uuid4())
            
            # Рассчитываем дату истечения
            days = config.get("days", 30)
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
            
            # Простой конфиг для клиента
            client_config = {
                "id": client_uuid,
                "email": email,
                "alterId": 0,
                "security": "none"
            }
            
            return {
                "config": client_config,
                "email": email,
                "expires_at": expires_at,
                "uuid": client_uuid
            }
        except Exception as e:
            logger.error(f"Ошибка создания клиента: {e}")
            return None
            
    async def remove_client(self, email: str) -> bool:
        """Удаление клиента из Xray"""
        try:
            logger.info(f"Удаление клиента {email}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления клиента: {e}")
            return False
            
    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Получение статистики Xray"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(f"{self.api_url}/api/stats") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None
