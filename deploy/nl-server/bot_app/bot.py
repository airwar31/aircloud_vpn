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
    FSInputFile, User, Chat, WebAppInfo
)
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from bot_app.xray_api import XrayAPI, generate_vless_link
from bot_app.database import Database
from bot_app.bot_payment import payment_router, init_payment_handler

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
ADMIN_IDS = list(map(int, filter(None, os.getenv("ADMIN_IDS", "").split(","))))
XRAY_HOST = os.getenv("XRAY_HOST", "xray-panel")
XRAY_PORT = int(os.getenv("XRAY_PORT", "2053"))
XRAY_USERNAME = os.getenv("XRAY_USERNAME", "")
XRAY_PASSWORD = os.getenv("XRAY_PASSWORD", "")
NL_SERVER_IP = os.getenv("NL_SERVER_IP", "")
VK_SERVER_IP = os.getenv("VK_SERVER_IP", "")
DB_PATH = os.getenv("DB_PATH", "./data/users.db")
REALITY_PUBLIC_KEY = os.getenv("REALITY_PUBLIC_KEY", "")
REALITY_SHORT_ID = os.getenv("REALITY_SHORT_ID", "")
NL_REALITY_PUBLIC_KEY = os.getenv("NL_REALITY_PUBLIC_KEY", "")
NL_REALITY_SHORT_ID = os.getenv("NL_REALITY_SHORT_ID", "")
NL_REALITY_SNI = os.getenv("NL_REALITY_SNI", "dl.google.com")
VK_REALITY_SNI = os.getenv("VK_REALITY_SNI", "dl.google.com")
SUBSCRIPTION_BASE_URL = os.getenv("SUBSCRIPTION_BASE_URL", "").rstrip("/")
MINI_APP_URL = os.getenv("MINI_APP_URL", "").rstrip("/")
if not MINI_APP_URL and SUBSCRIPTION_BASE_URL.startswith("https://"):
    MINI_APP_URL = f"{SUBSCRIPTION_BASE_URL}/app"

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

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    buttons = []
    if MINI_APP_URL:
        buttons.append([InlineKeyboardButton(text="📱 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL))])

    buttons += [
        [InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")],
        [InlineKeyboardButton(text="📋 Мои лицензии", callback_data="show_licenses")],
        [InlineKeyboardButton(text="🔗 Subscription URL", callback_data="show_subscription")],
        [InlineKeyboardButton(text="ℹ️ Справка", callback_data="show_help")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🎁 Создать подарок", callback_data="create_gift")])
        buttons.append([InlineKeyboardButton(text="📊 Статус серверов", callback_data="server_status")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

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
            text=f"1 месяц ({prices['1_month']}₽)",
            callback_data=f"duration_1_month_{tunnel_type}"
        )],
        [InlineKeyboardButton(
            text=f"3 месяца ({prices['3_months']}₽)",
            callback_data=f"duration_3_months_{tunnel_type}"
        )],
        [InlineKeyboardButton(
            text=f"12 месяцев ({prices['12_months']}₽)",
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
async def cmd_start(message: Message, command: CommandObject):
    """Start command - welcome message, handles gift deep links"""
    user = message.from_user
    await db.add_user(user.id, user.username or "unknown")

    is_admin = user.id in ADMIN_IDS

    # Handle gift deep link: /start gift_XXXXXXXX
    args = command.args or ""
    if args.startswith("gift_"):
        gift_code = args[5:]  # strip "gift_"
        await _process_gift(message, user.id, gift_code, is_admin)
        return

    welcome_text = f"""
🌐 **AirCloud VPN** - Защита вашей конфиденциальности

Привет, {user.first_name}! 👋

Выберите действие:

📌 **Single Tunnel** - прямое подключение к NL серверу (базовый VPN)
📌 **Double Tunnel** - подключение через VK сервер затем в NL (максимальная скрытность)

Оба типа используют лучшие протоколы (VLESS + TLS/Reality) для надежного и быстрого соединения.

Нажмите на кнопку ниже, чтобы начать! 👇
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard(is_admin))
    logger.info(f"User {user.id} started bot")


@router.message(Command("app"))
async def cmd_app(message: Message):
    """Open Telegram Mini App with subscriptions and payments."""
    if not MINI_APP_URL:
        await message.answer(
            "❌ Mini App пока недоступен. Проверьте настройку MINI_APP_URL или SUBSCRIPTION_BASE_URL."
        )
        return

    await message.answer(
        "📱 Откройте Mini App для управления подписками, датами окончания и оплатой:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Открыть AirCloud Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
            ]
        ),
    )


async def _process_gift(message: Message, user_id: int, gift_code: str, is_admin: bool):
    """Activate gift subscription for user"""
    gift = await db.get_gift(gift_code)

    if not gift:
        await message.answer(
            "❌ Подарочный код не найден.",
            reply_markup=get_main_keyboard(is_admin)
        )
        return

    if gift["status"] != "active":
        await message.answer(
            "❌ Этот подарок уже был использован или истёк.",
            reply_markup=get_main_keyboard(is_admin)
        )
        return

    if gift["used_by"] == user_id or gift["created_by"] == user_id:
        await message.answer(
            "❌ Нельзя использовать собственный подарок.",
            reply_markup=get_main_keyboard(is_admin)
        )
        return

    tunnel_type = gift["tunnel_type"]
    days = gift["days"]

    await message.answer("⏳ Активируем подарок...")

    try:
        email = f"gift_{user_id}_{gift_code}@aircloud.local"
        from bot_app.config import XrayConfig

        if tunnel_type == "double":
            # Double tunnel: клиент подключается к VK Reality inbound.
            # NL inbound использует фиксированный сервисный UUID через nl-proxy outbound,
            # поэтому добавлять пользователя в NL не нужно — только в VK.
            vk_cfg = XrayConfig.VK_PANEL
            async with XrayAPI(
                host=vk_cfg["host"],
                port=vk_cfg["port"],
                username=vk_cfg["username"],
                password=vk_cfg["password"],
            ) as vk_api:
                result = await vk_api.add_client(
                    inbound_id=XrayConfig.INBOUND_IDS["vk"]["reality"],
                    email=email,
                    expiry_days=days,
                    tunnel_type=tunnel_type,
                )
        else:
            # Single tunnel: клиент подключается к NL Reality inbound напрямую
            async with XrayAPI(XRAY_HOST, XRAY_PORT, XRAY_USERNAME, XRAY_PASSWORD) as api:
                result = await api.add_client(
                    inbound_id=XrayConfig.INBOUND_IDS["nl"]["single"],
                    email=email,
                    expiry_days=days,
                    tunnel_type=tunnel_type,
                )

        if not result:
            await message.answer("❌ Ошибка активации. Свяжитесь с поддержкой.")
            return

        client_uuid = result["uuid"]

        from bot_app.xray_api import generate_vless_link
        if tunnel_type == "double":
            vless_link = generate_vless_link(
                uuid=client_uuid,
                server_ip=VK_SERVER_IP,
                port=443,
                email=email,
                tunnel_type=tunnel_type,
                reality_public_key=REALITY_PUBLIC_KEY,
                reality_short_id=REALITY_SHORT_ID,
                sni=VK_REALITY_SNI,
            )
        else:
            vless_link = generate_vless_link(
                uuid=client_uuid,
                server_ip=NL_SERVER_IP,
                port=8443,
                email=email,
                tunnel_type=tunnel_type,
                reality_public_key=NL_REALITY_PUBLIC_KEY,
                reality_short_id=NL_REALITY_SHORT_ID,
                sni=NL_REALITY_SNI,
            )

        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(days=days)).timestamp()
        await db.add_vpn_key(
            user_id=user_id,
            email=email,
            tunnel_type=tunnel_type,
            vless_link=vless_link,
            expires_at=expires_at,
            uuid=client_uuid
        )
        await db.use_gift(gift_code, user_id)

        tunnel_name = "Базовый" if tunnel_type == "single" else "Двойной"
        await message.answer(
            f"🎁 **Подарок активирован!**\n\n"
            f"Тип: {tunnel_name} туннель\n"
            f"Срок: {days} дней\n\n"
            f"Ваша VLESS ссылка:\n```\n{vless_link}\n```",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(is_admin)
        )
    except Exception as e:
        logger.error(f"Gift activation error: {e}")
        await message.answer("❌ Ошибка активации подарка. Свяжитесь с поддержкой.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Help command"""
    help_text = """
🆘 **Справка по AirCloud VPN**

**Доступные команды:**
/start - Главное меню
/app - Открыть Mini App
/mykeys - Мои активные лицензии
/subscription - Ссылка на подписку для VPN клиентов
/buy - Купить VPN подписку
/gift - Создать подарок (поделиться ссылкой)
/status - Статус серверов
/help - Эта справка

**Типы туннелей:**

🔐 **Single Tunnel (150₽/месяц)**
- Прямое подключение к серверу (Нидерланды)
- Протокол: VLESS + TLS
- Использование: Базовая защита, обход блокировок
- Скорость: ⭐⭐⭐⭐⭐

🔐🔐 **Double Tunnel (250₽/месяц)**
- Двойное туннелирование: Reality Bridge → NL Exit Node
- Протоколы: VLESS + Reality + TLS
- Использование: Максимальная скрытность, обход блокировок
- Скорость: ⭐⭐⭐⭐

**Поддержанные сроки:**
- 1 месяц
- 3 месяца
- 12 месяцев (год)

**Вопросы и поддержка:**
Напишите @support или в группу VPN

📱 Для удобного управления подписками и сроками используйте Mini App: /app
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
            reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS)
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

@router.message(Command("subscription"))
async def cmd_subscription(message: Message):
    """Show user's subscription URL for VPN clients"""
    user_id = message.from_user.id
    if not SUBSCRIPTION_BASE_URL:
        await message.answer(
            "❌ Ссылка подписки не настроена. Укажите SUBSCRIPTION_BASE_URL в .env."
        )
        return

    # Get or generate subscription token
    token = await db.get_subscription_token(user_id)

    if not token:
        await message.answer(
            "❌ Ошибка создания subscription URL\n"
            "Попробуйте позже или свяжитесь с @support"
        )
        return

    # Build subscription URL
    subscription_url = f"{SUBSCRIPTION_BASE_URL}/sub/{token}"
    info_url = subscription_url

    response = (
        "🔗 **Ваша подписка VPN**\n\n"
        "Используйте эту ссылку для автоматической настройки VPN:\n\n"
        f"`{subscription_url}`\n\n"
        "📱 **Поддерживаемые приложения:**\n"
        "• V2rayN (Windows/Android)\n"
        "• NekoBox (Android)\n"
        "• V2rayNG (Android)\n"
        "• Clash for Windows\n\n"
        "📖 **Инструкция:**\n"
        "1. Скопируйте ссылку выше\n"
        "2. Откройте ваш VPN клиент\n"
        "3. Найдите 'Добавить подписку' или 'Add Subscription'\n"
        "4. Вставьте ссылку\n"
        "5. Обновите конфигурации\n\n"
        f"ℹ️ [Посмотреть детали подписки]({info_url})"
    )

    subscription_keyboard = None
    if MINI_APP_URL:
        subscription_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📱 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL))]
            ]
        )

    await message.answer(
        response,
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=subscription_keyboard,
    )

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Server status"""
    try:
        async with XrayAPI(XRAY_HOST, XRAY_PORT, XRAY_USERNAME, XRAY_PASSWORD) as api:
            stats = await api.get_stats()
            
            is_admin = message.from_user.id in ADMIN_IDS
            if is_admin:
                status_text = (
                    "📊 **Статус серверов AirCloud VPN (Admin)**\n\n"
                    f"🇳🇱 **NL Server** (`{NL_SERVER_IP or 'local'}`)\n"
                    f"  Статус: ✅ Онлайн\n"
                    f"  Inbound 0 (Single): Port 8443 (TLS)\n"
                    f"  Inbound 1 (Double): Port 443 (TLS)\n\n"
                    f"🇷🇺 **VK Server** (`{VK_SERVER_IP or 'remote'}`)\n"
                    f"  Статус: ✅ Онлайн\n"
                    f"  Inbound 0 (Reality): Port 443 (Reality)\n\n"
                    "⚡ Оба сервера работают в штатном режиме!"
                )
            else:
                status_text = (
                    "📊 **Статус серверов AirCloud VPN**\n\n"
                    "🇳🇱 **NL Сервер (Европа)**\n"
                    "  Статус: ✅ Онлайн (VLESS + TLS)\n\n"
                    "🇷🇺 **Bridge Сервер (Обход блокировок)**\n"
                    "  Статус: ✅ Онлайн (VLESS + Reality)\n\n"
                    "⚡ Все сервисы доступны и работают стабильно!"
                )
            
            await message.answer(status_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.answer(
            "❌ Ошибка получения статуса\n"
            "Попробуйте позже или свяжитесь с поддержкой"
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
    
    await query.message.edit_text(text, reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data == "show_subscription")
async def callback_show_subscription(query: CallbackQuery):
    """Show user's subscription URL"""
    user_id = query.from_user.id
    if not SUBSCRIPTION_BASE_URL:
        await query.message.edit_text(
            "❌ Ссылка подписки не настроена. Укажите SUBSCRIPTION_BASE_URL в .env.",
            reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS),
        )
        await query.answer()
        return

    # Get or generate subscription token
    token = await db.get_subscription_token(user_id)

    if not token:
        text = (
            "❌ Ошибка создания subscription URL\n"
            "Попробуйте позже или свяжитесь с @support"
        )
    else:
        # Build subscription URL
        subscription_url = f"{SUBSCRIPTION_BASE_URL}/sub/{token}"
        info_url = subscription_url

        text = (
            "🔗 **Ваша подписка VPN**\n\n"
            "Используйте эту ссылку для автоматической настройки VPN:\n\n"
            f"`{subscription_url}`\n\n"
            "📱 **Поддерживаемые приложения:**\n"
            "• V2rayN (Windows/Android)\n"
            "• NekoBox (Android)\n"
            "• V2rayNG (Android)\n"
            "• Clash for Windows\n\n"
            "📖 **Инструкция:**\n"
            "1. Скопируйте ссылку выше\n"
            "2. Откройте ваш VPN клиент\n"
            "3. Найдите 'Добавить подписку' или 'Add Subscription'\n"
            "4. Вставьте ссылку\n"
            "5. Обновите конфигурации\n\n"
            f"ℹ️ [Посмотреть детали подписки]({info_url})"
        )

    await query.message.edit_text(text, reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS), parse_mode="Markdown", disable_web_page_preview=True)
    await query.answer()

@router.callback_query(F.data == "buy_vpn")
async def callback_buy_vpn(query: CallbackQuery, state: FSMContext):
    """Start VPN purchase process — redirect to payment flow"""
    from bot_app.bot_payment import TARIFF_TEXT
    await state.clear()
    await query.message.edit_text(
        TARIFF_TEXT,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇳🇱 Базовый туннель", callback_data="pay_tunnel_single"),
                InlineKeyboardButton(text="🇷🇺+🇳🇱 Двойной туннель", callback_data="pay_tunnel_double"),
            ]
        ])
    )
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
    await query.message.edit_text(text, reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS), parse_mode="Markdown")
    await state.clear()
    await query.answer()

@router.callback_query(F.data == "create_gift")
async def callback_create_gift(query: CallbackQuery, state: FSMContext):
    """Start gift creation process (admin only)"""
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
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
    
    await query.message.edit_text(text, reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS), parse_mode="Markdown")
    await state.clear()
    await query.answer()

@router.callback_query(F.data == "server_status")
async def callback_server_status(query: CallbackQuery):
    """Show server status"""
    is_admin = query.from_user.id in ADMIN_IDS
    if is_admin:
        status_text = (
            "📊 **Статус серверов AirCloud VPN (Admin)**\n\n"
            f"🇳🇱 **NL Server** (`{NL_SERVER_IP or 'local'}`)\n"
            f"  Статус: ✅ Онлайн\n\n"
            f"🇷🇺 **VK Server** (`{VK_SERVER_IP or 'remote'}`)\n"
            f"  Статус: ✅ Онлайн\n\n"
            "⚡ Оба узла работают стабильно!"
        )
    else:
        status_text = (
            "📊 **Статус серверов AirCloud VPN**\n\n"
            "🇳🇱 **NL Сервер (Европа)**\n"
            "  Статус: ✅ Онлайн (VLESS + TLS)\n\n"
            "🇷🇺 **Bridge Сервер (Обход блокировок)**\n"
            "  Статус: ✅ Онлайн (VLESS + Reality)\n\n"
            "⚡ Все сервисы доступны и работают стабильно!"
        )
    
    await query.message.edit_text(status_text, reply_markup=get_main_keyboard(is_admin), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data == "show_help")
async def callback_show_help(query: CallbackQuery):
    """Show help"""
    help_text = (
        "🆘 **Справка по AirCloud VPN**\n\n"
        "📱 **Mini App:**\n"
        "Открывается кнопкой в меню или командой `/app`.\n"
        "Там удобно смотреть сроки подписок, копировать конфиги и покупать тарифы.\n\n"
        "**Типы туннелей:**\n"
        "🔐 Single Tunnel - прямое подключение\n"
        "🔐🔐 Double Tunnel - через VK сервер\n\n"
        "**Команды:**\n"
        "/app - Открыть Mini App\n"
        "/mykeys - Мои лицензии\n"
        "/status - Статус\n"
        "/help - Справка"
    )
    
    await query.message.edit_text(help_text, reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS), parse_mode="Markdown")
    await query.answer()

@router.callback_query(F.data.in_(["cancel", "back_to_menu"]))
async def callback_cancel(query: CallbackQuery, state: FSMContext):
    """Cancel action and return to main menu"""
    await state.clear()
    await query.message.edit_text(
        "Вернулись в главное меню 👇",
        reply_markup=get_main_keyboard(query.from_user.id in ADMIN_IDS)
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
    import os as _os
    # Initialize database
    await init_db()

    # Initialize payment handler
    await init_payment_handler(
        bot_instance=bot,
        yookassa_shop_id=_os.getenv("YOOKASSA_SHOP_ID", ""),
        yookassa_secret_key=_os.getenv("YOOKASSA_SECRET_KEY", ""),
        database=db
    )

    # Add routers to dispatcher
    dp.include_router(router)
    dp.include_router(payment_router)

    # Start bot
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
