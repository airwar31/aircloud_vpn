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
    selecting_period = State()
    selecting_devices = State()
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
            self.process_period_selection, 
            F.data.startswith("period_")
        )
        self.dp.callback_query.register(
            self.process_device_selection, 
            F.data.startswith("device_")
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
        
    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        # Проверяем реферальную ссылку
        referrer_id = None
        if len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
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
        
        # Основные кнопки тарифов
        keyboard_buttons = [
            [InlineKeyboardButton(
                text=f"{period['name']} - от {period['base_price']}₽", 
                callback_data=f"period_{period_id}"
            )]
            for period_id, period in BASE_PLANS.items()
        ]
        
        # Обычные кнопки
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
        ])
        
        # Кнопка админ-панели для админов
        if user.id in ADMIN_IDS:
            keyboard_buttons.append([
                InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN\n"
            "⚡ Безлимитный трафик\n"
            "🔒 Максимальная безопасность\n\n"
            "📅 <b>Шаг 1:</b> Выберите срок подписки:",
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
        
    async def process_period_selection(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора периода подписки"""
        period_id = callback.data.split("_")[1]
        period = BASE_PLANS.get(period_id)
        
        if not period:
            await callback.answer("❌ Неверный период")
            return
            
        await state.update_data(period_id=period_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{device['name']} (+{device['extra_price']}₽)", 
                callback_data=f"device_{period_id}_{device_count}"
            )]
            for device_count, device in DEVICE_PLANS.items()
        ] + [
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_menu")]
        ])
        
        await callback.message.edit_text(
            f"📅 <b>Выбрано:</b> {period['name']}\n"
            f"💰 <b>Базовая цена:</b> {period['base_price']}₽\n\n"
            f"📱 <b>Шаг 2:</b> Выберите количество устройств:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def process_device_selection(self, callback: types.CallbackQuery, state: FSMContext):
        """Обработка выбора количества устройств"""
        parts = callback.data.split("_")
        period_id = parts[1]
        device_count = int(parts[2])
        
        period = BASE_PLANS.get(period_id)
        device_plan = DEVICE_PLANS.get(device_count)
        
        if not period or not device_plan:
            await callback.answer("❌ Неверные параметры")
            return
            
        total_price = calculate_price(period_id, device_count)
        plan_id = f"{period_id}_{device_count}dev"
            
        await state.update_data(
            period_id=period_id,
            device_count=device_count,
            plan_id=plan_id
        )
            
        # Создание платежа в ЮKassa
        payment = await self.create_payment(
            total_price, 
            f"VPN {period['name']} ({device_plan['name']})",
            callback.from_user.id
        )
        
        if payment:
            # Создаем заказ в БД
            order_id = db.create_order(
                user_id=callback.from_user.id,
                plan_id=plan_id,
                payment_id=payment.id,
                amount=total_price
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
                f"💰 <b>К оплате:</b> {total_price}₽\n"
                f"📅 <b>Период:</b> {period['name']}\n"
                f"📱 <b>Устройств:</b> {device_plan['name']}\n"
                f"⏰ <b>Срок:</b> {period['days']} дней\n"
                f"🔥 <b>Трафик:</b> безлимитный\n\n"
                f"💳 Базовая цена: {period['base_price']}₽\n"
                f"📱 Доплата за устройства: +{device_plan['extra_price']}₽\n\n"
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
                period_id = data.get("period_id")
                await self.process_referral_payment(user_id, order_id, period_id)
                
                # Создаем VPN ключ
                device_count = data.get("device_count", 1)
                vpn_result = await self.create_vpn_client(user_id, period_id, device_count, callback.from_user.username)
                
                if vpn_result:
                    vpn_config, email, expires_at = vpn_result
                    
                    # Сохраняем VPN ключ в БД
                    db.add_vpn_key(
                        user_id=user_id,
                        order_id=order_id,
                        email=email,
                        config=vpn_config,
                        expires_at=expires_at,
                        traffic_limit=0,  # Безлимитный
                        device_limit=device_count
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
            
    async def create_vpn_client(self, user_id: int, period_id: str, device_count: int, username: str = None) -> Optional[tuple]:
        """Создание VPN клиента через Xray API"""
        period = BASE_PLANS[period_id]
        plan = {
            "days": period["days"],
            "device_limit": device_count
        }
        
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
            f"📱 <b>Лимит устройств:</b> {key.get('device_limit', 1)}\n"
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
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="🔑 VPN ключи", callback_data="admin_keys")],
            [InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments")],
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
        
    async def process_referral_payment(self, user_id: int, order_id: int, period_id: str):
        """Обработка реферальной выплаты"""
        referrer_id = db.get_referrer(user_id)
        if not referrer_id:
            return
            
        bonus_amount = REFERRAL_RATES.get(period_id, 0)
        if bonus_amount > 0:
            # Добавляем выплату
            db.add_referral_earning(referrer_id, user_id, order_id, period_id, bonus_amount)
            
            # Уведомляем реферера
            try:
                period_name = BASE_PLANS[period_id]["name"]
                await self.bot.send_message(
                    referrer_id,
                    f"🎉 Ваш реферал купил подписку!\n"
                    f"📅 Период: {period_name}\n"
                    f"💰 Ваш бонус: {bonus_amount}₽"
                )
            except:
                pass

        
    async def back_to_menu(self, callback: types.CallbackQuery, state: FSMContext = None):
        """Возврат в главное меню"""
        if state:
            await state.clear()
        
        # Основные кнопки
        keyboard_buttons = [
            [InlineKeyboardButton(
                text=f"{period['name']} - от {period['base_price']}₽", 
                callback_data=f"period_{period_id}"
            )]
            for period_id, period in BASE_PLANS.items()
        ]
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")]
        ])
        
        # Кнопка админ-панели для админов
        if callback.from_user.id in ADMIN_IDS:
            keyboard_buttons.append([
                InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "🚀 <b>Добро пожаловать в VPN бот!</b>\n\n"
            "🔐 Быстрый и надежный VPN\n"
            "⚡ Безлимитный трафик\n"
            "🔒 Максимальная безопасность\n\n"
            "📅 <b>Шаг 1:</b> Выберите срок подписки:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
                
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