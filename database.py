import logging
import aiosqlite
from datetime import datetime

from config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self):
        self.db_file = DATABASE_URL
        self.db = None
    
    async def connect(self):
        """Подключение к базе данных"""
        if self.db is None:
            self.db = await aiosqlite.connect(self.db_file)
            self.db.row_factory = aiosqlite.Row
        return self.db
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            db = await self.connect()
            
            # Создаем таблицу пользователей
            await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Создаем таблицу подписок
            await db.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                vpn_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')
            
            # Создаем таблицу платежей
            await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                payment_id TEXT UNIQUE,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id)
            )
            ''')
            
            await db.commit()
            logger.info("База данных инициализирована")
        
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")
    
    async def create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Создание нового пользователя"""
        try:
            db = await self.connect()
            
            await db.execute(
                "INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                (telegram_id, username, first_name, last_name)
            )
            
            await db.commit()
            logger.info(f"Создан новый пользователь: {telegram_id}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {str(e)}")
            return False
    
    async def get_user(self, telegram_id):
        """Получение информации о пользователе"""
        try:
            db = await self.connect()
            
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
                user = await cursor.fetchone()
            
            if user:
                return dict(user)
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {str(e)}")
            return None
    
    async def create_subscription(self, user_id, vpn_key, expiry_date):
        """Создание новой подписки"""
        try:
            db = await self.connect()
            
            # Проверяем, существует ли пользователь
            user = await self.get_user(user_id)
            if not user:
                # Создаем пользователя, если он не существует
                await self.create_user(user_id)
            
            # Деактивируем предыдущие подписки пользователя
            await db.execute(
                "UPDATE subscriptions SET active = 0 WHERE user_id = ?",
                (user_id,)
            )
            
            # Создаем новую подписку
            await db.execute(
                "INSERT INTO subscriptions (user_id, vpn_key, expiry_date) VALUES (?, ?, ?)",
                (user_id, vpn_key, expiry_date.isoformat())
            )
            
            await db.commit()
            logger.info(f"Создана новая подписка для пользователя: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при создании подписки: {str(e)}")
            return False
    
    async def get_user_subscription(self, user_id):
        """Получение активной подписки пользователя"""
        try:
            db = await self.connect()
            
            async with db.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? AND active = 1",
                (user_id,)
            ) as cursor:
                subscription = await cursor.fetchone()
            
            if subscription:
                subscription_dict = dict(subscription)
                
                # Преобразуем строку даты в объект datetime
                expiry_date = datetime.fromisoformat(subscription_dict['expiry_date'])
                subscription_dict['expiry_date'] = expiry_date
                
                # Проверяем, не истекла ли подписка
                if expiry_date < datetime.now():
                    subscription_dict['active'] = False
                    
                    # Обновляем статус подписки в базе данных
                    await db.execute(
                        "UPDATE subscriptions SET active = 0 WHERE id = ?",
                        (subscription_dict['id'],)
                    )
                    await db.commit()
                
                return subscription_dict
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении подписки пользователя: {str(e)}")
            return None
    
    async def extend_subscription(self, user_id, new_expiry_date):
        """Продление подписки пользователя"""
        try:
            db = await self.connect()
            
            # Получаем текущую активную подписку
            subscription = await self.get_user_subscription(user_id)
            
            if subscription:
                # Обновляем дату истечения подписки
                await db.execute(
                    "UPDATE subscriptions SET expiry_date = ? WHERE id = ?",
                    (new_expiry_date.isoformat(), subscription['id'])
                )
                
                await db.commit()
                logger.info(f"Подписка продлена для пользователя: {user_id}")
                return True
            else:
                logger.error(f"Не найдена активная подписка для пользователя: {user_id}")
                return False
        
        except Exception as e:
            logger.error(f"Ошибка при продлении подписки: {str(e)}")
            return False
    
    async def create_payment(self, user_id, amount, payment_id, status="pending"):
        """Создание записи о платеже"""
        try:
            db = await self.connect()
            
            await db.execute(
                "INSERT INTO payments (user_id, amount, payment_id, status) VALUES (?, ?, ?, ?)",
                (user_id, amount, payment_id, status)
            )
            
            await db.commit()
            logger.info(f"Создан новый платеж для пользователя: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {str(e)}")
            return False
    
    async def update_payment_status(self, payment_id, status):
        """Обновление статуса платежа"""
        try:
            db = await self.connect()
            
            await db.execute(
                "UPDATE payments SET status = ? WHERE payment_id = ?",
                (status, payment_id)
            )
            
            await db.commit()
            logger.info(f"Обновлен статус платежа: {payment_id} -> {status}")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса платежа: {str(e)}")
            return False
    
    async def get_payment(self, payment_id):
        """Получение информации о платеже"""
        try:
            db = await self.connect()
            
            async with db.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
                payment = await cursor.fetchone()
            
            if payment:
                return dict(payment)
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении платежа: {str(e)}")
            return None
    
    async def get_user_by_payment(self, payment_id):
        """Получение пользователя по ID платежа"""
        try:
            db = await self.connect()
            
            async with db.execute("SELECT user_id FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
                result = await cursor.fetchone()
            
            if result:
                return result['user_id']
            else:
                return None
        
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по ID платежа: {str(e)}")
            return None
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.db:
            await self.db.close()
            self.db = None