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

class AdminStates(StatesGroup):
    waiting_gift_user_id = State()
    waiting_gift_days = State()
    waiting_gift_link_days = State()

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
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
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
            days = db.use_gift_link(gift_code, user.id)
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
                        f"⏰ <b>Действует до:</b> {expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
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
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
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
                )],
                [InlineKeyboardButton(
                    text="⬅️ Назад", 
                    callback_data="back_menu"
                )]
            ])
            
            await callback.message.edit_text(
                f"💰 <b>К оплате:</b> {plan['price']}₽\n"
                f"📦 <b>Тариф:</b> {plan['name']}\n"
                f"⏰ <b>Срок:</b> {plan['days']} дней\n"
                f"🔥 <b>Трафик:</b> безлимитный\n\n"
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
                
                # Обрабатываем реферальную выплату
                await self.process_referral_payment(user_id, order_id, plan_id)
                
                # Создаем VPN ключ
                vpn_result = await self.create_vpn_client(user_id, plan_id, callback.from_user.username)
                
                if vpn_result:
                    vpn_config, email, expires_at = vpn_result
                    
                    # Сохраняем VPN ключ в БД
                    db.add_vpn_key(
                        user_id=user_id,
                        order_id=order_id,
                        email=email,
                        config=vpn_config,
                        expires_at=expires_at,
                        traffic_limit=0
                    )
                    
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
                    
                    await callback.message.edit_text(
                        "✅ <b>Оплата прошла успешно!</b>\n\n"
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
            expires_at = datetime.fromisoformat(key['expires_at'].replace('Z', '+00:00'))
            status = "✅" if expires_at > datetime.now() else "❌"
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
            
        expires_at = datetime.fromisoformat(key['expires_at'].replace('Z', '+00:00'))
        status = "✅ Активен" if expires_at > datetime.now() else "❌ Истек"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="my_keys")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_menu")]
        ])
        
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
            f"• 1мес - 25₽, 3мес - 60₽, 6мес - 100₽, 1год - 150₽"
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
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
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
                        f"⏰ <b>Действует до:</b> {expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
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
            if db.create_gift_link(gift_code, days):
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