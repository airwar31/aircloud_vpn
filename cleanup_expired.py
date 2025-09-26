#!/usr/bin/env python3
import asyncio
import logging
import os
from datetime import datetime

# Проверяем обязательные переменные окружения
required_env_vars = ['MYSQL_PASSWORD', 'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_DATABASE']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]

if missing_vars:
    print(f"Отсутствуют переменные окружения: {', '.join(missing_vars)}")
    print("Доступные переменные:")
    for key, value in os.environ.items():
        if 'MYSQL' in key:
            print(f"  {key}={value}")
    exit(1)

# Импорт с обработкой ошибок
try:
    from database_mysql import db
except Exception as e:
    print(f"Ошибка подключения к БД: {e}")
    exit(1)
from xray_manager import XrayManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

XRAY_API_URL = os.getenv("XRAY_API_URL", "http://xray-api:8080")

async def cleanup_expired_keys():
    """Удаление истекших VPN ключей"""
    try:
        # db уже инициализирована в модуле
        
        # Получаем все истекшие ключи
        expired_keys = db.get_expired_vpn_keys()
        
        if not expired_keys:
            logger.info("Нет истекших ключей для удаления")
            return
            
        logger.info(f"Найдено {len(expired_keys)} истекших ключей")
        
        async with XrayManager(XRAY_API_URL) as xray:
            for key in expired_keys:
                try:
                    # Удаляем из Xray
                    success = await xray.remove_client(key['email'])
                    
                    if success:
                        # Помечаем как удаленный в БД
                        db.mark_key_as_deleted(key['id'])
                        logger.info(f"Удален ключ: {key['email']}")
                    else:
                        logger.error(f"Не удалось удалить ключ: {key['email']}")
                        
                except Exception as e:
                    logger.error(f"Ошибка удаления ключа {key['email']}: {e}")
                    
    except Exception as e:
        logger.error(f"Общая ошибка очистки: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_expired_keys())