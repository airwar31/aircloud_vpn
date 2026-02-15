"""
Configuration for AirCloud VPN Bot
Load environment variables and define constants
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# ==================== BOT CONFIGURATION ====================

class BotConfig:
    """Telegram Bot Configuration"""
    
    # Bot token from Telegram Bot Father
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    
    # Admin IDs (comma-separated)
    ADMIN_IDS: list = list(map(int, filter(None, os.getenv("ADMIN_IDS", "").split(","))))
    
    # Bot settings
    POLLING_TIMEOUT: int = 30  # seconds
    REQUEST_TIMEOUT: int = 30  # seconds
    CONNECTION_POOL_SIZE: int = 100

# ==================== SERVER CONFIGURATION ====================

class ServerConfig:
    """VPN Server Configuration"""
    
    # NL Server (Main exit node)
    NL_SERVER: Dict[str, Any] = {
        "ip": os.getenv("NL_SERVER_IP", "85.239.56.174"),
        "country": "Netherlands",
        "flag": "🇳🇱",
        "inbounds": {
            "single": {
                "port": 8443,
                "protocol": "vless",
                "security": "tls",
                "description": "Single Tunnel (Direct TLS)"
            },
            "double": {
                "port": 443,
                "protocol": "vless",
                "security": "tls",
                "description": "Double Tunnel (TLS from VK)"
            }
        }
    }
    
    # VK Server (Client entry with Reality obfuscation)
    VK_SERVER: Dict[str, Any] = {
        "ip": os.getenv("VK_SERVER_IP", "89.208.86.167"),
        "country": "Russia",
        "flag": "🇷🇺",
        "inbounds": {
            "reality": {
                "port": 443,
                "protocol": "vless",
                "security": "reality",
                "description": "Reality Obfuscation Entry"
            }
        }
    }

# ==================== TUNNEL CONFIGURATION ====================

class TunnelConfig:
    """VPN Tunnel Types Configuration"""
    
    # Single Tunnel - Direct connection to NL
    SINGLE_TUNNEL: Dict[str, Any] = {
        "type": "single",
        "name": "Базовый туннель",
        "emoji": "🔐",
        "description": "Прямое подключение к NL серверу",
        "server": "NL",
        "protocol": "VLESS + TLS",
        "port": 8443,
        "pricing": {
            "1_month": 150,
            "3_months": 400,
            "12_months": 1200,
        },
        "features": [
            "✅ Быстрое и стабильное соединение",
            "✅ Стандартное TLS шифрование",
            "✅ Хорошо для повседневного использования",
        ],
        "recommended_for": "Обычные пользователи VPN"
    }
    
    # Double Tunnel - Client → VK (Reality) → NL (TLS) → Internet
    DOUBLE_TUNNEL: Dict[str, Any] = {
        "type": "double",
        "name": "Двойной туннель (Белые листы)",
        "emoji": "🔐🔐",
        "description": "Скрытый туннель через VK и NL с обфускацией Reality",
        "protocol": "VLESS + Reality + VLESS + TLS",
        "servers": ["VK", "NL"],
        "ports": {
            "vk": 443,
            "nl": 443
        },
        "pricing": {
            "1_month": 250,
            "3_months": 650,
            "12_months": 2200,
        },
        "features": [
            "✅ Reality обфускация (выглядит как обычный HTTPS)",
            "✅ Двойной слой шифрования",
            "✅ Обход белых листов ISP",
            "✅ Максимальная приватность",
        ],
        "recommended_for": "Максимальная защита, обход блокировок"
    }
    
    TUNNEL_TYPES = {
        "single": SINGLE_TUNNEL,
        "double": DOUBLE_TUNNEL,
    }
    
    @staticmethod
    def get_tunnel(tunnel_type: str) -> Dict[str, Any]:
        """Get tunnel configuration by type"""
        return TunnelConfig.TUNNEL_TYPES.get(tunnel_type)
    
    @staticmethod
    def get_price(tunnel_type: str, duration: str) -> float:
        """Get price for tunnel type and duration"""
        tunnel = TunnelConfig.get_tunnel(tunnel_type)
        if tunnel:
            return tunnel["pricing"].get(duration, 0.0)
        return 0.0

# ==================== 3XUI PANEL CONFIGURATION ====================

class XrayConfig:
    """Xray/3xui Panel Configuration"""
    
    # NL Panel
    NL_PANEL: Dict[str, Any] = {
        "host": os.getenv("XRAY_HOST", "xray-panel"),
        "port": int(os.getenv("XRAY_PORT", "54321")),
        "username": os.getenv("XRAY_USERNAME", "admin"),
        "password": os.getenv("XRAY_PASSWORD", "admin"),
        "scheme": "http",  # Change to https in production
        "timeout": 30,
        "retries": 3,
    }
    
    # VK Panel
    VK_PANEL: Dict[str, Any] = {
        "host": os.getenv("VK_XRAY_HOST", "89.208.86.167"),
        "port": int(os.getenv("VK_XRAY_PORT", "54321")),
        "username": os.getenv("VK_XRAY_USERNAME", "admin"),
        "password": os.getenv("VK_XRAY_PASSWORD", "admin"),
        "scheme": "http",
        "timeout": 30,
        "retries": 3,
    }
    
    # Inbound IDs
    INBOUND_IDS = {
        "nl": {
            "single": 0,      # NL Single Tunnel (Port 8443)
            "double": 1,      # NL Double Tunnel (Port 443)
        },
        "vk": {
            "reality": 0,     # VK Reality Obfuscation (Port 443)
        }
    }
    
    # Reality Protocol Parameters
    REALITY_PARAMS: Dict[str, str] = {
        "public_key": os.getenv("REALITY_PUBLIC_KEY", ""),  # Generated at setup
        "short_id": os.getenv("REALITY_SHORT_ID", ""),
        "fingerprint": "chrome",  # Chrome TLS fingerprint for obfuscation
        "spx": "%2F",  # URL path
        "sni": "dl.google.com",  # SNI for Reality handshake
        "flow": "xtls-rprx-vision",  # Flow control
    }

# ==================== DATABASE CONFIGURATION ====================

class DatabaseConfig:
    """Database Configuration"""
    
    # SQLite Database Path
    DB_PATH: str = os.getenv("DB_PATH", "./data/users.db")
    
    # Enable debug logging
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Cleanup settings
    CLEANUP_EXPIRED_INTERVAL: int = 3600  # 1 hour
    CLEANUP_EXPIRED_AFTER_DAYS: int = 7   # Keep expired keys for 7 days

# ==================== PAYMENT CONFIGURATION ====================

class PaymentConfig:
    """Конфигурация платежей для РФ рынка"""
    
    # YooKassa (Юкасса) - основной платежный провайдер
    # https://yookassa.ru/developers/api
    YOOKASSA_ENABLED: bool = os.getenv("YOOKASSA_ENABLED", "True").lower() == "true"
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    YOOKASSA_API_TIMEOUT: int = int(os.getenv("YOOKASSA_API_TIMEOUT", "30"))
    YOOKASSA_RETRIES: int = int(os.getenv("YOOKASSA_RETRIES", "3"))
    
    # Telegram Stars (звезды) - встроенная платежная система Telegram
    TELEGRAM_STARS_ENABLED: bool = os.getenv("TELEGRAM_STARS_ENABLED", "True").lower() == "true"
    # Курс: 1 звезда ≈ 1-2 рубля (устанавливается Telegram)
    # Преобразование цен в звезды происходит автоматически
    STARS_CONVERSION_RATE: float = 0.8  # Коэффициент: рубли в звезды
    
    # Криптовалюта (USDT, USDC, TON и т.д.)
    CRYPTO_ENABLED: bool = os.getenv("CRYPTO_ENABLED", "True").lower() == "true"
    CRYPTO_WALLET_ADDRESS: str = os.getenv("CRYPTO_WALLET_ADDRESS", "")  # Ethereum, TON, BSC адрес
    CRYPTO_NETWORKS: list = os.getenv("CRYPTO_NETWORKS", "ETH,TON,BSC").split(",")  # Поддерживаемые сети
    CRYPTO_MIN_AMOUNT: float = 50.0  # Минимальная сумма в рублях
    
    # Валюта - только рубли
    DEFAULT_CURRENCY: str = "RUB"
    SUPPORTED_CURRENCIES: list = ["RUB"]
    
    # Комиссии платежных систем (в процентах)
    YOOKASSA_COMMISSION: float = 2.5  # YooKassa комиссия
    STARS_COMMISSION: float = 0.0  # Telegram Stars (нет комиссии)
    CRYPTO_COMMISSION: float = 1.0  # Крипто комиссия

# ==================== LOGGING CONFIGURATION ====================

class LoggingConfig:
    """Logging Configuration"""
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    LOG_FORMAT: str = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/bot.log")
    
    # Create logs directory
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

# ==================== MESSAGING TEMPLATES ====================

class Messages:
    """Message templates for bot responses"""
    
    WELCOME = """
🌐 **AirCloud VPN** - Your Privacy Guardian 👋

Welcome, {user_name}!

Choose your VPN plan:
🔐 **Single Tunnel** - Direct, fast, reliable
🔐🔐 **Double Tunnel** - Ultra-private, maximum stealth

Both plans use military-grade encryption (VLESS + TLS/Reality)
"""
    
    TUNNEL_SINGLE = """
🔐 **Базовый туннель**

**Сервер:** NL (Нидерланды) 🇳🇱
**Протокол:** VLESS + TLS
**Порт:** 8443
**Особенности:**
✅ Быстрое соединение
✅ Стандартное шифрование
✅ Идеально для повседневного использования
✅ Работает на всех устройствах

**Цены:**
💰 150₽/месяц
💰 400₽/3 месяца (-11% скидка)
💰 1200₽/год (-33% скидка)
"""
    
    TUNNEL_DOUBLE = """
🔐🔐 **Двойной туннель (Белые листы)**

**Маршрут:** Клиент → VK (Reality) → NL (TLS) → Интернет
**Серверы:** Россия 🇷🇺 + Нидерланды 🇳🇱
**Протокол:** VLESS + Reality + VLESS + TLS
**Особенности:**
✅ Выглядит как обычный HTTPS трафик
✅ Обходит белые листы ISP
✅ Двойной слой шифрования
✅ Максимальная анонимность
✅ Лучшая защита приватности

**Цены:**
💰 250₽/месяц
💰 650₽/3 месяца (-13% скидка)
💰 2200₽/год (-27% скидка)
"""
    
    PAYMENT_PENDING = """
⏳ **Подтверждение заказа**

Ваш заказ готов к оплате!

**Сумма:** {amount}₽
**План:** {plan}
**Срок:** {duration}

**Доступные способы оплаты:**

💳 **Яндекс.Касса (YooKassa)**
- Карты Visa, Mastercard
- Яндекс.Кошелек
- Онлайн-банкинг
- Мобильные операторы

⭐ **Telegram Stars (звезды)**
- Встроенная система Telegram
- Безопасно и быстро
- Без комиссии

🪙 **Криптовалюта**
- USDT (Ethereum, BSC, TON)
- USDC
- Другие стейблкоины

Выберите удобный способ оплаты или свяжитесь с @support для других вариантов.
\"\"\""
    
    SUBSCRIPTION_ACTIVATED = """
✅ **VPN Activated!**

Your {tunnel_type} Tunnel subscription is active!

📧 **Email:** {email}
⏰ **Expires:** {expiry_date}
📱 **Days Remaining:** {days_left}

**Your VLESS Config:**
```
{vless_link}
```

Choose your VPN client and paste the config.

Recommended clients:
- Nekobox (Android)
- Clashfor Windows (Windows)
- NekoX (iOS)
- V2rayN (PC)
"""
    
    GIFT_CREATED = """
🎁 **Gift Created Successfully!**

{tunnel_type} Tunnel - {days} days

**Gift Code:** `{gift_code}`
**Expires:** {expires_date}

**Share Link:**
```
{share_link}
```

Your friend will activate this VPN when using the link! 🎉
"""
    
    ERROR_PAYMENT = "❌ Ошибка платежа. Пожалуйста, попробуйте еще раз или свяжитесь с поддержкой."
    ERROR_INVALID_CONFIG = "❌ Неверная конфигурация. Свяжитесь с @support"
    ERROR_PERMISSION_DENIED = "❌ У вас нет доступа к этому действию."
    ERROR_ALREADY_EXPIRED = "❌ Эта подписка уже истекла."

# ==================== VALIDATION ====================

def validate_config() -> bool:
    """Validate critical configuration"""
    
    errors = []
    
    # Check BOT_TOKEN
    if not BotConfig.BOT_TOKEN or BotConfig.BOT_TOKEN == "YOUR_BOT_TOKEN":
        errors.append("BOT_TOKEN is not set")
    
    # Check admin IDs
    if not BotConfig.ADMIN_IDS:
        errors.append("ADMIN_IDS is empty")
    
    # Check server IPs
    if not ServerConfig.NL_SERVER["ip"] or ServerConfig.NL_SERVER["ip"] == "CHANGE_ME":
        errors.append("NL_SERVER_IP is not set")
    
    if not ServerConfig.VK_SERVER["ip"] or ServerConfig.VK_SERVER["ip"] == "CHANGE_ME":
        errors.append("VK_SERVER_IP is not set")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration Error: {error}")
        return False
    
    return True

# ==================== EXPORT CONFIGURATION ====================

def get_config() -> Dict[str, Any]:
    """Get complete configuration dictionary"""
    return {
        "bot": BotConfig.__dict__,
        "servers": {
            "nl": ServerConfig.NL_SERVER,
            "vk": ServerConfig.VK_SERVER,
        },
        "tunnels": TunnelConfig.TUNNEL_TYPES,
        "xray": {
            "nl": XrayConfig.NL_PANEL,
            "vk": XrayConfig.VK_PANEL,
            "inbound_ids": XrayConfig.INBOUND_IDS,
            "reality": XrayConfig.REALITY_PARAMS,
        },
        "database": {
            "path": DatabaseConfig.DB_PATH,
            "debug": DatabaseConfig.DEBUG,
        },
        "payment": PaymentConfig.__dict__,
    }

# Validate configuration on import
if not validate_config():
    logger.warning("Configuration validation failed - some features may not work")
