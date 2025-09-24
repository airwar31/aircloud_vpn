#!/usr/bin/env python3
"""
Исправление проблем с YooKassa
"""
import os
import requests
import json
import uuid
import base64
from dotenv import load_dotenv

load_dotenv()

def fix_yookassa_request():
    """Исправленный запрос к YooKassa"""
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    
    # Создаем правильные заголовки
    auth_string = f"{shop_id}:{secret_key}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json',
        'Idempotence-Key': str(uuid.uuid4())
    }
    
    # Правильный формат данных
    data = {
        "amount": {
            "value": "99.00",  # Минимум 1 рубль
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/test"
        },
        "capture": True,
        "description": "VPN подписка"
    }
    
    try:
        response = requests.post(
            'https://api.yookassa.ru/v3/payments',
            headers=headers,
            data=json.dumps(data)
        )
        
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.text}")
        
        if response.status_code == 200:
            payment = response.json()
            print(f"✅ Платеж создан: {payment['id']}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

if __name__ == "__main__":
    fix_yookassa_request()