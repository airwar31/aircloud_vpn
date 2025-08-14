import logging
import asyncio
from datetime import datetime, timedelta
from utils import safe_edit_message

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUBSCRIPTION_PLANS, ADMIN_IDS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from database import Database
from xray_api import XrayAPI
from payments.yookassa_integration import YooKassaPayment

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Инициализация сервисов
db = Database()
xray = XrayAPI()  # Теперь использует Xray-core API
payment_service = YooKassaPayment(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)

# Состояния для FSM
class UserStates(StatesGroup):
    start = State()
    select_plan = State()
    payment = State()
    waiting_payment = State()
    admin_give_subscription = State()
    admin_select_plan = State()

# Клавиатуры
def get_main_keyboard(has_subscription=False):
    """Получение основной клавиатуры"""
    if has_subscription:
        keyboard = [
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="📱 VPN ключ", callback_data="show_key")],
            [InlineKeyboardButton(text="⏰ Продлить подписку", callback_data="extend")],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="💳 Купить подписку", callback_data="select_plan")],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_plans_keyboard():
    """Получение клавиатуры с тарифными планами"""
    keyboard = []
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        # Обратная совместимость с старыми планами
        price = plan.get('base_price', plan.get('price', 0))
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - от {price} ₽", 
                callback_data=f"select_devices_{plan_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_devices_keyboard(plan_id: str):
    """Клавиатура выбора количества устройств"""
    from config import calculate_plan_price, DEVICE_PRICING
    
    keyboard = []
    
    for devices in DEVICE_PRICING.keys():
        price = calculate_plan_price(plan_id, devices)
        device_text = "📱" if devices == 1 else f"📱x{devices}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{device_text} - {price} ₽",
                callback_data=f"buy_{plan_id}_{devices}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="select_plan")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(payment_url, payment_id):
    """Получение клавиатуры для оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = message.from_user
    
    # Проверяем, что это не бот и не канал
    if user.is_bot or user.id < 0:
        logger.warning(f"Отклонен запрос от бота/канала: {user.id}")
        return
    
    logger.info(f"Пользователь {user.id} ({user.first_name}) запустил бота")
    
    await db.create_user(user.id, user.username, user.first_name, user.last_name)
    subscription = await db.get_user_subscription(user.id)
    
    if subscription and subscription['active']:
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await message.answer(
            f"🎉 Привет, {user.first_name}!\n\n"
            f"✅ У вас активная подписка\n"
            f"📅 До: {expiry_date.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось: {days_left} дней",
            reply_markup=get_main_keyboard(has_subscription=True)
        )
    else:
        await message.answer(
            f"👋 Привет, {user.first_name}!\n\n"
            f"🚀 Добро пожаловать в AirCloud VPN\n"
            f"🔒 Быстрый и безопасный VPN на базе Xray\n\n"
            f"💡 Выберите действие:",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
    
    await state.set_state(UserStates.start)

# Обработчики callback'ов
@router.callback_query(F.data == "select_plan")
async def select_plan_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифного плана"""
    if callback.from_user.is_bot:
        return
        
    plans_text = "💳 Выберите тарифный план:\n\n"
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        # Обратная совместимость
        price = plan.get('base_price', plan.get('price', 0))
        
        plans_text += f"📦 {plan['name']}\n"
        plans_text += f"💰 от {price} ₽\n"
        plans_text += f"📅 {plan['duration']} дней\n"
        plans_text += f"🚀 Безлимитный трафик\n\n"
    
    await callback.message.edit_text(
        plans_text,
        reply_markup=get_plans_keyboard()
    )
    await state.set_state(UserStates.select_plan)

@router.callback_query(F.data.startswith("select_devices_"))
async def select_devices_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор количества устройств"""
    if callback.from_user.is_bot:
        return
        
    plan_id = callback.data.split("_")[2]
    
    if plan_id not in SUBSCRIPTION_PLANS:
        await callback.answer("❌ Неверный тариф")
        return
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    
    # Обратная совместимость
    base_price = plan.get('base_price', plan.get('price', 0))
    
    devices_text = (
        f"📦 {plan['name']}\n\n"
        f"📱 Выберите количество устройств:\n\n"
        f"💰 Базовая цена: {base_price} ₽\n"
        f"➕ Доплата за каждое доп. устройство"
    )
    
    await callback.message.edit_text(
        devices_text,
        reply_markup=get_devices_keyboard(plan_id)
    )
    await state.set_state(UserStates.select_plan)

@router.callback_query(F.data.startswith("buy_"))
async def buy_plan_callback(callback: CallbackQuery, state: FSMContext):
    """Покупка выбранного плана с устройствами"""
    if callback.from_user.is_bot:
        return
        
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Неверные данные")
        return
        
    plan_id = parts[1]
    devices = int(parts[2])
    
    if plan_id not in SUBSCRIPTION_PLANS:
        await callback.answer("❌ Неверный тариф")
        return
    
    from config import calculate_plan_price
    plan = SUBSCRIPTION_PLANS[plan_id]
    price = calculate_plan_price(plan_id, devices)
    user_id = callback.from_user.id
    
    # Создаем платеж
    payment_result = payment_service.create_payment(
        amount=price,
        description=f"Подписка {plan['name']} ({devices} устр.) - AirCloud VPN",
        user_id=user_id,
        plan_id=f"{plan_id}_{devices}"
    )
    
    if payment_result['success']:
        # Сохраняем информацию о платеже
        await db.create_payment(
            user_id=user_id,
            amount=price,
            payment_id=payment_result['payment_id'],
            plan_id=f"{plan_id}_{devices}"
        )
        
        await state.update_data(
            payment_id=payment_result['payment_id'],
            plan_id=plan_id,
            devices=devices
        )
        
        device_text = "📱 1 устройство" if devices == 1 else f"📱 {devices} устройств"
        
        await callback.message.edit_text(
            f"💳 Оплата подписки\n\n"
            f"📦 План: {plan['name']}\n"
            f"{device_text}\n"
            f"💰 Сумма: {price} ₽\n"
            f"📅 Срок: {plan['duration']} дней\n\n"
            f"👆 Нажмите кнопку для оплаты",
            reply_markup=get_payment_keyboard(
                payment_result['payment_url'], 
                payment_result['payment_id']
            )
        )
        await state.set_state(UserStates.waiting_payment)
    else:
        await callback.answer("❌ Ошибка создания платежа")

@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_callback(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    payment_id = callback.data.split("_")[2]
    
    payment_status = payment_service.check_payment_status(payment_id)
    
    if payment_status['success'] and payment_status['paid']:
        # Платеж успешен, активируем подписку
        user_id = callback.from_user.id
        data = await state.get_data()
        plan_id = data.get('plan_id')
        
        if plan_id:
            plan = SUBSCRIPTION_PLANS[plan_id]
            
            # Получаем данные о количестве устройств
            data = await state.get_data()
            devices = data.get('devices', 1)
            
            # Получаем внутренний user_id по telegram_id
            internal_user_id = await db.create_user(user_id, callback.from_user.username, 
                                                   callback.from_user.first_name, callback.from_user.last_name)
            
            # Создаем подписку с указанным количеством устройств
            subscription = await db.create_subscription(
                user_id=internal_user_id,
                plan_id=plan_id,
                duration_days=plan['duration'],
                devices=devices
            )
            
            # Создаем конфигурацию Xray
            xray_config = await xray.create_user_config(user_id)
            if xray_config['success']:
                await db.update_subscription_xray_uuid(
                    subscription['id'], 
                    xray_config['uuid']
                )
            
            # Обновляем статус платежа
            await db.update_payment_status(payment_id, 'succeeded')
            
            device_text = "📱 1 устройство" if devices == 1 else f"📱 {devices} устройств"
            
            await callback.message.edit_text(
                f"✅ Платеж успешно обработан!\n\n"
                f"🎉 Подписка активирована\n"
                f"📦 План: {plan['name']}\n"
                f"{device_text}\n"
                f"📅 Срок: {plan['duration']} дней\n\n"
                f"🔑 Получите ваш VPN ключ:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 Получить ключ", callback_data="show_key")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
            await state.set_state(UserStates.start)
        else:
            await callback.answer("❌ Ошибка обработки платежа")
    else:
        await callback.answer("⏳ Платеж еще не обработан")

@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    """Профиль пользователя"""
    user_id = callback.from_user.id
    user = callback.from_user
    subscription = await db.get_user_subscription(user_id)
    user_stats = await db.get_user_stats(user_id)
    
    # Основная информация о пользователе
    reg_date = "Неизвестно"
    if user_stats and user_stats.get('registration_date'):
        try:
            # Пробуем разные форматы даты
            reg_str = user_stats['registration_date']
            if isinstance(reg_str, str):
                # SQLite формат: 2024-01-15 12:30:45
                if ' ' in reg_str:
                    reg_datetime = datetime.strptime(reg_str, '%Y-%m-%d %H:%M:%S')
                else:
                    reg_datetime = datetime.fromisoformat(reg_str)
                reg_date = reg_datetime.strftime('%d.%m.%Y')
        except Exception as e:
            logger.error(f"Ошибка парсинга даты: {e}")
            reg_date = "Неизвестно"
    
    profile_text = (
        f"👤 Мой профиль\n\n"
        f"📝 Имя: {user.first_name or 'Не указано'}\n"
        f"🆔 Username: @{user.username or 'нет'}\n"
        f"🆔 ID: `{user_id}`\n"
        f"📅 Регистрация: {reg_date}\n\n"
    )
    
    if subscription and subscription['active']:
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        plan_name = SUBSCRIPTION_PLANS.get(subscription['plan_id'], {}).get('name', 'Неизвестно')
        
        # Статус подписки
        if days_left > 7:
            status_emoji = "✅"
            status_text = "Активна"
        elif days_left > 0:
            status_emoji = "⚠️"
            status_text = "Скоро истекает"
        else:
            status_emoji = "❌"
            status_text = "Неактивна"
        
        profile_text += (
            f"💳 Подписка:\n"
            f"{status_emoji} Статус: {status_text}\n"
            f"📦 План: {plan_name}\n"
            f"📅 До: {expiry_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏳ Осталось: {days_left} дней\n\n"
        )
        
        # VPN ключ
        if subscription['xray_uuid']:
            config = await xray.get_user_config(subscription['xray_uuid'])
            if config['success']:
                # Показываем сокращенный ключ
                short_key = config['config'][:50] + "..." if len(config['config']) > 50 else config['config']
                profile_text += f"🔑 VPN ключ:\n`{short_key}`\n\n"
        
        # Статистика использования
        profile_text += (
            f"📈 Статистика:\n"
            f"📁 Трафик: Неограничен\n"
            f"🌍 Сервер: Онлайн\n"
            f"🔒 Шифрование: AES-256\n\n"
            f"📊 Общая статистика:\n"
            f"📦 Подписок: {user_stats.get('total_subscriptions', 0) if user_stats else 0}\n"
            f"💰 Потрачено: {user_stats.get('total_spent', 0) if user_stats else 0} ₽"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="📱 Полный ключ", callback_data="show_key")],
            [InlineKeyboardButton(text="⏰ Продлить", callback_data="extend")],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ]
    else:
        profile_text += (
            f"❌ Подписка: Неактивна\n\n"
            f"📊 Общая статистика:\n"
            f"📦 Подписок: {user_stats.get('total_subscriptions', 0) if user_stats else 0}\n"
            f"💰 Потрачено: {user_stats.get('total_spent', 0) if user_stats else 0} ₽\n\n"
            f"💳 Купите подписку для получения доступа к VPN"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="💳 Купить подписку", callback_data="select_plan")],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ]
    
    await callback.message.edit_text(
        profile_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "show_key")
async def show_key_callback(callback: CallbackQuery):
    """Показать VPN ключ пользователя"""
    user_id = callback.from_user.id
    subscription = await db.get_user_subscription(user_id)
    
    if not subscription or not subscription['active']:
        await callback.answer("❌ У вас нет активной подписки")
        return
    
    if subscription['xray_uuid']:
        config = await xray.get_user_config(subscription['xray_uuid'])
        
        if config['success']:
            await callback.message.edit_text(
                f"🔑 Ваш VPN ключ:\n\n"
                f"```\n{config['config']}\n```\n\n"
                f"📱 Скопируйте ключ и добавьте в приложение\n"
                f"📖 Инструкция по настройке: /instructions",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📖 Инструкция", callback_data="instructions")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
                ])
            )
        else:
            await callback.answer("❌ Ошибка получения конфигурации")
    else:
        await callback.answer("❌ Конфигурация не найдена")

@router.callback_query(F.data == "status")
async def status_callback(callback: CallbackQuery):
    """Показать статус подписки"""
    user_id = callback.from_user.id
    subscription = await db.get_user_subscription(user_id)
    
    if subscription and subscription['active']:
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await callback.message.edit_text(
            f"📊 Статус подписки:\n\n"
            f"✅ Активна\n"
            f"📅 До: {expiry_date.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось: {days_left} дней\n"
            f"📦 План: {subscription.get('plan_id', 'Неизвестно')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏰ Продлить", callback_data="extend")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
            ])
        )
    else:
        await callback.message.edit_text(
            f"❌ У вас нет активной подписки\n\n"
            f"💡 Выберите тарифный план:",
            reply_markup=get_plans_keyboard()
        )

@router.callback_query(F.data == "extend")
async def extend_callback(callback: CallbackQuery, state: FSMContext):
    """Продление подписки"""
    await select_plan_callback(callback, state)

@router.callback_query(F.data == "instructions")
async def instructions_callback(callback: CallbackQuery):
    """Инструкция по настройке"""
    instructions_text = (
        "📖 Инструкция по настройке VPN:\n\n"
        "📱 Android:\n"
        "1. Скачайте v2rayNG из Google Play\n"
        "2. Нажмите + и выберите 'Импорт из буфера'\n"
        "3. Вставьте ваш ключ\n\n"
        "🍎 iOS:\n"
        "1. Скачайте Shadowrocket из App Store\n"
        "2. Нажмите + в правом верхнем углу\n"
        "3. Выберите 'Paste' и вставьте ключ\n\n"
        "💻 Windows:\n"
        "1. Скачайте v2rayN с GitHub\n"
        "2. Добавьте сервер через буфер обмена\n\n"
        "🖥 macOS:\n"
        "1. Скачайте V2rayU из App Store\n"
        "2. Импортируйте конфигурацию"
    )
    
    await callback.message.edit_text(
        instructions_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
    )

@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    """Поддержка"""
    await callback.message.edit_text(
        f"💬 Поддержка AirCloud VPN\n\n"
        f"📧 Email: support@aircloud-vpn.com\n"
        f"💬 Telegram: @aircloud_support\n\n"
        f"⏰ Время работы: 24/7\n"
        f"⚡ Среднее время ответа: 15 минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ])
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    if callback.from_user.is_bot:
        return
        
    user = callback.from_user
    subscription = await db.get_user_subscription(user.id)
    
    if subscription and subscription['active']:
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await callback.message.edit_text(
            f"🎉 Привет, {user.first_name}! У вас есть активная подписка.\n"
            f"📅 Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"⏳ Осталось дней: {days_left}",
            reply_markup=get_main_keyboard(has_subscription=True)
        )
    else:
        await callback.message.edit_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"🚀 Добро пожаловать в AirCloud VPN\n"
            f"🔒 Быстрый и безопасный VPN на базе Xray\n\n"
            f"💡 Выберите действие:",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
    
    await state.set_state(UserStates.start)

@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена операции"""
    await back_to_main_callback(callback, state)

@router.callback_query(F.data.startswith("admin_"))
async def admin_callback_handler(callback: CallbackQuery):
    """Обработчик для необработанных админ callback'ов"""
    # Перенаправляем на админ панель
    pass

@router.callback_query()
async def unknown_callback_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик для неизвестных callback'ов"""
    await callback.answer("❌ Неизвестная команда")
    await back_to_main_callback(callback, state)

# Административные команды
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Административная панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    stats = await db.get_stats()
    
    admin_text = (
        f"👑 Административная панель\n\n"
        f"👥 Пользователей: {stats.get('users', 0)}\n"
        f"✅ Активных подписок: {stats.get('active_subscriptions', 0)}\n"
        f"💰 Доход за месяц: {stats.get('monthly_revenue', 0)} ₽\n\n"
        f"Команды:\n"
        f"/give_subscription <user_id> - Выдать подписку\n"
        f"/users - Список пользователей\n"
        f"/stats - Подробная статистика"
    )
    
    await message.answer(admin_text)

# Middleware для фильтрации ботов
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable

class BotFilterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем сообщения от ботов и каналов
        if hasattr(event, 'from_user') and event.from_user:
            # Пропускаем ботов
            if event.from_user.is_bot:
                return
            # Пропускаем каналы (отрицательные ID)
            if event.from_user.id < 0:
                return
        
        # Пропускаем сообщения из каналов
        if hasattr(event, 'chat') and event.chat and event.chat.id < 0:
            return
            
        return await handler(event, data)

# Подключаем middleware
dp.message.middleware(BotFilterMiddleware())
dp.callback_query.middleware(BotFilterMiddleware())

# Регистрация роутеров
dp.include_router(router)

# Подключаем админ панель
import admin_panel
dp.include_router(admin_panel.router)

async def main():
    """Запуск бота"""
    logger.info("Запуск бота...")
    
    # Запускаем мониторинг устройств в фоновом режиме
    from device_monitor import device_monitor
    monitoring_task = asyncio.create_task(device_monitor.start_monitoring())
    
    try:
        await dp.start_polling(bot)
    finally:
        device_monitor.stop_monitoring()
        monitoring_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())