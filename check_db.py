import sqlite3
from config import DATABASE_URL

def check_database():
    """Проверка структуры базы данных"""
    print("Проверка структуры базы данных...")
    
    # Подключение к базе данных
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Получаем список таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Таблицы в базе данных:")
    for table in tables:
        print(f"- {table[0]}")
        
        # Получаем структуру таблицы
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        
        print("  Колонки:")
        for column in columns:
            print(f"  - {column[1]} ({column[2]})")
    
    # Закрываем соединение
    conn.close()

if __name__ == "__main__":
    check_database()