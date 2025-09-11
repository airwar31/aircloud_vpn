"""
Webhook для обработки уведомлений от ЮKassa
Используется для автоматической обработки платежей без необходимости проверки статуса вручную
"""

from flask import Flask, request, jsonify
import json
import logging
from yookassa import Configuration, Payment
from database import db
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настройка ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/yookassa/webhook', methods=['POST'])
def yookassa_webhook():
    """Обработчик webhook от ЮKassa"""
    try:
        # Получаем данные от ЮKassa
        data = request.get_json()
        
        if not data:
            logger.error("Пустые данные от ЮKassa")
            return jsonify({"error": "No data"}), 400
            
        # Проверяем тип события
        event_type = data.get('event')
        if event_type != 'payment.succeeded':
            logger.info(f"Игнорируем событие: {event_type}")
            return jsonify({"status": "ignored"}), 200
            
        # Получаем информацию о платеже
        payment_data = data.get('object', {})
        payment_id = payment_data.get('id')
        
        if not payment_id:
            logger.error("Отсутствует ID платежа")
            return jsonify({"error": "No payment ID"}), 400
            
        # Проверяем платеж через API ЮKassa для безопасности
        payment = Payment.find_one(payment_id)
        
        if payment.status != 'succeeded':
            logger.warning(f"Платеж {payment_id} не успешен: {payment.status}")
            return jsonify({"status": "payment_not_succeeded"}), 200
            
        # Обновляем статус заказа в БД
        success = db.update_order_status(payment_id, 'paid')
        
        if success:
            logger.info(f"Заказ для платежа {payment_id} успешно обновлен")
            
            # Здесь можно добавить логику для автоматического создания VPN ключа
            # и отправки уведомления пользователю через Telegram API
            
            return jsonify({"status": "success"}), 200
        else:
            logger.error(f"Не удалось обновить заказ для платежа {payment_id}")
            return jsonify({"error": "Database update failed"}), 500
            
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервиса"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Для разработки
    app.run(host='0.0.0.0', port=5000, debug=True)
    
    # Для продакшена рекомендуется использовать gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 webhook:app