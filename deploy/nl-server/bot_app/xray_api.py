"""
Полная интеграция с 3xui API для управления клиентами Xray
"""

import aiohttp
import json
import logging
import uuid as uuid_lib
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
            host: IP/доменное имя сервера (например 'xray-panel' или '198.51.100.1')
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
        self.last_error = ""

    def _set_error(self, message: str):
        self.last_error = str(message)

    @staticmethod
    def _parse_json_field(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}
        
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
                    data = await resp.json(content_type=None)
                    if isinstance(data, dict) and not data.get("success", True):
                        msg = data.get("msg") or "login rejected"
                        self._set_error(f"3x-ui login rejected: {msg}")
                        logger.error(f"❌ Ошибка авторизации в 3xui: {msg}")
                        return False
                    # Сохраняем cookies для последующих запросов
                    self.cookies = {}
                    for key, cookie in resp.cookies.items():
                        self.cookies[key] = cookie.value
                    self.last_error = ""
                    logger.info(f"✅ Авторизация в 3xui ({self.host}) успешна")
                    return True
                else:
                    self._set_error(f"3x-ui login HTTP {resp.status}")
                    logger.error(f"❌ Ошибка авторизации в 3xui: {resp.status}")
                    return False
        except Exception as e:
            self._set_error(f"3x-ui login exception: {e}")
            logger.error(f"❌ Ошибка подключения к 3xui: {e}")
            return False
    
    async def get_inbounds(self) -> Optional[list]:
        """Получить список всех inbounds"""
        try:
            async with self.session.get(
                f"{self.base_url}/panel/api/inbounds/list",
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if not data.get("success", True):
                        msg = data.get("msg") or "get inbounds failed"
                        self._set_error(msg)
                        logger.error(f"❌ Ошибка получения inbounds: {msg}")
                        return None
                    self.last_error = ""
                    return data.get("obj", [])
                else:
                    self._set_error(f"get inbounds HTTP {resp.status}")
                    logger.error(f"❌ Ошибка получения inbounds: {resp.status}")
                    return None
        except Exception as e:
            self._set_error(f"get inbounds exception: {e}")
            logger.error(f"❌ Ошибка при получении inbounds: {e}")
            return None

    async def find_inbound_id(
        self,
        prefer_security: str = "",
        prefer_port: int = 0,
        prefer_protocol: str = "vless",
    ) -> Optional[int]:
        """
        Find best matching inbound id by protocol/security/port.
        Useful when configured inbound IDs changed after panel recreation.
        """
        inbounds = await self.get_inbounds()
        if not inbounds:
            if not self.last_error:
                self._set_error("no inbounds returned by panel")
            return None

        best_score = -1
        best_id: Optional[int] = None
        sec_pref = prefer_security.strip().lower()
        proto_pref = prefer_protocol.strip().lower()

        for inbound in inbounds:
            if not isinstance(inbound, dict):
                continue

            try:
                inbound_id = int(inbound.get("id"))
            except Exception:
                continue

            protocol = str(inbound.get("protocol", "")).strip().lower()
            port = int(inbound.get("port", 0) or 0)
            remark = str(inbound.get("remark", "")).strip().lower()

            stream_settings = self._parse_json_field(inbound.get("streamSettings"))
            security = str(stream_settings.get("security", "")).strip().lower()

            if proto_pref and protocol and protocol != proto_pref:
                continue

            score = 0
            if sec_pref and security == sec_pref:
                score += 4
            if prefer_port and port == prefer_port:
                score += 2
            if sec_pref and sec_pref in remark:
                score += 1
            if prefer_port and str(prefer_port) in remark:
                score += 1

            if score > best_score:
                best_score = score
                best_id = inbound_id

        if best_id is not None:
            self.last_error = ""
            return best_id

        self._set_error(
            f"no inbound match for protocol={prefer_protocol or '*'}, "
            f"security={prefer_security or '*'}, port={prefer_port or '*'}"
        )
        return None

    async def add_client(self, inbound_id: int, email: str, expiry_days: int,
                        tunnel_type: str = "single", client_uuid: str = "") -> Optional[Dict[str, Any]]:
        """
        Добавить клиента в inbound (MHSanaei 3x-ui API)

        Args:
            inbound_id: ID inbound в панели (реальный ID из БД панели)
            email: Email клиента (уникальный идентификатор)
            expiry_days: Количество дней до истечения
            tunnel_type: Тип туннеля (single или double)
            client_uuid: UUID клиента (если пусто — генерируется новый)

        Returns:
            Dict с информацией о клиенте или None
        """
        try:
            expiry_ms = int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)
            if not client_uuid:
                client_uuid = str(uuid_lib.uuid4())

            # MHSanaei 3x-ui: settings передаётся как JSON-строка
            client_entry = {
                "id": client_uuid,
                "email": email,
                "enable": True,
                "expiryTime": expiry_ms,
                "limitIp": 0,
                "totalGB": 0,
                "tgId": "",
                "subId": "",
                "comment": "",
                "reset": 0,
            }
            # Reality требует xtls-rprx-vision flow (оба туннеля используют Reality)
            client_entry["flow"] = "xtls-rprx-vision"

            settings = json.dumps({"clients": [client_entry]})

            payload = {
                "id": inbound_id,
                "settings": settings
            }

            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json=payload,
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    resp_data = await resp.json()
                    if resp_data.get("success"):
                        self.last_error = ""
                        logger.info(f"✅ Клиент {email} добавлен в inbound {inbound_id} (тип: {tunnel_type})")
                        return {
                            "status": "success",
                            "uuid": client_uuid,
                            "email": email,
                            "tunnel_type": tunnel_type,
                            "expires_at": datetime.fromtimestamp(expiry_ms / 1000).isoformat()
                        }
                    else:
                        msg = resp_data.get("msg") or "unknown addClient error"
                        self._set_error(f"addClient failed in inbound {inbound_id}: {msg}")
                        logger.error(f"❌ Ошибка добавления клиента: {msg}")
                        return None
                else:
                    error_text = await resp.text()
                    self._set_error(f"addClient HTTP {resp.status}: {error_text}")
                    logger.error(f"❌ Ошибка добавления клиента: {resp.status} - {error_text}")
                    return None

        except Exception as e:
            self._set_error(f"addClient exception for {email}: {e}")
            logger.error(f"❌ Ошибка при добавлении клиента {email}: {e}")
            return None
    
    async def update_client(self, inbound_id: int, email: str, expiry_days: int,
                            client_uuid: str = "") -> bool:
        """Update client expiry in MHSanaei 3x-ui."""
        try:
            expiry_ms = int((datetime.now() + timedelta(days=expiry_days)).timestamp() * 1000)

            resolved_uuid = client_uuid or ""
            if not resolved_uuid:
                existing = await self.get_client_by_email(inbound_id, email)
                if existing:
                    resolved_uuid = existing.get("id", "")

            if not resolved_uuid:
                self._set_error(f"UUID not found for {email} in inbound {inbound_id}")
                logger.error(f"Failed to resolve UUID for {email} in inbound {inbound_id}")
                return False

            settings = json.dumps({
                "clients": [{
                    "id": resolved_uuid,
                    "email": email,
                    "expiryTime": expiry_ms,
                    "enable": True,
                    "limitIp": 0,
                    "totalGB": 0,
                    "tgId": "",
                    "subId": "",
                    "comment": "",
                    "reset": 0
                }]
            })

            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/updateClient/{resolved_uuid}",
                json={"id": inbound_id, "settings": settings},
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if isinstance(data, dict) and not data.get("success", True):
                        msg = data.get("msg") or "updateClient failed"
                        self._set_error(msg)
                        logger.error(f"Failed to update client {email}: {msg}")
                        return False
                    self.last_error = ""
                    logger.info(f"Client {email} updated for {expiry_days} days")
                    return True

                self._set_error(f"updateClient HTTP {resp.status}")
                logger.error(f"Failed to update client {email}: HTTP {resp.status}")
                return False

        except Exception as e:
            self._set_error(f"updateClient exception for {email}: {e}")
            logger.error(f"Error updating client {email}: {e}")
            return False

    async def get_client_by_email(self, inbound_id: int, email: str) -> Optional[Dict[str, Any]]:
        """Find client in inbound settings by email."""
        try:
            inbound = await self.get_inbound(inbound_id)
            if not inbound:
                if not self.last_error:
                    self._set_error(f"inbound {inbound_id} not found")
                return None

            obj = inbound.get("obj", inbound)
            settings_raw = obj.get("settings") if isinstance(obj, dict) else None
            if not settings_raw:
                self._set_error(f"inbound {inbound_id} has empty settings")
                return None

            if isinstance(settings_raw, str):
                settings = json.loads(settings_raw)
            elif isinstance(settings_raw, dict):
                settings = settings_raw
            else:
                self._set_error(f"inbound {inbound_id} settings have unsupported type")
                return None

            clients = settings.get("clients", []) if isinstance(settings, dict) else []
            for client in clients:
                if str(client.get("email", "")).strip().lower() == str(email).strip().lower():
                    self.last_error = ""
                    return client
            self._set_error(f"client {email} not found in inbound {inbound_id}")
            return None
        except Exception as e:
            self._set_error(f"search client exception for {email}: {e}")
            logger.error(f"Error searching client {email} in inbound {inbound_id}: {e}")
            return None

    async def remove_client(self, inbound_id: int, client_uuid: str) -> bool:
        """Удалить клиента из inbound (MHSanaei 3x-ui)"""
        try:
            async with self.session.post(
                f"{self.base_url}/panel/api/inbounds/{inbound_id}/delClient/{client_uuid}",
                cookies=self.cookies,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    if isinstance(data, dict) and not data.get("success", True):
                        msg = data.get("msg") or "delClient failed"
                        self._set_error(msg)
                        logger.error(f"❌ Ошибка удаления клиента: {msg}")
                        return False
                    self.last_error = ""
                    logger.info(f"✅ Клиент {client_uuid} удален из inbound {inbound_id}")
                    return True
                else:
                    self._set_error(f"delClient HTTP {resp.status}")
                    logger.error(f"❌ Ошибка удаления клиента: {resp.status}")
                    return False

        except Exception as e:
            self._set_error(f"delClient exception for {client_uuid}: {e}")
            logger.error(f"❌ Ошибка при удалении клиента {client_uuid}: {e}")
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
                    if not data.get("success", True):
                        msg = data.get("msg") or f"inbound {inbound_id} not available"
                        self._set_error(msg)
                        logger.error(f"❌ Ошибка получения inbound {inbound_id}: {msg}")
                        return None
                    self.last_error = ""
                    logger.info(f"✅ Информация об inbound {inbound_id} получена")
                    return data
                else:
                    self._set_error(f"get inbound HTTP {resp.status}")
                    logger.error(f"❌ Ошибка получения inbound: {resp.status}")
                    return None
                    
        except Exception as e:
            self._set_error(f"get inbound exception {inbound_id}: {e}")
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
                    data = await resp.json()
                    if isinstance(data, dict) and not data.get("success", True):
                        msg = data.get("msg") or "stats failed"
                        self._set_error(msg)
                        return None
                    self.last_error = ""
                    return data
                self._set_error(f"stats HTTP {resp.status}")
                return None
                    
        except Exception as e:
            self._set_error(f"stats exception: {e}")
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return None


def generate_vless_link(
    uuid: str,
    server_ip: str,
    port: int,
    email: str,
    tunnel_type: str = "single",
    reality_public_key: str = "",
    reality_short_id: str = "",
    sni: str = "dl.google.com",
) -> str:
    """
    Генерация VLESS ссылки для клиента

    Args:
        uuid: UUID клиента из Xray
        server_ip: IP адрес сервера
        port: Порт подключения
        email: Email клиента
        tunnel_type: Тип туннеля (single=TLS, double=Reality)
        reality_public_key: Публичный ключ Reality (для double tunnel)
        reality_short_id: Short ID Reality (для double tunnel)
        sni: SNI для TLS/Reality соединения

    Returns:
        VLESS ссылка для подключения
    """
    # Оба туннеля используют Reality (single → NL Reality, double → VK Reality)
    params = (
        f"security=reality&encryption=none"
        f"&pbk={reality_public_key}"
        f"&headerType=none&fp=chrome"
        f"&spx=%2F&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"&sni={sni}&sid={reality_short_id}"
    )

    link = f"vless://{uuid}@{server_ip}:{port}?{params}#{quote(email)}"
    return link
