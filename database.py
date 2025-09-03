import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "aircloud_vpn.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Для доступа по именам колонок
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица подписок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                devices INTEGER DEFAULT 1,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                xray_uuid TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Добавляем колонку devices для существующих таблиц
        try:
            cursor.execute('ALTER TABLE subscriptions ADD COLUMN devices INTEGER DEFAULT 1')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        # Индекс для уникальности UUID
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_xray_uuid 
            ON subscriptions(xray_uuid) WHERE xray_uuid IS NOT NULL
        ''')
        
        # Таблица активных сессий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                xray_uuid TEXT NOT NULL,
                client_ip TEXT,
                device_fingerprint TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (xray_uuid) REFERENCES subscriptions(xray_uuid)
            )
        ''')
        
        # Индекс для быстрого поиска сессий
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_uuid 
            ON active_sessions(xray_uuid)
        ''')
        
        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                payment_id TEXT UNIQUE NOT NULL,
                plan_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_user(self, telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None) -> int:
        """Создание пользователя"""
        # Проверяем, что это не бот или канал
        if telegram_id < 0:  # Каналы и группы имеют отрицательные ID
            logger.warning(f"Попытка создать пользователя с отрицательным ID: {telegram_id}")
            return None
        
        # Проверяем диапазон пользовательских ID (1-9999999999)
        if telegram_id > 9999999999:
            logger.warning(f"Подозрительный ID: {telegram_id}")
            return None
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            
            if cursor.rowcount == 0:
                # Пользователь уже существует, обновляем данные
                cursor.execute('''
                    UPDATE users SET username = ?, first_name = ?, last_name = ?
                    WHERE telegram_id = ?
                ''', (username, first_name, last_name, telegram_id))
                logger.info(f"Обновлены данные пользователя {telegram_id}")
            
            conn.commit()
            
            # Получаем ID пользователя
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            user_id = cursor.fetchone()[0]
            
            logger.info(f"Создан пользователь {telegram_id} с ID {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            return None
        finally:
            conn.close()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'created_at': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
        finally:
            conn.close()
    
    async def create_subscription(self, user_id: int, plan_id: str, 
                                duration_days: int, devices: int = 1) -> Dict:
        """Создание подписки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=duration_days)
            
            cursor.execute('''
                INSERT INTO subscriptions (user_id, plan_id, devices, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, plan_id, devices, start_date, end_date))
            
            subscription_id = cursor.lastrowid
            conn.commit()
            
            return {
                'id': subscription_id,
                'user_id': user_id,
                'plan_id': plan_id,
                'start_date': start_date,
                'end_date': end_date,
                'active': True
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания подписки: {e}")
            return None
        finally:
            conn.close()
    
    async def get_user_subscription(self, telegram_id: int) -> Optional[Dict]:
        """Получение активной подписки пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.* FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ? AND s.is_active = TRUE AND s.end_date > ?
                ORDER BY s.end_date DESC LIMIT 1
            ''', (telegram_id, datetime.now()))
            
            row = cursor.fetchone()
            
            if row:
                # Безопасное преобразование дат
                def safe_datetime(date_value):
                    if isinstance(date_value, datetime):
                        return date_value
                    if isinstance(date_value, str):
                        try:
                            return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        except:
                            try:
                                return datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')
                            except:
                                return datetime.now()
                    return datetime.now()
                
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'plan_id': row[2],
                    'devices': row[3] if len(row) > 7 else 1,
                    'start_date': safe_datetime(row[4]),
                    'expiry_date': safe_datetime(row[5]),
                    'active': row[6],
                    'xray_uuid': row[7] if len(row) > 7 else row[6]
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения подписки: {e}")
            return None
        finally:
            conn.close()
    
    async def update_subscription_xray_uuid(self, subscription_id: int, xray_uuid: str):
        """Обновление UUID Xray для подписки"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE subscriptions SET xray_uuid = ? WHERE id = ?
            ''', (xray_uuid, subscription_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Ошибка обновления UUID: {e}")
        finally:
            conn.close()
    
    async def create_payment(self, user_id: int, amount: float, 
                           payment_id: str, plan_id: str) -> int:
        """Создание записи о платеже"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO payments (user_id, amount, payment_id, plan_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, payment_id, plan_id))
            
            payment_record_id = cursor.lastrowid
            conn.commit()
            
            return payment_record_id
            
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            return None
        finally:
            conn.close()
    
    async def update_payment_status(self, payment_id: str, status: str):
        """Обновление статуса платежа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE payments SET status = ? WHERE payment_id = ?
            ''', (status, payment_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Ошибка обновления статуса платежа: {e}")
        finally:
            conn.close()
    
    async def get_stats(self) -> Dict:
        """Получение статистики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            users_count = cursor.fetchone()[0]
            
            # Активные подписки
            cursor.execute('''
                SELECT COUNT(*) FROM subscriptions 
                WHERE is_active = TRUE AND end_date > ?
            ''', (datetime.now(),))
            active_subscriptions = cursor.fetchone()[0]
            
            # Доход за месяц
            month_ago = datetime.now() - timedelta(days=30)
            cursor.execute('''
                SELECT SUM(amount) FROM payments 
                WHERE status = 'succeeded' AND created_at > ?
            ''', (month_ago,))
            monthly_revenue = cursor.fetchone()[0] or 0
            
            return {
                'users': users_count,
                'active_subscriptions': active_subscriptions,
                'monthly_revenue': monthly_revenue
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
        finally:
            conn.close()
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Получение пользователя по username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'created_at': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
        finally:
            conn.close()
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получение пользователя по telegram_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'created_at': row[5]
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
        finally:
            conn.close()
    
    async def cancel_user_subscription(self, user_id: int) -> bool:
        """Отмена подписки пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE subscriptions SET is_active = FALSE 
                WHERE user_id = ? AND is_active = TRUE
            ''', (user_id,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Ошибка отмены подписки: {e}")
            return False
        finally:
            conn.close()
    
    async def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users')
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                users.append({
                    'id': row[0],
                    'telegram_id': row[1],
                    'username': row[2],
                    'first_name': row[3],
                    'last_name': row[4],
                    'created_at': row[5]
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []
        finally:
            conn.close()
    
    async def get_detailed_stats(self) -> Dict:
        """Подробная статистика"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = TRUE AND end_date > ?', (datetime.now(),))
            stats['active_subscriptions'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE end_date <= ?', (datetime.now(),))
            stats['expired_subscriptions'] = cursor.fetchone()[0]
            
            # Доходы
            day_ago = datetime.now() - timedelta(days=1)
            week_ago = datetime.now() - timedelta(days=7)
            month_ago = datetime.now() - timedelta(days=30)
            
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "succeeded" AND created_at > ?', (day_ago,))
            stats['daily_revenue'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "succeeded" AND created_at > ?', (week_ago,))
            stats['weekly_revenue'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "succeeded" AND created_at > ?', (month_ago,))
            stats['monthly_revenue'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(amount) FROM payments WHERE status = "succeeded"')
            stats['total_revenue'] = cursor.fetchone()[0] or 0
            
            # Статистика по планам
            cursor.execute('SELECT plan_id, COUNT(*) FROM subscriptions GROUP BY plan_id')
            plan_stats = {}
            for row in cursor.fetchall():
                plan_stats[row[0]] = row[1]
            stats['plan_stats'] = plan_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения детальной статистики: {e}")
            return {}
        finally:
            conn.close()
    
    async def get_user_stats(self, telegram_id: int) -> Dict:
        """Получение статистики пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Количество подписок
            cursor.execute('''
                SELECT COUNT(*) FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ?
            ''', (telegram_id,))
            result = cursor.fetchone()
            total_subscriptions = result[0] if result else 0
            
            # Общая сумма платежей
            cursor.execute('''
                SELECT SUM(p.amount) FROM payments p
                JOIN users u ON p.user_id = u.id
                WHERE u.telegram_id = ? AND p.status = "succeeded"
            ''', (telegram_id,))
            result = cursor.fetchone()
            total_spent = result[0] if result and result[0] else 0
            
            # Дата регистрации
            cursor.execute('SELECT created_at FROM users WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            registration_date = result[0] if result else None
            
            return {
                'total_subscriptions': total_subscriptions,
                'total_spent': total_spent,
                'registration_date': registration_date
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики пользователя: {e}")
            return {}
        finally:
            conn.close()
    
    async def is_uuid_exists(self, xray_uuid: str) -> bool:
        """Проверка существования UUID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE xray_uuid = ?', (xray_uuid,))
            count = cursor.fetchone()[0]
            return count > 0
            
        except Exception as e:
            logger.error(f"Ошибка проверки UUID: {e}")
            return False
        finally:
            conn.close()
    
    async def get_user_uuid(self, telegram_id: int) -> Optional[str]:
        """Получение UUID пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT s.xray_uuid FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE u.telegram_id = ? AND s.xray_uuid IS NOT NULL
                ORDER BY s.created_at DESC LIMIT 1
            ''', (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения UUID: {e}")
            return None
        finally:
            conn.close()
    
    async def save_user_uuid(self, telegram_id: int, xray_uuid: str) -> bool:
        """Сохранение UUID пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Сохраняем в отдельной таблице для быстрого поиска
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_uuids (
                    telegram_id INTEGER PRIMARY KEY,
                    xray_uuid TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_uuids (telegram_id, xray_uuid)
                VALUES (?, ?)
            ''', (telegram_id, xray_uuid))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения UUID: {e}")
            return False
        finally:
            conn.close()