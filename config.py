import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot API токен (получите у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1127420")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "test_5ed7HCB8W7xTWQm4WjSjrSi_gNjI5lvh42-j-1Ts5Zc")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://t.me/vpn_aircloud_bot")

# Настройки VPN
VPN_SERVER_ADDRESS = os.getenv("VPN_SERVER_ADDRESS", "5.129.224.166")
VPN_DEFAULT_PROTOCOL = os.getenv("VPN_DEFAULT_PROTOCOL", "vless")

# Настройки Xray
XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/etc/xray/config.json")
XRAY_TEMPLATE_PATH = os.getenv("XRAY_TEMPLATE_PATH", "/etc/xray/config.template.json")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "aircloud_vpn.db")

# Цены на подписки (в рублях)
SUBSCRIPTION_PRICE = {
    "1_month": 150,
}

# Настройки администратора
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "1262543088").split(","))) if os.getenv("ADMIN_IDS") else []