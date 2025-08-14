import uuid
import requests
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class YooKassaPayment:
    def __init__(self, shop_id: str, secret_key: str):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.base_url = "https://api.yookassa.ru/v3"
        
    def create_payment(self, amount: float, description: str, user_id: int, 
                      plan_id: str, return_url: str = None) -> Dict:
        """Создание платежа в ЮKassa"""
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://your-site.com/success"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "plan_id": plan_id
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4())
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/payments",
                json=payment_data,
                headers=headers,
                auth=(self.shop_id, self.secret_key)
            )
            
            if response.status_code == 200:
                payment_info = response.json()
                logger.info(f"Платеж создан: {payment_info['id']}")
                return {
                    "success": True,
                    "payment_id": payment_info["id"],
                    "payment_url": payment_info["confirmation"]["confirmation_url"],
                    "status": payment_info["status"]
                }
            else:
                logger.error(f"Ошибка создания платежа: {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Исключение при создании платежа: {e}")
            return {"success": False, "error": str(e)}
    
    def check_payment_status(self, payment_id: str) -> Dict:
        """Проверка статуса платежа"""
        
        try:
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}",
                auth=(self.shop_id, self.secret_key)
            )
            
            if response.status_code == 200:
                payment_info = response.json()
                return {
                    "success": True,
                    "status": payment_info["status"],
                    "paid": payment_info["status"] == "succeeded",
                    "amount": float(payment_info["amount"]["value"]),
                    "metadata": payment_info.get("metadata", {})
                }
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Ошибка проверки статуса платежа: {e}")
            return {"success": False, "error": str(e)}
    
    def process_webhook(self, webhook_data: Dict) -> Dict:
        """Обработка webhook от ЮKassa"""
        
        try:
            event_type = webhook_data.get("event")
            payment_object = webhook_data.get("object", {})
            
            if event_type == "payment.succeeded":
                payment_id = payment_object.get("id")
                metadata = payment_object.get("metadata", {})
                amount = float(payment_object.get("amount", {}).get("value", 0))
                
                return {
                    "success": True,
                    "event": "payment_succeeded",
                    "payment_id": payment_id,
                    "user_id": int(metadata.get("user_id", 0)),
                    "plan_id": metadata.get("plan_id"),
                    "amount": amount
                }
            
            elif event_type == "payment.canceled":
                return {
                    "success": True,
                    "event": "payment_canceled",
                    "payment_id": payment_object.get("id")
                }
            
            return {"success": False, "error": "Unknown event type"}
            
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return {"success": False, "error": str(e)}