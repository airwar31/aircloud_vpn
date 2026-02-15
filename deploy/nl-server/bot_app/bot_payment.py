"""
Команды платежей для Telegram Bot
"""

import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton,
    PreCheckoutQuery, ShippingAddress
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot_app.config import PaymentConfig, TUNNEL_PRICES, ServerConfig
from bot_app.payment_handler import PaymentHandler, calculate_price_with_commission, convert_rubles_to_stars
from bot_app.database import Database

logger = logging.getLogger(__name__)

payment_router = Router()


class PaymentStates(StatesGroup):
    """Состояния для выбора платежа"""
    choosing_tunnel = State()
    choosing_duration = State()
    confirming_payment = State()
    processing_payment = State()


class TelegramStarsStates(StatesGroup):
    """Состояния для Telegram Stars платежей"""
    confirming_stars = State()


# Текст с описанием тарифов
TARIFF_TEXT = """
💰 **ТАРИФЫ AIRCLOUD VPN**

**Базовый туннель (Нидерланды)**
🇳🇱 Одно соединение через NL Server (8443 TLS)

├ 1 месяц: 150₽
├ 3 месяца: 400₽ (скидка 11%)
└ 12 месяцев: 1200₽ (скидка 33%)

**Двойной туннель (VK → NL)**
🇷🇺 + 🇳🇱 Два соединения с максимальной защитой

├ 1 месяц: 250₽
├ 3 месяца: 650₽ (скидка 13%)
└ 12 месяцев: 2200₽ (скидка 27%)

**❓ Как выбрать:**
• Базовый - для общего использования
• Двойной - для высокой конфиденциальности

Выберите для начала тип туннеля:
"""

PAYMENT_METHODS_TEXT = """
🔐 **СПОСОБЫ ОПЛАТЫ**

Мы поддерживаем несколько безопасных способов оплаты:

**YooKassa (Юкасса)** ✓ Рекомендуется
• Банковские карты Visa/Mastercard
• Электронные кошельки
• Мобильные операторы

**Telegram Stars** ⭐
• Встроенный в Telegram
• Без комиссий
• Быстрая активация

**Криптовалута** 🪙
• USDT (ETH/BSC/TON)
• USDC (ETH/BSC)
• TON (прямые переводы)
• Минимум: 50₽

Какой способ вам удобнее?
"""

# Инстанс обработчика платежей
payment_handler: Optional[PaymentHandler] = None


async def init_payment_handler(
    bot_instance: Bot,
    yookassa_shop_id: str,
    yookassa_secret_key: str,
    database: Database
):
    """Инициализировать обработчик платежей"""
    global payment_handler
    
    try:
        from bot_app.xray_api import XrayAPI
        
        xray = XrayAPI(
            server_ip=ServerConfig.NL_SERVER["ip"],
            port=ServerConfig.NL_SERVER["port"],
            username=ServerConfig.NL_SERVER["username"],
            password=ServerConfig.NL_SERVER["password"]
        )
        
        payment_handler = PaymentHandler(
            yookassa_shop_id=yookassa_shop_id,
            yookassa_secret_key=yookassa_secret_key,
            database=database,
            xray_api=xray,
            bot=bot_instance
        )
        
        await payment_handler.init()
        logger.info("Payment handler initialized successfully")
    
    except Exception as e:
        logger.error(f"Error initializing payment handler: {e}")


# Команда /pay - начало платежа

@payment_router.message(F.text == "/pay")
async def cmd_pay(message: Message, state: FSMContext):
    """Команда для начала платежа"""
    try:
        await message.answer(
            TARIFF_TEXT,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🇳🇱 Базовый туннель", callback_data="pay_tunnel_single"),
                    InlineKeyboardButton(text="🇷🇺+🇳🇱 Двойной туннель", callback_data="pay_tunnel_double"),
                ]
            ])
        )
        await state.set_state(PaymentStates.choosing_tunnel)
    
    except Exception as e:
        logger.error(f"Error in /pay command: {e}")
        await message.answer("❌ Ошибка при обработке команды. Попробуйте позже.")


# Выбор типа туннеля

@payment_router.callback_query(F.data.startswith("pay_tunnel_"))
async def select_tunnel(callback: CallbackQuery, state: FSMContext):
    """Выбор типа туннеля"""
    try:
        tunnel_type = callback.data.split("_")[-1]  # 'single' или 'double'
        await state.update_data(tunnel_type=tunnel_type)
        
        tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
        prices = TUNNEL_PRICES[tunnel_type]
        
        duration_text = f"""
✅ Вы выбрали: **{tunnel_name}**

💰 **Цена по длительности:**

🔸 1 месяц: {prices['1_month']}₽
🔸 3 месяца: {prices['3_months']}₽
🔸 12 месяцев: {prices['12_months']}₽

Выберите длительность подписки:
"""
        
        await callback.message.edit_text(
            duration_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="1 месяц - 150₽" if tunnel_type == "single" else "1 месяц - 250₽", 
                                     callback_data="pay_duration_1_month")],
                [InlineKeyboardButton(text="3 месяца - 400₽" if tunnel_type == "single" else "3 месяца - 650₽", 
                                     callback_data="pay_duration_3_months")],
                [InlineKeyboardButton(text="12 месяцев - 1200₽" if tunnel_type == "single" else "12 месяцев - 2200₽", 
                                     callback_data="pay_duration_12_months")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="pay_back_tunnels")]
            ])
        )
        
        await state.set_state(PaymentStates.choosing_duration)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error selecting tunnel: {e}")
        await callback.answer("❌ Ошибка при выборе туннеля")


# Выбор длительности

@payment_router.callback_query(F.data.startswith("pay_duration_"))
async def select_duration(callback: CallbackQuery, state: FSMContext):
    """Выбор длительности подписки"""
    try:
        duration = callback.data.split("_", 2)[-1]  # '1_month', '3_months', '12_months'
        await state.update_data(duration=duration)
        
        data = await state.get_data()
        tunnel_type = data.get("tunnel_type")
        
        prices = TUNNEL_PRICES[tunnel_type]
        price = prices.get(duration)
        
        if not price:
            await callback.answer("❌ Ошибка: неизвестная длительность")
            return
        
        tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
        duration_text_map = {
            "1_month": "1 месяц",
            "3_months": "3 месяца",
            "12_months": "12 месяцев"
        }
        duration_label = duration_text_map.get(duration)
        
        confirm_text = f"""
✅ **Подтверждение платежа**

📦 Подписка: {tunnel_name}
⏱️ Длительность: {duration_label}
💰 Сумма: {price}₽

Выберите способ оплаты:
"""
        
        await callback.message.edit_text(
            confirm_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 YooKassa", callback_data="pay_method_yookassa")],
                [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_method_stars")],
                [InlineKeyboardButton(text="🪙 Криптовалута", callback_data="pay_method_crypto")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="pay_back_durations")]
            ])
        )
        
        await state.set_state(PaymentStates.confirming_payment)
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error selecting duration: {e}")
        await callback.answer("❌ Ошибка при выборе длительности")


# Выбор способа оплаты

@payment_router.callback_query(F.data.startswith("pay_method_"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    try:
        method = callback.data.split("_")[-1]  # 'yookassa', 'stars', 'crypto'
        
        data = await state.get_data()
        tunnel_type = data.get("tunnel_type")
        duration = data.get("duration")
        
        prices = TUNNEL_PRICES[tunnel_type]
        base_price = prices.get(duration)
        
        if not base_price:
            await callback.answer("❌ Ошибка: невалидная сумма")
            return
        
        if method == "yookassa":
            await _handle_yookassa_payment(callback, state, tunnel_type, duration, base_price)
        
        elif method == "stars":
            await _handle_stars_payment(callback, state, tunnel_type, duration, base_price)
        
        elif method == "crypto":
            await _handle_crypto_payment(callback, state, tunnel_type, duration, base_price)
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error selecting payment method: {e}")
        await callback.answer("❌ Ошибка при выборе способа оплаты")


# YooKassa платеж

async def _handle_yookassa_payment(
    callback: CallbackQuery,
    state: FSMContext,
    tunnel_type: str,
    duration: str,
    price: float
):
    """Обработка YooKassa платежа"""
    global payment_handler
    
    if not payment_handler:
        await callback.answer("❌ Система платежей временно недоступна")
        return
    
    try:
        user_id = callback.from_user.id
        email = f"vpn_{user_id}@aircloud.local"
        
        # Создаем платеж
        payment_id, confirmation_url = await payment_handler.create_payment(
            user_id=user_id,
            amount_rubles=price,
            tunnel_type=tunnel_type,
            duration=duration,
            email=email
        )
        
        if not payment_id or not confirmation_url:
            await callback.answer("❌ Ошибка при создании платежа")
            return
        
        await state.update_data(
            payment_id=payment_id,
            payment_method="yookassa",
            email=email
        )
        
        # Отправляем ссылку на оплату
        payment_text = f"""
✅ **Платеж создан**

🔗 **Ссылка на оплату:**
[Оплатить {price}₽ через YooKassa]({confirmation_url})

📱 Способы оплаты:
• Банковские карты (Visa, Mastercard, MIR)
• Яндекс.Касса
• Сбербанк Онлайн
• Мобильные платежи
• Электронные кошельки

**Важно:** После оплаты нажмите кнопку "Проверить платеж" ниже.

⏰ Ссылка активна 24 часа.
"""
        
        await callback.message.edit_text(
            payment_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Открыть оплату", url=confirmation_url)],
                [InlineKeyboardButton(text="✅ Проверить платеж", callback_data="pay_verify_yookassa")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")]
            ])
        )
        
        await state.set_state(PaymentStates.processing_payment)
    
    except Exception as e:
        logger.error(f"Error handling YooKassa payment: {e}")
        await callback.answer("❌ Ошибка при обработке платежа")


# Telegram Stars платеж

async def _handle_stars_payment(
    callback: CallbackQuery,
    state: FSMContext,
    tunnel_type: str,
    duration: str,
    price: float
):
    """Обработка Telegram Stars платежа"""
    try:
        user = callback.from_user
        user_id = user.id
        
        # Конвертируем рубли в звезды
        stars_amount = convert_rubles_to_stars(price)
        
        # Формируем описание товара
        tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
        duration_text = {
            "1_month": "1 месяц",
            "3_months": "3 месяца",
            "12_months": "12 месяцев"
        }.get(duration, "неизвестный срок")
        
        from aiogram.types import LabeledPrice
        
        # Отправляем инвойс для Telegram Stars
        await callback.bot.send_invoice(
            chat_id=user_id,
            title=f"AirCloud VPN - {tunnel_name}",
            description=f"Подписка на {duration_text}",
            payload=f"{tunnel_type}_{duration}",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label="Подписка", amount=stars_amount)],
            provider_token="",  # Для Telegram Stars не нужен провайдер
            start_parameter=f"vpn_{tunnel_type}_{duration}"
        )
        
        await state.update_data(
            payment_method="stars",
            tunnel_type=tunnel_type,
            duration=duration,
            stars_amount=stars_amount
        )
        
        await state.set_state(TelegramStarsStates.confirming_stars)
        await callback.answer("✅ Счет создан, следуйте инструкциям в боте")
    
    except Exception as e:
        logger.error(f"Error handling Stars payment: {e}")
        await callback.answer("❌ Ошибка при обработке платежа Stars")


# Криптовалута платеж

async def _handle_crypto_payment(
    callback: CallbackQuery,
    state: FSMContext,
    tunnel_type: str,
    duration: str,
    price: float
):
    """Обработка криптовалютного платежа"""
    try:
        user_id = callback.from_user.id
        
        crypto_text = f"""
🪙 **Криптовалютный платеж**

💰 **Сумма к оплате:** {price}₽ (≈ {price * 0.015:.2f} USDT)

**Выберите криптовалюту:**

🔸 **USDT** (Tether)
├ Сеть ETH - мин. {PaymentConfig.CRYPTO_MIN_AMOUNT}₽
├ Сеть BSC (BEP-20) - комиссия ≈1%
└ Адрес: `0x...` (см. инструкцию)

🔸 **USDC** (USD Coin)
├ Сеть ETH - быстро и надежно
└ Сеть BSC - дешевле комиссия

🔸 **TON** (прямые переводы)
├ Минимум: 50₽ в TON
└ Адрес кошелька будет предоставлен

**Как платить:**
1. Выберите криптовалюту снизу
2. Скопируйте адрес кошелька
3. Отправьте платеж из вашего кошелька
4. Ожидайте подтверждения (2-5 блоков)

⚠️ **Внимание:** Отправляйте только необходимую сумму, переплаты не возвращаются
"""
        
        await callback.message.edit_text(
            crypto_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 USDT (ETH)", callback_data="pay_crypto_usdt_eth")],
                [InlineKeyboardButton(text="🟡 USDT (BSC)", callback_data="pay_crypto_usdt_bsc")],
                [InlineKeyboardButton(text="🔵 USDC", callback_data="pay_crypto_usdc")],
                [InlineKeyboardButton(text="🟦 TON", callback_data="pay_crypto_ton")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="pay_back_methods")]
            ])
        )
        
        await state.update_data(
            payment_method="crypto",
            tunnel_type=tunnel_type,
            duration=duration,
            crypto_price=price
        )
    
    except Exception as e:
        logger.error(f"Error handling crypto payment: {e}")
        await callback.answer("❌ Ошибка при обработке криптовалютного платежа")


# Проверка YooKassa платежа

@payment_router.callback_query(F.data == "pay_verify_yookassa")
async def verify_yookassa_payment(callback: CallbackQuery, state: FSMContext):
    """Проверить статус YooKassa платежа"""
    global payment_handler
    
    if not payment_handler:
        await callback.answer("❌ Система платежей временно недоступна")
        return
    
    try:
        data = await state.get_data()
        payment_id = data.get("payment_id")
        user_id = callback.from_user.id
        
        if not payment_id:
            await callback.answer("❌ Платеж не найден")
            return
        
        await callback.message.edit_text(
            "⏳ Проверяем статус платежа...",
            parse_mode="Markdown"
        )
        
        # Проверяем платеж и активируем подписку
        if await payment_handler.check_and_activate_payment(payment_id, user_id):
            success_text = """
✅ **Платеж успешен!**

🎉 Ваша подписка активирована

Ссылка на подключение была отправлена в отдельном сообщении выше.

**Что дальше:**
1. Установите VPN клиент (Nekobox, V2rayN и т.д.)
2. Импортируйте полученную ссылку
3. Выберите сервер и подключитесь

При возникновении проблем обратитесь в поддержку: @support
"""
            await callback.message.edit_text(
                success_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 Помощь с установкой", url="https://t.me/aircloud_help")],
                    [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/support")]
                ])
            )
            await state.clear()
        
        else:
            pending_text = """
⏳ **Платеж еще не подтвержден**

Возможные причины:
• Платеж еще обрабатывается (обычно 1-3 минуты)
• Платеж отклонен банком
• Неверный платежный метод

**Что делать:**
1. Проверьте статус платежа в своем банке
2. Попробуйте еще раз через минуту
3. Если проблема остается, обратитесь в поддержку

**Поддержка:** @support
"""
            await callback.message.edit_text(
                pending_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Проверить снова", callback_data="pay_verify_yookassa")],
                    [InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")]
                ])
            )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await callback.answer("❌ Ошибка при проверке платежа")


# Обработка успешного Telegram Stars платежа

@payment_router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    """Подтвердить перед обработкой Telegram Stars платежа"""
    await pre_checkout_query.answer(ok=True)


@payment_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    """Обработить успешный платеж Telegram Stars"""
    try:
        global payment_handler
        
        if not payment_handler:
            await message.answer("❌ Система платежей временно недоступна")
            return
        
        data = await state.get_data()
        tunnel_type = data.get("tunnel_type")
        duration = data.get("duration")
        user_id = message.from_user.id
        email = f"vpn_{user_id}_stars@aircloud.local"
        
        # Создаем подписку
        received_amount = message.successful_payment.total_amount
        
        # Активируем VPN
        days = 30 if duration == "1_month" else (90 if duration == "3_months" else 365)
        inbound_id = 0 if tunnel_type == "single" else 1
        
        from bot_app.xray_api import XrayAPI, generate_vless_link
        
        xray = XrayAPI(
            server_ip=ServerConfig.NL_SERVER["ip"],
            port=ServerConfig.NL_SERVER["port"],
            username=ServerConfig.NL_SERVER["username"],
            password=ServerConfig.NL_SERVER["password"]
        )
        
        success = await xray.add_client(
            inbound_id=inbound_id,
            email=email,
            expiry_days=days,
            tunnel_type=tunnel_type
        )
        
        if success:
            server_ip = ServerConfig.NL_SERVER["ip"] if tunnel_type == "single" else ServerConfig.VK_SERVER["ip"]
            port = 8443 if tunnel_type == "single" else 443
            
            vless_link = generate_vless_link(
                uuid=email,
                server_ip=server_ip,
                port=port,
                email=email,
                tunnel_type=tunnel_type
            )
            
            # Сохраняем в БД
            from datetime import datetime, timedelta
            expires_at = (datetime.now() + timedelta(days=days)).timestamp()
            
            await database.add_vpn_key(
                user_id=user_id,
                email=email,
                tunnel_type=tunnel_type,
                vless_link=vless_link,
                expires_at=expires_at
            )
            
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            
            success_text = f"""
✅ **Платеж успешен!**

🎉 Поздравляем! Ваша подписка активирована

📱 **Тип:** {tunnel_name}
⭐ **Способ:** Telegram Stars
⏰ **Дней:** {days}

**Ваша VLESS ссылка:**
```
{vless_link}
```

Ссылка была отправлена в отдельном сообщении.
"""
            
            await message.answer(success_text, parse_mode="Markdown")
            await message.answer(f"```\n{vless_link}\n```", parse_mode="Markdown")
            
            await state.clear()
        
        else:
            await message.answer("❌ Ошибка при активации подписки. Обратитесь в поддержку: @support")
    
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        await message.answer("❌ Ошибка при обработке платежа")


# Отмена платежа

@payment_router.callback_query(F.data == "pay_cancel")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Отменить платеж"""
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ Платеж отменен.\n\nВы можете начать новый платеж командой /pay",
            parse_mode="Markdown"
        )
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error canceling payment: {e}")
        await callback.answer("❌ Ошибка при отмене")


# Кнопки "Назад"

@payment_router.callback_query(F.data == "pay_back_tunnels")
async def back_tunnels(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору туннеля"""
    await callback.message.edit_text(
        TARIFF_TEXT,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇳🇱 Базовый туннель", callback_data="pay_tunnel_single"),
                InlineKeyboardButton(text="🇷🇺+🇳🇱 Двойной туннель", callback_data="pay_tunnel_double"),
            ]
        ])
    )
    await callback.answer()


@payment_router.callback_query(F.data == "pay_back_durations")
async def back_durations(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору длительности"""
    data = await state.get_data()
    tunnel_type = data.get("tunnel_type")
    
    prices = TUNNEL_PRICES[tunnel_type]
    
    duration_text = f"""
✅ Вы выбрали: **{"Базовый туннель" if tunnel_type == "single" else "Двойной туннель"}**

💰 **Цена по длительности:**

🔸 1 месяц: {prices['1_month']}₽
🔸 3 месяца: {prices['3_months']}₽
🔸 12 месяцев: {prices['12_months']}₽

Выберите длительность подписки:
"""
    
    await callback.message.edit_text(
        duration_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 месяц - 150₽" if tunnel_type == "single" else "1 месяц - 250₽", 
                                 callback_data="pay_duration_1_month")],
            [InlineKeyboardButton(text="3 месяца - 400₽" if tunnel_type == "single" else "3 месяца - 650₽", 
                                 callback_data="pay_duration_3_months")],
            [InlineKeyboardButton(text="12 месяцев - 1200₽" if tunnel_type == "single" else "12 месяцев - 2200₽", 
                                 callback_data="pay_duration_12_months")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="pay_back_tunnels")]
        ])
    )
    await callback.answer()


@payment_router.callback_query(F.data == "pay_back_methods")
async def back_methods(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору способа оплаты"""
    data = await state.get_data()
    tunnel_type = data.get("tunnel_type")
    duration = data.get("duration")
    
    prices = TUNNEL_PRICES[tunnel_type]
    price = prices.get(duration)
    
    tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
    duration_text_map = {
        "1_month": "1 месяц",
        "3_months": "3 месяца",
        "12_months": "12 месяцев"
    }
    duration_label = duration_text_map.get(duration)
    
    confirm_text = f"""
✅ **Подтверждение платежа**

📦 Подписка: {tunnel_name}
⏱️ Длительность: {duration_label}
💰 Сумма: {price}₽

Выберите способ оплаты:
"""
    
    await callback.message.edit_text(
        confirm_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 YooKassa", callback_data="pay_method_yookassa")],
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_method_stars")],
            [InlineKeyboardButton(text="🪙 Криптовалута", callback_data="pay_method_crypto")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="pay_back_durations")]
        ])
    )
    await callback.answer()
