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
        self.dp.callback_query.register(
            self.process_extend_plan, 
            F.data.startswith("extend_plan_")
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
            self.show_key_details, 
            F.data.startswith("key_")
        )
        self.dp.callback_query.register(
            self.show_referrals, 
            F.data == "referrals"
        )
        self.dp.callback_query.register(
            self.show_admin_panel, 
            F.data == "admin_panel"
        )
        self.dp.callback_query.register(
            self.back_to_menu, 
            F.data == "back_menu"
        )
        self.dp.callback_query.register(
            self.admin_gift_key, 
            F.data == "admin_gift_key"
        )
        self.dp.callback_query.register(
            self.admin_gift_link, 
            F.data == "admin_gift_link"
        )
        self.dp.message.register(
            self.process_gift_user_id,
            AdminStates.waiting_gift_user_id
        )
        self.dp.message.register(
            self.process_gift_days,
            AdminStates.waiting_gift_days
        )
        self.dp.message.register(
            self.process_gift_link_days,
            AdminStates.waiting_gift_link_days
        )
        self.dp.callback_query.register(
            self.extend_key,
            F.data.startswith("extend_")
        )
        self.dp.callback_query.register(
            self.delete_key,
            F.data.startswith("delete_")
        )
        self.dp.callback_query.register(
            self.show_help_instructions,
            F.data == "help_instructions"
        )
        self.dp.callback_query.register(
            self.admin_reset_referral,
            F.data == "admin_reset_referral"
        )
        self.dp.callback_query.register(
            self.reset_user_earnings,
            F.data.startswith("reset_user_")
        )
        self.dp.callback_query.register(
            self.admin_check_user,
            F.data == "admin_check_user"
        )
        self.dp.message.register(
            self.process_check_user_id,
            AdminStates.waiting_check_user_id
        )
        self.dp.callback_query.register(
            self.accept_agreement,
            F.data == "accept_agreement"
        )
        self.dp.message.register(
            self.process_email_input,
            OrderStates.waiting_email
        )
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        user = message.from_user
        
        # Проверяем согласие с пользовательским соглашением
        if not db.has_user_agreed(user.id):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📜 Прочитать соглашение", url="https://air31cloud.ru/agreement")],
                [InlineKeyboardButton(text="✅ Принять соглашение", callback_data="accept_agreement")]
            ])
            
            await message.answer(
                "📜 <b>Пользовательское соглашение</b>\n\n"
                "Для использования VPN-сервиса необходимо принять пользовательское соглашение.\n\n"
                "🔍 Пожалуйста, ознакомьтесь с условиями и подтвердите согласие.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return
        
        # Проверяем реферальную ссылку или подарочный код
        referrer_id = None
        gift_code = None
        if len(message.text.split()) > 1:
            param = message.text.split()[1]
            if param.startswith("gift_"):
                gift_code = param
            else:
                try:
                    referrer_id = int(param)
                except ValueError:
                    pass
                
        # Добавляем пользователя в БД
        user = message.from_user
        is_new_user = not db.get_user(user.id)
        
        db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Добавляем реферала если это новый пользователь
        if is_new_user and referrer_id and referrer_id != user.id:
            if db.get_user(referrer_id):
                db.add_referral(referrer_id, user.id)
                # Уведомляем реферера
                try:
                    await self.bot.send_message(
                        referrer_id,
                        f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                        f"💰 Вы получите бонус при его первой покупке!"
                    )
                except:
                    pass
        
        # Обрабатываем подарочный код
        if gift_code:
            logger.info(f"Получен подарочный код: {gift_code} от пользователя {user.id}")
            # Проверяем, есть ли код в БД
            logger.info(f"Проверяем подарочный код в MySQL БД")
            
            days = db.use_gift_link(gift_code, user.id)
            logger.info(f"Результат использования кода: {days}")
            if days:
                # Создаем подарочный VPN ключ
                vpn_result = await self.create_gift_vpn_client(user.id, days)
                
                if vpn_result:
                    vpn_config, email, expires_at = vpn_result
                    
                    db.add_vpn_key(
                        user_id=user.id,
                        order_id=None,
                        email=email,
                        config=vpn_config,
                        expires_at=expires_at,
                        traffic_limit=0
                    )
                    
                    await message.answer(
                        f"🎁 <b>Поздравляем! Вы активировали подарочный код!</b>\n\n"
                        f"🔑 <b>Ваш VPN ключ:</b>\n"
                        f"<code>{vpn_config}</code>\n\n"
                        f"⏰ <b>Действует до:</b> {datetime.fromisoformat(expires_at).strftime('%d.%m.%Y %H:%M')}\n\n"
                        "📱 Используйте /help для инструкции по подключению",
                        parse_mode="HTML"
                    )
                    return
                else:
                    await message.answer("❌ Ошибка создания VPN ключа. Обратитесь в поддержку.")
                    return
            else:
                await message.answer("❌ Подарочный код недействителен или уже использован.")
                return
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="💳 Купить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
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
            "🔧 <b>Команды бота:</b>\n"
            "/start - Главное меню\n"
            "/profile - Мои VPN ключи\n"
            "/help - Эта справка\n\n"
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
        # Парсим: plan_PLAN_ID -> берём PLAN_ID
        plan_id = callback.data.replace("plan_", "", 1)
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
        return
    
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
            
        # Создание платежа с email
        payment = await self.create_payment(
            plan["price"], 
            f"VPN {plan['name']}",
            message.from_user.id,
            email
        )
        
        if payment:
            # Создаем заказ в БД
            order_id = db.create_order(
                user_id=message.from_user.id,
                plan_id=plan_id,
                payment_id=payment.id,
                amount=plan["price"]
            )
            
            if not order_id:
                await message.answer("❌ Ошибка создания заказа")
                return
            
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
            
    async def create_payment(self, amount: int, description: str, user_id: int, user_email: str = None) -> Optional[Payment]:
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
                "metadata": {
                    "user_id": str(user_id)
                }
            }
            
            # Добавляем чек если есть email
            if user_email:
                payment_data["receipt"] = {
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
            
            payment = Payment.create(payment_data, uuid.uuid4())
            
            logger.info(f"Создан платеж {payment.id} на сумму {amount}₽")
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
                
                # Обрабатываем реферальную выплату
                await self.process_referral_payment(user_id, order_id, plan_id)
                
                # Создаем VPN ключ
                vpn_result = await self.create_vpn_client(user_id, plan_id, callback.from_user.username)
                
                if vpn_result:
                    vpn_config, email, expires_at = vpn_result
                    
                    # Проверяем, это продление или новый ключ
                    extend_key_id = data.get("extend_key_id")
                    
                    if extend_key_id:
                        # Продление существующего ключа
                        key_data = db.extend_vpn_key(extend_key_id, VPN_PLANS[plan_id]["days"])
                        if key_data:
                            async with XrayManager(XRAY_API_URL) as xray:
                                # Проверяем, активен ли ключ и не истек ли он
                                current_expires = datetime.fromisoformat(key_data['expires_at'].replace('Z', '+00:00'))
                                is_active_and_valid = key_data['is_active'] == 1 and current_expires > datetime.now()
                                
                                if is_active_and_valid:
                                    # Ключ активен и не истек - продлеваем через extend_client
                                    await xray.extend_client(key_data['email'], current_expires, VPN_PLANS[plan_id]["days"])
                                else:
                                    # Ключ неактивен или истек - восстанавливаем через restore_client
                                    await xray.restore_client(key_data['email'], key_data['config'], VPN_PLANS[plan_id]["days"])
                            success_text = "✅ <b>Ключ успешно продлен!</b>"
                        else:
                            success_text = "❌ Ошибка продления"
                    else:
                        # Создание нового ключа
                        db.add_vpn_key(
                            user_id=user_id,
                            order_id=order_id,
                            email=email,
                            config=vpn_config,
                            expires_at=expires_at,
                            traffic_limit=0
                        )
                        logger.info(f"VPN ключ добавлен в БД для пользователя {user_id}")
                        success_text = "✅ <b>Оплата прошла успешно!</b>"
                    
                    success_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="📱 Инструкция", 
                            callback_data="help"
                        )],
                        [InlineKeyboardButton(
                            text="👤 Мои ключи", 
                            callback_data="my_keys"
                        )],
                        [InlineKeyboardButton(
                            text="🏠 Главное меню", 
                            callback_data="back_menu"
                        )]
                    ])
                    
                    if extend_key_id:
                        # Продление - показываем статус
                        await callback.message.edit_text(
                            f"{success_text}\n\n"
                            "💬 Поддержка: @support",
                            reply_markup=success_keyboard,
                            parse_mode="HTML"
                        )
                    else:
                        # Новый ключ - показываем конфигурацию
                        await callback.message.edit_text(
                            f"{success_text}\n\n"
                            f"🔑 <b>Ваш VPN ключ:</b>\n"
                            f"<code>{vpn_config}</code>\n\n"
                            "💬 Поддержка: @support",
                            reply_markup=success_keyboard,
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
            
        keyboard_buttons = []
        for i, key in enumerate(vpn_keys, 1):
            # Обработка даты с учетом разных форматов
            expires_at_str = str(key['expires_at'])
            try:
                if 'Z' in expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                else:
                    expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                # Если формат даты некорректный, считаем ключ истекшим
                expires_at = datetime.now() - timedelta(days=1)
            
            is_active = expires_at > datetime.now() and key['is_active'] == 1
            status = "✅" if is_active else "❌"
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{status} {key['email'][:20]}...", 
                callback_data=f"key_{key['id']}"
            )])
            
        keyboard_buttons.append([InlineKeyboardButton(
            text="🏠 Главное меню", 
            callback_data="back_menu"
        )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "🔑 <b>Ваши VPN ключи:</b>\n\n"
            "Нажмите на ключ для подробностей:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def show_key_details(self, callback: types.CallbackQuery):
        """Показ деталей VPN ключа"""
        key_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        vpn_keys = db.get_user_vpn_keys(user_id)
        key = next((k for k in vpn_keys if k['id'] == key_id), None)
        
        if not key:
            await callback.answer("❌ Ключ не найден")
            return
            
        # Обработка даты с учетом разных форматов
        expires_at_str = str(key['expires_at'])
        try:
            if 'Z' in expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            else:
                expires_at = datetime.fromisoformat(expires_at_str)
        except ValueError:
            # Если формат даты некорректный, считаем ключ истекшим
            expires_at = datetime.now() - timedelta(days=1)
            
        is_active = expires_at > datetime.now() and key['is_active'] == 1
        
        if key['is_active'] == 0:
            status = "❌ Удален с сервера"
        elif expires_at <= datetime.now():
            status = "❌ Истек"
        else:
            status = "✅ Активен"
        
        # Кнопки зависят от статуса ключа
        buttons = []
        if key['is_active'] == 0:
            # Ключ удален с сервера - только удалить из профиля
            buttons = [
                [InlineKeyboardButton(text="🗑 Удалить из профиля", callback_data=f"delete_{key_id}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_keys")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
            ]
        elif is_active:
            # Активный ключ - продлить или навигация
            buttons = [
                [InlineKeyboardButton(text="🔄 Продлить", callback_data=f"extend_{key_id}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_keys")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
            ]
        else:
            # Истекший ключ - продлить или удалить
            buttons = [
                [InlineKeyboardButton(text="🔄 Продлить", callback_data=f"extend_{key_id}")],
                [InlineKeyboardButton(text="🗑 Удалить из профиля", callback_data=f"delete_{key_id}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_keys")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
            ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"🔑 <b>VPN Ключ:</b> {key['email']}\n\n"
            f"📅 <b>Истекает:</b> {expires_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"🔥 <b>Трафик:</b> безлимитный\n"
            f"🔘 <b>Статус:</b> {status}\n\n"
            f"🔑 <b>Конфигурация:</b>\n"
            f"<code>{key['config']}</code>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def show_referrals(self, callback: types.CallbackQuery):
        """Показ реферальной системы"""
        user_id = callback.from_user.id
        referrals = db.get_referrals(user_id)
        bonus = db.get_total_referral_earnings(user_id)
        
        bot_username = (await self.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
        ])
        
        text = (
            f"👥 <b>Реферальная система</b>\n\n"
            f"💰 <b>Заработано:</b> {bonus}₽\n"
            f"👤 <b>Привлечено:</b> {len(referrals)} чел.\n\n"
            f"🔗 <b>Ваша ссылка:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"🎁 <b>Условия:</b>\n"
            f"• Приведите друга по ссылке\n"
            f"• Получайте бонус с каждой покупки\n"
            f"• 1мес - 20₽, 3мес - 50₽, 6мес - 90₽, 1год - 140₽\n\n"
            f"💵 <b>Выплаты:</b> от 100₽\n"
            f"💬 Обращайтесь к @MiddleCloud1 для выплаты"
        )
        
        if referrals:
            text += "\n\n👥 <b>Ваши рефералы:</b>\n"
            for ref in referrals[:5]:  # Показываем последние 5
                name = ref['username'] or ref['first_name'] or f"ID{ref['referred_id']}"
                text += f"• {name}\n"
                
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    async def show_admin_panel(self, callback: types.CallbackQuery):
        """Показ админ-панели"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
            
        stats = db.get_stats()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Подарить ключ", callback_data="admin_gift_key")],
            [InlineKeyboardButton(text="🎁 Создать подарочную ссылку", callback_data="admin_gift_link")],
            [InlineKeyboardButton(text="🔍 Проверить пользователя", callback_data="admin_check_user")],
            [InlineKeyboardButton(text="💵 Сбросить реферальные деньги", callback_data="admin_reset_referral")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
        ])
        
        text = (
            f"⚙️ <b>Админ-панель</b>\n\n"
            f"👥 Пользователей: {stats.get('total_users', 0)}\n"
            f"💳 Оплаченных заказов: {stats.get('paid_orders', 0)}\n"
            f"🔑 Активных ключей: {stats.get('active_keys', 0)}\n"
            f"💰 Общая выручка: {stats.get('total_revenue', 0)}₽"
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    async def process_referral_payment(self, user_id: int, order_id: int, plan_id: str):
        """Обработка реферальной выплаты"""
        referrer_id = db.get_referrer(user_id)
        if not referrer_id:
            return
            
        bonus_amount = REFERRAL_RATES.get(plan_id, 0)
        if bonus_amount > 0:
            # Добавляем выплату
            db.add_referral_earning(referrer_id, user_id, order_id, plan_id, bonus_amount)
            
            # Уведомляем реферера
            try:
                plan_name = VPN_PLANS[plan_id]["name"]
                await self.bot.send_message(
                    referrer_id,
                    f"🎉 Ваш реферал купил подписку!\n"
                    f"📅 Период: {plan_name}\n"
                    f"💰 Ваш бонус: {bonus_amount}₽"
                )
            except:
                pass

        
    async def back_to_menu(self, callback: types.CallbackQuery, state: FSMContext = None):
        """Возврат в главное меню"""
        if state:
            await state.clear()
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="💳 Купить VPN", callback_data="buy_vpn")],
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
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
    async def admin_gift_key(self, callback: types.CallbackQuery, state: FSMContext):
        """Начало процесса подарка ключа"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
            
        await state.set_state(AdminStates.waiting_gift_user_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(
            "🎁 <b>Подарок ключа</b>\n\n"
            "Введите Telegram ID пользователя:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def process_gift_user_id(self, message: types.Message, state: FSMContext):
        """Обработка ID пользователя для подарка"""
        try:
            user_id = int(message.text)
            await state.update_data(gift_user_id=user_id)
            await state.set_state(AdminStates.waiting_gift_days)
            
            await message.answer(
                f"🎁 <b>Подарок для пользователя {user_id}</b>\n\n"
                "Введите количество дней подписки:",
                parse_mode="HTML"
            )
        except ValueError:
            await message.answer("❌ Неверный ID. Введите число.")
            
    async def process_gift_days(self, message: types.Message, state: FSMContext):
        """Обработка количества дней для подарка"""
        try:
            days = int(message.text)
            if days <= 0:
                await message.answer("❌ Количество дней должно быть больше 0.")
                return
                
            data = await state.get_data()
            user_id = data['gift_user_id']
            
            vpn_result = await self.create_gift_vpn_client(user_id, days)
            
            if vpn_result:
                vpn_config, email, expires_at = vpn_result
                
                db.add_vpn_key(
                    user_id=user_id,
                    order_id=None,
                    email=email,
                    config=vpn_config,
                    expires_at=expires_at,
                    traffic_limit=0
                )
                
                try:
                    await self.bot.send_message(
                        user_id,
                        f"🎁 <b>Подарок от администрации!</b>\n\n"
                        f"🔑 <b>Ваш VPN ключ:</b>\n"
                        f"<code>{vpn_config}</code>\n\n"
                        f"⏰ <b>Действует до:</b> {datetime.fromisoformat(expires_at).strftime('%d.%m.%Y %H:%M')}\n\n"
                        "📱 Используйте /help для инструкции по подключению",
                        parse_mode="HTML"
                    )
                    
                    await message.answer(
                        f"✅ <b>Подарок отправлен!</b>\n\n"
                        f"👤 Пользователь: {user_id}\n"
                        f"⏰ Период: {days} дней",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    await message.answer(
                        f"❌ Ошибка отправки пользователю {user_id}: {e}\n\n"
                        f"🔑 <b>Ключ создан:</b>\n"
                        f"<code>{vpn_config}</code>",
                        parse_mode="HTML"
                    )
            else:
                await message.answer("❌ Ошибка создания VPN ключа")
                
            await state.clear()
            
        except ValueError:
            await message.answer("❌ Неверное количество дней. Введите число.")
            
    async def admin_gift_link(self, callback: types.CallbackQuery, state: FSMContext):
        """Начало создания подарочной ссылки"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
            
        await state.set_state(AdminStates.waiting_gift_link_days)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(
            "🎁 <b>Подарочная ссылка</b>\n\n"
            "Введите количество дней подписки:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def process_gift_link_days(self, message: types.Message, state: FSMContext):
        """Обработка создания подарочной ссылки"""
        try:
            days = int(message.text)
            if days <= 0:
                await message.answer("❌ Количество дней должно быть больше 0.")
                return
                
            gift_code = f"gift_{uuid.uuid4().hex[:8]}"
            
            # Сохраняем в БД
            logger.info(f"Создаем подарочный код: {gift_code} на {days} дней")
            if db.create_gift_link(gift_code, days):
                logger.info(f"Подарочный код успешно сохранен в MySQL БД")
                bot_username = (await self.bot.get_me()).username
                gift_link = f"https://t.me/{bot_username}?start={gift_code}"
                
                await message.answer(
                    f"✅ <b>Подарочная ссылка создана!</b>\n\n"
                    f"🎁 <b>Период:</b> {days} дней\n"
                    f"🔗 <b>Ссылка:</b>\n"
                    f"<code>{gift_link}</code>\n\n"
                    f"📝 <b>Код:</b> <code>{gift_code}</code>",
                    parse_mode="HTML"
                )
            else:
                logger.error(f"Ошибка сохранения кода {gift_code} в MySQL БД")
                await message.answer("❌ Ошибка создания подарочной ссылки")
            
            await state.clear()
            
        except ValueError:
            await message.answer("❌ Неверное количество дней. Введите число.")
            
    async def create_gift_vpn_client(self, user_id: int, days: int) -> Optional[tuple]:
        """Создание подарочного VPN клиента"""
        email = f"gift_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        async with XrayManager(XRAY_API_URL) as xray:
            result = await xray.add_client(email, {"days": days})
            
            if result:
                return (result["config"], result["email"], result["expires_at"])
            else:
                logger.error(f"Не удалось создать подарочный VPN клиента для {email}")
                return None
                

            
    async def extend_key(self, callback: types.CallbackQuery):
        """Продление ключа - показ тарифов"""
        key_id = int(callback.data.split("_")[1])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']}₽", 
                callback_data=f"extend_plan_{key_id}_{plan_id}"
            )]
            for plan_id, plan in VPN_PLANS.items()
        ] + [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"key_{key_id}")]
        ])
        
        await callback.message.edit_text(
            "🔄 <b>Продление ключа</b>\n\n"
            "📅 Выберите период продления:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def delete_key(self, callback: types.CallbackQuery):
        """Удаление ключа из профиля"""
        key_id = int(callback.data.split("_")[1])
        user_id = callback.from_user.id
        
        # Скрываем ключ из профиля
        if db.hide_key_from_profile(key_id):
            await callback.message.edit_text(
                "✅ <b>Ключ удален из вашего профиля</b>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👍 Ок", callback_data="my_keys")]
                ]),
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка удаления")
            
    async def process_extend_plan(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора тарифа для продления"""
        # Парсим: extend_plan_KEY_ID_PLAN_ID -> берём KEY_ID и PLAN_ID
        parts = callback.data.split("_", 2)  # Разбиваем максимум на 3 части
        key_id = int(parts[1])
        plan_id = parts[2]  # Всё остальное - это план_id
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await callback.answer("❌ Неверный тариф")
            return
            
        # Создание платежа для продления
        payment = await self.create_payment(
            plan["price"], 
            f"VPN продление {plan['name']}",
            callback.from_user.id
        )
        
        if payment:
            # Создаем заказ на продление
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
                order_id=order_id,
                extend_key_id=key_id  # Для продления
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
                )],
                [InlineKeyboardButton(
                    text="⬅️ Назад", 
                    callback_data=f"key_{key_id}"
                )]
            ])
            
            await callback.message.edit_text(
                f"🔄 <b>Продление VPN ключа</b>\n\n"
                f"💰 <b>К оплате:</b> {plan['price']}₽\n"
                f"📦 <b>Период:</b> {plan['name']}\n"
                f"⏰ <b>Срок:</b> {plan['days']} дней\n\n"
                "Нажмите кнопку для оплаты:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка создания платежа")
    
    async def show_help_instructions(self, callback: types.CallbackQuery):
        """Показ инструкций по подключению"""
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
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
        ])
        
        await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="HTML")
    
    async def admin_reset_referral(self, callback: types.CallbackQuery):
        """Сброс реферальных денег пользователя"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
        
        # Получаем список пользователей с реферальными деньгами
        users_with_earnings = db.get_users_with_referral_earnings()
        
        if not users_with_earnings:
            await callback.message.edit_text(
                "💵 Нет пользователей с реферальными деньгами",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
                ])
            )
            return
        
        # Создаем кнопки для каждого пользователя
        buttons = []
        for user in users_with_earnings[:10]:  # Показываем первых 10
            name = user['username'] or user['first_name'] or f"ID{user['telegram_id']}"
            buttons.append([InlineKeyboardButton(
                text=f"{name} - {user['total_earnings']}₽",
                callback_data=f"reset_user_{user['telegram_id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            "💵 <b>Сброс реферальных денег</b>\n\n"
            "Выберите пользователя:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    async def admin_check_user(self, callback: types.CallbackQuery, state: FSMContext):
        """Начало проверки пользователя"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
            
        await state.set_state(AdminStates.waiting_check_user_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(
            "🔍 <b>Проверка пользователя</b>\n\n"
            "Введите Telegram ID пользователя:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    async def process_check_user_id(self, message: types.Message, state: FSMContext):
        """Обработка ID пользователя для проверки"""
        try:
            user_id = int(message.text)
            user_info = db.get_user(user_id)
            
            if not user_info:
                await message.answer("❌ Пользователь не найден")
                return
            
            earnings = db.get_total_referral_earnings(user_id)
            referrals = db.get_referrals(user_id)
            vpn_keys = db.get_user_vpn_keys(user_id)
            
            name = user_info['username'] or user_info['first_name'] or f"ID{user_id}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💵 Сбросить деньги", callback_data=f"reset_user_{user_id}")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
            ])
            
            await message.answer(
                f"👤 <b>Пользователь:</b> {name}\n"
                f"🆔 <b>ID:</b> {user_id}\n"
                f"💰 <b>Реферальные деньги:</b> {earnings}₽\n"
                f"👥 <b>Привлечено рефералов:</b> {len(referrals)}\n"
                f"🔑 <b>VPN ключей:</b> {len(vpn_keys)}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            await state.clear()
            
        except ValueError:
            await message.answer("❌ Неверный ID. Введите число.")
    
    async def reset_user_earnings(self, callback: types.CallbackQuery):
        """Сброс реферальных денег конкретного пользователя"""
        if callback.from_user.id not in ADMIN_IDS:
            await callback.answer("❌ Доступ запрещен")
            return
        
        user_id = int(callback.data.split("_")[2])
        
        # Получаем сумму до сброса
        earnings = db.get_total_referral_earnings(user_id)
        
        if db.reset_user_referral_earnings(user_id):
            user_info = db.get_user(user_id)
            name = user_info['username'] or user_info['first_name'] or f"ID{user_id}"
            
            await callback.message.edit_text(
                f"✅ <b>Реферальные деньги сброшены!</b>\n\n"
                f"👤 Пользователь: {name}\n"
                f"💰 Сумма: {earnings}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]
                ]),
                parse_mode="HTML"
            )
            # Уведомляем пользователя о сбросе
            try:
                await self.bot.send_message(
                    user_id,
                    f"💵 Ваши реферальные деньги ({earnings}₽) были выплачены.\n"
                    f"💬 По вопросам обращайтесь: @MiddleCloud1"
                )
            except:
                pass
        else:
            await callback.answer("❌ Ошибка сброса")
            
    async def accept_agreement(self, callback: types.CallbackQuery):
        """Принятие пользовательского соглашения"""
        user_id = callback.from_user.id
        
        if db.accept_user_agreement(user_id):
            await callback.message.edit_text(
                "✅ <b>Соглашение принято!</b>\n\n"
                "🎉 Добро пожаловать в VPN-сервис AirCloud!\n\n"
                "Нажмите /start для продолжения.",
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Ошибка принятия соглашения")
                
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