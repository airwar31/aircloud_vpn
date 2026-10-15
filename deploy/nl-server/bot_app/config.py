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


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


def _env_list(name: str) -> list[str]:
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]


APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower()
STRICT_CONFIG = _env_bool("STRICT_CONFIG", False) or APP_ENV in {"prod", "production"}
PLACEHOLDER_VALUES = {"", "CHANGE_ME", "YOUR_BOT_TOKEN", "your_bot_token_here"}
INSECURE_DEFAULT_CREDENTIALS = {"admin", "admin123", "password", "changeme"}
ALLOWED_PROVISIONER_MODES = {"legacy", "hybrid", "remnawave"}
ALLOWED_READ_MODES = {"legacy", "hybrid", "remnawave"}
ALLOWED_REMNAWAVE_AUTH_MODES = {"bearer", "x-api-key"}


# ==================== MIGRATION FEATURE FLAGS ====================

class MigrationConfig:
    """Feature flags for controlled migration to RemnaWave."""

    PROVISIONER_MODE: str = os.getenv("PROVISIONER_MODE", "legacy").strip().lower()
    READ_MODE: str = os.getenv("READ_MODE", "legacy").strip().lower()

    # Use hybrid shadow-write safely without affecting primary activation path.
    SHADOW_WRITE_ENABLED: bool = _env_bool("SHADOW_WRITE_ENABLED", False)

    # Canary percent for user-bucket routing when cutover starts.
    CANARY_PERCENT: int = _env_int("CANARY_PERCENT", 0)

    # RemnaWave API credentials (used by future provisioner adapter).
    REMNAWAVE_API_URL: str = os.getenv("REMNAWAVE_API_URL", "").strip().rstrip("/")
    REMNAWAVE_API_TOKEN: str = os.getenv("REMNAWAVE_API_TOKEN", "").strip()
    REMNAWAVE_TIMEOUT_SECONDS: int = _env_int("REMNAWAVE_TIMEOUT_SECONDS", 20)
    REMNAWAVE_HTTP_RETRIES: int = _env_int("REMNAWAVE_HTTP_RETRIES", 3)
    REMNAWAVE_AUTH_MODE: str = os.getenv("REMNAWAVE_AUTH_MODE", "bearer").strip().lower()
    REMNAWAVE_FALLBACK_TO_LEGACY: bool = _env_bool("REMNAWAVE_FALLBACK_TO_LEGACY", True)

    # Optional internal squad mapping per product tunnel.
    REMNAWAVE_SINGLE_SQUADS: list[str] = _env_list("REMNAWAVE_SINGLE_SQUADS")
    REMNAWAVE_DOUBLE_SQUADS: list[str] = _env_list("REMNAWAVE_DOUBLE_SQUADS")

    @staticmethod
    def use_remnawave_provisioner() -> bool:
        return MigrationConfig.PROVISIONER_MODE in {"hybrid", "remnawave"}

    @staticmethod
    def use_remnawave_reads() -> bool:
        return MigrationConfig.READ_MODE in {"hybrid", "remnawave"}

# ==================== BOT CONFIGURATION ====================

class BotConfig:
    """Telegram Bot Configuration"""
    
    # Bot token from Telegram Bot Father
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
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
        "ip": os.getenv("NL_SERVER_IP", ""),
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
        "ip": os.getenv("VK_SERVER_IP", ""),
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
        "port": int(os.getenv("XRAY_PORT", "2053")),
        "username": os.getenv("XRAY_USERNAME", ""),
        "password": os.getenv("XRAY_PASSWORD", ""),
        "scheme": "http",  # Change to https in production
        "timeout": 30,
        "retries": 3,
    }
    
    # VK Panel
    VK_PANEL: Dict[str, Any] = {
        "host": os.getenv("VK_XRAY_HOST", ""),
        "port": int(os.getenv("VK_XRAY_PORT", "54321")),
        "username": os.getenv("VK_XRAY_USERNAME", ""),
        "password": os.getenv("VK_XRAY_PASSWORD", ""),
        "scheme": "http",
        "timeout": 30,
        "retries": 3,
    }
    
    # Inbound IDs (берутся из env, т.к. 3x-ui назначает реальные ID при создании)
    INBOUND_IDS = {
        "nl": {
            "single": int(os.getenv("NL_INBOUND_SINGLE_ID", "1")),   # NL Single Tunnel (Port 8443)
            "double": int(os.getenv("NL_INBOUND_DOUBLE_ID", "2")),   # NL Double Tunnel (Port 443)
        },
        "vk": {
            "reality": int(os.getenv("VK_INBOUND_REALITY_ID", "1")), # VK Reality (Port 443)
        }
    }
    
    # VK Reality Protocol Parameters (для double tunnel: клиент → VK)
    REALITY_PARAMS: Dict[str, str] = {
        "public_key": os.getenv("REALITY_PUBLIC_KEY", ""),
        "short_id": os.getenv("REALITY_SHORT_ID", ""),
        "fingerprint": "chrome",
        "spx": "%2F",
        "sni": os.getenv("VK_REALITY_SNI", "dl.google.com"),
        "flow": "xtls-rprx-vision",
    }

    # NL Reality Protocol Parameters (для single tunnel: клиент → NL)
    NL_REALITY_PARAMS: Dict[str, str] = {
        "public_key": os.getenv("NL_REALITY_PUBLIC_KEY", ""),
        "short_id": os.getenv("NL_REALITY_SHORT_ID", ""),
        "fingerprint": "chrome",
        "spx": "%2F",
        "sni": os.getenv("NL_REALITY_SNI", "dl.google.com"),
        "flow": "xtls-rprx-vision",
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
    YOOKASSA_VALIDATE_SOURCE: bool = _env_bool("YOOKASSA_VALIDATE_SOURCE", True)
    _YOOKASSA_DEFAULT_TRUSTED_IPS = (
        "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35"
    )
    YOOKASSA_TRUSTED_IPS: list = [
        item.strip()
        for item in os.getenv("YOOKASSA_TRUSTED_IPS", _YOOKASSA_DEFAULT_TRUSTED_IPS).split(",")
        if item.strip()
    ]
    
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
"""
    
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

# ==================== TUNNEL PRICES (top-level for easy import) ====================

TUNNEL_PRICES = {
    "single": {"1_month": 150, "3_months": 400, "12_months": 1200},
    "double": {"1_month": 250, "3_months": 650, "12_months": 2200},
}

# ==================== VALIDATION ====================

def validate_config(strict_mode: bool = STRICT_CONFIG) -> bool:
    """Validate critical configuration."""
    errors = []
    warnings = []

    # Required bot settings
    if not BotConfig.BOT_TOKEN:
        errors.append("BOT_TOKEN is not set")
    if not BotConfig.ADMIN_IDS:
        errors.append("ADMIN_IDS is empty")

    # Required server settings
    if ServerConfig.NL_SERVER["ip"] in PLACEHOLDER_VALUES:
        errors.append("NL_SERVER_IP is not set")
    if ServerConfig.VK_SERVER["ip"] in PLACEHOLDER_VALUES:
        errors.append("VK_SERVER_IP is not set")

    # Required Xray panel access
    if not XrayConfig.NL_PANEL["host"]:
        errors.append("XRAY_HOST is not set")
    if XrayConfig.NL_PANEL["username"] in PLACEHOLDER_VALUES:
        errors.append("XRAY_USERNAME is not set")
    if XrayConfig.NL_PANEL["password"] in PLACEHOLDER_VALUES:
        errors.append("XRAY_PASSWORD is not set")

    if not XrayConfig.VK_PANEL["host"]:
        errors.append("VK_XRAY_HOST is not set")
    if XrayConfig.VK_PANEL["username"] in PLACEHOLDER_VALUES:
        errors.append("VK_XRAY_USERNAME is not set")
    if XrayConfig.VK_PANEL["password"] in PLACEHOLDER_VALUES:
        errors.append("VK_XRAY_PASSWORD is not set")

    # Required payment settings (if enabled)
    if PaymentConfig.YOOKASSA_ENABLED:
        if PaymentConfig.YOOKASSA_SHOP_ID in PLACEHOLDER_VALUES:
            errors.append("YOOKASSA_SHOP_ID is not set")
        if PaymentConfig.YOOKASSA_SECRET_KEY in PLACEHOLDER_VALUES:
            errors.append("YOOKASSA_SECRET_KEY is not set")
        if PaymentConfig.YOOKASSA_VALIDATE_SOURCE and not PaymentConfig.YOOKASSA_TRUSTED_IPS:
            errors.append("YOOKASSA_TRUSTED_IPS is empty while YOOKASSA_VALIDATE_SOURCE is enabled")

    # Insecure defaults should never be used in strict mode
    insecure_nl_username = XrayConfig.NL_PANEL["username"].strip().lower() in INSECURE_DEFAULT_CREDENTIALS
    insecure_nl_password = XrayConfig.NL_PANEL["password"].strip().lower() in INSECURE_DEFAULT_CREDENTIALS
    insecure_vk_username = XrayConfig.VK_PANEL["username"].strip().lower() in INSECURE_DEFAULT_CREDENTIALS
    insecure_vk_password = XrayConfig.VK_PANEL["password"].strip().lower() in INSECURE_DEFAULT_CREDENTIALS

    if insecure_nl_username:
        target = errors if strict_mode else warnings
        target.append("XRAY_USERNAME uses insecure default value")
    if insecure_nl_password:
        target = errors if strict_mode else warnings
        target.append("XRAY_PASSWORD uses insecure default value")
    if insecure_vk_username:
        target = errors if strict_mode else warnings
        target.append("VK_XRAY_USERNAME uses insecure default value")
    if insecure_vk_password:
        target = errors if strict_mode else warnings
        target.append("VK_XRAY_PASSWORD uses insecure default value")

    # Migration feature flags
    if MigrationConfig.PROVISIONER_MODE not in ALLOWED_PROVISIONER_MODES:
        errors.append(
            "PROVISIONER_MODE must be one of: legacy, hybrid, remnawave"
        )

    if MigrationConfig.READ_MODE not in ALLOWED_READ_MODES:
        errors.append(
            "READ_MODE must be one of: legacy, hybrid, remnawave"
        )

    if not (0 <= MigrationConfig.CANARY_PERCENT <= 100):
        errors.append("CANARY_PERCENT must be between 0 and 100")

    if MigrationConfig.REMNAWAVE_AUTH_MODE not in ALLOWED_REMNAWAVE_AUTH_MODES:
        errors.append("REMNAWAVE_AUTH_MODE must be one of: bearer, x-api-key")

    if MigrationConfig.use_remnawave_provisioner() and not MigrationConfig.REMNAWAVE_API_URL:
        target = errors if strict_mode else warnings
        target.append(
            "REMNAWAVE_API_URL is required when PROVISIONER_MODE is hybrid/remnawave"
        )

    if MigrationConfig.use_remnawave_provisioner() and not MigrationConfig.REMNAWAVE_API_TOKEN:
        target = errors if strict_mode else warnings
        target.append(
            "REMNAWAVE_API_TOKEN is required when PROVISIONER_MODE is hybrid/remnawave"
        )

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Warning: {warning}")

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
        "migration": {
            "provisioner_mode": MigrationConfig.PROVISIONER_MODE,
            "read_mode": MigrationConfig.READ_MODE,
            "shadow_write_enabled": MigrationConfig.SHADOW_WRITE_ENABLED,
            "canary_percent": MigrationConfig.CANARY_PERCENT,
            "remnawave_api_url": MigrationConfig.REMNAWAVE_API_URL,
            "remnawave_timeout_seconds": MigrationConfig.REMNAWAVE_TIMEOUT_SECONDS,
            "remnawave_http_retries": MigrationConfig.REMNAWAVE_HTTP_RETRIES,
            "remnawave_auth_mode": MigrationConfig.REMNAWAVE_AUTH_MODE,
            "remnawave_fallback_to_legacy": MigrationConfig.REMNAWAVE_FALLBACK_TO_LEGACY,
            "remnawave_single_squads": MigrationConfig.REMNAWAVE_SINGLE_SQUADS,
            "remnawave_double_squads": MigrationConfig.REMNAWAVE_DOUBLE_SQUADS,
        },
    }

# Validate configuration on import
if not validate_config(strict_mode=STRICT_CONFIG):
    message = (
        f"Configuration validation failed (APP_ENV={APP_ENV}, STRICT_CONFIG={STRICT_CONFIG})"
    )
    if STRICT_CONFIG:
        raise RuntimeError(message)
    logger.warning(f"{message} - some features may not work")
