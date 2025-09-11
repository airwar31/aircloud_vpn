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
                    order_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    config TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    traffic_limit INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id),
                    FOREIGN KEY (order_id) REFERENCES orders (id)
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
            
    def add_vpn_key(self, user_id: int, order_id: int, email: str, 
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
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC
                """, (user_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения VPN ключей: {e}")
            return []
            
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

# Глобальный экземпляр базы данных
db = Database()