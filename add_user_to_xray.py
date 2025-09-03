#!/usr/bin/env python3
import json
import sys
import os

def add_user_to_config(user_uuid, email):
    """Добавляет пользователя в конфигурацию Xray"""
    config_path = '/usr/local/etc/xray/config.json'
    
    try:
        # Читаем текущую конфигурацию
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Находим vless-in inbound
        for inbound in config.get('inbounds', []):
            if inbound.get('tag') == 'vless-in':
                clients = inbound.get('settings', {}).get('clients', [])
                
                # Проверяем, нет ли уже такого пользователя
                for client in clients:
                    if client.get('id') == user_uuid:
                        print(f"✅ Пользователь {email} уже существует")
                        return True
                
                # Добавляем нового пользователя
                new_client = {
                    "id": user_uuid,
                    "email": email,
                    "flow": "xtls-rprx-vision"
                }
                clients.append(new_client)
                
                # Сохраняем конфигурацию
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ Пользователь {email} добавлен в конфигурацию")
                return True
        
        print("❌ Не найден inbound vless-in")
        return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python3 add_user_to_xray.py <uuid> <email>")
        sys.exit(1)
    
    user_uuid = sys.argv[1]
    email = sys.argv[2]
    
    if add_user_to_config(user_uuid, email):
        # Перезапускаем Xray
        os.system("systemctl reload xray")
        print("🔄 Xray перезагружен")
    else:
        sys.exit(1)