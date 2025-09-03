#!/usr/bin/env python3
"""HTTP сервис для автоматического добавления пользователей в Xray"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_xray_config():
    """Поиск конфигурации Xray"""
    possible_paths = [
        "/usr/local/etc/xray/config.json",
        "/etc/xray/config.json",
        "/opt/xray/config.json",
        "/root/xray/config.json",
        "./config.json",
        "/usr/share/xray/config.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    # Проверяем, есть ли нужный inbound
                    for inbound in config.get('inbounds', []):
                        if inbound.get('tag') == 'vless-in':
                            logger.info(f"Найдена конфигурация Xray: {path}")
                            return path
            except:
                continue
    
    logger.error("Конфигурация Xray не найдена")
    return None

CONFIG_PATH = find_xray_config()

class UserHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Проверка статуса сервиса"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        status = {
            'status': 'running',
            'config_path': CONFIG_PATH,
            'config_found': CONFIG_PATH is not None
        }
        
        self.wfile.write(json.dumps(status).encode())
    
    def do_POST(self):
        if self.path == '/add_user':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                user_uuid = data['uuid']
                email = data['email']
                
                if not CONFIG_PATH:
                    raise Exception("Конфигурация Xray не найдена")
                
                # Добавляем пользователя в конфиг
                script = f"""
import json
config_path = '{CONFIG_PATH}'
with open(config_path, 'r') as f:
    config = json.load(f)

for inbound in config['inbounds']:
    if inbound.get('tag') == 'vless-in':
        clients = inbound['settings']['clients']
        # Проверяем, нет ли уже такого пользователя
        for client in clients:
            if client.get('id') == '{user_uuid}':
                exit(0)  # Уже существует
        
        new_client = {{
            'id': '{user_uuid}',
            'email': '{email}',
            'flow': 'xtls-rprx-vision'
        }}
        clients.append(new_client)
        break

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
"""
                
                # Выполняем скрипт
                result = subprocess.run(['python3', '-c', script], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Перезагружаем Xray
                    subprocess.run(['systemctl', 'reload', 'xray'])
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'success'}).encode())
                    
                    logger.info(f"Добавлен пользователь {email}")
                else:
                    raise Exception(result.stderr)
                    
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 9999), UserHandler)
    logger.info("Сервис добавления пользователей запущен на порту 9999")
    server.serve_forever()