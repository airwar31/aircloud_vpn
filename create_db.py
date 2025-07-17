import sqlite3
import os
from config import DATABASE_URL

def create_database():
    """Создание и инициализация базы данных"""
    print("Начало создания базы данных...")
    
    # Подключение к базе данных
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Создаем таблицу пользователей
    cursor.execute('''
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
    cursor.execute('''
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
    cursor.execute('''
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
    
    # Сохраняем изменения и закрываем соединение
    conn.commit()
    conn.close()
    
    print(f"База данных успешно создана: {os.path.abspath(DATABASE_URL)}")

if __name__ == "__main__":
    create_database()