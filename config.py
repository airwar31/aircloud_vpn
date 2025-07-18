import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot API токен (получите у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "")

# Настройки VPN
VPN_SERVER_ADDRESS = os.getenv("VPN_SERVER_ADDRESS", "")
VPN_DEFAULT_PROTOCOL = os.getenv("VPN_DEFAULT_PROTOCOL", "vless")

# Настройки Xray
XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/etc/xray/config.json")
XRAY_TEMPLATE_PATH = os.getenv("XRAY_TEMPLATE_PATH", "/etc/xray/config.template.json")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "aircloud_vpn.db")

# Цены на подписки (в рублях)
SUBSCRIPTION_PRICE = {
    "1_month": 150,
    "3_months": 250,
    "6_months": 449,
    "12_months": 899
}

# Словарь с планами подписок
SUBSCRIPTION_PLANS = {
    "1_month": {"name": "1 месяц", "days": 30, "price": SUBSCRIPTION_PRICE["1_month"]},
    "3_months": {"name": "3 месяца", "days": 90, "price": SUBSCRIPTION_PRICE["3_months"]},
    "6_months": {"name": "6 месяцев", "days": 180, "price": SUBSCRIPTION_PRICE["6_months"]},
    "12_months": {"name": "12 месяцев", "days": 365, "price": SUBSCRIPTION_PRICE["12_months"]}
}

# Настройки администратора
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []