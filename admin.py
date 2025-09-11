#!/usr/bin/env python3
"""
Административная панель для VPN бота
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from database import db

def print_stats():
    """Вывод статистики"""
    stats = db.get_stats()
    
    print("=" * 50)
    print("📊 СТАТИСТИКА VPN БОТА")
    print("=" * 50)
    print(f"👥 Всего пользователей: {stats.get('total_users', 0)}")
    print(f"💰 Оплаченных заказов: {stats.get('paid_orders', 0)}")
    print(f"🔑 Активных VPN ключей: {stats.get('active_keys', 0)}")
    print(f"💵 Общая выручка: {stats.get('total_revenue', 0)} ₽")
    print("=" * 50)

def print_recent_orders():
    """Вывод последних заказов"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.*, u.username, u.first_name 
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.telegram_id
                WHERE o.status = 'paid'
                ORDER BY o.paid_at DESC
                LIMIT 10
            """)
            orders = cursor.fetchall()
            
        print("\n📋 ПОСЛЕДНИЕ ЗАКАЗЫ:")
        print("-" * 80)
        
        if not orders:
            print("Нет оплаченных заказов")
            return
            
        for order in orders:
            user_name = order['username'] or order['first_name'] or f"ID{order['user_id']}"
            paid_at = datetime.fromisoformat(order['paid_at']).strftime('%d.%m.%Y %H:%M')
            print(f"🆔 {order['id']} | 👤 {user_name} | 💰 {order['amount']}₽ | 📅 {paid_at}")
            
    except Exception as e:
        print(f"Ошибка получения заказов: {e}")

def print_active_keys():
    """Вывод активных VPN ключей"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.*, u.username, u.first_name
                FROM vpn_keys v
                LEFT JOIN users u ON v.user_id = u.telegram_id
                WHERE v.is_active = 1 AND v.expires_at > datetime('now')
                ORDER BY v.expires_at ASC
                LIMIT 20
            """)
            keys = cursor.fetchall()
            
        print("\n🔑 АКТИВНЫЕ VPN КЛЮЧИ:")
        print("-" * 80)
        
        if not keys:
            print("Нет активных VPN ключей")
            return
            
        for key in keys:
            user_name = key['username'] or key['first_name'] or f"ID{key['user_id']}"
            expires_at = datetime.fromisoformat(key['expires_at']).strftime('%d.%m.%Y %H:%M')
            traffic_gb = key['traffic_limit'] // (1024**3)
            print(f"📧 {key['email']} | 👤 {user_name} | 📊 {traffic_gb}ГБ | ⏰ {expires_at}")
            
    except Exception as e:
        print(f"Ошибка получения VPN ключей: {e}")

def cleanup_expired_keys():
    """Очистка истекших ключей"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE vpn_keys 
                SET is_active = 0 
                WHERE expires_at < datetime('now') AND is_active = 1
            """)
            count = cursor.rowcount
            conn.commit()
            
        print(f"✅ Деактивировано {count} истекших VPN ключей")
        
    except Exception as e:
        print(f"Ошибка очистки ключей: {e}")

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python admin.py stats     - показать статистику")
        print("  python admin.py orders    - показать последние заказы")
        print("  python admin.py keys      - показать активные VPN ключи")
        print("  python admin.py cleanup   - очистить истекшие ключи")
        print("  python admin.py all       - показать всю информацию")
        return
        
    command = sys.argv[1].lower()
    
    if command == "stats":
        print_stats()
    elif command == "orders":
        print_recent_orders()
    elif command == "keys":
        print_active_keys()
    elif command == "cleanup":
        cleanup_expired_keys()
    elif command == "all":
        print_stats()
        print_recent_orders()
        print_active_keys()
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == "__main__":
    main()