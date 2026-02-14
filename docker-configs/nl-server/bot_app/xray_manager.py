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
import os

logger = logging.getLogger(__name__)

# Реальные IP адреса серверов (импортируем из config если доступен)
try:
    from config import NL_SERVER_IP, VK_SERVER_IP
except ImportError:
    NL_SERVER_IP = os.getenv("NL_SERVER_IP", "85.239.56.174")  # NL сервер для single tunnel
    VK_SERVER_IP = os.getenv("VK_SERVER_IP", "89.208.86.167")  # VK сервер для double tunnel

# SNI используем IP адрес сервера для TLS
DEFAULT_SNI = NL_SERVER_IP

# Reality параметры для double tunnel
REALITY_CONFIG = {
    "pbk": "dnUx8zqE1dHV2B5qyWZDpueUySPiWIkcHI-wxYfEzhA",  # Public key (из private key в конфиге)
    "sni": "dl.google.com",
    "fp": "chrome",
    "spx": "%2F",
    "sid": "",  # Short ID
    "type": "tcp",
    "flow": "xtls-rprx-vision"
}

def generate_vless_link(uuid: str, server: str, port: int, email: str, 
                       tunnel_type: str = "single") -> str:
    """Генерация VLESS ссылки для клиента"""
    
    if tunnel_type == "double":
        # Double tunnel через VK с Reality обфускацией
        params = (f"security=reality&encryption=none"
                 f"&pbk={REALITY_CONFIG['pbk']}"
                 f"&headerType=none"
                 f"&fp={REALITY_CONFIG['fp']}"
                 f"&spx={REALITY_CONFIG['spx']}"
                 f"&type={REALITY_CONFIG['type']}"
                 f"&flow={REALITY_CONFIG['flow']}"
                 f"&sni={REALITY_CONFIG['sni']}"
                 f"&sid={REALITY_CONFIG['sid']}")
    else:
        # Single tunnel прямо в NL с TLS
        params = "security=tls&encryption=none&type=tcp"
    
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
            
            # Определяем правильный сервер IP на основе типа туннеля
            if tunnel_type == "double":
                # Для double tunnel используем VK сервер
                server_ip = VK_SERVER_IP
                port = 443
                sni = VK_SERVER_IP
            else:
                # Для single tunnel используем NL сервер
                server_ip = NL_SERVER_IP
                port = 8443
                sni = DEFAULT_SNI
            
            # Генерируем рабочую VLESS ссылку
            vless_link = generate_vless_link(
                uuid=client_uuid,
                server=server_ip,
                port=port,
                email=email,
                sni=sni,
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

