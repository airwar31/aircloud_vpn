#!/usr/bin/env python3
"""
HTTP сервис для управления пользователями Xray на хосте
Запускается на хосте и принимает запросы от бота в контейнере
"""

from flask import Flask, request, jsonify
import json
import subprocess
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_PATH = '/usr/local/etc/xray/config.json'

@app.route('/manage_user', methods=['POST'])
def manage_user():
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'add_user':
            uuid = data.get('uuid')
            email = data.get('email')
            result = add_user_to_config(uuid, email)
            return jsonify({'success': result})
            
        elif action == 'remove_user':
            uuid = data.get('uuid')
            result = remove_user_from_config(uuid)
            return jsonify({'success': result})
            
        else:
            return jsonify({'error': 'Unknown action'}), 400
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

def add_user_to_config(user_uuid, email):
    """Добавление пользователя в конфиг Xray"""
    try:
        # Читаем конфиг
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Находим vless-in inbound
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'vless-in':
                new_client = {
                    "id": user_uuid,
                    "email": email,
                    "flow": "xtls-rprx-vision"
                }
                inbound['settings']['clients'].append(new_client)
                break
        
        # Сохраняем конфиг
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Перезагружаем Xray
        subprocess.run(['systemctl', 'reload', 'xray'], check=True)
        
        logger.info(f"User {email} added successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return False

def remove_user_from_config(user_uuid):
    """Удаление пользователя из конфига Xray"""
    try:
        # Читаем конфиг
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Находим vless-in inbound и удаляем пользователя
        for inbound in config['inbounds']:
            if inbound.get('tag') == 'vless-in':
                clients = inbound['settings']['clients']
                inbound['settings']['clients'] = [c for c in clients if c['id'] != user_uuid]
                break
        
        # Сохраняем конфиг
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Перезагружаем Xray
        subprocess.run(['systemctl', 'reload', 'xray'], check=True)
        
        logger.info(f"User {user_uuid[:8]}... removed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        return False

if __name__ == '__main__':
    logger.info("Starting Xray User Manager on port 9999")
    app.run(host='0.0.0.0', port=9999, debug=False)