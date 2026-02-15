"""
Полная интеграция с 3xui API для управления клиентами Xray
"""

import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import quote
import os

logger = logging.getLogger(__name__)


class XrayAPI:
    """Класс для работы с 3xui API"""
    
    def __init__(self, host: str, port: int = 54321, username: str = "admin", password: str = "admin"):
        """
        Инициализация 3xui API клиента
        
        Args:
            host: IP/доменное имя сервера (nl-server или 85.239.56.174)
            port: Порт панели 3xui (по умолчанию 54321)
            username: Логин для входа
            password: Пароль для входа
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.username = username
        self.password = password
        self.session = None
        self.cookies = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        success = await self.login()
        if not success:
            raise Exception("❌ Не удалось авторизоваться в 3xui")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self) -> bool:
        """Авторизация в 3xui панели"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            payload = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(
                f"{self.base_url}/login",
                data=payload,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    # Сохраняем cookies для последующих запросов
                    self.cookies = {}
                    for key, cookie in resp.cookies.items():
                        self.cookies[key] = cookie.value
                    logger.info(f"✅ Авторизация в 3xui ({self.host}) успешна")
                    return True
                else:
                    logger.error(f"❌ Ошибка авторизации в 3xui: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к 3xui: {e}")
            return False
    
    async def add_client(self, inbound_id: int, email: str, expiry_days: int, 
                        tunnel_type: str = "single") -> Optional[Dict[str, Any]]:
        """
        Добавить клиента в inbound
        
        Args:
            inbound_id: ID inbound (0 = первый, 1 = второй, и т.д.)
            email: Email клиента (уникальный идентификатор)
            expiry_days: Количество дней до истечения
            tunnel_type: Тип туннеля (single или double)
            
        Returns:
            Dict с информацией о клиенте или None
        """
        try:
            expiry_ms = int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)
            
            client_data = {
                "id": "",  # Генерируется сервером
                "email": email,
                "enable": True,
                "expiryTime": expiry_ms
            }
            
            # Отправляем запрос на добавление клиента
            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/addClient/{inbound_id}",
                json=client_data,
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Клиент {email} добавлен в inbound {inbound_id} (тип: {tunnel_type})")
                    return {
                        "status": "success",
                        "email": email,
                        "tunnel_type": tunnel_type,
                        "expires_at": datetime.fromtimestamp(expiry_ms / 1000).isoformat()
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"❌ Ошибка добавления клиента: {resp.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении клиента {email}: {e}")
            return None
    
    async def update_client(self, inbound_id: int, email: str, expiry_days: int) -> bool:
        """Обновить срок действия клиента"""
        try:
            expiry_ms = int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)
            
            client_data = {
                "email": email,
                "expiryTime": expiry_ms,
                "enable": True
            }
            
            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/updateClient/{inbound_id}",
                json=client_data,
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Клиент {email} обновлен на {expiry_days} дней")
                    return True
                else:
                    logger.error(f"❌ Ошибка обновления клиента: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении клиента {email}: {e}")
            return False
    
    async def remove_client(self, inbound_id: int, email: str) -> bool:
        """Удалить клиента из inbound"""
        try:
            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/delClient/{inbound_id}",
                json={"email": email},
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Клиент {email} удален")
                    return True
                else:
                    logger.error(f"❌ Ошибка удаления клиента: {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении клиента {email}: {e}")
            return False
    
    async def get_inbound(self, inbound_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию об inbound"""
        try:
            async with self.session.get(
                f"{self.base_url}/panel/api/inbounds/get/{inbound_id}",
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ Информация об inbound {inbound_id} получена")
                    return data
                else:
                    logger.error(f"❌ Ошибка получения inbound: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при получении inbound {inbound_id}: {e}")
            return None
    
    async def get_stats(self) -> Optional[Dict[str, Any]]:
        """Получить статистику сервера"""
        try:
            async with self.session.get(
                f"{self.base_url}/panel/api/server/stats",
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


def generate_vless_link(uuid: str, server_ip: str, port: int, email: str, 
                        tunnel_type: str = "single") -> str:
    """
    Генерация VLESS ссылки для клиента
    
    Args:
        uuid: UUID клиента из Xray
        server_ip: IP адрес сервера
        port: Порт подключения
        email: Email клиента
        tunnel_type: Тип туннеля (single=TLS, double=Reality)
        
    Returns:
        VLESS ссылка для подключения
    """
    if tunnel_type == "double":
        # Double tunnel с Reality обфускацией (через VK)
        params = (
            "security=reality&encryption=none"
            "&pbk=dnUx8zqE1dHV2B5qyWZDpueUySPiWIkcHI-wxYfEzhA"
            "&headerType=none&fp=chrome"
            "&spx=%2F&type=tcp"
            "&flow=xtls-rprx-vision"
            "&sni=dl.google.com&sid="
        )
    else:
        # Single tunnel с TLS (прямо в NL)
        params = "security=tls&encryption=none&type=tcp"
    
    link = f"vless://{uuid}@{server_ip}:{port}?{params}#{quote(email)}"
    return link
