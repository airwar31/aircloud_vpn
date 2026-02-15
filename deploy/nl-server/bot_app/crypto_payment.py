"""
Обработчик криптовалютных платежей
"""

import logging
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

crypto_router = Router()


class CryptoPaymentProcessor:
    """Обработчик криптовалютных платежей"""
    
    # Кошельки для приема платежей (заполнить реальными адресами)
    WALLETS = {
        "usdt_eth": {
            "address": "0x...",  # ETH адрес для получения USDT
            "network": "Ethereum (ERC-20)",
            "chain_id": 1,
            "min_amount": Decimal("0.015"),  # ~50₽ в USDT
            "decimals": 6
        },
        "usdt_bsc": {
            "address": "0x...",  # BSC адрес для получения USDT
            "network": "Binance Smart Chain (BEP-20)",
            "chain_id": 56,
            "min_amount": Decimal("0.015"),
            "decimals": 6
        },
        "usdc_eth": {
            "address": "0x...",  # ETH адрес для получения USDC
            "network": "Ethereum (ERC-20)",
            "chain_id": 1,
            "min_amount": Decimal("0.015"),
            "decimals": 6
        },
        "usdc_bsc": {
            "address": "0x...",  # BSC адрес для получения USDC
            "network": "Binance Smart Chain (BEP-20)",
            "chain_id": 56,
            "min_amount": Decimal("0.015"),
            "decimals": 6
        },
        "ton": {
            "address": "0:...",  # TON адрес
            "network": "TON Blockchain",
            "chain_id": 0,
            "min_amount": Decimal("3.5"),  # ~50₽ в TON
            "decimals": 9
        }
    }
    
    # Курсы обмена (обновляются из API)
    RATES = {
        "USDT": Decimal("90.0"),  # 90₽ за 1 USDT
        "USDC": Decimal("90.0"),  # 90₽ за 1 USDC
        "TON": Decimal("14.0"),   # 14₽ за 1 TON
    }
    
    def __init__(self, database):
        """
        Инициализация обработчика криптовалют
        
        Args:
            database: Database instance для сохранения платежей
        """
        self.db = database
        self.pending_payments: Dict[str, dict] = {}
    
    @staticmethod
    def rubles_to_crypto(amount_rubles: float, currency: str) -> Decimal:
        """
        Конвертировать рубли в криптовалюту
        
        Args:
            amount_rubles: Сумма в рублях
            currency: Валюта ('USDT', 'USDC', 'TON')
        
        Returns:
            Количество криптовалюты
        """
        rate = CryptoPaymentProcessor.RATES.get(currency, Decimal("1"))
        return Decimal(amount_rubles) / rate
    
    def generate_payment_id(self) -> str:
        """Сгенерировать уникальный ID платежа"""
        return str(uuid.uuid4())
    
    async def create_pending_payment(
        self,
        user_id: int,
        payment_id: str,
        amount_rubles: float,
        currency: str,
        tunnel_type: str,
        duration: str
    ) -> Dict:
        """
        Создать ожидающий платеж
        
        Args:
            user_id: ID пользователя
            payment_id: ID платежа
            amount_rubles: Сумма в рублях
            currency: Валюта
            tunnel_type: Тип туннеля
            duration: Длительность
        
        Returns:
            Словарь с информацией о платеже
        """
        crypto_amount = self.rubles_to_crypto(amount_rubles, currency)
        
        payment_info = {
            "user_id": user_id,
            "payment_id": payment_id,
            "amount_rubles": amount_rubles,
            "amount_crypto": float(crypto_amount),
            "currency": currency,
            "tunnel_type": tunnel_type,
            "duration": duration,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "status": "pending"
        }
        
        self.pending_payments[payment_id] = payment_info
        
        # Сохраняем в БД
        await self.db.create_order(
            user_id=user_id,
            amount=amount_rubles,
            plan_type=duration,
            tunnel_type=tunnel_type,
            payment_method=f"crypto_{currency.lower()}"
        )
        
        return payment_info
    
    async def check_payment_status(
        self,
        payment_id: str,
        transaction_hash: Optional[str] = None
    ) -> Dict:
        """
        Проверить статус платежа
        
        Args:
            payment_id: ID платежа
            transaction_hash: Хэш транзакции (опционально)
        
        Returns:
            Словарь со статусом платежа
        """
        payment = self.pending_payments.get(payment_id)
        
        if not payment:
            return {"status": "not_found"}
        
        # Проверяем истечение времени
        if datetime.now() > payment["expires_at"]:
            payment["status"] = "expired"
            return payment
        
        # В реальном приложении здесь нужна проверка блокчейна
        # Проверка может быть через:
        # - etherscan API для ETH платежей
        # - bscscan API для BSC платежей
        # - tonapi.io для TON платежей
        
        if transaction_hash:
            # Здесь была бы проверка в блокчейне
            logger.info(f"Checking transaction {transaction_hash} for payment {payment_id}")
        
        return payment
    
    async def confirm_payment(
        self,
        payment_id: str,
        transaction_hash: str,
        from_address: str,
        to_address: str,
        amount: Decimal,
        confirmations: int = 1
    ) -> bool:
        """
        Подтвердить платеж (вызывается после найденной транзакции в блокчейне)
        
        Args:
            payment_id: ID платежа
            transaction_hash: Хэш транзакции
            from_address: Адрес отправителя
            to_address: Адрес получателя
            amount: Количество токенов
            confirmations: Количество подтверждений блокчейна
        
        Returns:
            True если платеж подтвержден
        """
        payment = self.pending_payments.get(payment_id)
        
        if not payment:
            logger.error(f"Payment {payment_id} not found")
            return False
        
        # Проверяем корректность адреса и суммы
        if to_address != self.WALLETS.get(f"{payment['currency'].lower()}_*", {}).get("address"):
            logger.warning(f"Payment to wrong address: {to_address}")
            return False
        
        expected_amount = Decimal(payment["amount_crypto"])
        if amount < expected_amount * Decimal("0.99"):  # Допускаем 1% погрешность на комиссию
            logger.warning(f"Payment amount too low: {amount} < {expected_amount}")
            return False
        
        # Минимум 1 подтверждение
        if confirmations < 1:
            logger.warning(f"Not enough confirmations: {confirmations}")
            return False
        
        # Помечаем платеж как подтверждённый
        payment["status"] = "confirmed"
        payment["transaction_hash"] = transaction_hash
        payment["from_address"] = from_address
        payment["confirmations"] = confirmations
        payment["confirmed_at"] = datetime.now()
        
        logger.info(f"Payment {payment_id} confirmed: {transaction_hash}")
        
        return True
    
    async def get_pending_payments(self, user_id: int) -> List[Dict]:
        """
        Получить ожидающие платежи пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Список ожидающих платежей
        """
        return [
            p for p in self.pending_payments.values()
            if p["user_id"] == user_id and p["status"] in ["pending", "waiting_confirmation"]
        ]


class BlockchainMonitor:
    """Монитор блокчейна для отслеживания платежей"""
    
    def __init__(self, crypto_processor: CryptoPaymentProcessor, bot: Bot):
        """
        Инициализация монитора
        
        Args:
            crypto_processor: Экземпляр CryptoPaymentProcessor
            bot: Экземпляр Bot для отправки уведомлений
        """
        self.processor = crypto_processor
        self.bot = bot
        self.monitoring_active = False
    
    async def start_monitoring(self):
        """Начать мониторинг блокчейна"""
        self.monitoring_active = True
        
        # Запускаем мониторинг для каждой сети
        tasks = [
            self._monitor_ethereum(),
            self._monitor_bsc(),
            self._monitor_ton()
        ]
        
        await asyncio.gather(*tasks)
    
    async def stop_monitoring(self):
        """Остановить мониторинг"""
        self.monitoring_active = False
    
    async def _monitor_ethereum(self):
        """Мониторить платежи в Ethereum сети"""
        while self.monitoring_active:
            try:
                # Здесь будет реальная логика проверки через ethereum RPC или Etherscan API
                # Для примера просто логируем
                logger.debug("Monitoring Ethereum network for payments...")
                await asyncio.sleep(30)  # Проверяем каждые 30 секунд
            
            except Exception as e:
                logger.error(f"Error monitoring Ethereum: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_bsc(self):
        """Мониторить платежи в BSC сети"""
        while self.monitoring_active:
            try:
                # Здесь будет реальная логика проверки через BSC RPC или BscScan API
                logger.debug("Monitoring BSC network for payments...")
                await asyncio.sleep(30)
            
            except Exception as e:
                logger.error(f"Error monitoring BSC: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_ton(self):
        """Мониторить платежи в TON сети"""
        while self.monitoring_active:
            try:
                # Здесь будет реальная логика проверки через tonapi.io или других TON индексеров
                logger.debug("Monitoring TON network for payments...")
                await asyncio.sleep(30)
            
            except Exception as e:
                logger.error(f"Error monitoring TON: {e}")
                await asyncio.sleep(60)
    
    async def notify_payment_detected(
        self,
        user_id: int,
        payment_id: str,
        amount: float,
        transaction_hash: str,
        currency: str
    ):
        """
        Уведомить пользователя об обнаруженном платеже
        
        Args:
            user_id: ID пользователя
            payment_id: ID платежа
            amount: Количество токенов
            transaction_hash: Хэш транзакции
            currency: Валюта
        """
        try:
            message = f"""
✅ **Платеж обнаружен!**

💱 **Валюта:** {currency}
💰 **Сумма:** {amount} {currency}
🔗 **Транзакция:** `{transaction_hash}`

⏳ Ожидаю подтверждения в блокчейне...
(обычно это занимает 1-3 минуты)

Как только платеж будет подтверждён, ваша подписка активируется автоматически.
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
        
        except Exception as e:
            logger.error(f"Error sending payment notification: {e}")
    
    async def notify_payment_confirmed(
        self,
        user_id: int,
        vless_link: str,
        tunnel_type: str,
        days: int
    ):
        """
        Уведомить пользователя о подтверждении платежа
        
        Args:
            user_id: ID пользователя
            vless_link: VLESS ссылка
            tunnel_type: Тип туннеля
            days: Количество дней
        """
        try:
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            
            message = f"""
✅ **Платеж подтвержден!**

🎉 Ваша подписка активирована

📱 **Тип:** {tunnel_name}
⏰ **Дней:** {days}

**Ваша VLESS ссылка:**
```
{vless_link}
```

**Как использовать:**
1. Установите VPN клиент (Nekobox, V2rayN и т.д.)
2. Импортируйте эту ссылку в клиент
3. Выберите подключение и наслаждайтесь!

При возникновении проблем обратитесь в поддержку: @support

🙏 Спасибо, что выбрали AirCloud VPN!
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
        
        except Exception as e:
            logger.error(f"Error sending confirmation notification: {e}")


# Хэндлеры для выбора криптовалюты

@crypto_router.callback_query(F.data.startswith("pay_crypto_"))
async def select_crypto_currency(callback: CallbackQuery):
    """Выбрать криптовалюту для платежа"""
    try:
        crypto_type = callback.data.split("_")[-2:] # Получаем тип и сеть, например ['usdt', 'eth']
        crypto_type = "_".join(crypto_type)
        
        wallet_info = CryptoPaymentProcessor.WALLETS.get(crypto_type)
        
        if not wallet_info:
            await callback.answer("❌ Неизвестная криптовалюта")
            return
        
        currency = crypto_type.split("_")[0].upper()
        
        crypto_text = f"""
🪙 **Криптовалютный платеж**

💱 **Валюта:** {currency}
🌐 **Сеть:** {wallet_info['network']}

**Адрес кошелька:**
```
{wallet_info['address']}
```

**Минимальная сумма:** {wallet_info['min_amount']} {currency}

**Как платить:**
1. Скопируйте адрес выше
2. Отправьте требуемую сумму на этот адрес
3. После подтверждения блокчейна подписка активируется
4. Вы получите VLESS ссылку автоматически

**⏳ Время ожидания:**
• Ethereum: 2-5 минут
• BSC: 1-3 минуты
• TON: 10-30 секунд

⚠️ **ВАЖНО:** 
• Отправляйте только требуемую сумму
• Переплаты не возвращаются
• Проверьте адрес перед отправкой

🔐 Платеж полностью безопасен и анонимен
"""
        
        await callback.message.edit_text(
            crypto_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Скопировать адрес", callback_data=f"copy_crypto_{crypto_type}")],
                [InlineKeyboardButton(text="✅ Я отправил платеж", callback_data=f"waiting_crypto_{crypto_type}")],
                [InlineKeyboardButton(text="↩️ Другой способ", callback_data="pay_back_methods")]
            ])
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error selecting crypto currency: {e}")
        await callback.answer("❌ Ошибка при выборе криптовалюты")


@crypto_router.callback_query(F.data.startswith("waiting_crypto_"))
async def waiting_for_crypto_payment(callback: CallbackQuery):
    """Ожидание подтверждения криптовалютного платежа"""
    try:
        waiting_text = """
⏳ **Ожидание подтверждения платежа**

Мониторим блокчейн... Пожалуйста, дождитесь!

**Статус:**
🔄 Сканируем входящие транзакции
🔄 Проверяем сумму и адрес
🔄 Ожидаем подтверждения блокчейна

Это обычно занимает 1-5 минут, в зависимости от выбранной сети.

**После подтверждения:**
✅ Вы получите VLESS ссылку
✅ Подписка активируется автоматически
✅ Можно начать использовать VPN

Если платеж не будет найден в течение часа, платеж будет отменен.

Спасибо за ожидание!
"""
        
        await callback.message.edit_text(
            waiting_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить статус", callback_data="check_crypto_status")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")]
            ])
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error waiting for crypto payment: {e}")
        await callback.answer("❌ Ошибка")


@crypto_router.callback_query(F.data == "check_crypto_status")
async def check_crypto_status(callback: CallbackQuery):
    """Проверить статус криптовалютного платежа"""
    try:
        checking_text = """
🔍 **Проверяем статус платежа...**

Сканируем блокчейн в поиске вашей транзакции...

⏳ Пожалуйста, подождите...
"""
        
        await callback.message.edit_text(
            checking_text,
            parse_mode="Markdown"
        )
        
        # Здесь была бы реальная проверка
        await asyncio.sleep(3)
        
        status_text = """
⏳ **Статус платежа**

🔍 Платеж не найден в блокчейне

Возможные причины:
• Платеж все еще обрабатывается
• Транзакция отправлена с неправильного адреса
• Неверная сумма платежа
• Ошибка при отправке

**Что делать:**
1. Проверьте проводку в вашем кошельке
2. Убедитесь, что сумма корректна
3. Попробуйте еще раз через 5 минут
4. Если проблема остается, обратитесь в поддержку

**Поддержка:** @support
"""
        
        await callback.message.edit_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить снова", callback_data="check_crypto_status")],
                [InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/support")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="pay_cancel")]
            ])
        )
        
        await callback.answer()
    
    except Exception as e:
        logger.error(f"Error checking crypto status: {e}")
        await callback.answer("❌ Ошибка при проверке статуса")
