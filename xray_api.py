from flask import Flask, request, jsonify
import json
import uuid
import base64
import subprocess
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация Xray
XRAY_CONFIG_PATH = "/etc/xray/config.json"
XRAY_BINARY = "/usr/local/bin/xray"

class XrayAPI:
    def __init__(self):
        self.clients = {}
        self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации Xray"""
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
        """Сохранение конфигурации"""
        try:
            os.makedirs(os.path.dirname(XRAY_CONFIG_PATH), exist_ok=True)
            with open(XRAY_CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.restart_xray()
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            
    def restart_xray(self):
        """Перезапуск Xray"""
        try:
            subprocess.run(["pkill", "-f", "xray"], check=False)
            subprocess.Popen([XRAY_BINARY, "-config", XRAY_CONFIG_PATH])
            logger.info("Xray перезапущен")
        except Exception as e:
            logger.error(f"Ошибка перезапуска Xray: {e}")
            
    def get_default_config(self) -> Dict[str, Any]:
        """Базовая конфигурация Xray"""
        return {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 443,
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {
                    "network": "tcp",
                    "security": "none"
                }
            }],
            "outbounds": [{
                "protocol": "freedom",
                "settings": {}
            }]
        }
        
    def add_client(self, email: str, client_id: str, traffic_limit: int, expires_at: str) -> str:
        """Добавление клиента"""
        try:
            client = {
                "id": client_id,
                "email": email,
                "enable": True
            }
            
            # Добавляем клиента в конфигурацию
            self.config["inbounds"][0]["settings"]["clients"].append(client)
            
            # Сохраняем информацию о клиенте
            self.clients[email] = {
                "id": client_id,
                "traffic_limit": traffic_limit,
                "expires_at": expires_at,
                "up": 0,
                "down": 0
            }
            
            self.save_config()
            
            # Генерируем конфигурацию для клиента
            config = self.generate_client_config(client_id, email)
            return config
            
        except Exception as e:
            logger.error(f"Ошибка добавления клиента: {e}")
            raise
            
    def remove_client(self, email: str) -> bool:
        """Удаление клиента"""
        try:
            # Удаляем из конфигурации Xray
            clients = self.config["inbounds"][0]["settings"]["clients"]
            self.config["inbounds"][0]["settings"]["clients"] = [
                c for c in clients if c["email"] != email
            ]
            
            # Удаляем из локального хранилища
            if email in self.clients:
                del self.clients[email]
                
            self.save_config()
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления клиента: {e}")
            return False
            
    def generate_client_config(self, client_id: str, email: str) -> str:
        """Генерация конфигурации для клиента"""
        server_ip = os.getenv("SERVER_IP", "YOUR_SERVER_IP")
        port = self.config["inbounds"][0]["port"]
        
        # VLESS конфигурация
        config = f"vless://{client_id}@{server_ip}:{port}?type=tcp&security=none#{email}"
        return config
        
    def get_client_stats(self, email: str) -> Dict[str, Any]:
        """Получение статистики клиента"""
        if email in self.clients:
            client = self.clients[email]
            expires_at = datetime.fromisoformat(client["expires_at"])
            is_expired = expires_at < datetime.now()
            
            return {
                "email": email,
                "traffic_used": client["up"] + client["down"],
                "traffic_limit": client["traffic_limit"],
                "expires_at": client["expires_at"],
                "is_expired": is_expired,
                "is_active": not is_expired and client["up"] + client["down"] < client["traffic_limit"]
            }
        return {}

# Глобальный экземпляр API
xray_api = XrayAPI()

@app.route('/api/clients', methods=['POST'])
def add_client():
    """Добавление клиента"""
    try:
        data = request.get_json()
        email = data.get('email')
        client_id = data.get('id')
        traffic_limit = data.get('traffic_limit')
        expires_at = data.get('expires_at')
        
        if not all([email, client_id, traffic_limit, expires_at]):
            return jsonify({"error": "Missing required fields"}), 400
            
        config = xray_api.add_client(email, client_id, traffic_limit, expires_at)
        
        return jsonify({
            "success": True,
            "config": config,
            "email": email
        })
        
    except Exception as e:
        logger.error(f"Ошибка API добавления клиента: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clients/<email>', methods=['DELETE'])
def remove_client(email):
    """Удаление клиента"""
    try:
        success = xray_api.remove_client(email)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clients/<email>/stats', methods=['GET'])
def get_client_stats(email):
    """Статистика клиента"""
    try:
        stats = xray_api.get_client_stats(email)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)