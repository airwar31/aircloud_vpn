from flask import Flask, request, jsonify
import json
import uuid
import subprocess
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

XRAY_CONFIG_PATH = "/etc/xray/config.json"

class XrayAPI:
    def __init__(self):
        self.clients = {}
        self.load_config()
        
    def load_config(self):
        try:
            if os.path.exists(XRAY_CONFIG_PATH):
                with open(XRAY_CONFIG_PATH, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = self.get_default_config()
                self.save_config()
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.config = self.get_default_config()
            
    def save_config(self):
        try:
            os.makedirs(os.path.dirname(XRAY_CONFIG_PATH), exist_ok=True)
            with open(XRAY_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.restart_xray()
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            
    def restart_xray(self):
        try:
            result = subprocess.run(["pkill", "-USR1", "-f", "/usr/local/bin/xray"], check=False)
            if result.returncode == 0:
                logger.info("Конфигурация Xray перезагружена")
            else:
                logger.info("Конфигурация сохранена")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            
    def get_default_config(self):
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 443,
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": "dl.google.com:443",
                        "xver": 0,
                        "serverNames": ["dl.google.com"],
                        "privateKey": "CEHvlKw_qfG858suo8iHTMhg0CgpzAHWRu-VdPQO6nk",
                        "shortIds": ["23"]
                    },
                    "tcpSettings": {"acceptProxyProtocol": False}
                }
            }],
            "outbounds": [{"protocol": "freedom", "settings": {}}]
        }
        
    def add_client(self, email: str, client_id: str, expires_at: str, devices: int = 1) -> str:
        try:
            clients = self.config["inbounds"][0]["settings"]["clients"]
            self.config["inbounds"][0]["settings"]["clients"] = [
                c for c in clients if c["email"] != email
            ]
            
            client = {
                "id": client_id,
                "email": email,
                "enable": True,
                "flow": "xtls-rprx-vision",
                "limitIp": devices
            }
            
            self.config["inbounds"][0]["settings"]["clients"].append(client)
            self.clients[email] = {
                "id": client_id,
                "expires_at": expires_at,
                "up": 0,
                "down": 0
            }
            
            self.save_config()
            config = self.generate_client_config(client_id, email)
            return config
            
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            raise
            
    def generate_client_config(self, client_id: str, email: str) -> str:
        server_domain = os.getenv("SERVER_DOMAIN", "air31cloud.ru")
        external_port = os.getenv("VPN_EXTERNAL_PORT", "8444")
        
        # Используем правильный публичный ключ
        public_key = "dnUx8zqE1dHV2B5qyWZDpueUySPiWIkcHI-wxYfEzhA"
        short_id = "23"
        
        config = (f"vless://{client_id}@{server_domain}:{external_port}?"
                 f"security=reality&encryption=none&pbk={public_key}&"
                 f"headerType=none&fp=chrome&spx=%2F&type=tcp&"
                 f"flow=xtls-rprx-vision&sni=dl.google.com&sid={short_id}#{email}")
        return config

xray_api = XrayAPI()

@app.route('/api/clients', methods=['POST'])
def add_client():
    try:
        logger.info("Получен POST запрос на /api/clients")
        data = request.get_json()
        
        email = data.get('email')
        client_id = data.get('id') or str(uuid.uuid4())
        expires_at = data.get('expires_at') or (datetime.now() + timedelta(days=30)).isoformat()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
            
        config = xray_api.add_client(email, client_id, expires_at)
        
        return jsonify({
            "success": True,
            "config": config,
            "email": email,
            "expires_at": expires_at
        })
        
    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=8080)