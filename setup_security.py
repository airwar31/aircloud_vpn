#!/usr/bin/env python3
"""
Скрипт для настройки безопасности Xray сервера
Генерирует ключи и обновляет конфигурацию
"""

import json
import os
from security_config import SecurityConfig

def setup_xray_security():
    """Настройка безопасности Xray"""
    
    # Генерируем ключи
    reality_keys = SecurityConfig.generate_reality_keypair()
    short_ids = SecurityConfig.generate_short_ids()
    domains = SecurityConfig.get_secure_domains()
    ws_path = SecurityConfig.generate_ws_path()
    
    # Читаем текущую конфигурацию
    config_path = "xray-config/config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Обновляем Reality настройки
    for inbound in config['inbounds']:
        if inbound.get('tag') == 'vless-reality':
            reality_settings = inbound['streamSettings']['realitySettings']
            reality_settings['privateKey'] = reality_keys['private_key']
            reality_settings['shortIds'] = short_ids
            reality_settings['serverNames'] = domains[:2]  # Используем первые 2 домена
            reality_settings['dest'] = f"{domains[0]}:443"
        
        elif inbound.get('tag') == 'vless-ws':
            ws_settings = inbound['streamSettings']['wsSettings']
            ws_settings['path'] = ws_path
    
    # Сохраняем обновленную конфигурацию
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # Создаем файл с переменными окружения
    env_content = f"""# Xray Security Configuration
REALITY_PRIVATE_KEY={reality_keys['private_key']}
REALITY_PUBLIC_KEY={reality_keys['public_key']}
REALITY_SHORT_IDS={','.join(short_ids)}
WEBSOCKET_PATH={ws_path}
REALITY_DEST_DOMAIN={domains[0]}
"""
    
    with open('.env.security', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("🔐 Безопасность Xray настроена!")
    print(f"📁 Конфигурация обновлена: {config_path}")
    print(f"🔑 Ключи сохранены в: .env.security")
    print(f"🌐 Reality Public Key: {reality_keys['public_key']}")
    print(f"🛡️ WebSocket Path: {ws_path}")
    
    return {
        'reality_private_key': reality_keys['private_key'],
        'reality_public_key': reality_keys['public_key'],
        'short_ids': short_ids,
        'ws_path': ws_path,
        'domains': domains
    }

if __name__ == "__main__":
    setup_xray_security()