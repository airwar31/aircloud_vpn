import logging
import uuid
from datetime import datetime

from yookassa import Configuration, Payment
from yookassa.domain.notification import WebhookNotification

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL

logger = logging.getLogger(__name__)

# Инициализация ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

class YooKassaPayment:
    """Класс для работы с ЮKassa API"""
    
    @staticmethod
    async def create_payment(amount, description, user_id, days=30):
        """Создание платежа через ЮKassa"""
        try:
            idempotence_key = str(uuid.uuid4())
            
            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": YOOKASSA_RETURN_URL
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "days": str(days),
                    "timestamp": datetime.now().isoformat()
                }
            }, idempotence_key)
            
            logger.info(f"Создан платеж ЮKassa: {payment.id}, сумма: {amount}, пользователь: {user_id}, дней: {days}")
            
            return {
                "payment_id": payment.id,
                "payment_url": payment.confirmation.confirmation_url,
                "amount": amount,
                "description": description,
                "status": payment.status,
                "days": days
            }
        
        except Exception as e:
            logger.error(f"Ошибка при создании платежа ЮKassa: {str(e)}")
            return None
    
    @staticmethod
    async def check_payment(payment_id):
        """Проверка статуса платежа через ЮKassa"""
        try:
            payment = Payment.find_one(payment_id)
            
            logger.info(f"Проверка платежа ЮKassa: {payment_id}, статус: {payment.status}")
            
            return {
                "status": payment.status,
                "payment_id": payment_id,
                "metadata": payment.metadata
            }
        
        except Exception as e:
            logger.error(f"Ошибка при проверке платежа ЮKassa: {str(e)}")
            return None
    
    @staticmethod
    def process_webhook(request_body):
        """Обработка уведомления от ЮKassa"""
        try:
            notification_object = WebhookNotification(request_body)
            payment = notification_object.object
            
            logger.info(f"Получено уведомление от ЮKassa: {payment.id}, статус: {payment.status}")
            
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "metadata": payment.metadata
            }
        
        except Exception as e:
            logger.error(f"Ошибка при обработке уведомления от ЮKassa: {str(e)}")
            return None