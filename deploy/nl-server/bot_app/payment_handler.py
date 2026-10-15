"""
Payment Handler для Integration YooKassa с Telegram Bot
"""

import logging
import asyncio
import os
from typing import Optional, Tuple
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InputFile
from aiogram.fsm.context import FSMContext

from bot_app.config import PaymentConfig, TUNNEL_PRICES
from bot_app.yookassa_payment import YooKassaAPI, rubles_to_kopeks, format_payment_amount
from bot_app.database import Database
from bot_app.provisioning import build_provisioner, ProvisioningError

logger = logging.getLogger(__name__)

router = Router()


class PaymentHandler:
    """Обработчик платежей"""
    
    def __init__(
        self,
        yookassa_shop_id: str,
        yookassa_secret_key: str,
        database: Database,
        bot: Bot
    ):
        """
        Инициализация обработчика платежей

        Args:
            yookassa_shop_id: Shop ID для YooKassa
            yookassa_secret_key: Secret key для YooKassa
            database: Database instance
            bot: Bot instance
        """
        self.shop_id = yookassa_shop_id
        self.secret_key = yookassa_secret_key
        self.db = database
        self.bot = bot
        self.yookassa: Optional[YooKassaAPI] = None
        self.provisioner = build_provisioner()
    
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
                    payment_method="yookassa",
                    payment_id=payment_id
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
        """Check payment status in YooKassa and activate/renew VPN subscription."""
        processing_reserved = False

        try:
            if not self.yookassa:
                logger.error("YooKassa not initialized")
                return False

            if await self.db.is_payment_processed(payment_id):
                logger.info(f"Payment {payment_id} already processed")
                return True

            status = await self.yookassa.check_payment_status(payment_id)

            if status == "waiting_for_capture":
                logger.info(f"Payment {payment_id} waiting for capture, capturing now...")
                capture_result = await self.yookassa.capture_payment(payment_id)
                if capture_result:
                    status = capture_result.get("status")
                    logger.info(f"Payment {payment_id} captured, new status: {status}")
                else:
                    logger.error(f"Failed to capture payment {payment_id}")
                    return False

            if status != "succeeded":
                logger.warning(f"Payment {payment_id} status: {status}")
                return False

            payment = await self.yookassa.get_payment(payment_id)
            if not payment:
                logger.error(f"Cannot get payment details for {payment_id}")
                return False

            metadata = payment.get("metadata", {})
            metadata_user_id = metadata.get("user_id")
            tunnel_type = metadata.get("tunnel_type")
            duration = metadata.get("duration")
            email = metadata.get("email")

            if metadata_user_id and str(metadata_user_id) != str(user_id):
                logger.error(
                    f"Payment {payment_id} belongs to user {metadata_user_id}, got user {user_id}"
                )
                return False

            if not all([tunnel_type, duration, email]):
                logger.error(f"Missing metadata in payment {payment_id}")
                return False

            if tunnel_type not in ("single", "double"):
                logger.error(f"Unsupported tunnel_type in metadata: {tunnel_type}")
                return False

            if "@" not in email:
                email = f"{email}@aircloud.local"

            can_process = await self.db.begin_payment_processing(
                payment_id=payment_id,
                user_id=user_id,
                tunnel_type=tunnel_type,
                duration=duration,
                email=email,
            )
            if not can_process:
                if await self.db.is_payment_processed(payment_id):
                    logger.info(f"Payment {payment_id} already completed by another worker")
                    return True
                logger.info(f"Payment {payment_id} is already being processed")
                return False
            processing_reserved = True

            days = self._duration_to_days(duration)

            # 1) Try to renew existing key for this tunnel type.
            renewed = await self._try_renew_existing_key(
                user_id=user_id,
                tunnel_type=tunnel_type,
                add_days=days,
            )
            if renewed:
                completed = await self.db.complete_order_by_payment_id(payment_id)
                if not completed:
                    await self.db.complete_pending_order(user_id, tunnel_type)

                await self.db.finish_payment_processing(payment_id, success=True)
                processing_reserved = False

                logger.info(f"Subscription renewed for user {user_id}: {renewed['email']}")
                await self._send_activation_message(
                    user_id=user_id,
                    email=renewed["email"],
                    tunnel_type=tunnel_type,
                    days=days,
                    expires_at_ts=renewed["expires_at_ts"],
                    is_renewal=True,
                )
                return True

            # 2) Create brand-new key if user has no previous key for this type.
            local, domain = email.split("@", 1)
            email_unique = f"{local}_{payment_id[:8]}@{domain}"
            activation_email = email_unique

            expires_at = (datetime.now() + timedelta(days=days)).timestamp()
            if tunnel_type == "single":
                existing_nl = await self.db.get_key_by_email(email_unique)
                if existing_nl and existing_nl.get("status") == "active" and existing_nl.get("vless_link"):
                    nl_uuid = existing_nl.get("uuid")
                    nl_vless_link = existing_nl["vless_link"]
                    logger.info(f"NL key already exists for user {user_id}: {email_unique}")
                else:
                    try:
                        nl_result = await self.provisioner.create_client(
                            tunnel_type="single",
                            email=email_unique,
                            expiry_days=days,
                            user_id=user_id,
                        )
                        nl_uuid = nl_result.uuid
                        nl_vless_link = nl_result.vless_link
                    except ProvisioningError as e:
                        logger.error(
                            "Failed to provision NL client for %s: %s (%s)",
                            email_unique,
                            e.code,
                            e.detail,
                        )
                        await self.db.finish_payment_processing(
                            payment_id,
                            success=False,
                            error=self._format_activation_error("nl_add_client_failed", f"{e.code}: {e.detail}"),
                        )
                        return False

                stored_nl = await self.db.add_vpn_key(
                    user_id=user_id,
                    email=email_unique,
                    tunnel_type="single",
                    vless_link=nl_vless_link,
                    expires_at=expires_at,
                    uuid=nl_uuid,
                )
                if not stored_nl:
                    existing_nl = await self.db.get_key_by_email(email_unique)
                    if not existing_nl or not existing_nl.get("vless_link"):
                        logger.error(f"Failed to store NL key for {email_unique}")
                        await self.db.finish_payment_processing(
                            payment_id,
                            success=False,
                            error=self._format_activation_error("nl_store_key_failed"),
                        )
                        return False

                logger.info(f"NL (single) key ready for user {user_id}: {email_unique}")
            else:
                vk_email = f"{email_unique.split('@')[0]}_vk@{email_unique.split('@')[1]}"
                activation_email = vk_email
                existing_vk = await self.db.get_key_by_email(vk_email)
                if existing_vk and existing_vk.get("status") == "active" and existing_vk.get("vless_link"):
                    logger.info(f"VK key already exists for user {user_id}: {vk_email}")
                else:
                    try:
                        vk_result = await self.provisioner.create_client(
                            tunnel_type="double",
                            email=vk_email,
                            expiry_days=days,
                            user_id=user_id,
                        )
                        vk_uuid = vk_result.uuid
                        vk_vless_link = vk_result.vless_link
                    except ProvisioningError as e:
                        logger.error(
                            "Failed to provision VK client for %s: %s (%s)",
                            vk_email,
                            e.code,
                            e.detail,
                        )
                        await self.db.finish_payment_processing(
                            payment_id,
                            success=False,
                            error=self._format_activation_error("vk_add_client_failed", f"{e.code}: {e.detail}"),
                        )
                        return False

                    stored_vk = await self.db.add_vpn_key(
                        user_id=user_id,
                        email=vk_email,
                        tunnel_type="double",
                        vless_link=vk_vless_link,
                        expires_at=expires_at,
                        uuid=vk_uuid,
                    )
                    if not stored_vk:
                        existing_vk = await self.db.get_key_by_email(vk_email)
                        if not existing_vk or not existing_vk.get("vless_link"):
                            logger.error(f"Failed to store VK key for {vk_email}")
                            await self.db.finish_payment_processing(
                                payment_id,
                                success=False,
                                error=self._format_activation_error("vk_store_key_failed"),
                            )
                            return False

                    logger.info(f"VK (double) key ready for user {user_id}: {vk_email}")

            completed = await self.db.complete_order_by_payment_id(payment_id)
            if not completed:
                await self.db.complete_pending_order(user_id, tunnel_type)

            await self.db.finish_payment_processing(payment_id, success=True)
            processing_reserved = False

            logger.info(f"Subscription activated for user {user_id}: {activation_email}")
            await self._send_activation_message(
                user_id=user_id,
                email=activation_email,
                tunnel_type=tunnel_type,
                days=days,
                expires_at_ts=expires_at,
                is_renewal=False,
            )
            return True

        except Exception as e:
            if processing_reserved:
                await self.db.finish_payment_processing(payment_id, success=False, error=str(e))
            logger.error(f"Error checking/activating payment: {e}")
            return False

    async def _try_renew_existing_key(self, user_id: int, tunnel_type: str, add_days: int):
        """Try to extend existing key expiry for the same tunnel type."""
        key = await self.db.get_latest_user_key(user_id, tunnel_type)
        if not key:
            return None

        email = (key.get("email") or "").strip()
        if not email:
            return None

        current_expiry_ts = self._parse_expires_at_to_ts(key.get("expires_at"))
        now_ts = datetime.now().timestamp()
        base_ts = current_expiry_ts if current_expiry_ts > now_ts else now_ts
        new_expiry_ts = base_ts + add_days * 86400
        days_from_now = max(1, int((new_expiry_ts - now_ts + 86399) // 86400))

        client_uuid = (key.get("uuid") or "").strip()
        try:
            renewed = await self.provisioner.renew_client(
                tunnel_type=tunnel_type,
                email=email,
                expiry_days=days_from_now,
                client_uuid=client_uuid,
                user_id=user_id,
            )
        except ProvisioningError as e:
            logger.error("Failed to renew key %s via provisioner: %s (%s)", email, e.code, e.detail)
            return None

        client_uuid = renewed.uuid
        vless_link = renewed.vless_link or key.get("vless_link")

        stored = await self.db.add_vpn_key(
            user_id=user_id,
            email=email,
            tunnel_type=tunnel_type,
            vless_link=vless_link,
            expires_at=new_expiry_ts,
            uuid=client_uuid,
        )
        if not stored:
            # Fallback explicit update for existing row.
            await self.db.update_key_expiry_timestamp(email, new_expiry_ts)

        return {"email": email, "expires_at_ts": new_expiry_ts}

    @staticmethod
    def _parse_expires_at_to_ts(value) -> float:
        """Parse DB expires_at value into Unix timestamp."""
        if value is None:
            return 0.0

        if isinstance(value, datetime):
            return float(value.timestamp())

        try:
            raw = str(value).strip()
            return float(datetime.fromisoformat(raw).timestamp())
        except Exception:
            pass

        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _duration_to_days(duration: str) -> int:
        return 30 if duration == "1_month" else (90 if duration == "3_months" else 365)

    @staticmethod
    def _format_activation_error(code: str, detail: str = "") -> str:
        """Build compact activation error for payment_events.error."""
        compact = " ".join(str(detail or "").split())
        if not compact:
            return code
        if len(compact) > 180:
            compact = f"{compact[:177]}..."
        return f"{code}: {compact}"

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
        tunnel_type: str,
        days: int,
        expires_at_ts: Optional[float] = None,
        is_renewal: bool = False,
    ):
        """
        Отправить пользователю сообщение с subscription URL

        Args:
            user_id: ID пользователя
            email: Email клиента
            tunnel_type: Тип туннеля
            days: Количество дней подписки
        """
        try:
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            if expires_at_ts:
                expiry_date = datetime.fromtimestamp(expires_at_ts).strftime("%d.%m.%Y")
            else:
                expiry_date = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")

            # Получаем или генерируем subscription token
            token = await self.db.get_subscription_token(user_id)
            if not token:
                logger.error(f"Failed to get subscription token for user {user_id}")
                token = "ERROR"

            # Формируем subscription URL
            base_url = os.getenv("SUBSCRIPTION_BASE_URL", "").rstrip("/")
            if not base_url:
                mini_app_url = os.getenv("MINI_APP_URL", "").rstrip("/")
                if mini_app_url.endswith("/app"):
                    base_url = mini_app_url[:-4]
            subscription_url = f"{base_url}/sub/{token}"

            action_text = "подписка продлена" if is_renewal else "подписка активирована"
            message = f"""
✅ **VPN Активирован!**

🎉 Поздравляем! Ваша {action_text}.

📌 **Тип:** {tunnel_name}
📧 **Email:** `{email}`
⏰ **Истекает:** {expiry_date}
📱 **Дней:** {days}

**Ваша subscription ссылка:**
```
{subscription_url}
```

**Как использовать:**
1. Установите VPN клиент (Nekobox, V2rayN, NekoX и т.д.)
2. Найдите "Добавить подписку" или "Add Subscription"
3. Вставьте эту ссылку
4. Обновите конфигурации
5. Выберите сервер и подключитесь!

**Рекомендуемые клиенты:**
• V2rayN (Windows) - полнофункциональный
• NekoBox (Android) - простой и удобный
• V2rayNG (Android) - стабильный
• Clash for Windows - универсальный

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
