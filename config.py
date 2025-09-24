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

# VPN Plans
VPN_PLANS = {
    "1month": {
        "name": "1 месяц",
        "price": 99,
        "days": 30
    },
    "3months": {
        "name": "3 месяца", 
        "price": 279,
        "days": 90
    },
    "6months": {
        "name": "6 месяцев",
        "price": 499, 
        "days": 180
    },
    "1year": {
        "name": "1 год",
        "price": 899,
        "days": 365
    }
}

# Реферальная система
REFERRAL_RATES = {
    "1month": 20,  
    "3months": 50, 
    "6months": 90, 
    "1year": 140   
}

# Админы (добавьте свои Telegram ID)
ADMIN_IDS = [1262543088]  # Замените на реальные ID



