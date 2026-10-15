#!/usr/bin/env python3
"""
Скрипт для ручного подтверждения (capture) YooKassa платежа
Использование: python capture_payment.py PAYMENT_ID
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv('.env')

async def capture_payment(payment_id: str):
    """Подтвердить платеж"""
    from bot_app.yookassa_payment import YooKassaAPI

    shop_id = os.getenv('YOOKASSA_SHOP_ID')
    secret_key = os.getenv('YOOKASSA_SECRET_KEY')

    if not shop_id or not secret_key:
        print("❌ YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY не установлены в .env")
        return

    print(f"🔄 Подтверждаю платеж {payment_id}...")

    async with YooKassaAPI(shop_id, secret_key) as yookassa:
        # Проверяем текущий статус
        status = await yookassa.check_payment_status(payment_id)
        print(f"📊 Текущий статус: {status}")

        if status == "waiting_for_capture":
            print("⏳ Подтверждаю платеж...")
            result = await yookassa.capture_payment(payment_id)

            if result:
                new_status = result.get('status')
                print(f"✅ Платеж подтвержден! Новый статус: {new_status}")

                if new_status == "succeeded":
                    print("\n🎉 Платеж успешно завершен!")
                    print("Теперь можно нажать 'Проверить оплату' в боте")
            else:
                print("❌ Ошибка при подтверждении платежа")
        elif status == "succeeded":
            print("✅ Платеж уже подтвержден!")
        else:
            print(f"⚠️ Платеж в статусе {status}, подтверждение невозможно")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python capture_payment.py PAYMENT_ID")
        print("\nПример:")
        print("python capture_payment.py 3129b014-000f-5001-8000-12f0cde1f282")
        sys.exit(1)

    payment_id = sys.argv[1]
    asyncio.run(capture_payment(payment_id))
