"""
Payment Handler для Integration YooKassa с Telegram Bot
"""

import logging
import asyncio
from typing import Optional, Tuple
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputFile
from aiogram.fsm.context import FSMContext

from bot_app.config import PaymentConfig, TUNNEL_PRICES
from bot_app.yookassa_payment import YooKassaAPI, rubles_to_kopeks, format_payment_amount
from bot_app.database import Database
from bot_app.xray_api import XrayAPI, generate_vless_link

logger = logging.getLogger(__name__)

router = Router()


class PaymentHandler:
    """Обработчик платежей"""
    
    def __init__(
        self,
        yookassa_shop_id: str,
        yookassa_secret_key: str,
        database: Database,
        xray_api: XrayAPI,
        bot: Bot
    ):
        """
        Инициализация обработчика платежей
        
        Args:
            yookassa_shop_id: Shop ID для YooKassa
            yookassa_secret_key: Secret key для YooKassa
            database: Database instance
            xray_api: XrayAPI instance
            bot: Bot instance
        """
        self.shop_id = yookassa_shop_id
        self.secret_key = yookassa_secret_key
        self.db = database
        self.xray = xray_api
        self.bot = bot
        self.yookassa: Optional[YooKassaAPI] = None
    
    async def init(self):
        """Инициализировать YooKassa API"""
        self.yookassa = YooKassaAPI(
            shop_id=self.shop_id,
            secret_key=self.secret_key,
            timeout=PaymentConfig.YOOKASSA_API_TIMEOUT,
            retries=PaymentConfig.YOOKASSA_RETRIES
        )
        await self.yookassa.__aenter__()
    
    async def cleanup(self):
        """Очистить ресурсы"""
        if self.yookassa:
            await self.yookassa.__aexit__(None, None, None)
    
    async def create_payment(
        self,
        user_id: int,
        amount_rubles: float,
        tunnel_type: str,
        duration: str,
        email: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Создать платеж в YooKassa
        
        Args:
            user_id: ID пользователя Telegram
            amount_rubles: Сумма в рублях
            tunnel_type: Тип туннеля ('single' или 'double')
            duration: Длительность ('1_month', '3_months', '12_months')
            email: Email для VLESS ключа
        
        Returns:
            Кортеж (payment_id, confirmation_url) или (None, None) если ошибка
        """
        try:
            if not self.yookassa:
                logger.error("YooKassa not initialized")
                return None, None
            
            # Преобразуем рубли в копейки для YooKassa
            amount_kopeks = rubles_to_kopeks(amount_rubles)
            
            # Описание платежа
            duration_text = self._get_duration_text(duration)
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            description = f"AirCloud VPN - {tunnel_name} ({duration_text})"
            
            # Метаданные для отслеживания
            metadata = {
                "user_id": str(user_id),
                "tunnel_type": tunnel_type,
                "duration": duration,
                "email": email
            }
            
            # Создаем платеж
            payment = await self.yookassa.create_payment(
                amount=amount_kopeks,
                currency="RUB",
                description=description,
                email=f"user_{user_id}@vpn.local",
                return_url="https://t.me/aircloud_vpn_bot",  # Возврат в бот
                customer_id=str(user_id),
                metadata=metadata
            )
            
            if payment:
                payment_id = payment.get("id")
                confirmation_url = payment.get("confirmation", {}).get("confirmation_url")
                
                logger.info(f"Payment created: {payment_id} for user {user_id}")
                
                # Сохраняем платеж в БД
                await self.db.create_order(
                    user_id=user_id,
                    amount=amount_rubles,
                    plan_type=duration,
                    tunnel_type=tunnel_type,
                    payment_method="yookassa"
                )
                
                return payment_id, confirmation_url
            else:
                logger.error(f"Failed to create payment for user {user_id}")
                return None, None
        
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None, None
    
    async def check_and_activate_payment(
        self,
        payment_id: str,
        user_id: int
    ) -> bool:
        """
        Проверить статус платежа и активировать подписку
        
        Args:
            payment_id: ID платежа в YooKassa
            user_id: ID пользователя Telegram
        
        Returns:
            True если платеж успешен и подписка активирована
        """
        try:
            if not self.yookassa:
                logger.error("YooKassa not initialized")
                return False
            
            # Проверяем статус платежа
            status = await self.yookassa.check_payment_status(payment_id)
            
            if status != "succeeded":
                logger.warning(f"Payment {payment_id} status: {status}")
                return False
            
            # Получаем полную информацию о платеже
            payment = await self.yookassa.get_payment(payment_id)
            if not payment:
                logger.error(f"Cannot get payment details for {payment_id}")
                return False
            
            metadata = payment.get("metadata", {})
            tunnel_type = metadata.get("tunnel_type")
            duration = metadata.get("duration")
            email = metadata.get("email")
            amount = payment.get("amount", {}).get("value", 0)
            
            if not all([tunnel_type, duration, email]):
                logger.error(f"Missing metadata in payment {payment_id}")
                return False
            
            # Вычисляем количество дней
            days = 30 if duration == "1_month" else (90 if duration == "3_months" else 365)
            
            # Определяем inbound ID для XrayAPI
            inbound_id = 0 if tunnel_type == "single" else 1
            
            # Добавляем клиента в Xray через API
            success = await self.xray.add_client(
                inbound_id=inbound_id,
                email=email,
                expiry_days=days,
                tunnel_type=tunnel_type
            )
            
            if not success:
                logger.error(f"Failed to add client to Xray for {email}")
                return False
            
            # Генерируем VLESS ссылку
            from bot_app.config import ServerConfig
            server_ip = ServerConfig.NL_SERVER["ip"] if tunnel_type == "single" else ServerConfig.VK_SERVER["ip"]
            port = 8443 if tunnel_type == "single" else 443
            
            vless_link = generate_vless_link(
                uuid=email,  # В данном случае используем email как уникальный идентификатор
                server_ip=server_ip,
                port=port,
                email=email,
                tunnel_type=tunnel_type
            )
            
            # Сохраняем подписку в БД
            expires_at = (datetime.now() + timedelta(days=days)).timestamp()
            await self.db.add_vpn_key(
                user_id=user_id,
                email=email,
                tunnel_type=tunnel_type,
                vless_link=vless_link,
                expires_at=expires_at
            )
            
            # Обновляем статус заказа
            await self.db.complete_order(user_id)
            
            logger.info(f"Subscription activated for user {user_id}: {email}")
            
            # Отправляем VLESS ссылку пользователю
            await self._send_activation_message(user_id, email, vless_link, tunnel_type, days)
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking/activating payment: {e}")
            return False
    
    async def refund_payment(
        self,
        payment_id: str,
        user_id: int,
        reason: str = ""
    ) -> bool:
        """
        Вернуть деньги клиенту
        
        Args:
            payment_id: ID платежа для возврата
            user_id: ID пользователя
            reason: Причина возврата
        
        Returns:
            True если возврат успешен
        """
        try:
            if not self.yookassa:
                logger.error("YooKassa not initialized")
                return False
            
            refund = await self.yookassa.refund_payment(
                payment_id=payment_id,
                description=f"Возврат: {reason}"
            )
            
            if refund:
                logger.info(f"Refund created for payment {payment_id}: {refund.get('id')}")
                return True
            else:
                logger.error(f"Failed to create refund for payment {payment_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return False
    
    async def _send_activation_message(
        self,
        user_id: int,
        email: str,
        vless_link: str,
        tunnel_type: str,
        days: int
    ):
        """
        Отправить пользователю сообщение с VLESS ссылкой
        
        Args:
            user_id: ID пользователя
            email: Email клиента
            vless_link: VLESS ссылка
            tunnel_type: Тип туннеля
            days: Количество дней подписки
        """
        try:
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            expiry_date = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")
            
            message = f"""
✅ **VPN Активирован!**

🎉 Поздравляем! Ваша подписка активирована!

📌 **Тип:** {tunnel_name}
📧 **Email:** `{email}`
⏰ **Истекает:** {expiry_date}
📱 **Дней:** {days}

**Ваша VLESS ссылка:**
```
{vless_link}
```

**Как использовать:**
1. Установите VPN клиент (Nekobox, V2rayN, NekoX и т.д.)
2. Импортируйте эту ссылку в клиент
3. Выберите подключение и наслаждайтесь!

**Рекомендуемые клиенты:**
• Nekobox (Android) - самый простой
• V2rayN (Windows) - полнофункциональный
• NekoX (iOS) - для яблочников
• Clash (macOS) - универсальный

**Нужна помощь?** Напишите @support

🙏 Спасибо, что выбрали AirCloud VPN!
"""
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
        
        except Exception as e:
            logger.error(f"Error sending activation message: {e}")
    
    @staticmethod
    def _get_duration_text(duration: str) -> str:
        """Преобразовать duration в текст"""
        duration_map = {
            "1_month": "1 месяц",
            "3_months": "3 месяца",
            "12_months": "12 месяцев"
        }
        return duration_map.get(duration, "неизвестный срок")


# Вспомогательные функции для расчета цены с комиссией

def calculate_price_with_commission(base_price: float, payment_method: str = "yookassa") -> float:
    """
    Рассчитать итоговую цену с учетом комиссии
    
    Args:
        base_price: Базовая цена в рублях
        payment_method: Способ оплаты ('yookassa', 'stars', 'crypto')
    
    Returns:
        Итоговая цена в рублях
    """
    commission_percent = {
        "yookassa": PaymentConfig.YOOKASSA_COMMISSION,
        "stars": PaymentConfig.STARS_COMMISSION,
        "crypto": PaymentConfig.CRYPTO_COMMISSION,
    }.get(payment_method, 0)
    
    return base_price * (1 + commission_percent / 100)


def convert_rubles_to_stars(rubles: float) -> int:
    """
    Конвертировать рубли в Telegram Stars
    
    Args:
        rubles: Сумма в рублях
    
    Returns:
        Количество звезд
    """
    return max(int(rubles * PaymentConfig.STARS_CONVERSION_RATE), 1)
