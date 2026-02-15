"""
YooKassa Payment Integration
Polled API интеграция с платежной системой YooKassa (Юкасса)
"""

import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)


class YooKassaAPI:
    """
    YooKassa (Юкасса) платежная система
    Документация: https://yookassa.ru/developers/api
    """
    
    # YooKassa endpoints
    API_URL = "https://api.yookassa.ru/v3"
    
    def __init__(
        self,
        shop_id: str,
        secret_key: str,
        timeout: int = 30,
        retries: int = 3
    ):
        """
        Инициализация YooKassa API
        
        Args:
            shop_id: ID магазина (из личного кабинета YooKassa)
            secret_key: Секретный ключ (из личного кабинета YooKassa)
            timeout: Таймаут запроса
            retries: Количество повторов при ошибке
        """
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.timeout = timeout
        self.retries = retries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_auth_header(self) -> str:
        """
        Генерирует Basic Auth заголовок для YooKassa
        Формат: Basic base64(shopId:secretKey)
        """
        credentials = f"{self.shop_id}:{self.secret_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def create_payment(
        self,
        amount: int,
        currency: str = "RUB",
        description: str = "",
        email: str = "",
        phone: str = "",
        return_url: str = "",
        customer_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Создать платеж через YooKassa
        
        Args:
            amount: Сумма в копейках (например, 15000 для 150 рублей)
            currency: Валюта (RUB по умолчанию)
            description: Описание платежа
            email: Email плательщика
            phone: Номер телефона плательщика
            return_url: URL для возврата после платежа
            customer_id: ID клиента
            metadata: Дополнительные данные (например, user_id, tunnel_type)
        
        Returns:
            dict с информацией о платеже или None если ошибка
        """
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            # Формируем тело запроса
            payload = {
                "amount": {
                    "value": amount / 100,  # YooKassa требует рубли, а не копейки
                    "currency": currency
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or "https://yoursite.com/return"
                },
                "description": description,
                "metadata": metadata or {}
            }
            
            # Добавляем опциональные поля
            if email:
                payload["receipt"] = {
                    "customer": {
                        "email": email
                    }
                }
            
            if phone:
                if "receipt" not in payload:
                    payload["receipt"] = {"customer": {}}
                payload["receipt"]["customer"]["phone"] = phone
            
            if customer_id:
                payload["metadata"]["customer_id"] = customer_id
            
            # Отправляем запрос
            headers = {
                "Authorization": self._get_auth_header(),
                "Idempotency-Key": str(uuid4()),  # Уникальный ключ для идемпотентности
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                f"{self.API_URL}/payments",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info(f"Payment created: {data.get('id')}")
                    return data
                else:
                    logger.error(f"YooKassa error: {response.status} - {data}")
                    return None
        
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None
    
    async def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить информацию о платеже
        
        Args:
            payment_id: ID платежа от YooKassa
        
        Returns:
            dict с информацией о платеже или None если ошибка
        """
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            headers = {
                "Authorization": self._get_auth_header(),
                "Content-Type": "application/json"
            }
            
            async with self.session.get(
                f"{self.API_URL}/payments/{payment_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data
                else:
                    logger.error(f"Failed to get payment: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error getting payment: {e}")
            return None
    
    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[int] = None,
        description: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Вернуть деньги (полный или частичный возврат)
        
        Args:
            payment_id: ID платежа для возврата
            amount: Сумма возврата в копейках (None = полный возврат)
            description: Причина возврата
        
        Returns:
            dict с информацией о возврате или None если ошибка
        """
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            payload = {
                "payment_id": payment_id,
                "description": description
            }
            
            if amount:
                payload["amount"] = {
                    "value": amount / 100,
                    "currency": "RUB"
                }
            
            headers = {
                "Authorization": self._get_auth_header(),
                "Idempotency-Key": str(uuid4()),
                "Content-Type": "application/json"
            }
            
            async with self.session.post(
                f"{self.API_URL}/refunds",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    logger.info(f"Refund created: {data.get('id')}")
                    return data
                else:
                    logger.error(f"Refund error: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return None
    
    async def check_payment_status(self, payment_id: str) -> Optional[str]:
        """
        Проверить статус платежа
        
        Args:
            payment_id: ID платежа
        
        Returns:
            Статус платежа ('succeeded', 'pending', 'failed', 'canceled') или None если ошибка
        """
        try:
            payment = await self.get_payment(payment_id)
            if payment:
                status = payment.get("status")
                logger.info(f"Payment {payment_id} status: {status}")
                return status
            return None
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return None
    
    async def list_payments(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> Optional[list]:
        """
        Получить список платежей
        
        Args:
            limit: Количество результатов (до 100)
            offset: Смещение
            status: Фильтр по статусу ('succeeded', 'pending', 'failed', 'canceled')
        
        Returns:
            list платежей или None если ошибка
        """
        try:
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            params = {
                "limit": min(limit, 100),
                "offset": offset
            }
            
            if status:
                params["status"] = status
            
            headers = {
                "Authorization": self._get_auth_header(),
                "Content-Type": "application/json"
            }
            
            async with self.session.get(
                f"{self.API_URL}/payments",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return data.get("items", [])
                else:
                    logger.error(f"Failed to list payments: {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error listing payments: {e}")
            return None


class YooKassaWebhookValidator:
    """
    Валидатор вебхуков от YooKassa
    Проверяет подпись и целостность данных
    """
    
    @staticmethod
    def validate_webhook(
        event_data: Dict[str, Any],
        signature: str,
        secret_key: str
    ) -> bool:
        """
        Проверить подпись вебхука
        
        Args:
            event_data: Данные события из YooKassa
            signature: Подпись из заголовка (X-Yookassa-Signature)
            secret_key: Секретный ключ
        
        Returns:
            True если вебхук валиден, False иначе
        """
        import json
        import hashlib
        import hmac
        
        try:
            # Преобразуем данные в JSON
            data_str = json.dumps(event_data, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
            
            # Ключ для HMAC - это секретный ключ
            expected_signature = hashlib.sha256(
                (data_str + secret_key).encode()
            ).hexdigest()
            
            # Сравниваем подписи
            return hmac.compare_digest(signature, expected_signature)
        
        except Exception as e:
            logger.error(f"Error validating webhook: {e}")
            return False


# Вспомогательные функции для работы с суммами

def rubles_to_kopeks(rubles: float) -> int:
    """Сумму в рублях в копейки"""
    return int(rubles * 100)


def kopeks_to_rubles(kopeks: int) -> float:
    """Сумму в копейких в рубли"""
    return kopeks / 100


def format_payment_amount(kopeks: int) -> str:
    """Форматировать сумму для отображения (e.g., '150.00₽')"""
    rubles = kopeks_to_rubles(kopeks)
    return f"{rubles:.2f}₽"
