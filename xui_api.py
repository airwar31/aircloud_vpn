import json
import logging
import uuid
import aiohttp
from datetime import datetime, timedelta

from config import XUI_API_URL, XUI_API_USERNAME, XUI_API_PASSWORD, VPN_SERVER_ADDRESS, VPN_DEFAULT_PROTOCOL

logger = logging.getLogger(__name__)

class XUIApi:
    """Класс для работы с API X UI"""
    
    def __init__(self):
        self.api_url = XUI_API_URL
        self.username = XUI_API_USERNAME
        self.password = XUI_API_PASSWORD
        self.session = None
        self.cookies = None
        self.server_address = VPN_SERVER_ADDRESS
        self.default_protocol = VPN_DEFAULT_PROTOCOL
    
    async def get_session(self):
        """Получение сессии для запросов"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def login(self):
        """Авторизация в X UI API"""
        try:
            session = await self.get_session()
            login_url = f"{self.api_url}/login"
            data = {
                "username": self.username,
                "password": self.password
            }
            
            async with session.post(login_url, data=data) as response:
                if response.status == 200:
                    # Сохраняем cookie для дальнейших запросов
                    self.cookies = response.cookies
                    logger.info("Успешная авторизация в X UI API")
                    return True
                else:
                    logger.error(f"Ошибка авторизации в X UI API: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Ошибка при авторизации в X UI API: {str(e)}")
            return False
    
    async def create_user(self):
        """Создание нового пользователя VPN"""
        if not self.cookies and not await self.login():
            return None
        
        try:
            session = await self.get_session()
            
            # Генерируем уникальный UUID для пользователя
            user_uuid = str(uuid.uuid4())
            
            # Настройки для нового пользователя
            expiry_time = datetime.now() + timedelta(days=32)  # Немного больше месяца для запаса
            
            # Формируем данные для создания пользователя
            # Структура данных зависит от версии X UI и может отличаться
            user_data = {
                "protocol": self.default_protocol,
                "remark": f"tg_user_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "enable": True,
                "uuid": user_uuid,
                "expiryTime": int(expiry_time.timestamp() * 1000),  # в миллисекундах
                "total": 107374182400,  # 100 GB в байтах
                "limitIp": 0,  # без ограничения IP
                "tgId": "",
                "subId": "",
                "decryption": "none"  # Обязательный параметр для VLESS
            }
            
            # URL для создания пользователя (может отличаться в зависимости от версии X UI)
            create_url = f"{self.api_url}/panel/inbound/add"
            
            async with session.post(create_url, json=user_data, cookies=self.cookies) as response:
                if response.status == 200:
                    # Получаем данные созданного пользователя
                    response_data = await response.json()
                    
                    if response_data.get("success"):
                        # Формируем VPN ключ для пользователя
                        # Формат ключа зависит от протокола (VLESS, VMess, Trojan)
                        if self.default_protocol == "vless":
                            # Формат: vless://uuid@ip:port?type=tcp&security=reality&pbk=publicKey&fp=chrome&sni=domain&sid=shortId&spx=%2F&flow=xtls-rprx-vision#remark
                            vpn_key = f"vless://{user_uuid}@{self.server_address}:443?type=tcp&security=reality&pbk=yT3sWMj27ozWgQ1LlQWT73BhtQWWXPpnytu40cyjLxY&fp=chrome&sni=dl.google.com&sid=aedfdde8563d180a&spx=%2F&flow=xtls-rprx-vision#AirCloud-{user_data['remark']}"
                        elif self.default_protocol == "vmess":
                            vmess_config = {
                                "v": "2",
                                "ps": user_data['remark'],
                                "add": self.server_address,
                                "port": "443",
                                "id": user_uuid,
                                "aid": "0",
                                "net": "ws",
                                "type": "none",
                                "host": "",
                                "path": "/vmess",
                                "tls": "tls"
                            }
                            import base64
                            vpn_key = f"vmess://{base64.b64encode(json.dumps(vmess_config).encode()).decode()}"
                        else:
                            # Для других протоколов
                            vpn_key = f"{self.default_protocol}://{user_uuid}@{self.server_address}:443"
                        
                        logger.info(f"Создан новый пользователь VPN: {user_data['remark']}")
                        return vpn_key
                    else:
                        logger.error(f"Ошибка при создании пользователя VPN: {response_data.get('msg')}")
                        return None
                else:
                    logger.error(f"Ошибка при создании пользователя VPN: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя VPN: {str(e)}")
            return None
    
    async def delete_user(self, user_id):
        """Удаление пользователя VPN"""
        if not self.cookies and not await self.login():
            return False
        
        try:
            session = await self.get_session()
            delete_url = f"{self.api_url}/panel/inbound/del/{user_id}"
            
            async with session.post(delete_url, cookies=self.cookies) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    if response_data.get("success"):
                        logger.info(f"Пользователь VPN удален: {user_id}")
                        return True
                    else:
                        logger.error(f"Ошибка при удалении пользователя VPN: {response_data.get('msg')}")
                        return False
                else:
                    logger.error(f"Ошибка при удалении пользователя VPN: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя VPN: {str(e)}")
            return False
    
    async def get_user_traffic(self, user_id):
        """Получение информации о трафике пользователя"""
        if not self.cookies and not await self.login():
            return None
        
        try:
            session = await self.get_session()
            traffic_url = f"{self.api_url}/panel/inbound/list"
            
            async with session.post(traffic_url, cookies=self.cookies) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    if response_data.get("success"):
                        inbounds = response_data.get("obj", [])
                        
                        for inbound in inbounds:
                            if inbound.get("id") == user_id:
                                up = inbound.get("up", 0)
                                down = inbound.get("down", 0)
                                total = inbound.get("total", 0)
                                
                                # Конвертируем байты в мегабайты
                                up_mb = up / (1024 * 1024)
                                down_mb = down / (1024 * 1024)
                                total_mb = total / (1024 * 1024)
                                
                                return {
                                    "upload": up_mb,
                                    "download": down_mb,
                                    "total": total_mb,
                                    "used_percentage": ((up + down) / total) * 100 if total > 0 else 0
                                }
                        
                        logger.error(f"Пользователь VPN не найден: {user_id}")
                        return None
                    else:
                        logger.error(f"Ошибка при получении трафика пользователя VPN: {response_data.get('msg')}")
                        return None
                else:
                    logger.error(f"Ошибка при получении трафика пользователя VPN: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении трафика пользователя VPN: {str(e)}")
            return None
    
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            self.session = None