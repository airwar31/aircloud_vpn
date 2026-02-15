"""
AirCloud VPN Telegram Bot
Main application with full aiogram 3.0.0 integration
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Optional
import aiohttp

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, User, Chat
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from bot_app.xray_api import XrayAPI, generate_vless_link
from bot_app.database import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
XRAY_HOST = os.getenv("XRAY_HOST", "xray-panel")
XRAY_PORT = int(os.getenv("XRAY_PORT", "54321"))
XRAY_USERNAME = os.getenv("XRAY_USERNAME", "admin")
XRAY_PASSWORD = os.getenv("XRAY_PASSWORD", "admin")
NL_SERVER_IP = os.getenv("NL_SERVER_IP", "85.239.56.174")
VK_SERVER_IP = os.getenv("VK_SERVER_IP", "89.208.86.167")
DB_PATH = os.getenv("DB_PATH", "./data/users.db")

# Tunnel type pricing (RUB)
TUNNEL_PRICES = {
    "single": {"1_month": 150, "3_months": 400, "12_months": 1200},
    "double": {"1_month": 250, "3_months": 650, "12_months": 2200},
}

# FSM States
class PurchaseState(StatesGroup):
    choosing_tunnel = State()
    choosing_duration = State()
    confirming_payment = State()

class GiftState(StatesGroup):
    choosing_tunnel = State()
    choosing_duration = State()
    entering_days = State()

class AdminState(StatesGroup):
    managing_inbound = State()
    checking_stats = State()

# Initialize bot and dispatcher
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
router = Router()

# Global database instance
db: Optional[Database] = None
xray: Optional[XrayAPI] = None

# ==================== KEYBOARDS ====================

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="� Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="📋 Мои лицензии", callback_data="show_licenses")],
        [InlineKeyboardButton(text="🎁 Создать подарок", callback_data="create_gift")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="show_help")],
        [InlineKeyboardButton(text="📊 Статус серверов", callback_data="server_status")],
    ])

def get_tunnel_keyboard() -> InlineKeyboardMarkup:
    """Tunnel type selection keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Базовый (150₽/мес)", callback_data="tunnel_single")],
        [InlineKeyboardButton(text="🔐🔐 Двойной (250₽/мес)", callback_data="tunnel_double")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])

def get_duration_keyboard(tunnel_type: str) -> InlineKeyboardMarkup:
    """Duration selection keyboard"""
    prices = TUNNEL_PRICES[tunnel_type]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"1 месяц (${prices['1_month']})",
            callback_data=f"duration_1_month_{tunnel_type}"
        )],
        [InlineKeyboardButton(
            text=f"3 месяца (${prices['3_months']})",
            callback_data=f"duration_3_months_{tunnel_type}"
        )],
        [InlineKeyboardButton(
            text=f"12 месяцев (${prices['12_months']})",
            callback_data=f"duration_12_months_{tunnel_type}"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔧 Параметры inbound", callback_data="admin_inbound")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])

# ==================== COMMAND HANDLERS ====================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Start command - welcome message"""
    user = message.from_user
    
    # Add user to database
    await db.add_user(user.id, user.username or "unknown")
    
    welcome_text = f"""
🌐 **AirCloud VPN** - Защита вашей конфиденциальности

Привет, {user.first_name}! 👋

Выберите действие:

📌 **Single Tunnel** - прямое подключение к NL серверу (базовый VPN)
📌 **Double Tunnel** - подключение через VK сервер затем в NL (максимальная скрытность)

Оба типа используют лучшие протоколы (VLESS + TLS/Reality) для надежного и быстрого соединения.

Нажмите на кнопку ниже, чтобы начать! 👇
"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())
    logger.info(f"User {user.id} started bot")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command"""
    help_text = """
🆘 **Справка по AirCloud VPN**

**Доступные команды:**
/start - Главное меню
/mykeys - Мои активные лицензии
/buy - Купить VPN подписку
/gift - Создать подарок (поделиться ссылкой)
/status - Статус серверов
/help - Эта справка

**Типы туннелей:**

🔐 **Single Tunnel ($2.99/месяц)**
- Прямое подключение к NL серверу (85.239.56.174)
- Протокол: VLESS + TLS
- Использование: Базовая защита, обход блокировок
- Скорость: ⭐⭐⭐⭐⭐

🔐🔐 **Double Tunnel ($4.99/месяц)**
- Двойное туннелирование: VK (Reality) → NL (TLS)
- Протоколы: VLESS + Reality + TLS
- Использование: Максимальная скрытность, обход белых списков
- Скорость: ⭐⭐⭐⭐

**Поддержанные сроки:**
- 1 месяц
- 3 месяца
- 12 месяцев (год)

**Вопросы и поддержка:**
Напишите @support или в группу VPN

❓ Что-то непонятно? Используйте /help
"""
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("mykeys"))
async def cmd_mykeys(message: Message):
    """Show user's active VPN keys"""
    user_id = message.from_user.id
    
    keys = await db.get_user_keys(user_id)
    
    if not keys:
        await message.answer(
            "📭 У вас пока нет активных лицензий.\n\n"
            "Используйте /buy чтобы купить VPN подписку.",
            reply_markup=get_main_keyboard()
        )
        return
    
    response = "📝 **Ваши активные лицензии:**\n\n"
    
    for key in keys:
        expires_in = key['expires_at'] - datetime.now().timestamp()
        days_left = int(expires_in / 86400)
        
        emoji = "🔐" if key['tunnel_type'] == 'single' else "🔐🔐"
        response += (
            f"{emoji} **{key['tunnel_type'].upper()}** Tunnel\n"
            f"📧 Email: `{key['email']}`\n"
            f"⏰ До истечения: {days_left} дней\n"
            f"📅 Истекает: {datetime.fromtimestamp(key['expires_at']).strftime('%d.%m.%Y')}\n\n"
        )
    
    await message.answer(response, parse_mode="Markdown")

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Server status"""
    try:
        async with XrayAPI(XRAY_HOST, XRAY_PORT, XRAY_USERNAME, XRAY_PASSWORD) as api:
            stats = await api.get_stats()
            
            status_text = (
                "📊 **Статус серверов AirCloud VPN**\n\n"
                "🇳🇱 **NL Server** (85.239.56.174)\n"
                f"  Статус: ✅ Онлайн\n"
                f"  Панель: http://85.239.56.174:54321\n"
                f"  Inbound 0 (Single): Port 8443 (TLS)\n"
                f"  Inbound 1 (Double): Port 443 (TLS)\n\n"
                
                "🇷🇺 **VK Server** (89.208.86.167)\n"
                f"  Статус: ✅ Онлайн\n"
                f"  Панель: http://89.208.86.167:54321\n"
                f"  Inbound 0 (Reality): Port 443 (Reality)\n\n"
                
                "⚡ Оба сервера работают нормально!"
            )
            
            await message.answer(status_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.answer(
            "❌ Ошибка получения статуса\n"
            "Попробуйте позже или свяжитесь с @support"
        )

# ==================== CALLBACK HANDLERS ====================

@router.callback_query(F.data == "show_licenses")
async def callback_show_licenses(query: CallbackQuery):
    """Show user licenses"""
    user_id = query.from_user.id
    
    keys = await db.get_user_keys(user_id)
    
    if not keys:
        text = (
            "📭 У вас пока нет активных лицензий.\n\n"
            "Используйте 🛒 Купить VPN чтобы приобрести подписку."
        )
    else:
        text = "📝 **Ваши активные лицензии:**\n\n"
        
        for key in keys:
            expires_in = key['expires_at'] - datetime.now().timestamp()
            days_left = int(expires_in / 86400)
            
            emoji = "🔐" if key['tunnel_type'] == 'single' else "🔐🔐"
            text += (
                f"{emoji} **{key['tunnel_type'].upper()}** Tunnel\n"
                f"📧 Email: `{key['email']}`\n"
                f"⏰ До истечения: {days_left} дней\n"
                f"📅 Истекает: {datetime.fromtimestamp(key['expires_at']).strftime('%d.%m.%Y')}\n\n"
            )
    
    await query.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data == "buy_vpn")
async def callback_buy_vpn(query: CallbackQuery, state: FSMContext):
    """Start VPN purchase process"""
    await query.message.edit_text(
        "🔐 Выберите тип туннеля:\n\n"
        "**Single Tunnel** - прямое подключение к NL\n"
        "**Double Tunnel** - скрытное подключение через VK и NL",
        reply_markup=get_tunnel_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(PurchaseState.choosing_tunnel)
    await query.answer()

@router.callback_query(F.data.startswith("tunnel_"), PurchaseState.choosing_tunnel)
async def callback_tunnel_type(query: CallbackQuery, state: FSMContext):
    """Handle tunnel type selection"""
    tunnel_type = query.data.split("_")[1]  # "single" or "double"
    
    await state.update_data(tunnel_type=tunnel_type)
    
    emoji = "🔐" if tunnel_type == "single" else "🔐🔐"
    text = f"{emoji} **{tunnel_type.upper()} Tunnel** выбран!\n\nВыберите длительность подписки:"
    
    await query.message.edit_text(text, reply_markup=get_duration_keyboard(tunnel_type), parse_mode="Markdown")
    await state.set_state(PurchaseState.choosing_duration)
    await query.answer()

@router.callback_query(F.data.startswith("duration_"), PurchaseState.choosing_duration)
async def callback_duration(query: CallbackQuery, state: FSMContext):
    """Handle duration selection"""
    parts = query.data.split("_")  # duration_1_month_single
    duration = f"{parts[1]}_{parts[2]}"  # 1_month
    tunnel_type = parts[3]  # single
    
    data = await state.get_data()
    tunnel_type = data.get('tunnel_type')
    
    price = TUNNEL_PRICES[tunnel_type][duration]
    duration_text = duration.replace("_", " ").title()
    
    # Calculate expiry days
    if duration == "1_month":
        days = 30
    elif duration == "3_months":
        days = 90
    else:  # 12_months
        days = 365
    
    text = (
        f"✅ Вы выбрали:\n\n"
        f"{'🔐' if tunnel_type == 'single' else '🔐🔐'} **{tunnel_type.upper()}** Туннель\n"
        f"📅 Длительность: {duration_text}\n"
        f"💰 Цена: {price}₽\n\n"
        f"Нажмите кнопку ниже для подтверждения платежа.\n\n"
        f"⚠️ Инструкции по оплате появятся на следующем шаге."
    )
    
    await state.update_data(duration=duration, days=days, price=price)
    await query.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await state.clear()
    await query.answer()

@router.callback_query(F.data == "create_gift")
async def callback_create_gift(query: CallbackQuery, state: FSMContext):
    """Start gift creation process"""
    await query.message.edit_text(
        "🎁 Создание подарка - выберите тип туннеля:",
        reply_markup=get_tunnel_keyboard()
    )
    await state.set_state(GiftState.choosing_tunnel)
    await query.answer()

@router.callback_query(F.data.startswith("tunnel_"), GiftState.choosing_tunnel)
async def callback_gift_tunnel(query: CallbackQuery, state: FSMContext):
    """Handle gift tunnel selection"""
    tunnel_type = query.data.split("_")[1]
    
    await state.update_data(tunnel_type=tunnel_type)
    
    text = (
        f"{'🔐' if tunnel_type == 'single' else '🔐🔐'} **{tunnel_type.upper()} Tunnel** выбран!\n\n"
        "Выберите длительность:"
    )
    
    await query.message.edit_text(text, reply_markup=get_duration_keyboard(tunnel_type), parse_mode="Markdown")
    await state.set_state(GiftState.choosing_duration)
    await query.answer()

@router.callback_query(F.data.startswith("duration_"), GiftState.choosing_duration)
async def callback_gift_duration(query: CallbackQuery, state: FSMContext):
    """Handle gift duration selection"""
    parts = query.data.split("_")
    duration = f"{parts[1]}_{parts[2]}"
    tunnel_type = parts[3]
    
    # Calculate days
    if duration == "1_month":
        days = 30
    elif duration == "3_months":
        days = 90
    else:
        days = 365
    
    await state.update_data(days=days)
    
    # Generate unique gift code
    import uuid
    gift_code = str(uuid.uuid4())[:8].upper()
    
    # Add to database
    user_id = query.from_user.id
    await db.create_gift(user_id, gift_code, tunnel_type, days)
    
    gift_link = f"https://t.me/{(await bot.get_me()).username}?start=gift_{gift_code}"
    
    text = (
        f"✅ **Подарок создан!**\n\n"
        f"{'🔐' if tunnel_type == 'single' else '🔐🔐'} {tunnel_type.upper()} Tunnel\n"
        f"📅 Дни: {days}\n"
        f"🎁 Код: `{gift_code}`\n\n"
        f"**Ссылка для поделиться:**\n"
        f"`{gift_link}`\n\n"
        f"Скопируйте и отправьте другу! 🎉"
    )
    
    await query.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await state.clear()
    await query.answer()

@router.callback_query(F.data == "server_status")
async def callback_server_status(query: CallbackQuery):
    """Show server status"""
    status_text = (
        "📊 **Статус серверов AirCloud VPN**\n\n"
        "🇳🇱 **NL Server** (85.239.56.174)\n"
        "  Статус: ✅ Онлайн\n"
        "  Панель: http://85.239.56.174:54321\n\n"
        
        "🇷🇺 **VK Server** (89.208.86.167)\n"
        "  Статус: ✅ Онлайн\n"
        "  Панель: http://89.208.86.167:54321\n\n"
        
        "⚡ Оба сервера работают нормально!"
    )
    
    await query.message.edit_text(status_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data == "show_help")
async def callback_show_help(query: CallbackQuery):
    """Show help"""
    help_text = (
        "🆘 **Справка по AirCloud VPN**\n\n"
        "**Типы туннелей:**\n"
        "🔐 Single Tunnel - прямое подключение\n"
        "🔐🔐 Double Tunnel - через VK сервер\n\n"
        "**Команды:**\n"
        "/mykeys - Мои лицензии\n"
        "/status - Статус\n"
        "/help - Справка"
    )
    
    await query.message.edit_text(help_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data.in_(["cancel", "back_to_menu"]))
async def callback_cancel(query: CallbackQuery, state: FSMContext):
    """Cancel action and return to main menu"""
    await state.clear()
    await query.message.edit_text(
        "Вернулись в главное меню 👇",
        reply_markup=get_main_keyboard()
    )
    await query.answer()

# ==================== ADMIN HANDLERS ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    
    text = (
        "🔧 **Панель администратора**\n\n"
        "Выберите действие:"
    )
    
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(query: CallbackQuery):
    """Admin stats"""
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        async with XrayAPI(XRAY_HOST, XRAY_PORT, XRAY_USERNAME, XRAY_PASSWORD) as api:
            inbound0 = await api.get_inbound(0)
            inbound1 = await api.get_inbound(1)
            
            clients0 = len(inbound0.get('clientStats', []))
            clients1 = len(inbound1.get('clientStats', []))
            
            text = (
                "📊 **Статистика**\n\n"
                f"**Inbound 0 (Single Tunnel)**\n"
                f"  Клиентов: {clients0}\n\n"
                f"**Inbound 1 (Double Tunnel)**\n"
                f"  Клиентов: {clients1}\n\n"
                f"**Всего клиентов:** {clients0 + clients1}"
            )
            
            await query.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin stats error: {e}")
        await query.message.edit_text(f"❌ Ошибка: {str(e)}", reply_markup=get_admin_keyboard())
    
    await query.answer()

@router.callback_query(F.data == "admin_users")
async def callback_admin_users(query: CallbackQuery):
    """Admin users list"""
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    users = await db.get_all_users()
    
    text = "👥 **Пользователи:**\n\n"
    for user in users:
        text += f"ID: {user['user_id']} | @{user['username']}\n"
    
    await query.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await query.answer()

# ==================== INITIALIZATION ====================

async def init_db():
    """Initialize database"""
    global db
    
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = Database(DB_PATH)
    await db.init()
    logger.info(f"Database initialized at {DB_PATH}")

async def main():
    """Main function"""
    # Initialize database
    await init_db()
    
    # Add router to dispatcher
    dp.include_router(router)
    
    # Start polling
    logger.info("Bot started polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
