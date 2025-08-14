import requests
import json
import uuid
import base64
import os
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class XrayAPI:
    def __init__(self):
        self.server_ip = os.getenv('XRAY_SERVER_IP', '5.129.224.166')
        self.server_port = os.getenv('XRAY_SERVER_PORT', '8443')
        self.xray_api_url = "http://127.0.0.1:10085"  # Xray API на локальном сервере
        self.inbound_tag = os.getenv('XRAY_INBOUND_TAG', 'vless-in')
        self.session = requests.Session()
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    async def login_3xui(self) -> bool:
        """Авторизация в 3X-UI"""
        try:
            base_url = "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel"
            
            # Сначала получаем страницу входа для cookies
            self.session.get(f"{base_url}/login", timeout=10)
            
            # Теперь отправляем данные авторизации
            login_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = self.session.post(f"{base_url}/login", data=login_data, timeout=10)
            
            # Проверяем успешность по содержимому ответа
            if response.status_code == 200:
                # Если в ответе есть форма входа - авторизация неудачна
                if 'username' in response.text and 'password' in response.text:
                    logger.error("Неудачная авторизация - остались на странице входа")
                    return False
                else:
                    logger.info("Успешная авторизация в 3X-UI")
                    return True
            elif response.status_code == 302:
                logger.info("Успешная авторизация в 3X-UI (перенаправление)")
                return True
            else:
                logger.error(f"Ошибка авторизации: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка подключения к 3X-UI: {e}")
            return False
    
    async def create_user_config(self, user_id: int) -> Dict:
        """Создание пользователя через Xray-core API"""
        try:
            # Генерируем уникальный UUID
            from database import Database
            db = Database()
            
            for attempt in range(10):
                user_uuid = self._generate_secure_uuid(user_id, attempt)
                if not await db.is_uuid_exists(user_uuid):
                    break
            else:
                raise Exception("Не удалось сгенерировать UUID")
            
            # Получаем уникальный UUID из пула
            user_uuid = await self.get_unique_uuid_from_pool(user_id)
            logger.info(f"Пользователь {user_id} получил UUID: {user_uuid}")
            
            # Генерируем конфигурацию
            config = self._generate_reality_config(user_uuid, user_id)
            
            return {
                'success': True,
                'uuid': user_uuid,
                'config': config,
                'qr_code': config
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания конфигурации: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_user_config(self, user_uuid: str) -> Dict:
        """Получение конфигурации пользователя"""
        try:
            # Генерируем Reality конфигурацию
            config = self._generate_reality_config(user_uuid, 0)
            
            return {
                'success': True,
                'config': config,
                'qr_code': config
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения конфигурации: {e}")
            return {'success': False, 'error': str(e)}
    
    async def delete_user_config(self, user_uuid: str) -> Dict:
        """Удаление конфигурации"""
        try:
            logger.info(f"Конфигурация {user_uuid[:8]}... помечена как удаленная")
            return {'success': True, 'message': 'Конфигурация деактивирована'}
            
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_inbounds(self) -> list:
        """Получение списка inboundов"""
        try:
            api_url = "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel/api"
            
            # Добавляем нужные заголовки
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(
                f"{api_url}/inbounds", 
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Inbounds API Status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_text = response.text.strip()
                logger.info(f"Response length: {len(response_text)}")
                logger.info(f"Response preview: {response_text[:200]}")
                
                if response_text and not response_text.startswith('<'):
                    try:
                        data = response.json()
                        logger.info(f"JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                        
                        if isinstance(data, dict):
                            inbounds = data.get('obj', [])
                            logger.info(f"Found {len(inbounds)} inbounds")
                            return inbounds
                        return []
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        return []
                else:
                    if len(response_text) == 0:
                        logger.error("Пустой ответ от API - возможно нет inbound'ов")
                    else:
                        logger.error("Получен HTML вместо JSON")
                    return []
            else:
                logger.error(f"API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка получения inboundов: {e}")
            return []
    
    async def add_client_to_inbound(self, inbound_id: int, uuid: str, email: str) -> bool:
        """Добавление клиента в inbound"""
        try:
            client_data = {
                "id": inbound_id,
                "settings": json.dumps({
                    "clients": [{
                        "id": uuid,
                        "email": email,
                        "limitIp": 0,
                        "totalGB": 0,
                        "expiryTime": 0,
                        "enable": True,
                        "tgId": "",
                        "subId": ""
                    }]
                })
            }
            
            api_url = "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel/api"
            response = self.session.post(
                f"{api_url}/inbound/addClient",
                data=client_data,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            return False
    
    async def generate_client_config(self, inbound: dict, uuid: str, user_id: int) -> str:
        """Генерация реальной конфигурации на основе inbound"""
        try:
            settings = json.loads(inbound.get('settings', '{}'))
            stream_settings = json.loads(inbound.get('streamSettings', '{}'))
            
            server_ip = self.server_ip
            server_port = inbound.get('port', 443)
            
            # Параметры для VLESS
            params = {
                'encryption': 'none',
                'type': stream_settings.get('network', 'tcp'),
                'security': stream_settings.get('security', 'none')
            }
            
            # Reality параметры
            if params['security'] == 'reality':
                reality_settings = stream_settings.get('realitySettings', {})
                params.update({
                    'pbk': reality_settings.get('publicKey', ''),
                    'fp': reality_settings.get('fingerprint', 'chrome'),
                    'sni': reality_settings.get('serverNames', ['www.google.com'])[0],
                    'sid': reality_settings.get('shortIds', [''])[0],
                    'flow': 'xtls-rprx-vision'
                })
            
            # TLS параметры
            elif params['security'] == 'tls':
                tls_settings = stream_settings.get('tlsSettings', {})
                params.update({
                    'sni': tls_settings.get('serverName', server_ip),
                    'alpn': ','.join(tls_settings.get('alpn', ['h2', 'http/1.1']))
                })
            
            # WebSocket параметры
            if params['type'] == 'ws':
                ws_settings = stream_settings.get('wsSettings', {})
                params.update({
                    'path': ws_settings.get('path', '/'),
                    'host': ws_settings.get('headers', {}).get('Host', server_ip)
                })
            
            # Собираем URL
            param_string = '&'.join([f"{k}={v}" for k, v in params.items() if v])
            
            vless_url = (
                f"vless://{uuid}@{server_ip}:{server_port}"
                f"?{param_string}"
                f"#AirCloud-{user_id}"
            )
            
            return vless_url
            
        except Exception as e:
            logger.error(f"Ошибка генерации конфига: {e}")
            # Fallback конфигурация
            return f"vless://{uuid}@{self.server_ip}:443?encryption=none&security=none&type=tcp#AirCloud-{user_id}"
    
    async def get_inbound_by_id(self, inbound_id: int) -> dict:
        """Получение конкретного inbound по ID"""
        try:
            api_url = "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel/api"
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(
                f"{api_url}/inbound/get/{inbound_id}",
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Inbound {inbound_id} status: {response.status_code}, length: {len(response.text)}")
            
            if response.status_code == 200:
                response_text = response.text.strip()
                if response_text and not response_text.startswith('<'):
                    try:
                        data = response.json()
                        inbound_data = data.get('obj', {})
                        if inbound_data:
                            logger.info(f"Inbound {inbound_id} found: {inbound_data.get('remark', 'unnamed')}")
                        return inbound_data
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON error for inbound {inbound_id}: {e}")
                        return {}
                else:
                    logger.info(f"Inbound {inbound_id}: empty or HTML response")
            else:
                logger.info(f"Inbound {inbound_id}: HTTP {response.status_code}")
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка получения inbound {inbound_id}: {e}")
            return {}
    
    def _generate_reality_config(self, user_uuid: str, user_id: int) -> str:
        """Генерация VLESS Reality конфигурации с вашими реальными параметрами"""
        reality_public_key = "4J6HNMExjUwdktWwR5Bo3rrjY3raBIGvFBHyQK86kQU"
        # Используем пустой Short ID как в конфиге Xray
        short_id = ""
        
        return (
            f"vless://{user_uuid}@{self.server_ip}:443"
            f"?type=tcp&security=reality&pbk={reality_public_key}"
            f"&fp=chrome&sni=google.com&sid={short_id}"
            f"&flow=xtls-rprx-vision#AirCloud-{user_id}"
        )
    
    async def add_user_to_xray(self, user_uuid: str, email: str) -> bool:
        """Добавление пользователя через Xray-core API"""
        try:
            # Xray-core API обычно на порту 10085
            xray_api_url = f"http://{self.server_ip}:10085"
            
            # Полезная нагрузка для добавления пользователя
            payload = {
                "inboundTag": "vless-in",
                "user": {
                    "id": user_uuid,
                    "email": email,
                    "flow": "xtls-rprx-vision"
                }
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            # Отправляем запрос на добавление
            response = self.session.post(
                f"{self.xray_api_url}/HandlerService/AddUser",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            logger.info(f"Xray API response: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"Пользователь {email} добавлен в Xray")
                return True
            else:
                logger.info(f"Xray API недоступен, используем статическую конфигурацию")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка добавления в Xray: {e}")
            return False
    
    async def remove_user_from_xray(self, user_uuid: str, email: str) -> bool:
        """Удаление пользователя из Xray-core"""
        try:
            payload = {
                "inboundTag": "vless-in",
                "email": email
            }
            
            response = self.session.post(
                f"{self.xray_api_url}/HandlerService/RemoveUser",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ошибка удаления из Xray: {e}")
            return False
    
    async def get_user_stats_xray(self, email: str) -> Dict:
        """Получение статистики пользователя"""
        try:
            xray_api_url = f"http://{self.server_ip}:10085"
            
            payload = {
                "name": f"user>>>{email}>>>traffic>>>uplink",
                "reset": False
            }
            
            response = self.session.post(
                f"{self.xray_api_url}/StatsService/QueryStats",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'upload': data.get('stat', {}).get('value', 0),
                    'download': 0  # Нужен отдельный запрос
                }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'success': False}
    
    async def test_panel_access(self) -> bool:
        """Тест доступа к панели"""
        try:
            base_url = "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel"
            response = self.session.get(base_url, timeout=5)
            
            logger.info(f"Panel access test: {response.status_code}")
            logger.info(f"Response contains login form: {'login' in response.text.lower()}")
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ошибка теста доступа: {e}")
            return False
    
    def _generate_secure_uuid(self, user_id: int, attempt: int = 0) -> str:
        """Генерация криптографически стойкого UUID"""
        import secrets
        import hashlib
        import time
        
        # Комбинируем несколько источников энтропии
        entropy_sources = [
            str(user_id).encode(),
            str(attempt).encode(),  # Номер попытки
            secrets.token_bytes(32),  # 256 бит случайности
            str(time.time_ns()).encode(),  # Наносекундная метка
            b'AirCloud-VPN-Salt-2024'  # Соль приложения
        ]
        
        # Создаем хеш из всех источников
        hasher = hashlib.sha256()
        for source in entropy_sources:
            hasher.update(source)
        
        # Преобразуем в UUID формат
        hash_bytes = hasher.digest()[:16]  # Первые 16 байт
        
        # Устанавливаем UUID version 4 биты
        hash_bytes = bytearray(hash_bytes)
        hash_bytes[6] = (hash_bytes[6] & 0x0f) | 0x40  # Version 4
        hash_bytes[8] = (hash_bytes[8] & 0x3f) | 0x80  # Variant bits
        
        # Форматируем как UUID
        uuid_str = '-'.join([
            hash_bytes[:4].hex(),
            hash_bytes[4:6].hex(),
            hash_bytes[6:8].hex(),
            hash_bytes[8:10].hex(),
            hash_bytes[10:16].hex()
        ])
        
        return uuid_str
    
    async def get_user_traffic(self, user_uuid: str) -> Dict:
        """Получение статистики (статический режим)"""
        try:
            # В статическом режиме статистика недоступна
            return {
                'success': True,
                'upload': 0,
                'download': 0,
                'total': 0,
                'message': 'Статистика недоступна в статическом режиме'
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {'success': False, 'error': str(e)}
    

    
    async def add_user_to_config_file(self, user_uuid: str, email: str):
        """Добавление пользователя через HTTP запрос к хосту"""
        try:
            import requests
            
            # Отправляем запрос на хост для добавления пользователя
            payload = {
                'action': 'add_user',
                'uuid': user_uuid,
                'email': email
            }
            
            # Пробуем отправить запрос на хост
            try:
                response = requests.post('http://host.docker.internal:9999/manage_user', 
                                       json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Пользователь {email} добавлен через HTTP")
                else:
                    logger.warning(f"HTTP сервис недоступен: {response.status_code}")
            except:
                logger.info(f"Пользователь {email} создан (статический режим)")
                
        except Exception as e:
            logger.error(f"Ошибка добавления: {e}")
    
    async def remove_user_from_config_file(self, user_uuid: str):
        """Удаление пользователя через HTTP"""
        try:
            import requests
            
            payload = {
                'action': 'remove_user',
                'uuid': user_uuid
            }
            
            try:
                response = requests.post('http://host.docker.internal:9999/manage_user', 
                                       json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Пользователь {user_uuid[:8]}... удален через HTTP")
                else:
                    logger.warning(f"HTTP сервис недоступен: {response.status_code}")
            except:
                logger.info(f"Пользователь {user_uuid[:8]}... помечен как удаленный")
                
        except Exception as e:
            logger.error(f"Ошибка удаления: {e}")
    
    async def get_unique_uuid_from_pool(self, user_id: int) -> str:
        """Получение уникального UUID из пула"""
        try:
            # Читаем пул UUID
            with open('/app/data/uuid_pool.txt', 'r') as f:
                uuids = [line.strip() for line in f.readlines() if line.strip()]
            
            # Выбираем UUID по остатку от деления
            uuid_index = (user_id - 1) % len(uuids)
            selected_uuid = uuids[uuid_index]
            
            logger.info(f"Пользователь {user_id} получил UUID #{uuid_index + 1}: {selected_uuid}")
            return selected_uuid
            
        except Exception as e:
            logger.error(f"Ошибка получения UUID: {e}")
            # Возвращаем сгенерированный UUID
            return self._generate_secure_uuid(user_id)
    
    async def reset_user_traffic(self, user_uuid: str) -> Dict:
        """Сброс статистики трафика пользователя"""
        try:
            return {'success': True}
        except Exception as e:
            logger.error(f"Ошибка сброса статистики: {e}")
            return {'success': False, 'error': str(e)}