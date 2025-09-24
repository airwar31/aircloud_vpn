#!/usr/bin/env python3
"""
Скрипт синхронизации ключей между БД и Xray
"""

import asyncio
import requests
from database_mysql import db
from datetime import datetime

XRAY_API_URL = "http://localhost:8080"

async def sync_keys():
    """Синхронизация всех активных ключей с Xray"""
    print("Начинаем синхронизацию ключей...")
    
    # Получаем все активные ключи из БД
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT key_id, email, config, expires_at, is_active 
        FROM vpn_keys 
        WHERE is_active = 1 AND expires_at > NOW()
    """)
    active_keys = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"Найдено {len(active_keys)} активных ключей в БД")
    
    # Получаем ключи из Xray
    try:
        response = requests.get(f"{XRAY_API_URL}/api/clients")
        if response.status_code == 200:
            xray_clients = response.json()
            xray_emails = [client.get('email', '') for client in xray_clients]
            print(f"Найдено {len(xray_emails)} ключей в Xray")
        else:
            print(f"Ошибка получения ключей из Xray: {response.status_code}")
            return
    except Exception as e:
        print(f"Ошибка подключения к Xray API: {e}")
        return
    
    # Добавляем недостающие ключи в Xray
    added_count = 0
    for key in active_keys:
        if key['email'] not in xray_emails:
            try:
                response = requests.post(f"{XRAY_API_URL}/api/clients", json={
                    "id": key['key_id'],
                    "email": key['email']
                })
                if response.status_code == 200:
                    print(f"✅ Добавлен ключ: {key['email']}")
                    added_count += 1
                else:
                    print(f"❌ Ошибка добавления {key['email']}: {response.status_code}")
            except Exception as e:
                print(f"❌ Ошибка добавления {key['email']}: {e}")
    
    print(f"Синхронизация завершена. Добавлено ключей: {added_count}")

if __name__ == "__main__":
    asyncio.run(sync_keys())