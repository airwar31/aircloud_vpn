import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///aircloud_vpn.db")

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
    raise ValueError("YooKassa credentials are required")

# 3X-UI API
XRAY_API_URL = os.getenv("XRAY_API_URL")
XRAY_API_KEY = os.getenv("XRAY_API_KEY", "")
XRAY_API_USERNAME = os.getenv("XRAY_API_USERNAME")
XRAY_API_PASSWORD = os.getenv("XRAY_API_PASSWORD")
XRAY_SERVER_IP = os.getenv("XRAY_SERVER_IP")
XRAY_SERVER_PORT = os.getenv("XRAY_SERVER_PORT", "443")

if not all([XRAY_API_URL, XRAY_API_USERNAME, XRAY_API_PASSWORD, XRAY_SERVER_IP]):
    raise ValueError("X-UI API credentials are required")

# Тарифные планы
SUBSCRIPTION_PLANS = {
    "month": {
        "name": "1 месяц",
        "base_price": 99,
        "duration": 30
    },
    "3months": {
        "name": "3 месяца",
        "base_price": 249,
        "duration": 90
    },
    "6months": {
        "name": "6 месяцев",
        "base_price": 499,
        "duration": 180
    },
    "year": {
        "name": "12 месяцев",
        "base_price": 999,
        "duration": 365
    }
}

# Цены за дополнительные устройства
DEVICE_PRICING = {
    1: 0,    # 1 устройство - базовая цена
    2: 50,   # +50₽ за 2-е устройство
    3: 100,  # +100₽ за 3-е устройство
    4: 150,  
    5: 200,
    10: 500
}

def calculate_plan_price(plan_id: str, devices: int) -> int:
    """Расчет цены плана с учетом количества устройств"""
    if plan_id not in SUBSCRIPTION_PLANS or devices not in DEVICE_PRICING:
        return 0
    
    base_price = SUBSCRIPTION_PLANS[plan_id]["base_price"]
    device_surcharge = DEVICE_PRICING[devices]
    
    return base_price + device_surcharge