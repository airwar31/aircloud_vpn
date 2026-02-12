"""
Менеджер для управления различными типами VPN туннелей
Поддерживает одиночные и двойные туннели через разные серверы
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class TunnelManager:
    """Менеджер для создания и управления VPN туннелями"""
    
    # Конфигурация серверов по регионам
    SERVERS = {
        "vk": {
            "name": "ВК (Россия)",
            "address": "vk.vpn.example.com",
            "port": 443,
            "priority": 1
        },
        "nl": {
            "name": "Нидерланды",
            "address": "nl.vpn.example.com",
            "port": 443,
            "priority": 2
        }
    }
    
    # Маршруты для двойного туннеля
    DOUBLE_TUNNEL_ROUTES = {
        "vk_to_nl": {
            "name": "ВК → Нидерланды (Double VPN)",
            "first_hop": "vk",
            "second_hop": "nl",
            "description": "Двойное туннелирование через ВК затем через Нидерланды"
        }
    }
    
    @staticmethod
    def generate_single_tunnel_config(email: str, client_id: str, expires_at: datetime) -> str:
        """
        Генерирует конфигурацию для одиночного туннеля
        Single подписка идет НАПРЯМУЮ на NL сервер (без промежуточного VK)
        
        Args:
            email: Email пользователя
            client_id: UUID клиента
            expires_at: Дата истечения подписки
            
        Returns:
            Строка конфигурации VPN
        """
        try:
            # Одиночный VPN - НАПРЯМУЮ на NL, без VK промежуточного узла
            config = {
                "type": "single",
                "email": email,
                "client_id": client_id,
                "expires_at": expires_at.isoformat(),
                "servers": [TunnelManager.SERVERS["nl"]],  # ← ПРЯМО НА NL!
                "description": "Одиночный VPN туннель (напрямую на Нидерланды)"
            }
            return json.dumps(config, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка генерации одиночного туннеля: {e}")
            return ""
    
    @staticmethod
    def generate_double_tunnel_config(email: str, client_id: str, expires_at: datetime, 
                                     route: str = "vk_to_nl") -> Dict[str, Any]:
        """
        Генерирует конфигурацию для двойного туннеля
        
        Args:
            email: Email пользователя
            client_id: UUID клиента
            expires_at: Дата истечения подписки
            route: Маршрут туннеля (vk_to_nl, etc)
            
        Returns:
            Словарь с конфигурацией двойного туннеля
        """
        try:
            if route not in TunnelManager.DOUBLE_TUNNEL_ROUTES:
                logger.error(f"Неизвестный маршрут: {route}")
                return {}
            
            route_config = TunnelManager.DOUBLE_TUNNEL_ROUTES[route]
            first_server = TunnelManager.SERVERS[route_config["first_hop"]]
            second_server = TunnelManager.SERVERS[route_config["second_hop"]]
            
            # Конфигурация двойного туннеля
            config = {
                "type": "double",
                "email": email,
                "client_id": client_id,
                "expires_at": expires_at.isoformat(),
                "route": route,
                "route_name": route_config["name"],
                "description": route_config["description"],
                "tunnels": [
                    {
                        "hop": 1,
                        "server_name": first_server["name"],
                        "address": first_server["address"],
                        "port": first_server["port"],
                        "protocol": "vless",
                        "tls": True
                    },
                    {
                        "hop": 2,
                        "server_name": second_server["name"],
                        "address": second_server["address"],
                        "port": second_server["port"],
                        "protocol": "vless",
                        "tls": True
                    }
                ],
                "connection_chain": f"{first_server['name']} → {second_server['name']}",
                "features": {
                    "obfuscation": True,
                    "split_tunneling": False,
                    "kill_switch": True,
                    "leak_protection": True
                }
            }
            return config
        except Exception as e:
            logger.error(f"Ошибка генерации двойного туннеля: {e}")
            return {}
    
    @staticmethod
    def get_config_for_plan(plan_id: str, email: str, client_id: str, 
                           expires_at: datetime) -> Dict[str, Any]:
        """
        Получает конфигурацию в зависимости от плана подписки
        
        Args:
            plan_id: ID плана (например, "1month", "double_tunnel_3months")
            email: Email пользователя
            client_id: UUID клиента
            expires_at: Дата истечения
            
        Returns:
            Словарь с конфигурацией
        """
        try:
            if "double_tunnel" in plan_id:
                # Извлекаем маршрут из плана
                route = "vk_to_nl"  # По умолчанию
                config = TunnelManager.generate_double_tunnel_config(
                    email, client_id, expires_at, route
                )
                return config
            else:
                # Одиночный туннель
                config_str = TunnelManager.generate_single_tunnel_config(
                    email, client_id, expires_at
                )
                return json.loads(config_str) if config_str else {}
        except Exception as e:
            logger.error(f"Ошибка получения конфигурации: {e}")
            return {}
    
    @staticmethod
    def validate_tunnel_type(tunnel_type: str) -> bool:
        """Проверяет валидность типа туннеля"""
        return tunnel_type in ["single", "double"]
    
    @staticmethod
    def get_tunnel_info(tunnel_type: str, route: str = "") -> Dict[str, str]:
        """Получает информацию о туннеле для отображения пользователю"""
        info = {
            "type": tunnel_type,
            "description": ""
        }
        
        if tunnel_type == "single":
            info["description"] = "Одиночный VPN туннель через основной сервер"
            info["servers"] = "1 (основной)"
        elif tunnel_type == "double":
            if route in TunnelManager.DOUBLE_TUNNEL_ROUTES:
                route_info = TunnelManager.DOUBLE_TUNNEL_ROUTES[route]
                info["description"] = route_info["description"]
                info["route"] = route_info["name"]
                info["servers"] = "2 (цепь: ВК → Нидерланды)"
        
        return info
