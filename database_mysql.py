"""
Модуль для работы с MySQL базой данных
"""

import mysql.connector
from mysql.connector import pooling
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class MySQLDatabase:
    def __init__(self):
        self.config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'database': os.getenv('MYSQL_DATABASE', 'default_db'),
            'user': os.getenv('MYSQL_USER', 'gen_user'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': False
        }
        

        
        # Создаем пул соединений
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="vpn_pool",
                pool_size=5,
                pool_reset_session=True,
                **self.config
            )
            logger.info(f"Подключение к MySQL: {self.config['host']}:{self.config['port']}")
        except Exception as e:
            logger.error(f"Ошибка подключения к MySQL: {e}")
            raise
        
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с БД"""
        conn = None
        try:
            conn = self.pool.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            if conn:
                conn.close()
                
    def add_user(self, telegram_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None) -> bool:
        """Добавление пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name)
                """, (telegram_id, username, first_name, last_name))
                conn.commit()
                logger.info(f"Пользователь {telegram_id} добавлен в БД")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return False
            
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
            
    def create_order(self, user_id: int, plan_id: str, payment_id: str, amount: int) -> Optional[int]:
        """Создание заказа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (user_id, plan_id, payment_id, amount)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, plan_id, payment_id, amount))
                conn.commit()
                order_id = cursor.lastrowid
                logger.info(f"Создан заказ {order_id} для пользователя {user_id}")
                return order_id
        except Exception as e:
            logger.error(f"Ошибка создания заказа: {e}")
            return None
            
    def update_order_status(self, payment_id: str, status: str) -> bool:
        """Обновление статуса заказа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE orders 
                    SET status = %s
                    WHERE payment_id = %s
                """, (status, payment_id))
                conn.commit()
                logger.info(f"Статус заказа {payment_id} обновлен на {status}")
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса заказа: {e}")
            return False
            
    def add_vpn_key(self, user_id: int, order_id: Optional[int], email: str, 
                    config: str, expires_at: datetime, traffic_limit: int) -> bool:
        """Добавление VPN ключа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vpn_keys 
                    (user_id, order_id, email, config, expires_at, traffic_limit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, order_id, email, config, expires_at, traffic_limit))
                conn.commit()
                logger.info(f"VPN ключ добавлен для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления VPN ключа: {e}")
            return False
            
    def get_user_vpn_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение VPN ключей пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT * FROM vpn_keys 
                    WHERE user_id = %s AND is_hidden = FALSE
                    ORDER BY 
                        CASE WHEN expires_at > NOW() AND is_active = TRUE THEN 0 ELSE 1 END,
                        expires_at DESC
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения VPN ключей: {e}")
            return []
            
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Добавление реферала"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO referrals (referrer_id, referred_id)
                    VALUES (%s, %s)
                """, (referrer_id, referred_id))
                conn.commit()
                logger.info(f"Реферал добавлен: {referrer_id} -> {referred_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления реферала: {e}")
            return False
            
    def get_referrals(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение рефералов пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT r.*, u.username, u.first_name 
                    FROM referrals r
                    LEFT JOIN users u ON r.referred_id = u.telegram_id
                    WHERE r.referrer_id = %s
                    ORDER BY r.created_at DESC
                """, (user_id,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения рефералов: {e}")
            return []
            
    def add_referral_earning(self, referrer_id: int, referred_id: int, order_id: int, plan_id: str, amount: int) -> bool:
        """Добавление реферальной выплаты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO referral_earnings (referrer_id, referred_id, order_id, plan_id, amount)
                    VALUES (%s, %s, %s, %s, %s)
                """, (referrer_id, referred_id, order_id, plan_id, amount))
                conn.commit()
                logger.info(f"Реферальная выплата: {referrer_id} получил {amount}₽")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления выплаты: {e}")
            return False
            
    def get_referrer(self, user_id: int) -> Optional[int]:
        """Получение ID реферера"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = %s", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения реферера: {e}")
            return None
            
    def get_total_referral_earnings(self, user_id: int) -> int:
        """Получение общей суммы реферальных выплат"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id = %s", (user_id,))
                result = cursor.fetchone()[0]
                return result or 0
        except Exception as e:
            logger.error(f"Ошибка получения выплат: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """Получение статистики"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
                paid_orders = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM vpn_keys WHERE is_active = TRUE")
                active_keys = cursor.fetchone()[0]
                
                cursor.execute("SELECT SUM(amount) FROM orders WHERE status = 'paid'")
                total_revenue = cursor.fetchone()[0] or 0
                
                return {
                    "total_users": total_users,
                    "paid_orders": paid_orders,
                    "active_keys": active_keys,
                    "total_revenue": total_revenue
                }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
            
    def get_expired_vpn_keys(self) -> List[Dict[str, Any]]:
        """Получение истекших VPN ключей"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT id, email, expires_at FROM vpn_keys 
                    WHERE expires_at < NOW() AND is_active = TRUE
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения истекших ключей: {e}")
            return []
            
    def mark_key_as_deleted(self, key_id: int) -> bool:
        """Пометить ключ как удаленный с сервера"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE vpn_keys SET is_active = FALSE WHERE id = %s", (key_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка пометки ключа как удаленного: {e}")
            return False
            
    def hide_key_from_profile(self, key_id: int) -> bool:
        """Скрыть ключ из профиля пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE vpn_keys SET is_hidden = TRUE WHERE id = %s", (key_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка скрытия ключа: {e}")
            return False
            
    def extend_vpn_key(self, key_id: int, days: int) -> Optional[Dict[str, Any]]:
        """Продление VPN ключа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT * FROM vpn_keys WHERE id = %s", (key_id,))
                key = cursor.fetchone()
                if not key:
                    return None
                
                is_active_and_valid = key['is_active'] and key['expires_at'] > datetime.now()
                
                if is_active_and_valid:
                    cursor.execute("""
                        UPDATE vpn_keys 
                        SET expires_at = DATE_ADD(expires_at, INTERVAL %s DAY)
                        WHERE id = %s
                    """, (days, key_id))
                else:
                    cursor.execute("""
                        UPDATE vpn_keys 
                        SET expires_at = DATE_ADD(NOW(), INTERVAL %s DAY),
                            is_active = TRUE
                        WHERE id = %s
                    """, (days, key_id))
                    
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"VPN ключ {key_id} продлен на {days} дней")
                    return key
                return None
        except Exception as e:
            logger.error(f"Ошибка продления ключа: {e}")
            return None
            
    def create_gift_link(self, gift_code: str, days: int) -> bool:
        """Создание подарочной ссылки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO gift_links (gift_code, days)
                    VALUES (%s, %s)
                """, (gift_code, days))
                conn.commit()
                logger.info(f"Подарочная ссылка создана: {gift_code} на {days} дней")
                return True
        except Exception as e:
            logger.error(f"Ошибка создания подарочной ссылки: {e}")
            return False
            
    def use_gift_link(self, gift_code: str, user_id: int) -> Optional[int]:
        """Использование подарочной ссылки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT days FROM gift_links 
                    WHERE gift_code = %s AND used_by IS NULL
                """, (gift_code,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                    
                days = result[0]
                
                cursor.execute("""
                    UPDATE gift_links 
                    SET used_by = %s, used_at = NOW()
                    WHERE gift_code = %s
                """, (user_id, gift_code))
                conn.commit()
                
                logger.info(f"Подарочная ссылка {gift_code} использована пользователем {user_id}")
                return days
        except Exception as e:
            logger.error(f"Ошибка использования подарочной ссылки: {e}")
            return None

    def get_users_with_referral_earnings(self) -> List[Dict[str, Any]]:
        """Получение пользователей с реферальными деньгами"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT u.telegram_id, u.username, u.first_name, SUM(re.amount) as total_earnings
                    FROM users u
                    JOIN referral_earnings re ON u.telegram_id = re.referrer_id
                    GROUP BY u.telegram_id
                    HAVING total_earnings > 0
                    ORDER BY total_earnings DESC
                """)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка получения пользователей с деньгами: {e}")
            return []
    
    def reset_user_referral_earnings(self, user_id: int) -> bool:
        """Сброс реферальных денег пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM referral_earnings WHERE referrer_id = %s", (user_id,))
                conn.commit()
                logger.info(f"Реферальные деньги сброшены для пользователя {user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка сброса реферальных денег: {e}")
            return False
            
    def has_user_agreed(self, user_id: int) -> bool:
        """Проверка согласия пользователя с соглашением"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_agreements WHERE user_id = %s", (user_id,))
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logger.error(f"Ошибка проверки соглашения: {e}")
            return False
            
    def accept_user_agreement(self, user_id: int) -> bool:
        """Принятие пользовательского соглашения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_agreements (user_id)
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE agreed_at = NOW()
                """, (user_id,))
                conn.commit()
                logger.info(f"Пользователь {user_id} принял соглашение")
                return True
        except Exception as e:
            logger.error(f"Ошибка принятия соглашения: {e}")
            return False

# Глобальный экземпляр базы данных
db = MySQLDatabase()