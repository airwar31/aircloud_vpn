#!/usr/bin/env python3
"""
Тест YooKassa API для диагностики проблем
"""
import os
import sys
from dotenv import load_dotenv
from yookassa import Configuration, Payment
import uuid
import logging

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_yookassa():
    """Тест подключения к YooKassa"""
    
    # Проверяем переменные окружения
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    if not shop_id:
        logger.error("YOOKASSA_SHOP_ID не найден в .env")
        return False
        
    if not secret_key:
        logger.error("YOOKASSA_SECRET_KEY не найден в .env")
        return False
    
    logger.info(f"Shop ID: {shop_id}")
    logger.info(f"Secret Key: {secret_key[:10]}...")
    
    # Настраиваем YooKassa
    Configuration.account_id = shop_id
    Configuration.secret_key = secret_key
    
    try:
        # Создаем тестовый платеж
        payment_data = {
            "amount": {
                "value": "1.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/test"
            },
            "capture": True,
            "description": "Тестовый платеж",
            "metadata": {
                "user_id": "test"
            }
        }
        
        logger.info(f"Создаем тестовый платеж: {payment_data}")
        
        payment = Payment.create(payment_data, uuid.uuid4())
        
        logger.info(f"✅ Платеж создан успешно!")
        logger.info(f"ID: {payment.id}")
        logger.info(f"Статус: {payment.status}")
        logger.info(f"URL: {payment.confirmation.confirmation_url}")
        
        # Отменяем тестовый платеж
        try:
            Payment.cancel(payment.id, uuid.uuid4())
            logger.info("✅ Тестовый платеж отменен")
        except:
            logger.info("ℹ️ Не удалось отменить платеж (это нормально)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания платежа: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        
        # Дополнительная диагностика
        if "400" in str(e):
            logger.error("Ошибка 400 - проверьте правильность данных")
        elif "401" in str(e):
            logger.error("Ошибка 401 - проверьте shop_id и secret_key")
        elif "403" in str(e):
            logger.error("Ошибка 403 - проверьте права доступа")
        
        return False

def check_credentials():
    """Проверка корректности учетных данных"""
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    logger.info("=== Проверка учетных данных ===")
    
    # Проверяем формат shop_id
    if shop_id and shop_id.isdigit():
        logger.info(f"✅ Shop ID корректен: {shop_id}")
    else:
        logger.error(f"❌ Shop ID некорректен: {shop_id}")
        return False
    
    # Проверяем формат secret_key
    if secret_key and (secret_key.startswith("live_") or secret_key.startswith("test_")):
        logger.info(f"✅ Secret Key корректен: {secret_key[:15]}...")
    else:
        logger.error(f"❌ Secret Key некорректен: {secret_key}")
        return False
    
    return True

if __name__ == "__main__":
    logger.info("=== Диагностика YooKassa ===")
    
    if not check_credentials():
        sys.exit(1)
    
    if test_yookassa():
        logger.info("✅ YooKassa работает корректно!")
    else:
        logger.error("❌ Проблемы с YooKassa")
        sys.exit(1)