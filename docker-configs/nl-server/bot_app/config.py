import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
if not YOOKASSA_SHOP_ID:
    raise ValueError("YOOKASSA_SHOP_ID environment variable is required")
if not YOOKASSA_SECRET_KEY:
    raise ValueError("YOOKASSA_SECRET_KEY environment variable is required")

# Xray API  
XRAY_API_URL = os.getenv("XRAY_API_URL", "http://xray-vpn:8080")

# Реальные IP адреса серверов для VLESS ссылок
NL_SERVER_IP = os.getenv("NL_SERVER_IP", "85.239.56.174")  # NL сервер для single tunnel
VK_SERVER_IP = os.getenv("VK_SERVER_IP", "89.208.86.167")  # VK сервер для double tunnel

# VPN Plans
VPN_PLANS = {
    # Обычные планы (одиночный туннель)
    "1month": {
        "name": "1 месяц",
        "price": 250,
        "days": 30,
        "tunnel_type": "single"
    },
    "3months": {
        "name": "3 месяца", 
        "price": 279,
        "days": 90,
        "tunnel_type": "single"
    },
    "6months": {
        "name": "6 месяцев",
        "price": 499, 
        "days": 180,
        "tunnel_type": "single"
    },
    "1year": {
        "name": "1 год",
        "price": 899,
        "days": 365,
        "tunnel_type": "single"
    },
    # Планы с двойным туннелированием (ВК -> Нидерланды) - обход белых листов
    "double_tunnel_1month": {
        "name": "1 месяц (Двойной туннель ВК→NL)",
        "price": 250,
        "days": 30,
        "tunnel_type": "double",
        "route": "vk_to_nl"
    },
    "double_tunnel_3months": {
        "name": "3 месяца (Двойной туннель ВК→NL)",
        "price": 500,
        "days": 90,
        "tunnel_type": "double",
        "route": "vk_to_nl"
    },
    "double_tunnel_6months": {
        "name": "6 месяцев (Двойной туннель ВК→NL)",
        "price": 800,
        "days": 180,
        "tunnel_type": "double",
        "route": "vk_to_nl"
    },
    "double_tunnel_1year": {
        "name": "1 год (Двойной туннель ВК→NL)",
        "price": 1500,
        "days": 365,
        "tunnel_type": "double",
        "route": "vk_to_nl"
    }
}

# Реферальная система
REFERRAL_RATES = {
    "1month": 50,  
    "3months": 70, 
    "6months": 130, 
    "1year": 200,
    # Двойной туннель - выше ставки (обход белых листов)
    "double_tunnel_1month": 50,
    "double_tunnel_3months": 125,
    "double_tunnel_6months": 200,
    "double_tunnel_1year": 375
}

# Админы (добавьте свои Telegram ID)
ADMIN_IDS = [1262543088]  # Замените на реальные ID



