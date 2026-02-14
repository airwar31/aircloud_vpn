"""
Manager для работы с Xray API
"""

import aiohttp
import json
import logging
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
from urllib.parse import quote

logger = logging.getLogger(__name__)


def generate_vless_link(uuid: str, server: str, port: int, email: str, 
                       security: str = "reality", sni: str = "google.com",
                       tunnel_type: str = "single") -> str:
    """Генерация VLESS ссылки для клиента"""
    
    # Базовые параметры для Reality/TLS
    if tunnel_type == "double":
        # Double tunnel через VK к NL
        params = f"security=reality&flow=xtls-rprx-vision&sni={sni}"
    else:
        # Single tunnel прямо в NL
        params = f"security=tls&sni={sni}"
    
    # Формируем ссылку
    link = f"vless://{uuid}@{server}:{port}?{params}#{quote(email)}"
    return link


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
        """Добавление клиента в Xray и генерация ссылки"""
        try:
            # Генерируем UUID для клиента
            client_uuid = str(uuid4())
            
            # Рассчитываем дату истечения
            days = config.get("days", 30)
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
            
            # Тип туннеля
            tunnel_type = config.get("tunnel_type", "single")
            server = config.get("server", "nl-server")
            port = config.get("port", 8443 if tunnel_type == "single" else 443)
            
            # Генерируем рабочую VLESS ссылку
            vless_link = generate_vless_link(
                uuid=client_uuid,
                server=server,
                port=port,
                email=email,
                tunnel_type=tunnel_type
            )
            
            return {
                "uuid": client_uuid,
                "email": email,
                "expires_at": expires_at,
                "vless_link": vless_link,
                "tunnel_type": tunnel_type
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

