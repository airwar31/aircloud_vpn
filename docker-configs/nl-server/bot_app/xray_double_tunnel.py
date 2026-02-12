"""
Менеджер для конфигурации Xray с поддержкой двойного туннелирования
Управляет цепочками туннелей (ВК → Нидерланды)
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class XrayDoubleTunnelConfig:
    """Генератор конфигураций Xray для двойного туннелирования"""
    
    @staticmethod
    def get_double_tunnel_vless_config(client_id: str, email: str, 
                                       vk_server: str, nl_server: str,
                                       vk_port: int = 443, nl_port: int = 443) -> str:
        """
        Генерирует VLESS конфигурацию для двойного туннеля (ВК → NL)
        
        Args:
            client_id: UUID клиента
            email: Email клиента
            vk_server: Адрес VK сервера
            nl_server: Адрес NL сервера
            vk_port: Порт VK сервера
            nl_port: Порт NL сервера
            
        Returns:
            Строка конфигурации в формате share link
        """
        try:
            # Создаем цепь туннелей: клиент -> VK -> NL -> выход
            # Первый hop через VK
            vk_link = (f"vless://{client_id}@{vk_server}:{vk_port}?"
                      f"security=reality&encryption=none&headerType=none&"
                      f"fp=chrome&type=tcp&flow=xtls-rprx-vision&"
                      f"sni=dl.google.com#{email}%20(VK)")
            
            # Второй hop через NL
            nl_link = (f"vless://{client_id}@{nl_server}:{nl_port}?"
                      f"security=tls&encryption=none&headerType=none&"
                      f"fp=chrome&type=tcp&sni=nl.cdn.example.com"
                      f"#{email}%20(NL)")
            
            # Комбинированная конфигурация для двойного туннеля
            config = {
                "version": "1",
                "email": email,
                "type": "double_tunnel",
                "route": "vk_to_nl",
                "chains": [
                    {
                        "order": 1,
                        "name": "🇷🇺 ВК (Первый хоп)",
                        "link": vk_link,
                        "server": vk_server,
                        "port": vk_port,
                        "protocol": "vless",
                        "security": "reality"
                    },
                    {
                        "order": 2,
                        "name": "🇳🇱 Нидерланды (Второй хоп)",
                        "link": nl_link,
                        "server": nl_server,
                        "port": nl_port,
                        "protocol": "vless",
                        "security": "tls"
                    }
                ],
                "description": "Двойное туннелирование: ВК → Нидерланды",
                "setup_instructions": [
                    "1. Импортируйте оба звена в клиент (например, V2RayNG, Clash)",
                    "2. Создайте цепь: Первый хоп → Второй хоп",
                    "3. Включите режим цепочки/chain mode",
                    "4. Подключитесь к первому звену (ВК)",
                    "5. Система автоматически маршрутизирует через Нидерланды"
                ]
            }
            
            return json.dumps(config, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка генерации двойного туннеля VLESS: {e}")
            return ""
    
    @staticmethod
    def get_double_tunnel_clash_config(client_id: str, email: str,
                                       vk_server: str, nl_server: str,
                                       vk_port: int = 443, nl_port: int = 443) -> str:
        """
        Генерирует конфигурацию Clash для двойного туннеля
        
        Returns:
            YAML конфигурация Clash
        """
        try:
            config = {
                "port": 7890,
                "socks_port": 7891,
                "redir_port": 7892,
                "mixed_port": 7893,
                "allow_lan": False,
                "mode": "rule",
                "log_level": "info",
                "dns": {
                    "enable": True,
                    "ipv6": False,
                    "nameserver": ["8.8.8.8", "1.1.1.1"],
                    "fallback": ["8.8.4.4", "1.0.0.1"]
                },
                "proxies": [
                    {
                        "name": f"ВК-{email[:8]}",
                        "type": "vless",
                        "server": vk_server,
                        "port": vk_port,
                        "uuid": client_id,
                        "cipher": "auto",
                        "tls": True,
                        "reality": {
                            "enabled": True,
                            "public_key": "dnUx8zqE1dHV2B5qyWZDpueUySPiWIkcHI-wxYfEzhA",
                            "shortid": "0123456789abcdef"
                        }
                    },
                    {
                        "name": f"NL-{email[:8]}",
                        "type": "vless",
                        "server": nl_server,
                        "port": nl_port,
                        "uuid": client_id,
                        "cipher": "auto",
                        "tls": True
                    }
                ],
                "proxy_groups": [
                    {
                        "name": "🌍 Двойной туннель ВК-NL",
                        "type": "relay",
                        "proxies": [f"ВК-{email[:8]}", f"NL-{email[:8]}"],
                        "strategy": "consistent-hashing"
                    },
                    {
                        "name": "🔀 Дефолт",
                        "type": "select",
                        "proxies": [
                            "🌍 Двойной туннель ВК-NL",
                            "DIRECT"
                        ]
                    }
                ],
                "rules": [
                    "DOMAIN-SUFFIX,google.com,🌍 Двойной туннель ВК-NL",
                    "IP-CIDR,8.8.8.8/32,🌍 Двойной туннель ВК-NL",
                    "MATCH,🔀 Дефолт"
                ]
            }
            
            import yaml
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Ошибка генерации Clash конфигурации: {e}")
            return ""
    
    @staticmethod
    def create_xray_outbound_chain(vk_outbound: Dict, nl_outbound: Dict) -> Dict:
        """
        Создает цепь outbound ноды в конфигурации Xray
        
        Args:
            vk_outbound: Конфигурация outbound для VK
            nl_outbound: Конфигурация outbound для NL
            
        Returns:
            Конфигурация цепи
        """
        try:
            chain_config = {
                "tag": "double-tunnel-chain",
                "protocol": "freedom",
                "settings": {
                    "redirect": "127.0.0.1:8888",  # Локальный прокси для цепи
                },
                "streamSettings": {
                    "network": "tcp"
                }
            }
            return chain_config
        except Exception as e:
            logger.error(f"Ошибка создания цепи outbound: {e}")
            return {}
    
    @staticmethod
    def get_single_tunnel_vless_config(client_id: str, email: str, 
                                      nl_server: str, nl_port: int = 443) -> str:
        """
        Генерирует VLESS конфигурацию для одиночного туннеля
        Single подписка - НАПРЯМУЮ на NL сервер (без VK промежуточного узла)
        
        Args:
            client_id: UUID клиента
            email: Email клиента
            nl_server: Адрес NL сервера
            nl_port: Порт NL сервера
            
        Returns:
            Строка конфигурации в формате VLESS link
        """
        try:
            # VLESS ссылка - СРАЗУ на NL без VK
            nl_link = (f"vless://{client_id}@{nl_server}:{nl_port}?"
                      f"security=tls&encryption=none&headerType=none&"
                      f"fp=chrome&type=tcp&sni=nl.vpn.example.com"
                      f"#{email}")
            
            # Конфигурация для одиночного туннеля
            config = {
                "version": "1",
                "email": email,
                "type": "single_tunnel",
                "server": {
                    "name": "🇳🇱 Нидерланды (Single)",
                    "link": nl_link,
                    "server": nl_server,
                    "port": nl_port,
                    "protocol": "vless",
                    "security": "tls",
                    "description": "Прямое подключение на Нидерланды"
                },
                "description": "Одиночный VPN туннель (напрямую на NL)"
            }
            return json.dumps(config, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Ошибка генерации single tunnel: {e}")
            return ""

    @staticmethod
    def get_setup_instructions() -> str:
        """Получает инструкции по настройке двойного туннеля"""
        instructions = """
╔══════════════════════════════════════════════════════════╗
║     Инструкция по подключению двойного туннеля (ВК→NL)   ║
╚══════════════════════════════════════════════════════════╝

📱 ДЛЯ ANDROID (V2RayNG):
────────────────────────
1. Откройте V2RayNG
2. Нажмите '+' и выберите 'Import config from clipboard'
3. Вставьте первый link (ВК)
4. Повторите для второго link (NL)
5. В настройках маршрута включите режим цепи
6. Выберите оба прокси и установите режим "Chain"
7. Подключитесь к первому серверу (ВК)

💻 ДЛЯ ПК (Clash):
─────────────────
1. Скопируйте YAML конфигурацию
2. Откройте Clash (Clash for Windows, ClashX и т.д.)
3. Вставьте конфигурацию в editor
4. Нажмите 'Reload'
5. Выберите профиль '🌍 Двойной туннель ВК-NL'
6. Нажмите 'Connect'

🍎 ДЛЯ iOS (Shadowrocket/Quantumult X):
───────────────────────────────────────
1. Откройте приложение
2. Добавьте узлы через копирование link
3. Включите режим цепи в параметрах
4. Создайте групповую политику для цепи
5. Активируйте подключение

⚠️ ВАЖНО:
─────────
• Убедитесь, что оба звена имеют одинаковый UUID
• Не отключайте VPN при смене звеньев
• Для лучшей скорости - сначала ВК, затем NL
• Если скорость упала - попробуйте отключить и переподключиться

✅ КАК ПРОВЕРИТЬ:
──────────────────
• Вы должны видеть IP Нидерландов (проверьте на ipinfo.io)
• Скорость может быть ниже на 30-50% из-за двойного туннеля
• Все трафик будет зашифрован дважды
        """
        return instructions
