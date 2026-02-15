"""
Обработчик вебхуков YooKassa для активации платежей
"""

import logging
import json
from typing import Optional
from aiohttp import web
from datetime import datetime, timedelta

from bot_app.config import PaymentConfig
from bot_app.yookassa_payment import YooKassaWebhookValidator
from bot_app.database import Database
from bot_app.xray_api import XrayAPI, generate_vless_link

logger = logging.getLogger(__name__)

# Глобальные экземпляры (заполняются при инициализации)
payment_handler: Optional[object] = None
db: Optional[Database] = None
bot = None


def init_webhook_handler(
    payment_h: object,
    database: Database,
    bot_instance
):
    """Инициализировать обработчик вебхуков"""
    global payment_handler, db, bot
    payment_handler = payment_h
    db = database
    bot = bot_instance


class YooKassaWebhookHandler:
    """Обработчик YooKassa вебхуков"""
    
    # Поддерживаемые события
    SUPPORTED_EVENTS = [
        "payment.succeeded",
        "payment.canceled",
        "refund.succeeded",
        "payout.succeeded"
    ]
    
    @staticmethod
    async def handle_webhook(request: web.Request) -> web.Response:
        """
        Обработить вебхук от YooKassa
        
        Args:
            request: HTTP запрос от YooKassa
        
        Returns:
            HTTP ответ
        """
        try:
            # Получаем тело запроса
            body = await request.text()
            data = json.loads(body)
            
            # Получаем сигнатуру
            signature = request.headers.get("HTTP_X_V3_DK_SIGNATURE")
            
            if not signature:
                logger.warning("Webhook without signature received")
                return web.json_response(
                    {"error": "No signature provided"},
                    status=400
                )
            
            # Валидируем сигнатуру
            if not YooKassaWebhookValidator.validate_webhook(
                data,
                signature,
                PaymentConfig.YOOKASSA_SECRET_KEY
            ):
                logger.error("Invalid webhook signature")
                return web.json_response(
                    {"error": "Invalid signature"},
                    status=403
                )
            
            # Обработаем событие
            event_type = data.get("event")
            
            if event_type not in YooKassaWebhookHandler.SUPPORTED_EVENTS:
                logger.warning(f"Unsupported event type: {event_type}")
                return web.json_response(
                    {"status": "ok", "message": "Event acknowledged"}
                )
            
            logger.info(f"Processing webhook event: {event_type}")
            
            if event_type == "payment.succeeded":
                await YooKassaWebhookHandler._handle_payment_succeeded(data)
            
            elif event_type == "payment.canceled":
                await YooKassaWebhookHandler._handle_payment_canceled(data)
            
            elif event_type == "refund.succeeded":
                await YooKassaWebhookHandler._handle_refund_succeeded(data)
            
            return web.json_response({"status": "ok"})
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {e}")
            return web.json_response(
                {"error": "Invalid JSON"},
                status=400
            )
        
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    @staticmethod
    async def _handle_payment_succeeded(data: dict):
        """Обработить успешный платеж"""
        try:
            payment_obj = data.get("object", {})
            payment_id = payment_obj.get("id")
            status = payment_obj.get("status")
            
            if status != "succeeded":
                logger.warning(f"Payment {payment_id} status is {status}, not succeeded")
                return
            
            # Получаем метаданные платежа
            metadata = payment_obj.get("metadata", {})
            user_id = metadata.get("user_id")
            tunnel_type = metadata.get("tunnel_type")
            duration = metadata.get("duration")
            email = metadata.get("email")
            
            if not all([user_id, tunnel_type, duration, email]):
                logger.error(f"Missing metadata in payment {payment_id}")
                return
            
            logger.info(f"Processing successful payment {payment_id} for user {user_id}")
            
            # Активируем подписку
            success = await YooKassaWebhookHandler._activate_subscription(
                user_id=int(user_id),
                email=email,
                tunnel_type=tunnel_type,
                duration=duration
            )
            
            if success:
                logger.info(f"Subscription activated for user {user_id}")
                
                # Отправляем уведомление пользователю
                await YooKassaWebhookHandler._notify_user_activated(
                    user_id=int(user_id),
                    email=email,
                    tunnel_type=tunnel_type,
                    duration=duration
                )
            else:
                logger.error(f"Failed to activate subscription for user {user_id}")
        
        except Exception as e:
            logger.error(f"Error handling payment.succeeded: {e}", exc_info=True)
    
    @staticmethod
    async def _activate_subscription(
        user_id: int,
        email: str,
        tunnel_type: str,
        duration: str
    ) -> bool:
        """
        Активировать подписку в Xray
        
        Args:
            user_id: ID пользователя
            email: Email для VLESS
            tunnel_type: Тип туннеля
            duration: Длительность подписки
        
        Returns:
            True если подписка активирована
        """
        try:
            from bot_app.config import ServerConfig
            
            # Вычисляем количество дней
            days = 30 if duration == "1_month" else (90 if duration == "3_months" else 365)
            
            # Определяем inbound ID
            inbound_id = 0 if tunnel_type == "single" else 1
            
            # Инициализируем XrayAPI с нужным сервером
            server_config = ServerConfig.NL_SERVER if tunnel_type == "single" else ServerConfig.VK_SERVER
            
            xray = XrayAPI(
                server_ip=server_config["ip"],
                port=server_config["port"],
                username=server_config["username"],
                password=server_config["password"]
            )
            
            # Добавляем клиента в Xray
            success = await xray.add_client(
                inbound_id=inbound_id,
                email=email,
                expiry_days=days,
                tunnel_type=tunnel_type
            )
            
            if not success:
                logger.error(f"Failed to add client {email} to Xray")
                return False
            
            # Генерируем VLESS ссылку
            server_ip = server_config["ip"]
            port = server_config["port"]
            
            vless_link = generate_vless_link(
                uuid=email,
                server_ip=server_ip,
                port=port,
                email=email,
                tunnel_type=tunnel_type
            )
            
            # Сохраняем в БД
            expires_at = (datetime.now() + timedelta(days=days)).timestamp()
            
            await db.add_vpn_key(
                user_id=user_id,
                email=email,
                tunnel_type=tunnel_type,
                vless_link=vless_link,
                expires_at=expires_at
            )
            
            # Отмечаем заказ как завершенный
            await db.complete_order(user_id)
            
            logger.info(f"Subscription activated: user={user_id}, email={email}, days={days}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error activating subscription: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def _notify_user_activated(
        user_id: int,
        email: str,
        tunnel_type: str,
        duration: str
    ):
        """Отправить уведомление пользователю об активации"""
        try:
            from bot_app.config import ServerConfig
            
            tunnel_name = "Базовый туннель" if tunnel_type == "single" else "Двойной туннель"
            
            days = 30 if duration == "1_month" else (90 if duration == "3_months" else 365)
            expiry_date = (datetime.now() + timedelta(days=days)).strftime("%d.%m.%Y")
            
            # Получаем VLESS ссылку из БД
            vpn_keys = await db.get_vpn_keys(user_id)
            vless_link = None
            
            for key in vpn_keys:
                if key[2] == email:  # key[2] это email
                    vless_link = key[3]  # key[3] это vless_link
                    break
            
            if not vless_link:
                logger.warning(f"VLESS link not found for user {user_id}")
                vless_link = "URL не найден"
            
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
            
            if bot:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown"
                )
                logger.info(f"Activation notification sent to user {user_id}")
        
        except Exception as e:
            logger.error(f"Error sending activation notification: {e}")
    
    @staticmethod
    async def _handle_payment_canceled(data: dict):
        """Обработить отмененный платеж"""
        try:
            payment_obj = data.get("object", {})
            payment_id = payment_obj.get("id")
            metadata = payment_obj.get("metadata", {})
            user_id = metadata.get("user_id")
            
            logger.warning(f"Payment {payment_id} was canceled for user {user_id}")
            
            if not user_id or not bot:
                return
            
            message = f"""
❌ **Платеж отменен**

Ваш платеж был отменен или отклонен банком.

**Причины отмены:**
• Отклонение банком
• Недостаточно средств
• Истечение времени ожидания платежа

**Что делать:**
1. Проверьте ваш счет и баланс карты
2. Попробуйте еще раз команду /pay
3. Используйте другой способ оплаты (Stars, Крипто)
4. Обратитесь в поддержку: @support
"""
            
            await bot.send_message(
                chat_id=int(user_id),
                text=message,
                parse_mode="Markdown"
            )
        
        except Exception as e:
            logger.error(f"Error handling payment.canceled: {e}")
    
    @staticmethod
    async def _handle_refund_succeeded(data: dict):
        """Обработить успешный возврат"""
        try:
            refund_obj = data.get("object", {})
            refund_id = refund_obj.get("id")
            payment_id = refund_obj.get("payment_id")
            amount = refund_obj.get("amount", {}).get("value", 0)
            
            logger.info(f"Refund {refund_id} processed for payment {payment_id}, amount: {amount/100}₽")
            
            # Можно добавить логику уведомления пользователя о возврате
        
        except Exception as e:
            logger.error(f"Error handling refund.succeeded: {e}")


# Создаем веб-приложение для обработки вебхуков

def create_webhook_app():
    """Создать веб-приложение для вебхуков"""
    app = web.Application()
    
    # Маршрут для YooKassa вебхуков
    app.router.add_post("/yookassa-webhook", YooKassaWebhookHandler.handle_webhook)
    
    # Маршрут для проверки здоровья
    app.router.add_get("/health", health_check)
    
    return app


async def health_check(request: web.Request) -> web.Response:
    """Проверка здоровья вебхука сервера"""
    return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})


async def run_webhook_server(port: int = 8080):
    """
    Запустить вебхук сервер
    
    Args:
        port: Порт для прослушивания
    """
    app = create_webhook_app()
    runner = web.AppRunner(app)
    
    try:
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Webhook server started on port {port}")
        
        # Бесконечный цикл
        while True:
            await asyncio.sleep(3600)
    
    except Exception as e:
        logger.error(f"Error running webhook server: {e}")
    
    finally:
        await runner.cleanup()


# Интеграция в основной бот

"""
Для интеграции в main.py:

import asyncio
from webhook_handler import run_webhook_server, init_webhook_handler

async def main():
    # ... инициализация существующих компонентов ...
    
    # Инициализируем вебхук обработчик
    init_webhook_handler(
        payment_h=payment_handler,
        database=db,
        bot_instance=bot
    )
    
    # Запускаем вебхук сервер в фоне
    webhook_task = asyncio.create_task(run_webhook_server(port=8080))
    
    # Запускаем основной бот
    await dp.start_polling(bot)

Убедитесь, что:
1. Вебхук сервер доступен из интернета
2. YooKassa настроена на отправку вебхуков на правильный URL
3. Сервер использует HTTPS (обязательно для YooKassa)
4. Настроит порт на сервере/firewall
"""
