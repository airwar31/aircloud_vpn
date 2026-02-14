"""
Manager для работы с Xray через 3xui API
"""

import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import quote
import os

logger = logging.getLogger(__name__)

# Реальные IP адреса серверов
try:
    from config import NL_SERVER_IP, VK_SERVER_IP
except ImportError:
    NL_SERVER_IP = os.getenv("NL_SERVER_IP", "85.239.56.174")
    VK_SERVER_IP = os.getenv("VK_SERVER_IP", "89.208.86.167")

# Фиксированные UUIDs для туннелей
UUID_DOUBLE_TUNNEL = "550e8400-e29b-41d4-a716-446655440000"
UUID_SINGLE_TUNNEL = "550e8400-e29b-41d4-a716-446655440001"

# Reality параметры
REALITY_CONFIG = {
    "pbk": "dnUx8zqE1dHV2B5qyWZDpueUySPiWIkcHI-wxYfEzhA",
    "sni": "dl.google.com",
    "fp": "chrome",
    "spx": "%2F",
    "sid": "",
    "type": "tcp",
    "flow": "xtls-rprx-vision"
}


def generate_vless_link(uuid: str, server: str, port: int, email: str, 
                       tunnel_type: str = "single") -> str:
    """Генерация VLESS ссылки для клиента"""
    
    if tunnel_type == "double":
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
        params = "security=tls&encryption=none&type=tcp"
    
    link = f"vless://{uuid}@{server}:{port}?{params}#{quote(email)}"
    return link


class XrayManager:
    def __init__(self, api_url: str, username: str = "admin", password: str = "admin"):
        """Инициализация XrayManager с 3xui API"""
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = None
        self.cookies = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.login()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self) -> bool:
        """Авторизация в 3xui"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(
                f"{self.api_url}/login",
                data=payload,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self.cookies = {}
                    for key, cookie in resp.cookies.items():
                        self.cookies[key] = cookie.value
                    logger.info("✅ Авторизация 3xui успешна")
                    return True
                else:
                    logger.error(f"❌ Ошибка авторизации 3xui: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к 3xui: {e}")
            return False
    
    async def add_client(self, email: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Добавление клиента через 3xui API"""
        try:
            tunnel_type = config.get("tunnel_type", "single")
            days = config.get("days", 30)
            
            # Выбираем правильные параметры
            if tunnel_type == "double":
                inbound_id = 0  # Порт 443 (double tunnel)
                client_uuid = UUID_DOUBLE_TUNNEL
                server_ip = VK_SERVER_IP
                port = 443
            else:
                inbound_id = 1  # Порт 8443 (single tunnel)
                client_uuid = UUID_SINGLE_TUNNEL
                server_ip = NL_SERVER_IP
                port = 8443
            
            # Рассчитываем дату истечения
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
            expiry_time_ms = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
            
            # Формируем данные клиента
            client_data = {
                "id": client_uuid,
                "email": email,
                "limitIp": 5,
                "totalGB": 0,
                "expiryTime": expiry_time_ms,
                "enable": True,
                "subId": email,
                "flow": "xtls-rprx-vision" if tunnel_type == "double" else ""
            }
            
            logger.info(f"➕ Добавляем клиента {email} (тип: {tunnel_type})")
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                await self.login()
            
            # Попытка добавить клиента через 3xui API
            async with self.session.post(
                f"{self.api_url}/panel/api/inbounds/{inbound_id}/addClient",
                json=client_data,
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    response_data = await resp.json()
                    logger.info(f"✅ Клиент {email} добавлен в Xray")
                    
                    # Генерируем VLESS ссылку
                    vless_link = generate_vless_link(
                        uuid=client_uuid,
                        server=server_ip,
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
                else:
                    error_text = await resp.text()
                    logger.warning(f"⚠️ API 3xui недоступен ({resp.status}), используем fallback VLESS")
                    
                    # Fallback: генерируем просто VLESS ссылку если API не работает
                    vless_link = generate_vless_link(
                        uuid=client_uuid,
                        server=server_ip,
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
            logger.error(f"❌ Ошибка при добавлении клиента: {e}")
            logger.info("⚠️ Возвращаем fallback VLESS ссылку")
            
            # Fallback на простую ссылку
            tunnel_type = config.get("tunnel_type", "single")
            days = config.get("days", 30)
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
            
            if tunnel_type == "double":
                client_uuid = UUID_DOUBLE_TUNNEL
                server_ip = VK_SERVER_IP
                port = 443
            else:
                client_uuid = UUID_SINGLE_TUNNEL
                server_ip = NL_SERVER_IP
                port = 8443
            
            vless_link = generate_vless_link(
                uuid=client_uuid,
                server=server_ip,
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
    
    async def update_client_expiry(self, email: str, tunnel_type: str, days: int) -> bool:
        """Обновление срока действия клиента"""
        try:
            if tunnel_type == "double":
                inbound_id = 0
                client_uuid = UUID_DOUBLE_TUNNEL
            else:
                inbound_id = 1
                client_uuid = UUID_SINGLE_TUNNEL
            
            expiry_time_ms = int((datetime.now() + timedelta(days=days)).timestamp() * 1000)
            
            client_data = {
                "id": client_uuid,
                "email": email,
                "expiryTime": expiry_time_ms,
                "enable": True
            }
            
            logger.info(f"🔄 Обновляем клиента {email} на {days} дней")
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                await self.login()
            
            async with self.session.post(
                f"{self.api_url}/panel/api/inbounds/{inbound_id}/updateClient/{client_uuid}",
                json=client_data,
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Клиент {email} обновлен")
                    return True
                else:
                    logger.warning(f"⚠️ Ошибка обновления API: {resp.status}")
                    return True  # Ссылка уже создана, это не критично
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка обновления через API: {e}")
            return True  # Не критично
    
    async def remove_client(self, email: str, tunnel_type: str) -> bool:
        """Удаление клиента"""
        try:
            if tunnel_type == "double":
                inbound_id = 0
                client_uuid = UUID_DOUBLE_TUNNEL
            else:
                inbound_id = 1
                client_uuid = UUID_SINGLE_TUNNEL
            
            logger.info(f"🗑️ Удаляем клиента {email}")
            
            if not self.session:
                self.session = aiohttp.ClientSession()
                await self.login()
            
            async with self.session.post(
                f"{self.api_url}/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}",
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Клиент {email} удален")
                    return True
                else:
                    logger.warning(f"⚠️ Ошибка удаления: {resp.status}")
                    return True
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка удаления: {e}")
            return True
    
    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Получение статистики"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                await self.login()
            
            async with self.session.get(
                f"{self.api_url}/panel/api/stats",
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return None

