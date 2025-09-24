import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebApp
import aiohttp
from yookassa import Configuration, Payment

# Конфигурация из переменных окружения
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
X_UI_URL = os.getenv("X_UI_URL", "http://localhost:54321")
X_UI_USERNAME = os.getenv("X_UI_USERNAME", "admin")
X_UI_PASSWORD = os.getenv("X_UI_PASSWORD", "admin")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not YOOKASSA_SHOP_ID:
    raise ValueError("YOOKASSA_SHOP_ID environment variable is required")
if not YOOKASSA_SECRET_KEY:
    raise ValueError("YOOKASSA_SECRET_KEY environment variable is required")

# Настройка ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния FSM
class OrderStates(StatesGroup):
    waiting_payment = State()

# Тарифы VPN
VPN_PLANS = {
    "1month": {"name": "1 месяц", "price": 200, "days": 30, "traffic": 100},
    "3months": {"name": "3 месяца", "price": 500, "days": 90, "traffic": 300},
    "6months": {"name": "6 месяцев", "price": 900, "days": 180, "traffic": 600},
    "1year": {"name": "1 год", "price": 1500, "days": 365, "traffic": 1200}
}

class VPNBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.session = None
        self.x_ui_session = None
        
    async def start(self):
        """Запуск бота"""
        self.session = aiohttp.ClientSession()
        await self.login_x_ui()
        self.setup_handlers()
        await self.dp.start_polling(self.bot)
        
    async def stop(self):
        """Остановка бота"""
        if self.session:
            await self.session.close()
            
    async def login_x_ui(self):
        """Авторизация в x-ui панели"""
        try:
            login_data = {
                "username": X_UI_USERNAME,
                "password": X_UI_PASSWORD
            }
            async with self.session.post(f"{X_UI_URL}/login", data=login_data) as resp:
                if resp.status == 200:
                    logger.info("Успешная авторизация в x-ui")
                else:
                    logger.error(f"Ошибка авторизации в x-ui: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка подключения к x-ui: {e}")
            
    def setup_handlers(self):
        """Настройка обработчиков"""
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.callback_query.register(self.process_plan_selection, lambda c: c.data.startswith("plan_"))
        self.dp.callback_query.register(self.process_payment_check, lambda c: c.data.startswith("check_"))
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{plan['name']} - {plan['price']}₽", 
                                callback_data=f"plan_{plan_id}")]
            for plan_id, plan in VPN_PLANS.items()
        ])
        
        await message.answer(
            "🚀 Добро пожаловать в VPN бот!\n\n"
            "Выберите тарифный план:",
            reply_markup=keyboard
        )
        
    async def process_plan_selection(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора тарифа"""
        plan_id = callback.data.split("_")[1]
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await callback.answer("Неверный тариф")
            return
            
        # Создание платежа в ЮKassa
        payment = await self.create_payment(plan["price"], f"VPN {plan['name']}")
        
        if payment:
            await state.update_data(
                plan_id=plan_id,
                payment_id=payment.id,
                user_id=callback.from_user.id
            )
            await state.set_state(OrderStates.waiting_payment)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=payment.confirmation.confirmation_url)],
                [InlineKeyboardButton(text="✅ Проверить оплату", 
                                    callback_data=f"check_{payment.id}")]
            ])
            
            await callback.message.edit_text(
                f"💰 К оплате: {plan['price']}₽\n"
                f"📦 Тариф: {plan['name']}\n"
                f"🔥 Трафик: безлимитный\n\n"
                "Нажмите кнопку для оплаты:",
                reply_markup=keyboard
            )
        else:
            await callback.answer("Ошибка создания платежа")
            
    async def create_payment(self, amount: int, description: str) -> Payment:
        """Создание платежа в ЮKassa"""
        try:
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/your_bot"
                },
                "capture": True,
                "description": description
            }, uuid.uuid4())
            
            return payment
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            return None
            
    async def process_payment_check(self, callback: types.CallbackQuery, state: FSMContext):
        """Проверка статуса платежа"""
        payment_id = callback.data.split("_")[1]
        
        try:
            payment = Payment.find_one(payment_id)
            
            if payment.status == "succeeded":
                # Платеж успешен, создаем VPN ключ
                data = await state.get_data()
                plan_id = data.get("plan_id")
                user_id = data.get("user_id")
                
                vpn_config = await self.create_vpn_client(user_id, plan_id)
                
                if vpn_config:
                    await callback.message.edit_text(
                        "✅ Оплата прошла успешно!\n\n"
                        f"🔑 Ваш VPN ключ:\n"
                        f"```\n{vpn_config}\n```\n\n"
                        "📱 Инструкция по подключению: /help",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                else:
                    await callback.answer("Ошибка создания VPN ключа")
            else:
                await callback.answer("Платеж еще не прошел")
                
        except Exception as e:
            logger.error(f"Ошибка проверки платежа: {e}")
            await callback.answer("Ошибка проверки платежа")
            
    async def create_vpn_client(self, user_id: int, plan_id: str) -> str:
        """Создание VPN клиента через x-ui API"""
        try:
            plan = VPN_PLANS[plan_id]
            
            # Получаем список inbound'ов
            async with self.session.get(f"{X_UI_URL}/panel/api/inbounds/list") as resp:
                if resp.status != 200:
                    return None
                    
                data = await resp.json()
                inbounds = data.get("obj", [])
                
                if not inbounds:
                    return None
                    
                # Берем первый активный inbound
                inbound = next((ib for ib in inbounds if ib.get("enable")), None)
                if not inbound:
                    return None
                    
            # Создаем клиента
            client_data = {
                "id": str(uuid.uuid4()),
                "email": f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "limitIp": 2,
                "totalGB": 0,  # 0 = безлимитный трафик
                "expiryTime": int((datetime.now() + timedelta(days=plan["days"])).timestamp() * 1000),
                "enable": True,
                "tgId": user_id,
                "subId": str(uuid.uuid4())[:8]
            }
            
            # Добавляем клиента к inbound
            add_client_data = {
                "id": inbound["id"],
                "settings": json.dumps({
                    "clients": [client_data]
                })
            }
            
            async with self.session.post(
                f"{X_UI_URL}/panel/api/inbounds/addClient",
                json=add_client_data
            ) as resp:
                if resp.status == 200:
                    # Генерируем конфигурацию
                    return self.generate_config(inbound, client_data)
                else:
                    logger.error(f"Ошибка создания клиента: {resp.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка создания VPN клиента: {e}")
            return None
            
    def generate_config(self, inbound: Dict[str, Any], client: Dict[str, Any]) -> str:
        """Генерация конфигурации для клиента"""
        try:
            settings = json.loads(inbound["settings"])
            stream_settings = json.loads(inbound.get("streamSettings", "{}"))
            
            if inbound["protocol"] == "vless":
                config = (
                    f"vless://{client['id']}@{inbound.get('listen', '0.0.0.0')}:{inbound['port']}"
                    f"?type={stream_settings.get('network', 'tcp')}"
                    f"&security={stream_settings.get('security', 'none')}"
                    f"#{client['email']}"
                )
            elif inbound["protocol"] == "vmess":
                vmess_config = {
                    "v": "2",
                    "ps": client["email"],
                    "add": inbound.get("listen", "0.0.0.0"),
                    "port": inbound["port"],
                    "id": client["id"],
                    "aid": settings.get("alterId", 0),
                    "net": stream_settings.get("network", "tcp"),
                    "type": "none",
                    "host": "",
                    "path": "",
                    "tls": stream_settings.get("security", "none")
                }
                import base64
                config = "vmess://" + base64.b64encode(json.dumps(vmess_config).encode()).decode()
            else:
                config = f"Протокол {inbound['protocol']} не поддерживается"
                
            return config
            
        except Exception as e:
            logger.error(f"Ошибка генерации конфигурации: {e}")
            return "Ошибка генерации конфигурации"

async def main():
    bot = VPNBot()
    try:
        await bot.start()
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())