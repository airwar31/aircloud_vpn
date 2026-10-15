"""
YooKassa webhook handling for payment activation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from aiohttp import web

from bot_app.config import PaymentConfig
from bot_app.database import Database
from bot_app.yookassa_payment import YooKassaWebhookValidator

logger = logging.getLogger(__name__)

payment_handler: Optional[object] = None
db: Optional[Database] = None
bot = None


def init_webhook_handler(payment_h: object, database: Database, bot_instance):
    """Initialize webhook dependencies."""
    global payment_handler, db, bot
    payment_handler = payment_h
    db = database
    bot = bot_instance


class YooKassaWebhookHandler:
    """YooKassa webhook handler."""

    SUPPORTED_EVENTS = {
        "payment.succeeded",
        "payment.canceled",
        "refund.succeeded",
        "payout.succeeded",
    }

    @staticmethod
    def _extract_client_ip(request: web.Request) -> Optional[str]:
        return YooKassaWebhookValidator.extract_client_ip(
            headers=dict(request.headers),
            remote_addr=request.remote,
        )

    @staticmethod
    def _validate_source(request: web.Request) -> bool:
        """
        YooKassa recommends validating webhook source by IP and object status.
        Status validation is performed later in payment_handler via API check.
        """
        if not PaymentConfig.YOOKASSA_VALIDATE_SOURCE:
            logger.warning("YooKassa webhook source validation is disabled")
            return True

        client_ip = YooKassaWebhookHandler._extract_client_ip(request)
        if not client_ip:
            logger.error("Cannot determine webhook source IP")
            return False

        is_trusted = YooKassaWebhookValidator.is_trusted_ip(
            client_ip,
            PaymentConfig.YOOKASSA_TRUSTED_IPS,
        )
        if not is_trusted:
            logger.error(f"Webhook request from untrusted IP: {client_ip}")
            return False

        return True

    @staticmethod
    async def handle_webhook(request: web.Request) -> web.Response:
        """Handle incoming YooKassa webhook request."""
        try:
            body = await request.text()
            data = json.loads(body) if body else {}

            if not YooKassaWebhookHandler._validate_source(request):
                return web.json_response({"error": "Forbidden source"}, status=403)

            event_type = data.get("event")
            if event_type not in YooKassaWebhookHandler.SUPPORTED_EVENTS:
                logger.warning(f"Unsupported event type: {event_type}")
                return web.json_response({"status": "ok", "message": "Event acknowledged"})

            logger.info(f"Processing webhook event: {event_type}")

            if event_type == "payment.succeeded":
                await YooKassaWebhookHandler._handle_payment_succeeded(data)
            elif event_type == "payment.canceled":
                await YooKassaWebhookHandler._handle_payment_canceled(data)
            elif event_type == "refund.succeeded":
                await YooKassaWebhookHandler._handle_refund_succeeded(data)

            return web.json_response({"status": "ok"})

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook")
            return web.json_response({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

    @staticmethod
    async def _handle_payment_succeeded(data: dict):
        payment_obj = data.get("object", {})
        payment_id = payment_obj.get("id")
        status = payment_obj.get("status")
        metadata = payment_obj.get("metadata", {})
        user_id = metadata.get("user_id")

        if status != "succeeded":
            logger.warning(f"Payment {payment_id} has status {status}")
            return

        if not payment_id or not user_id:
            logger.error(f"Missing required metadata for payment {payment_id}")
            return

        if not payment_handler or not hasattr(payment_handler, "check_and_activate_payment"):
            logger.error("Payment handler is not initialized")
            return

        success = await payment_handler.check_and_activate_payment(
            payment_id=payment_id,
            user_id=int(user_id),
        )

        if success:
            logger.info(f"Subscription activated for user {user_id}, payment {payment_id}")
        else:
            logger.error(f"Failed to activate subscription for user {user_id}, payment {payment_id}")

    @staticmethod
    async def _handle_payment_canceled(data: dict):
        payment_obj = data.get("object", {})
        payment_id = payment_obj.get("id")
        metadata = payment_obj.get("metadata", {})
        user_id = metadata.get("user_id")

        logger.warning(f"Payment {payment_id} canceled for user {user_id}")

        if not user_id or not bot:
            return

        message = (
            "❌ **Платеж отменен**\n\n"
            "Ваш платеж был отменен или отклонен банком.\n\n"
            "Попробуйте оплатить повторно командой /pay или выберите другой способ оплаты."
        )

        try:
            await bot.send_message(chat_id=int(user_id), text=message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send canceled-payment notification: {e}")

    @staticmethod
    async def _handle_refund_succeeded(data: dict):
        refund_obj = data.get("object", {})
        refund_id = refund_obj.get("id")
        payment_id = refund_obj.get("payment_id")
        amount = refund_obj.get("amount", {}).get("value", 0)
        logger.info(f"Refund {refund_id} processed for payment {payment_id}, amount={amount}")


def create_webhook_app():
    """Create aiohttp app for webhook handling."""
    app = web.Application()
    app.router.add_post("/yookassa-webhook", YooKassaWebhookHandler.handle_webhook)
    app.router.add_get("/health", health_check)
    return app


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "timestamp": datetime.now().isoformat()})


async def run_webhook_server(port: int = 8080):
    """Run webhook server."""
    app = create_webhook_app()
    runner = web.AppRunner(app)

    try:
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Webhook server started on port {port}")

        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logger.error(f"Error running webhook server: {e}")

    finally:
        await runner.cleanup()
