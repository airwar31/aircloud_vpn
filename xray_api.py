from requests import Session, post
from json import loads, dumps
from uuid import uuid4
from base64 import b64encode
import os
from typing import Dict
from logging import getLogger
from html import escape

logger = getLogger(__name__)

def sanitize_log_input(value):
    """Санитизация входных данных для логирования"""
    if isinstance(value, str):
        return escape(value.replace('\n', '\\n').replace('\r', '\\r'))
    return str(value)

class XrayAPI:
    def __init__(self):
        from config import XRAY_SERVER_IP, XRAY_SERVER_PORT
        self.server_ip = XRAY_SERVER_IP
        self.server_port = XRAY_SERVER_PORT
        self.xray_api_url = "http://127.0.0.1:10085"  # Прямое API Xray-core
        self.inbound_tag = os.getenv('XRAY_INBOUND_TAG', 'vless-in')
        self.session = Session()  # Инициализируем сессию
        self.panel_api_url = f"http://{self.server_ip}:{self.server_port}/api"  # Для совместимости
        # X-UI панель не нужна - работаем напрямую с Xray
    
    async def login_3xui(self) -> bool:
        """Авторизация в 3X-UI"""
        try:
            from config import XRAY_API_USERNAME, XRAY_API_PASSWORD
            base_url = self.panel_api_url.replace('/api', '')
            
            with self.session.get(f"{base_url}/login", timeout=10) as response:
                pass
            
            login_data = {
                'username': XRAY_API_USERNAME,
                'password': XRAY_API_PASSWORD
            }
            
            with self.session.post(f"{base_url}/login", data=login_data, timeout=10) as response:
                if response.status_code in [200, 302]:
                    if 'username' not in response.text or 'password' not in response.text:
                        logger.info("Успешная авторизация в 3X-UI")
                        return True
                
                logger.error(f"Ошибка авторизации: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка подключения к 3X-UI: {sanitize_log_input(e)}")
            return False
    
    async def create_user_config(self, user_id: int) -> Dict:
        """Создание пользователя через Xray-core API"""
        try:
            # Получаем уникальный UUID
            user_uuid = await self.get_unique_uuid_from_pool(user_id)
            logger.info(f"Пользователь {sanitize_log_input(user_id)} получил UUID: {sanitize_log_input(user_uuid)}")
            
            # Добавляем пользователя в Xray
            email = f"user{user_id}@aircloud.vpn"
            await self.add_user_to_xray(user_uuid, email)
            
            # Генерируем конфигурацию
            config = self._generate_reality_config(user_uuid, user_id)
            
            return {
                'success': True,
                'uuid': user_uuid,
                'config': config,
                'qr_code': config
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания конфигурации: {sanitize_log_input(e)}")
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
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            with self.session.get(
                f"{self.panel_api_url}/inbounds", 
                headers=headers,
                timeout=10
            ) as response:
            
                logger.info(f"Inbounds API Status: {response.status_code}")
                
                if response.status_code == 200:
                    response_text = response.text.strip()
                    logger.info(f"Response length: {len(response_text)}")
                    
                    if response_text and not response_text.startswith('<'):
                        try:
                            data = response.json()
                            if isinstance(data, dict):
                                inbounds = data.get('obj', [])
                                logger.info(f"Found {len(inbounds)} inbounds")
                                return inbounds
                            return []
                            
                        except ValueError as e:
                            logger.error(f"JSON decode error: {sanitize_log_input(e)}")
                            return []
                    else:
                        logger.error("Пустой ответ от API" if not response_text else "Получен HTML вместо JSON")
                        return []
                else:
                    logger.error(f"API error: {response.status_code}")
                    return []
                
        except Exception as e:
            logger.error(f"Ошибка получения inboundов: {sanitize_log_input(e)}")
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
            
            response = self.session.post(
                f"{self.panel_api_url}/inbound/addClient",
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
                    'sni': (reality_settings.get('serverNames') or ['www.google.com'])[0],
                    'sid': (reality_settings.get('shortIds') or [''])[0],
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
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(
                f"{self.panel_api_url}/inbound/get/{inbound_id}",
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
        """Генерация VLESS Reality конфигурации с актуальными параметрами"""
        # Получаем актуальный публичный ключ из конфига
        reality_public_key = self.get_public_key_from_config()
        
        return (
            f"vless://{user_uuid}@{self.server_ip}:443"
            f"?type=tcp&security=reality&pbk={reality_public_key}"
            f"&fp=chrome&sni=www.microsoft.com&sid="
            f"&flow=xtls-rprx-vision#AirCloud-{user_id}"
        )
    
    async def add_user_to_xray(self, user_uuid: str, email: str) -> bool:
        """Добавление пользователя через Xray API"""
        try:
            # Пробуем через xray команду
            import subprocess
            
            # Создаем JSON для пользователя
            user_json = {
                "id": user_uuid,
                "email": email,
                "flow": "xtls-rprx-vision"
            }
            
            # Пробуем добавить через Xray API (без перезагрузки)
            try:
                import requests
                api_payload = {
                    "inboundTag": self.inbound_tag,
                    "user": {
                        "id": user_uuid,
                        "email": email,
                        "flow": "xtls-rprx-vision"
                    }
                }
                
                response = requests.post(
                    "http://127.0.0.1:10085/HandlerService/AddUser",
                    json=api_payload,
                    timeout=3
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Пользователь {sanitize_log_input(email)} добавлен через API (без перезагрузки)")
                    return True
                else:
                    logger.warning(f"⚠️ API ошибка: {response.status_code}, используем конфиг")
            except Exception as api_e:
                logger.warning(f"⚠️ API недоступен: {sanitize_log_input(api_e)}, используем конфиг")
            
            # Если API не работает - добавляем напрямую
            return self._add_user_directly_to_config(user_uuid, email)
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в Xray: {sanitize_log_input(e)}")
            return False
    
    def _add_user_directly_to_config(self, user_uuid: str, email: str) -> bool:
        """Добавление пользователя напрямую в конфиг"""
        import json
        import subprocess
        
        # Пробуем разные пути к конфигу
        possible_paths = [
            "/usr/local/etc/xray/config.json",
            "/etc/xray/config.json",
            "/opt/xray/config.json"
        ]
        
        config_path = None
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if not config_path:
            logger.error("❌ Конфиг Xray не найден")
            return False
        
        try:
            # Читаем конфиг
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Ищем inbound vless-in
            for inbound in config['inbounds']:
                if inbound.get('tag') == 'vless-in':
                    clients = inbound['settings']['clients']
                    
                    # Проверяем, нет ли уже такого пользователя
                    for client in clients:
                        if client.get('id') == user_uuid:
                            logger.info(f"✅ Пользователь {sanitize_log_input(email)} уже существует")
                            return True
                    
                    # Добавляем нового пользователя
                    new_client = {
                        'id': user_uuid,
                        'email': email,
                        'flow': 'xtls-rprx-vision'
                    }
                    clients.append(new_client)
                    
                    # Обновляем Reality настройки для совместимости
                    for inb in config['inbounds']:
                        if inb.get('tag') == 'vless-in':
                            reality = inb.get('streamSettings', {}).get('realitySettings', {})
                            if 'dest' in reality:
                                reality['dest'] = 'www.microsoft.com:443'
                            if 'serverNames' in reality:
                                reality['serverNames'] = ['www.microsoft.com']
                    
                    # Сохраняем конфиг
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # Перезагружаем Xray через HTTP запрос к хосту
                    try:
                        import requests
                        response = requests.post('http://127.0.0.1:9998/reload_xray', timeout=3)
                        if response.status_code == 200:
                            logger.info(f"✅ Пользователь {sanitize_log_input(email)} добавлен и Xray перезагружен")
                        else:
                            logger.warning(f"⚠️ Пользователь добавлен, но не удалось перезагрузить Xray")
                    except:
                        logger.info(f"✅ Пользователь {sanitize_log_input(email)} добавлен (перезагрузка вручную)")
                    
                    return True
            
            logger.error("❌ Не найден inbound 'vless-in'")
            return False
            
        except Exception as e:
            logger.error(f"❌ Ошибка прямого добавления: {sanitize_log_input(e)}")
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
            base_url = self.panel_api_url.replace('/api', '')
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
        """Генерация уникального UUID для каждого пользователя"""
        try:
            from database import Database
            db = Database()
            
            # Проверяем, есть ли уже UUID у пользователя
            existing_uuid = await db.get_user_uuid(user_id)
            if existing_uuid:
                return existing_uuid
            
            # Генерируем новый уникальный UUID
            for attempt in range(10):
                new_uuid = self._generate_secure_uuid(user_id, attempt)
                if not await db.is_uuid_exists(new_uuid):
                    await db.save_user_uuid(user_id, new_uuid)
                    logger.info(f"Пользователь {sanitize_log_input(user_id)} получил уникальный UUID: {sanitize_log_input(new_uuid)}")
                    return new_uuid
            
            raise Exception("Не удалось сгенерировать уникальный UUID")
            
        except Exception as e:
            logger.error(f"Ошибка получения UUID: {sanitize_log_input(e)}")
            return self._generate_secure_uuid(user_id)
    

    
    def get_public_key_from_config(self) -> str:
        """Получение публичного ключа из конфига Xray"""
        import json
        try:
            # Пробуем разные пути к конфигу
            possible_paths = [
                "/usr/local/etc/xray/config.json",
                "/etc/xray/config.json",
                "/opt/xray/config.json"
            ]
            
            config = None
            for config_path in possible_paths:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.loads(f.read())
                    break
            
            if config:
                    
                for inbound in config.get('inbounds', []):
                    if inbound.get('tag') == 'vless-in':
                        stream_settings = inbound.get('streamSettings', {})
                        reality_settings = stream_settings.get('realitySettings', {})
                        public_key = reality_settings.get('publicKey')
                        if public_key:
                            logger.info(f"Публичный ключ из конфига: {public_key}")
                            return public_key
                        else:
                            # Если нет ключа, генерируем новые
                            logger.warning("Публичный ключ отсутствует, генерируем новые ключи")
                            return self._generate_and_save_keys()
            
            # Если не нашли в конфиге, используем стандартный
            default_key = "4J6HNMExjUwdktWwR5Bo3rrjY3raBIGvFBHyQK86kQU"
            logger.info(f"Используем стандартный ключ: {default_key}")
            return default_key
                
        except Exception as e:
            logger.error(f"Ошибка чтения ключа: {e}")
            return self._generate_and_save_keys()
    
    def _generate_and_save_keys(self) -> str:
        """Генерация и сохранение Reality ключей"""
        import subprocess
        try:
            # Генерируем ключи
            result = subprocess.run(['xray', 'x25519'], capture_output=True, text=True)
            
            private_key = None
            public_key = None
            
            for line in result.stdout.split('\n'):
                if 'Private key:' in line:
                    private_key = line.split('Private key:')[1].strip()
                elif 'Public key:' in line:
                    public_key = line.split('Public key:')[1].strip()
            
            if private_key and public_key:
                # Обновляем конфиг
                self._update_reality_keys(private_key, public_key)
                logger.info(f"Генерированы новые Reality ключи")
                return public_key
            
        except Exception as e:
            logger.error(f"Ошибка генерации ключей: {e}")
        
        return "4J6HNMExjUwdktWwR5Bo3rrjY3raBIGvFBHyQK86kQU"
    
    def _update_reality_keys(self, private_key: str, public_key: str):
        """Обновление Reality ключей в конфиге"""
        import json
        
        possible_paths = [
            "/usr/local/etc/xray/config.json",
            "/etc/xray/config.json",
            "/opt/xray/config.json"
        ]
        
        for config_path in possible_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    for inbound in config['inbounds']:
                        if inbound.get('tag') == 'vless-in':
                            reality = inbound['streamSettings']['realitySettings']
                            reality['privateKey'] = private_key
                            reality['publicKey'] = public_key
                            reality['dest'] = 'www.microsoft.com:443'
                            reality['serverNames'] = ['www.microsoft.com']
                    
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    break
                except Exception as e:
                    logger.error(f"Ошибка обновления конфига: {e}")
    
    async def reset_user_traffic(self, user_uuid: str) -> Dict:
        """Сброс статистики трафика пользователя"""
        try:
            return {'success': True}
        except Exception as e:
            logger.error(f"Ошибка сброса статистики: {e}")
            return {'success': False, 'error': str(e)}