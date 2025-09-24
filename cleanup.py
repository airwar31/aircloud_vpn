#!/usr/bin/env python3
"""
Скрипт очистки базы данных и конфигурации Xray
Удаляет всех клиентов из Xray и очищает базу данных
"""

import asyncio
import logging
import os
from datetime import datetime

from database_mysql import db
from xray_manager import XrayManager
from config import XRAY_API_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self):
        self.xray_manager = None
        
    async def cleanup_xray_clients(self):
        """Удаление всех клиентов из Xray"""
        try:
            async with XrayManager(XRAY_API_URL) as xray:
                # Получаем все VPN ключи из БД
                with db.get_connection() as conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT email FROM vpn_keys WHERE is_active = TRUE")
                    keys = cursor.fetchall()
                
                removed_count = 0
                for key in keys:
                    email = key['email']
                    if await xray.remove_client(email):
                        logger.info(f"Удален клиент: {email}")
                        removed_count += 1
                    else:
                        logger.warning(f"Не удалось удалить клиента: {email}")
                
                logger.info(f"Удалено клиентов из Xray: {removed_count}")
                return removed_count
                
        except Exception as e:
            logger.error(f"Ошибка очистки Xray: {e}")
            return 0
    
    def cleanup_database(self):
        """Очистка базы данных"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Очищаем таблицы в правильном порядке (учитывая внешние ключи)
                tables_to_clean = [
                    'referral_earnings',
                    'referrals', 
                    'vpn_keys',
                    'orders',
                    'gift_links',
                    'user_agreements',
                    'users'
                ]
                
                total_deleted = 0
                for table in tables_to_clean:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    
                    if count > 0:
                        cursor.execute(f"DELETE FROM {table}")
                        deleted = cursor.rowcount
                        total_deleted += deleted
                        logger.info(f"Очищена таблица {table}: удалено {deleted} записей")
                
                # Сбрасываем AUTO_INCREMENT
                for table in tables_to_clean:
                    try:
                        cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                    except Exception:
                        pass  # Игнорируем ошибки для таблиц без AUTO_INCREMENT
                
                conn.commit()
                logger.info(f"База данных очищена. Всего удалено записей: {total_deleted}")
                return total_deleted
                
        except Exception as e:
            logger.error(f"Ошибка очистки БД: {e}")
            return 0
    
    async def full_cleanup(self):
        """Полная очистка системы"""
        logger.info("🧹 Начинаем полную очистку системы...")
        
        # Очищаем Xray
        xray_removed = await self.cleanup_xray_clients()
        
        # Очищаем БД
        db_removed = self.cleanup_database()
        
        logger.info("✅ Очистка завершена!")
        logger.info(f"📊 Статистика:")
        logger.info(f"   - Удалено клиентов Xray: {xray_removed}")
        logger.info(f"   - Удалено записей БД: {db_removed}")
        
        return xray_removed, db_removed

async def main():
    """Главная функция"""
    print("🧹 Скрипт очистки VPN системы")
    print("⚠️  ВНИМАНИЕ: Это действие удалит ВСЕ данные!")
    
    # Запрашиваем подтверждение
    confirm = input("Вы уверены? Введите 'YES' для подтверждения: ")
    if confirm != 'YES':
        print("❌ Очистка отменена")
        return
    
    # Дополнительное подтверждение
    confirm2 = input("Последнее предупреждение! Введите 'CONFIRM' для продолжения: ")
    if confirm2 != 'CONFIRM':
        print("❌ Очистка отменена")
        return
    
    cleanup = CleanupService()
    
    try:
        await cleanup.full_cleanup()
        print("\n🎉 Система успешно очищена!")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Ошибка очистки: {e}")

if __name__ == "__main__":
    asyncio.run(main())