import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "YOUR_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "YOUR_SECRET_KEY")

# Xray API
XRAY_API_URL = os.getenv("XRAY_API_URL", "http://localhost:8080")

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



