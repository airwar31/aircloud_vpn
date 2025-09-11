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
        "price": 200,
        "days": 30,
        "traffic": 100  # GB
    },
    "3months": {
        "name": "3 месяца", 
        "price": 500,
        "days": 90,
        "traffic": 300
    },
    "6months": {
        "name": "6 месяцев",
        "price": 900, 
        "days": 180,
        "traffic": 600
    },
    "1year": {
        "name": "1 год",
        "price": 1500,
        "days": 365, 
        "traffic": 1200
    }
}