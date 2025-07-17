import json
import os
import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class XrayConfig:
    """Класс для управления конфигурацией Xray"""
    
    def __init__(self, config_path="/etc/xray/config.json", template_path="/etc/xray/config.template.json"):
        self.config_path = config_path
        self.template_path = template_path
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Конфигурация загружена из {self.config_path}")
            elif os.path.exists(self.template_path):
                with open(self.template_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"Конфигурация загружена из шаблона {self.template_path}")
            else:
                # Создаем базовую конфигурацию
                self.config = self.create_default_config()
                logger.info("Создана базовая конфигурация")
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {str(e)}")
            self.config = self.create_default_config()
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Конфигурация сохранена в {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {str(e)}")
            return False
    
    def create_default_config(self):
        """Создание базовой конфигурации Xray"""
        return {
            "log": {
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log",
                "loglevel": "warning"
            },
            "inbounds": [
                {
                    "port": 443,
                    "protocol": "vless",
                    "settings": {
                        "clients": [],
                        "decryption": "none",
                        "fallbacks": []
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "reality",
                        "realitySettings": {
                            "show": False,
                            "dest": "dl.google.com:443",
                            "xver": 0,
                            "serverNames": ["dl.google.com"],
                            "privateKey": "",
                            "shortIds": [""]
                        },
                        "tcpSettings": {
                            "acceptProxyProtocol": False,
                            "header": {
                                "type": "none"
                            }
                        }
                    },
                    "tag": "vless-in",
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls", "quic"]
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "settings": {},
                    "tag": "direct"
                },
                {
                    "protocol": "blackhole",
                    "settings": {},
                    "tag": "blocked"
                }
            ],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:private"],
                        "outboundTag": "blocked"
                    },
                    {
                        "type": "field",
                        "protocol": ["bittorrent"],
                        "outboundTag": "blocked"
                    }
                ]
            }
        }
    
    def add_user(self, email=None, days=30, traffic_limit_gb=100):
        """Добавление нового пользователя в конфигурацию"""
        try:
            if not email:
                email = f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Генерируем UUID для пользователя
            user_uuid = str(uuid.uuid4())
            
            # Находим inbound с протоколом vless
            vless_inbound = None
            for inbound in self.config["inbounds"]:
                if inbound.get("protocol") == "vless":
                    vless_inbound = inbound
                    break
            
            if not vless_inbound:
                logger.error("Не найден inbound с протоколом VLESS")
                return None
            
            # Добавляем пользователя
            if "clients" not in vless_inbound["settings"]:
                vless_inbound["settings"]["clients"] = []
            
            # Получаем приватный ключ и shortId для формирования ссылки
            private_key = vless_inbound["streamSettings"]["realitySettings"].get("privateKey", "")
            short_id = vless_inbound["streamSettings"]["realitySettings"].get("shortIds", [""])[0]
            
            # Вычисляем публичный ключ из приватного (в реальном коде нужно будет реализовать)
            # Здесь используем заглушку
            public_key = "yT3sWMj27ozWgQ1LlQWT73BhtQWWXPpnytu40cyjLxY"
            
            # Создаем нового пользователя
            new_user = {
                "id": user_uuid,
                "email": email,
                "flow": "xtls-rprx-vision",
                "decryption": "none"
            }
            
            vless_inbound["settings"]["clients"].append(new_user)
            
            # Сохраняем конфигурацию
            if self.save_config():
                # Формируем ссылку для подключения
                server_address = os.environ.get("VPN_SERVER_ADDRESS", "127.0.0.1")
                port = vless_inbound.get("port", 443)
                
                vpn_link = f"vless://{user_uuid}@{server_address}:{port}?type=tcp&security=reality&pbk={public_key}&fp=chrome&sni=dl.google.com&sid={short_id}&spx=%2F&flow=xtls-rprx-vision#AirCloud-{email}"
                
                logger.info(f"Добавлен новый пользователь: {email}")
                return {
                    "uuid": user_uuid,
                    "email": email,
                    "link": vpn_link,
                    "expiry_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                }
            else:
                logger.error("Ошибка при сохранении конфигурации")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {str(e)}")
            return None
    
    def remove_user(self, user_uuid):
        """Удаление пользователя из конфигурации"""
        try:
            removed = False
            
            # Находим inbound с протоколом vless
            for inbound in self.config["inbounds"]:
                if inbound.get("protocol") == "vless" and "clients" in inbound["settings"]:
                    # Ищем пользователя по UUID
                    clients = inbound["settings"]["clients"]
                    inbound["settings"]["clients"] = [c for c in clients if c.get("id") != user_uuid]
                    
                    # Проверяем, был ли удален пользователь
                    if len(clients) > len(inbound["settings"]["clients"]):
                        removed = True
            
            # Сохраняем конфигурацию, если были изменения
            if removed and self.save_config():
                logger.info(f"Пользователь удален: {user_uuid}")
                return True
            else:
                logger.error(f"Пользователь не найден: {user_uuid}")
                return False
        
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя: {str(e)}")
            return False
    
    def get_users(self):
        """Получение списка всех пользователей"""
        users = []
        
        try:
            # Находим inbound с протоколом vless
            for inbound in self.config["inbounds"]:
                if inbound.get("protocol") == "vless" and "clients" in inbound["settings"]:
                    for client in inbound["settings"]["clients"]:
                        users.append({
                            "uuid": client.get("id"),
                            "email": client.get("email"),
                            "flow": client.get("flow")
                        })
            
            return users
        
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
            return []
    
    def generate_reality_keys(self):
        """Генерация ключей для Reality"""
        # В реальном коде здесь должна быть генерация ключей
        # Для примера используем заглушки
        return {
            "private_key": "CA_SF7tsukCf5chWODTmfWo5O4D23wPwIx4wFdrqiXE",
            "public_key": "yT3sWMj27ozWgQ1LlQWT73BhtQWWXPpnytu40cyjLxY"
        }
    
    def setup_reality(self, dest="dl.google.com:443", server_names=None):
        """Настройка Reality для Xray"""
        if server_names is None:
            server_names = ["dl.google.com"]
        
        try:
            # Генерируем ключи
            keys = self.generate_reality_keys()
            
            # Генерируем shortId
            short_id = uuid.uuid4().hex[:8]
            
            # Находим inbound с протоколом vless
            for inbound in self.config["inbounds"]:
                if inbound.get("protocol") == "vless":
                    # Настраиваем Reality
                    inbound["streamSettings"]["security"] = "reality"
                    inbound["streamSettings"]["realitySettings"] = {
                        "show": False,
                        "dest": dest,
                        "xver": 0,
                        "serverNames": server_names,
                        "privateKey": keys["private_key"],
                        "shortIds": [short_id]
                    }
            
            # Сохраняем конфигурацию
            if self.save_config():
                logger.info("Reality настроен успешно")
                return {
                    "private_key": keys["private_key"],
                    "public_key": keys["public_key"],
                    "short_id": short_id
                }
            else:
                logger.error("Ошибка при сохранении конфигурации")
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при настройке Reality: {str(e)}")
            return None