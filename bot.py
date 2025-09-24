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
from database_mysql import db
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
    waiting_email = State()
    waiting_payment = State()

class AdminStates(StatesGroup):
    waiting_gift_user_id = State()
    waiting_gift_days = State()
    waiting_gift_link_days = State()
    waiting_check_user_id = State()

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
            self.show_plans, 
            F.data == "buy_vpn"
        )
        self.dp.callback_query.register(
            self.process_plan_selection, 
            F.data.startswith("plan_")
        )
        self.dp.message.register(
            self.process_email_input,
            OrderStates.waiting_email
        )
        self.dp.callback_query.register(
            self.process_payment_check, 
            F.data.startswith("check_")
        )
        self.dp.callback_query.register(
            self.show_my_keys, 
            F.data == "my_keys"
        )
        self.dp.callback_query.register(
            self.back_to_menu, 
            F.data == "back_menu"
        )
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        user = message.from_user
        
        # Добавляем пользователя в БД
        db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="💳 Купить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="📱 Инструкция", callback_data="help_instructions")]
        ]
        
        if user.id in ADMIN_IDS:
            keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN\n"
            "⚡ Безлимитный трафик\n"
            "🔒 Максимальная безопасность\n\n"
            "Используйте кнопки ниже для навигации:",
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
            "❓ Если возникли проблемы, обратитесь в поддержку: @MiddleCloud1"
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
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")]
        ])
        
        await message.answer(
            "👤 <b>Профиль</b>\n\n"
            "Используйте кнопку ниже для просмотра ваших VPN ключей.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def show_plans(self, callback: types.CallbackQuery):
        """Показ тарифов"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']}₽", 
                callback_data=f"plan_{plan_id}"
            )]
            for plan_id, plan in VPN_PLANS.items()
        ] + [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_menu")]
        ])
        
        await callback.message.edit_text(
            "💳 <b>Выберите тариф:</b>\n\n"
            "🔥 Безлимитный трафик\n"
            "⚡ Высокая скорость\n"
            "🔒 Полная анонимность",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def process_plan_selection(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора тарифа"""
        plan_id = callback.data.split("_")[1]
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await callback.answer("❌ Неверный тариф")
            return
        
        # Сохраняем выбранный план и запрашиваем email
        await state.update_data(plan_id=plan_id)
        await state.set_state(OrderStates.waiting_email)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_vpn")]
        ])
        
        await callback.message.edit_text(
            f"📧 <b>Введите ваш email для чека:</b>\n\n"
            f"📦 Тариф: {plan['name']} - {plan['price']}₽\n"
            f"⏰ Срок: {plan['days']} дней\n\n"
            "Отправьте ваш email сообщением:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def process_email_input(self, message: types.Message, state: FSMContext):
        """Обработка ввода email"""
        email = message.text.strip()
        
        if "@" not in email or "." not in email:
            await message.answer("❌ Некорректный email. Попробуйте ещё раз:")
            return
            
        data = await state.get_data()
        plan_id = data.get("plan_id")
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await message.answer("❌ Ошибка. Начните сначала.")
            await state.clear()
            return
            
        payment = await self.create_payment(
            plan["price"], 
            f"VPN {plan['name']}",
            message.from_user.id,
            email
        )
        
        if payment:
            order_id = db.create_order(
                user_id=message.from_user.id,
                plan_id=plan_id,
                payment_id=payment.id,
                amount=plan["price"]
            )
            
            await state.update_data(
                plan_id=plan_id,
                payment_id=payment.id,
                user_id=message.from_user.id,
                order_id=order_id,
                user_email=email
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
            
            await message.answer(
                f"💰 <b>К оплате:</b> {plan['price']}₽\n"
                f"📦 <b>Тариф:</b> {plan['name']}\n"
                f"📧 <b>Email:</b> {email}\n\n"
                "Нажмите кнопку для оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Ошибка создания платежа")
            
    async def create_payment(self, amount: int, description: str, user_id: int, user_email: str) -> Optional[Payment]:
        """Создание платежа в ЮKassa с чеком"""
        try:
            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/{(await self.bot.get_me()).username}"
                },
                "capture": True,
                "description": description[:128],
                "receipt": {
                    "customer": {
                        "email": user_email
                    },
                    "items": [{
                        "description": description[:128],
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount:.2f}",
                            "currency": "RUB"
                        },
                        "vat_code": 1
                    }]
                }
            }
            
            if user_id:
                payment_data["metadata"] = {"user_id": str(user_id)}
            
            logger.info(f"Создание платежа на {amount}₽")
            
            idempotence_key = str(uuid.uuid4())
            payment = Payment.create(payment_data, idempotence_key)
            
            logger.info(f"Создан платеж {payment.id}")
            return payment
            
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Ответ API: {e.response.text}")
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
                    
                    db.add_vpn_key(
                        user_id=user_id,
                        order_id=order_id,
                        email=email,
                        config=vpn_config,
                        expires_at=expires_at,
                        traffic_limit=0
                    )
                    
                    await callback.message.edit_text(
                        f"✅ <b>Оплата прошла успешно!</b>\n\n"
                        f"🔑 <b>Ваш VPN ключ:</b>\n"
                        f"<code>{vpn_config}</code>\n\n"
                        "💬 Поддержка: @MiddleCloud1",
                        parse_mode="HTML"
                    )
                    await state.clear()
                else:
                    await callback.message.edit_text(
                        "❌ Оплата прошла, но произошла ошибка при создании VPN ключа.\n"
                        "Обратитесь в поддержку: @MiddleCloud1"
                    )
                    
            elif payment.status == "pending":
                await callback.answer("⏳ Платеж обрабатывается, попробуйте через минуту")
            else:
                await callback.answer("⏳ Платеж еще не прошел")
                
        except Exception as e:
            logger.error(f"Ошибка проверки платежа {payment_id}: {e}")
            await callback.answer("❌ Ошибка проверки платежа")
            
    async def create_vpn_client(self, user_id: int, plan_id: str, username: str = None) -> Optional[tuple]:
        """Создание VPN клиента через Xray API"""
        plan = VPN_PLANS[plan_id]
        
        if username:
            email = f"{username}_{datetime.now().strftime('%m%d')}"
        else:
            email = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with XrayManager(XRAY_API_URL) as xray:
            result = await xray.add_client(email, {"days": plan["days"]})
            
            if result:
                return (result["config"], result["email"], result["expires_at"])
            else:
                logger.error(f"Не удалось создать VPN клиента для {email}")
                return None
                
    async def show_my_keys(self, callback: types.CallbackQuery):
        """Показ VPN ключей пользователя"""
        user_id = callback.from_user.id
        vpn_keys = db.get_user_vpn_keys(user_id)
        
        if not vpn_keys:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
            ])
            await callback.message.edit_text(
                "📭 У вас пока нет активных VPN ключей.\n\n"
                "Купите подписку в главном меню.",
                reply_markup=keyboard
            )
            return
            
        text = "🔑 <b>Ваши VPN ключи:</b>\n\n"
        for i, key in enumerate(vpn_keys, 1):
            expires_at = datetime.fromisoformat(key['expires_at'].replace('Z', '+00:00'))
            is_active = expires_at > datetime.now() and key['is_active'] == 1
            status = "✅" if is_active else "❌"
            text += f"{status} {key['email']}\n"
            text += f"<code>{key['config']}</code>\n\n"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    async def back_to_menu(self, callback: types.CallbackQuery, state: FSMContext = None):
        """Возврат в главное меню"""
        if state:
            await state.clear()
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="💳 Купить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="📱 Инструкция", callback_data="help_instructions")]
        ]
        
        if callback.from_user.id in ADMIN_IDS:
            keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN\n"
            "⚡ Безлимитный трафик\n"
            "🔒 Максимальная безопасность\n\n"
            "Используйте кнопки ниже для навигации:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
                
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
        
    async def back_to_menu(self, callback: types.CallbackQuery, state: FSMContext = None):
        """Возврат в главное меню"""
        if state:
            await state.clear()
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="💳 Купить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="📱 Инструкция", callback_data="help_instructions")]
        ]
        
        if callback.from_user.id in ADMIN_IDS:
            keyboard_buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN\n"
            "⚡ Безлимитный трафик\n"
            "🔒 Максимальная безопасность\n\n"
            "Используйте кнопки ниже для навигации:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
                
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