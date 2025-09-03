#!/usr/bin/env python3
"""Исправление Reality ключей в конфиге Xray"""

import json
import subprocess

def fix_reality_config():
    config_path = "/usr/local/etc/xray/config.json"
    
    # Генерируем новые ключи
    result = subprocess.run(['xray', 'x25519'], capture_output=True, text=True)
    
    private_key = None
    public_key = None
    
    for line in result.stdout.split('\n'):
        if 'Private key:' in line:
            private_key = line.split('Private key:')[1].strip()
        elif 'Public key:' in line:
            public_key = line.split('Public key:')[1].strip()
    
    print(f"🔐 Новый приватный ключ: {private_key}")
    print(f"🔑 Новый публичный ключ: {public_key}")
    
    # Обновляем конфиг
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    for inbound in config['inbounds']:
        if inbound.get('tag') == 'vless-in':
            reality_settings = inbound['streamSettings']['realitySettings']
            reality_settings['privateKey'] = private_key
            reality_settings['publicKey'] = public_key
            break
    
    # Сохраняем
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Перезагружаем Xray
    subprocess.run(['systemctl', 'restart', 'xray'])
    
    print("✅ Reality ключи обновлены и Xray перезапущен")
    return public_key

if __name__ == '__main__':
    public_key = fix_reality_config()
    
    # Генерируем новый токен
    uuid = "44524a54-bf42-4864-9b6c-7691bef1853e"
    server_ip = "5.129.224.166"
    
    token = f"vless://{uuid}@{server_ip}:443?type=tcp&security=reality&pbk={public_key}&fp=chrome&sni=google.com&sid=&flow=xtls-rprx-vision#TestUser"
    
    print(f"\n🎯 НОВЫЙ РАБОЧИЙ ТОКЕН:")
    print(token)