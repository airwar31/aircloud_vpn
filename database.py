"""
Модуль для работы с базой данных
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "vpn_bot.db"):
        self.db_path = db_path
        self.init_db()
        
    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Таблица заказов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    payment_id TEXT UNIQUE NOT NULL,
                    amount INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            """)
            
            # Таблица VPN ключей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vpn_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER,
                    email TEXT NOT NULL,
                    config TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    traffic_limit INTEGER NOT NULL,
                    device_limit INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT 1,
                    is_hidden BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (order_id) REFERENCES orders (id)
                )
            """)
            
            # Добавляем поле is_hidden если его нет
            try:
                cursor.execute("""
                    ALTER TABLE vpn_keys ADD COLUMN is_hidden BOOLEAN DEFAULT 0
                """)
            except Exception:
                # Поле уже существует
                pass
            
            # Таблица рефералов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    bonus_amount INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (referred_id) REFERENCES users (telegram_id)
                )
            """)
            
            # Таблица реферальных выплат
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_earnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    order_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (referrer_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (referred_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (order_id) REFERENCES orders (id)
                )
            """)
            
            # Таблица подарочных ссылок
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gift_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gift_code TEXT UNIQUE NOT NULL,
                    days INTEGER NOT NULL,
                    is_used BOOLEAN DEFAULT 0,
                    used_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMP,
                    FOREIGN KEY (used_by) REFERENCES users (telegram_id)
                )
            """)
            
            # Таблица уведомлений об истечении
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expiry_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_id INTEGER NOT NULL,
                    notification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (key_id) REFERENCES vpn_keys (id)
                )
            """)
            
            conn.commit()
            logger.info("База данных инициализирована")
            
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            conn.close()
            
    def add_user(self, telegram_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None) -> bool:
        """Добавление пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO users 
                    (telegram_id, username, first_name, last_name)
                    VALUES (?, ?, ?, ?)
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
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
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
                    VALUES (?, ?, ?, ?)
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
                paid_at = datetime.now() if status == 'paid' else None
                cursor.execute("""
                    UPDATE orders 
                    SET status = ?, paid_at = ?
                    WHERE payment_id = ?
                """, (status, paid_at, payment_id))
                conn.commit()
                logger.info(f"Статус заказа {payment_id} обновлен на {status}")
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса заказа: {e}")
            return False
            
    def get_order_by_payment_id(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Получение заказа по payment_id"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM orders WHERE payment_id = ?", (payment_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения заказа: {e}")
            return None
            
    def add_vpn_key(self, user_id: int, order_id: Optional[int], email: str, 
                    config: str, expires_at: datetime, traffic_limit: int) -> bool:
        """Добавление VPN ключа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO vpn_keys 
                    (user_id, order_id, email, config, expires_at, traffic_limit)
                    VALUES (?, ?, ?, ?, ?, ?)
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
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vpn_keys 
                    WHERE user_id = ? AND is_hidden = 0
                    ORDER BY 
                        CASE WHEN expires_at > datetime('now') AND is_active = 1 THEN 0 ELSE 1 END,
                        expires_at DESC
                """, (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения VPN ключей: {e}")
            return []
            
    def add_referral(self, referrer_id: int, referred_id: int, bonus_amount: int = 0) -> bool:
        """Добавление реферала"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, bonus_amount)
                    VALUES (?, ?, ?)
                """, (referrer_id, referred_id, bonus_amount))
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
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT r.*, u.username, u.first_name 
                    FROM referrals r
                    LEFT JOIN users u ON r.referred_id = u.telegram_id
                    WHERE r.referrer_id = ?
                    ORDER BY r.created_at DESC
                """, (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения рефералов: {e}")
            return []
            
    def get_referral_bonus(self, user_id: int) -> int:
        """Получение суммы реферального бонуса"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT SUM(bonus_amount) FROM referrals WHERE referrer_id = ?
                """, (user_id,))
                result = cursor.fetchone()[0]
                return result or 0
        except Exception as e:
            logger.error(f"Ошибка получения бонуса: {e}")
            return 0
            
    def add_referral_earning(self, referrer_id: int, referred_id: int, order_id: int, plan_id: str, amount: int) -> bool:
        """Добавление реферальной выплаты"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO referral_earnings (referrer_id, referred_id, order_id, plan_id, amount)
                    VALUES (?, ?, ?, ?, ?)
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
                cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (user_id,))
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
                cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id = ?", (user_id,))
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
                
                # Общее количество пользователей
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
                
                # Количество заказов
                cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
                paid_orders = cursor.fetchone()[0]
                
                # Активные VPN ключи
                cursor.execute("SELECT COUNT(*) FROM vpn_keys WHERE is_active = 1")
                active_keys = cursor.fetchone()[0]
                
                # Общая выручка
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
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email, expires_at FROM vpn_keys 
                    WHERE expires_at < datetime('now') AND is_active = 1
                """)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения истекших ключей: {e}")
            return []
            
    def get_expiring_vpn_keys(self, days_before: int = 3) -> List[Dict[str, Any]]:
        """Получение VPN ключей, которые скоро истекут"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT v.*, u.telegram_id, u.first_name 
                    FROM vpn_keys v
                    JOIN users u ON v.user_id = u.telegram_id
                    WHERE v.is_active = 1 
                    AND v.expires_at > datetime('now')
                    AND v.expires_at <= datetime('now', '+{} days')
                    AND v.id NOT IN (
                        SELECT key_id FROM expiry_notifications 
                        WHERE notification_date > datetime('now', '-1 day')
                    )
                """.format(days_before))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения истекающих ключей: {e}")
            return []
            
    def mark_notification_sent(self, key_id: int) -> bool:
        """Отметить что уведомление отправлено"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO expiry_notifications (key_id, notification_date)
                    VALUES (?, datetime('now'))
                """, (key_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка отметки уведомления: {e}")
            return False
            
    def mark_key_as_deleted(self, key_id: int) -> bool:
        """Пометить ключ как удаленный с сервера"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE vpn_keys SET is_active = 0 WHERE id = ?",
                    (key_id,)
                )
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
                cursor.execute(
                    "UPDATE vpn_keys SET is_hidden = 1 WHERE id = ?",
                    (key_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка скрытия ключа: {e}")
            return False
            
    def extend_vpn_key(self, key_id: int, days: int) -> Optional[Dict[str, Any]]:
        """Продление VPN ключа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем данные ключа
                cursor.execute("SELECT * FROM vpn_keys WHERE id = ?", (key_id,))
                key = cursor.fetchone()
                if not key:
                    return None
                
                # Проверяем, активен ли ключ и не истек ли он
                expires_at = datetime.fromisoformat(key['expires_at'].replace('Z', '+00:00'))
                is_active_and_valid = key['is_active'] == 1 and expires_at > datetime.now()
                
                if is_active_and_valid:
                    # Активный ключ - добавляем дни к текущей дате истечения
                    cursor.execute("""
                        UPDATE vpn_keys 
                        SET expires_at = datetime(expires_at, '+{} days')
                        WHERE id = ?
                    """.format(days), (key_id,))
                else:
                    # Неактивный или истекший ключ - считаем от текущего времени
                    cursor.execute("""
                        UPDATE vpn_keys 
                        SET expires_at = datetime('now', '+{} days'),
                            is_active = 1
                        WHERE id = ?
                    """.format(days), (key_id,))
                    
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"VPN ключ {key_id} продлен на {days} дней")
                    return dict(key)
                return None
        except Exception as e:
            logger.error(f"Ошибка продления ключа: {e}")
            return None
            
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE is_active = 1")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []
            
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по username"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения пользователя по username: {e}")
            return None
            
    def get_total_referrals(self) -> int:
        """Получение общего количества рефералов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM referrals")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка получения количества рефералов: {e}")
            return 0
            
    def get_total_referral_payouts(self) -> int:
        """Получение общей суммы реферальных выплат"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(amount) FROM referral_earnings")
                result = cursor.fetchone()[0]
                return result or 0
        except Exception as e:
            logger.error(f"Ошибка получения суммы выплат: {e}")
            return 0
            
    def get_user_vpn_keys_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Получение VPN ключей по email"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM vpn_keys
                    WHERE email = ? AND is_active = 1
                """, (email,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения VPN ключей по email: {e}")
            return []
            
    def create_gift_link(self, gift_code: str, days: int) -> bool:
        """Создание подарочной ссылки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO gift_links (gift_code, days)
                    VALUES (?, ?)
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
                
                # Проверяем, существует ли код и не использован ли он
                cursor.execute("""
                    SELECT days FROM gift_links 
                    WHERE gift_code = ? AND is_used = 0
                """, (gift_code,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                    
                days = result[0]
                
                # Отмечаем как использованный
                cursor.execute("""
                    UPDATE gift_links 
                    SET is_used = 1, used_by = ?, used_at = CURRENT_TIMESTAMP
                    WHERE gift_code = ?
                """, (user_id, gift_code))
                conn.commit()
                
                logger.info(f"Подарочная ссылка {gift_code} использована пользователем {user_id}")
                return days
        except Exception as e:
            logger.error(f"Ошибка использования подарочной ссылки: {e}")
            return None

# Глобальный экземпляр базы данных
db = Database("/shared/vpn_bot.db")