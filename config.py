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

# Базовые периоды подписки
BASE_PLANS = {
    "1month": {
        "name": "1 месяц",
        "base_price": 99,
        "days": 30
    },
    "3months": {
        "name": "3 месяца", 
        "base_price": 279,
        "days": 90
    },
    "6months": {
        "name": "6 месяцев",
        "base_price": 499, 
        "days": 180
    },
    "1year": {
        "name": "1 год",
        "base_price": 899,
        "days": 365
    }
}

# Тарифы устройств (доплата к базовой цене)
DEVICE_PLANS = {
    1: {"name": "1 устройство", "extra_price": 0},
    2: {"name": "2 устройства", "extra_price": 50},
    3: {"name": "3 устройства", "extra_price": 100},
    5: {"name": "5 устройств", "extra_price": 200}
}

# Функция для расчета итоговой цены
def calculate_price(period_id: str, device_count: int) -> int:
    """Расчет итоговой цены тарифа"""
    base = BASE_PLANS.get(period_id, {}).get("base_price", 0)
    extra = DEVICE_PLANS.get(device_count, {}).get("extra_price", 0)
    return base + extra

# Совместимость со старым форматом
VPN_PLANS = {}
for period_id, period_data in BASE_PLANS.items():
    for device_count, device_data in DEVICE_PLANS.items():
        plan_key = f"{period_id}_{device_count}dev"
        VPN_PLANS[plan_key] = {
            "name": f"{period_data['name']} ({device_data['name']})",
            "price": calculate_price(period_id, device_count),
            "days": period_data["days"],
            "device_limit": device_count,
            "period_id": period_id,
            "device_count": device_count
        }

# Реферальная система
REFERRAL_RATES = {
    "1month": 25,   # 25₽ за покупку 1 месяца
    "3months": 60,  # 60₽ за покупку 3 месяцев
    "6months": 100, # 100₽ за покупку 6 месяцев
    "1year": 150    # 150₽ за покупку 1 года
}

# Админы (добавьте свои Telegram ID)
ADMIN_IDS = [1262543088]  # Замените на реальные ID

# Ограничения VPN
DEVICE_LIMIT = int(os.getenv("DEVICE_LIMIT", 2))  # Максимум устройств на один ключ

