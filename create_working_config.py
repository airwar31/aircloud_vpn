#!/usr/bin/env python3
"""Создание рабочей конфигурации Xray"""

import json
import subprocess

def create_working_config():
    # Генерируем ключи
    result = subprocess.run(['xray', 'x25519'], capture_output=True, text=True)
    
    private_key = None
    public_key = None
    
    for line in result.stdout.split('\n'):
        if 'Private key:' in line:
            private_key = line.split('Private key:')[1].strip()
        elif 'Public key:' in line:
            public_key = line.split('Public key:')[1].strip()
    
    # Простая рабочая конфигурация
    config = {
        "log": {"loglevel": "info"},
        "inbounds": [
            {
                "tag": "vless-in",
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": "44524a54-bf42-4864-9b6c-7691bef1853e",
                            "email": "user1262543088@aircloud.vpn",
                            "flow": "xtls-rprx-vision"
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "dest": "www.microsoft.com:443",
                        "serverNames": ["www.microsoft.com"],
                        "privateKey": private_key,
                        "publicKey": public_key,
                        "shortIds": [""]
                    }
                }
            }
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"}
        ]
    }
    
    # Сохраняем
    with open('/usr/local/etc/xray/config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Перезапускаем
    subprocess.run(['systemctl', 'restart', 'xray'])
    
    print(f"✅ Создана простая конфигурация")
    print(f"🔑 Public Key: {public_key}")
    
    # Токен
    token = f"vless://44524a54-bf42-4864-9b6c-7691bef1853e@5.129.224.166:443?type=tcp&security=reality&pbk={public_key}&fp=chrome&sni=www.microsoft.com&sid=&flow=xtls-rprx-vision#AirCloud"
    
    print(f"\n🎯 ТЕСТОВЫЙ ТОКЕН:")
    print(token)

if __name__ == '__main__':
    create_working_config()