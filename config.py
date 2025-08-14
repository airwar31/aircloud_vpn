import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "7717019733:AAE8ElbxXYUTeoLct8s185m8aMA6lwx_mns")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "1262543088").split(",") if x.strip()]

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///aircloud_vpn.db")

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1127420")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "test_5ed7HCB8W7xTWQm4WjSjrSi_gNjI5lvh42-j-1Ts5Zc")

# 3X-UI API
XRAY_API_URL = os.getenv("XRAY_API_URL", "http://5.129.224.166:19620/44sA6Evz35TcCx1/panel/api")
XRAY_API_KEY = os.getenv("XRAY_API_KEY", "")
XRAY_API_USERNAME = os.getenv("XRAY_API_USERNAME", "GrokZNwkIU")
XRAY_API_PASSWORD = os.getenv("XRAY_API_PASSWORD", "NGN2u1f1NX")
XRAY_SERVER_IP = os.getenv("XRAY_SERVER_IP", "5.129.224.166")
XRAY_SERVER_PORT = os.getenv("XRAY_SERVER_PORT", "443")

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
    4: 150,  # +150₽ за 4-е устройство
    5: 200   # +200₽ за 5-е устройство
}

def calculate_plan_price(plan_id: str, devices: int) -> int:
    """Расчет цены плана с учетом количества устройств"""
    if plan_id not in SUBSCRIPTION_PLANS or devices not in DEVICE_PRICING:
        return 0
    
    base_price = SUBSCRIPTION_PLANS[plan_id]["base_price"]
    device_surcharge = DEVICE_PRICING[devices]
    
    return base_price + device_surcharge