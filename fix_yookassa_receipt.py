#!/usr/bin/env python3
"""
Исправление YooKassa с добавлением чека
"""
import os
import requests
import json
import uuid
import base64
from dotenv import load_dotenv

load_dotenv()

def test_yookassa_with_receipt():
    shop_id = os.getenv('YOOKASSA_SHOP_ID')
    secret_key = os.getenv('YOOKASSA_SECRET_KEY')
    
    auth_string = f'{shop_id}:{secret_key}'
    auth_b64 = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json',
        'Idempotence-Key': str(uuid.uuid4())
    }
    
    # Добавляем чек
    data = {
        'amount': {
            'value': '99.00',
            'currency': 'RUB'
        },
        'confirmation': {
            'type': 'redirect',
            'return_url': 'https://t.me/vpn_aircloud_bot'
        },
        'capture': True,
        'description': 'VPN подписка 1 месяц',
        'receipt': {
            'customer': {
                'email': 'customer@example.com'
            },
            'items': [{
                'description': 'VPN подписка 1 месяц',
                'quantity': '1.00',
                'amount': {
                    'value': '99.00',
                    'currency': 'RUB'
                },
                'vat_code': 1
            }]
        }
    }
    
    response = requests.post(
        'https://api.yookassa.ru/v3/payments',
        headers=headers,
        data=json.dumps(data)
    )
    
    print(f'Статус: {response.status_code}')
    print(f'Ответ: {response.text}')
    
    if response.status_code == 200:
        payment = response.json()
        print(f'✅ Платеж создан: {payment["id"]}')
        return True
    else:
        print('❌ Ошибка создания платежа')
        return False

if __name__ == "__main__":
    test_yookassa_with_receipt()