#!/usr/bin/env python3
"""
Тест подарочных ссылок
"""

from database import db
import uuid

def test_gift_links():
    print("=== Тест подарочных ссылок ===")
    
    # Создаем тестовый код
    gift_code = f"gift_{uuid.uuid4().hex[:8]}"
    days = 30
    
    print(f"Создаем код: {gift_code} на {days} дней")
    
    # Создаем подарочную ссылку
    result = db.create_gift_link(gift_code, days)
    print(f"Результат создания: {result}")
    
    if result:
        # Проверяем, что код существует в БД
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gift_links WHERE gift_code = ?", (gift_code,))
            row = cursor.fetchone()
            if row:
                print(f"Код найден в БД: {dict(row)}")
            else:
                print("❌ Код НЕ найден в БД!")
        
        # Тестируем использование кода
        user_id = 12345
        used_days = db.use_gift_link(gift_code, user_id)
        print(f"Результат использования: {used_days}")
        
        if used_days:
            print(f"✅ Код успешно использован на {used_days} дней")
        else:
            print("❌ Код не удалось использовать")
            
        # Проверяем повторное использование
        used_days2 = db.use_gift_link(gift_code, user_id)
        print(f"Повторное использование: {used_days2}")
        if used_days2 is None:
            print("✅ Повторное использование заблокировано")
        else:
            print("❌ Код можно использовать повторно!")
    
    # Показываем все подарочные коды
    print("\n=== Все подарочные коды в БД ===")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gift_links ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        for row in rows:
            print(dict(row))

if __name__ == "__main__":
    test_gift_links()