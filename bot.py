import asyncio
import logging
import json
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
from yookassa import Configuration, Payment

from config import *
from database import db
from xray_manager import XrayManager

# Настройка ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OrderStates(StatesGroup):
    waiting_payment = State()

class XUIClient:
    """Клиент для работы с X-UI API"""
    
    def __init__(self, url: str, username: str, password: str):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        await self.login()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def login(self):
        """Авторизация в X-UI"""
        try:
            login_data = {
                "username": self.username,
                "password": self.password
            }
            async with self.session.post(f"{self.url}/login", data=login_data) as resp:
                if resp.status == 200:
                    logger.info("Успешная авторизация в X-UI")
                    return True
                else:
                    logger.error(f"Ошибка авторизации в X-UI: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка подключения к X-UI: {e}")
            return False
            
    async def get_inbounds(self) -> Optional[list]:
        """Получение списка inbound'ов"""
        try:
            async with self.session.get(f"{self.url}/panel/api/inbounds/list") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("obj", [])
                else:
                    logger.error(f"Ошибка получения inbound'ов: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения inbound'ов: {e}")
            return None
            
    async def add_client(self, inbound_id: int, client_data: dict) -> bool:
        """Добавление клиента к inbound"""
        try:
            payload = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [client_data]})
            }
            
            async with self.session.post(
                f"{self.url}/panel/api/inbounds/addClient",
                json=payload
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Клиент {client_data['email']} успешно добавлен")
                    return True
                else:
                    logger.error(f"Ошибка добавления клиента: {resp.status}")
                    text = await resp.text()
                    logger.error(f"Ответ сервера: {text}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            return False

class VPNBot:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.setup_handlers()
        
    def setup_handlers(self):
        """Настройка обработчиков"""
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.cmd_profile, Command("profile"))
        self.dp.callback_query.register(
            self.process_plan_selection, 
            F.data.startswith("plan_")
        )
        self.dp.callback_query.register(
            self.process_payment_check, 
            F.data.startswith("check_")
        )
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        # Добавляем пользователя в БД
        user = message.from_user
        db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']}₽ ({plan['traffic']}ГБ)", 
                callback_data=f"plan_{plan_id}"
            )]
            for plan_id, plan in VPN_PLANS.items()
        ])
        
        await message.answer(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN для обхода блокировок\n"
            "⚡ Высокая скорость подключения\n"
            "🌍 Серверы в разных странах\n\n"
            "Выберите тарифный план:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def cmd_help(self, message: types.Message):
        """Обработчик команды /help"""
        help_text = (
            "📱 <b>Инструкция по подключению VPN:</b>\n\n"
            "<b>Для Android:</b>\n"
            "1. Скачайте приложение v2rayNG из Google Play\n"
            "2. Нажмите + и выберите 'Импорт из буфера обмена'\n"
            "3. Вставьте полученную конфигурацию\n\n"
            "<b>Для iOS:</b>\n"
            "1. Скачайте приложение Shadowrocket из App Store\n"
            "2. Нажмите + и вставьте конфигурацию\n\n"
            "<b>Для Windows:</b>\n"
            "1. Скачайте v2rayN с GitHub\n"
            "2. Добавьте сервер через 'Импорт из буфера обмена'\n\n"
            "🔧 <b>Команды бота:</b>\n"
            "/start - Главное меню\n"
            "/profile - Мои VPN ключи\n"
            "/help - Эта справка\n\n"
            "❓ Если возникли проблемы, обратитесь в поддержку: @support"
        )
        await message.answer(help_text, parse_mode="HTML")
        
    async def cmd_profile(self, message: types.Message):
        """Обработчик команды /profile"""
        user_id = message.from_user.id
        vpn_keys = db.get_user_vpn_keys(user_id)
        
        if not vpn_keys:
            await message.answer(
                "📭 У вас пока нет активных VPN ключей.\n\n"
                "Используйте /start для покупки подписки."
            )
            return
            
        text = "🔑 <b>Ваши VPN ключи:</b>\n\n"
        
        for i, key in enumerate(vpn_keys, 1):
            expires_at = datetime.fromisoformat(key['expires_at'].replace('Z', '+00:00'))
            status = "✅ Активен" if expires_at > datetime.now() else "❌ Истек"
            
            text += (
                f"<b>{i}. {key['email']}</b>\n"
                f"📅 Истекает: {expires_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"📊 Лимит трафика: {key['traffic_limit'] // (1024**3)} ГБ\n"
                f"🔘 Статус: {status}\n\n"
            )
            
        await message.answer(text, parse_mode="HTML")
        
    async def process_plan_selection(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора тарифа"""
        plan_id = callback.data.split("_")[1]
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await callback.answer("❌ Неверный тариф")
            return
            
        # Создание платежа в ЮKassa
        payment = await self.create_payment(
            plan["price"], 
            f"VPN {plan['name']}",
            callback.from_user.id
        )
        
        if payment:
            # Создаем заказ в БД
            order_id = db.create_order(
                user_id=callback.from_user.id,
                plan_id=plan_id,
                payment_id=payment.id,
                amount=plan["price"]
            )
            
            await state.update_data(
                plan_id=plan_id,
                payment_id=payment.id,
                user_id=callback.from_user.id,
                order_id=order_id
            )
            await state.set_state(OrderStates.waiting_payment)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="💳 Оплатить", 
                    url=payment.confirmation.confirmation_url
                )],
                [InlineKeyboardButton(
                    text="✅ Проверить оплату", 
                    callback_data=f"check_{payment.id}"
                )]
            ])
            
            await callback.message.edit_text(
                f"💰 <b>К оплате:</b> {plan['price']}₽\n"
                f"📦 <b>Тариф:</b> {plan['name']}\n"
                f"📊 <b>Трафик:</b> {plan['traffic']} ГБ\n"
                f"⏰ <b>Срок:</b> {plan['days']} дней\n\n"
                "Нажмите кнопку для оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка создания платежа")
            
    async def create_payment(self, amount: int, description: str, user_id: int) -> Optional[Payment]:
        """Создание платежа в ЮKassa"""
        try:
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{(await self.bot.get_me()).username}"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id)
                }
            }, uuid.uuid4())
            
            logger.info(f"Создан платеж {payment.id} на сумму {amount}₽ для пользователя {user_id}")
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
                data = await state.get_data()
                plan_id = data.get("plan_id")
                user_id = data.get("user_id")
                order_id = data.get("order_id")
                
                # Обновляем статус заказа
                db.update_order_status(payment_id, "paid")
                
                # Создаем VPN ключ
                vpn_result = await self.create_vpn_client(user_id, plan_id, callback.from_user.username)
                
                if vpn_result:
                    vpn_config, email, expires_at = vpn_result
                    plan = VPN_PLANS[plan_id]
                    
                    # Сохраняем VPN ключ в БД
                    db.add_vpn_key(
                        user_id=user_id,
                        order_id=order_id,
                        email=email,
                        config=vpn_config,
                        expires_at=expires_at,
                        traffic_limit=plan["traffic"] * 1024 * 1024 * 1024
                    )
                    
                    await callback.message.edit_text(
                        "✅ <b>Оплата прошла успешно!</b>\n\n"
                        f"🔑 <b>Ваш VPN ключ:</b>\n"
                        f"<code>{vpn_config}</code>\n\n"
                        "📱 Инструкция по подключению: /help\n"
                        "👤 Мои ключи: /profile\n"
                        "💬 Поддержка: @support",
                        parse_mode="HTML"
                    )
                    await state.clear()
                    logger.info(f"VPN ключ успешно создан для пользователя {user_id}")
                else:
                    db.update_order_status(payment_id, "failed")
                    await callback.message.edit_text(
                        "❌ Оплата прошла, но произошла ошибка при создании VPN ключа.\n"
                        "Обратитесь в поддержку: @support"
                    )
                    
            elif payment.status == "pending":
                await callback.answer("⏳ Платеж обрабатывается, попробуйте через минуту")
            elif payment.status == "canceled":
                await callback.answer("❌ Платеж отменен")
                await state.clear()
            else:
                await callback.answer("⏳ Платеж еще не прошел")
                
        except Exception as e:
            logger.error(f"Ошибка проверки платежа {payment_id}: {e}")
            await callback.answer("❌ Ошибка проверки платежа")
            
    async def create_vpn_client(self, user_id: int, plan_id: str, username: str = None) -> Optional[tuple]:
        """Создание VPN клиента через Xray API"""
        plan = VPN_PLANS[plan_id]
        
        # Используем username или генерируем ID
        if username:
            email = f"{username}_{datetime.now().strftime('%m%d')}"
        else:
            email = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with XrayManager(XRAY_API_URL) as xray:
            result = await xray.add_client(email, plan)
            
            if result:
                return (result["config"], result["email"], result["expires_at"])
            else:
                logger.error(f"Не удалось создать VPN клиента для {email}")
                return None
                
    def generate_config(self, inbound: Dict[str, Any], client: Dict[str, Any]) -> str:
        """Генерация конфигурации для клиента"""
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            stream_settings = json.loads(inbound.get("streamSettings", "{}"))
            
            # Определяем параметры подключения
            address = inbound.get("listen", "0.0.0.0")
            if address in ["0.0.0.0", "::", ""]:
                address = "YOUR_SERVER_IP"  # Замените на IP вашего сервера
                
            port = inbound["port"]
            protocol = inbound["protocol"]
            
            if protocol == "vless":
                # Генерируем VLESS конфигурацию
                network = stream_settings.get("network", "tcp")
                security = stream_settings.get("security", "none")
                
                config = (
                    f"vless://{client['id']}@{address}:{port}"
                    f"?type={network}&security={security}"
                    f"#{client['email']}"
                )
                
            elif protocol == "vmess":
                # Генерируем VMess конфигурацию
                vmess_config = {
                    "v": "2",
                    "ps": client["email"],
                    "add": address,
                    "port": str(port),
                    "id": client["id"],
                    "aid": str(settings.get("alterId", 0)),
                    "net": stream_settings.get("network", "tcp"),
                    "type": "none",
                    "host": "",
                    "path": "",
                    "tls": stream_settings.get("security", "none")
                }
                
                config_json = json.dumps(vmess_config, separators=(',', ':'))
                config = "vmess://" + base64.b64encode(config_json.encode()).decode()
                
            else:
                config = f"Протокол {protocol} не поддерживается"
                
            return config
            
        except Exception as e:
            logger.error(f"Ошибка генерации конфигурации: {e}")
            return "Ошибка генерации конфигурации"
            
    async def start_polling(self):
        """Запуск бота"""
        logger.info("Запуск VPN бота...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
        finally:
            await self.bot.session.close()

async def main():
    bot = VPNBot()
    await bot.start_polling()

if __name__ == "__main__":
    asyncio.run(main())