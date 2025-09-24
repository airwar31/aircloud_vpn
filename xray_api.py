from flask import Flask, request, jsonify
import json
import uuid
import base64
import subprocess
import os
import secrets
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
        self.reality_keys = self.generate_reality_keys()
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
            # Отправляем сигнал HUP для перезагрузки конфигурации без перезапуска
            result = subprocess.run(["/usr/bin/pkill", "-HUP", "-f", "xray"], check=False)
            if result.returncode == 0:
                logger.info("Xray конфигурация перезагружена")
            else:
                logger.warning("Не удалось перезагрузить Xray, возможно процесс не запущен")
        except Exception as e:
            logger.error(f"Ошибка перезагрузки Xray: {e}")
            
    def get_default_config(self) -> Dict[str, Any]:
        """Базовая конфигурация Xray с Reality"""
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
                        "privateKey": self.reality_keys["private_key"],
                        "shortIds": [self.reality_keys["short_id"]]
                    },
                    "tcpSettings": {
                        "acceptProxyProtocol": False
                    }
                }
            }],
            "outbounds": [{
                "protocol": "freedom",
                "settings": {}
            }]
        }
        
    def add_client(self, email: str, client_id: str, expires_at: str, devices: int = 1) -> str:
        """Добавление клиента"""
        try:
            # Удаляем старые клиенты с таким же email
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
            
            # Добавляем нового клиента
            self.config["inbounds"][0]["settings"]["clients"].append(client)
            
            # Сохраняем информацию о клиенте
            self.clients[email] = {
                "id": client_id,
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
        """Генерация конфигурации для клиента с Reality"""
        server_domain = os.getenv("SERVER_DOMAIN", "air31cloud.ru")
        # Используем внешний порт 8444 вместо внутреннего 443
        external_port = os.getenv("VPN_EXTERNAL_PORT", "8444")
        
        # VLESS конфигурация с Reality
        config = (f"vless://{client_id}@{server_domain}:{external_port}?"
                 f"type=tcp&security=reality&pbk={self.reality_keys['public_key']}&"
                 f"fp=chrome&sni=dl.google.com&sid={self.reality_keys['short_id']}&spx=%2F&flow=xtls-rprx-vision#{email}")
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
                "expires_at": client["expires_at"],
                "is_expired": is_expired,
                "is_active": not is_expired
            }
        return {}
        
    def generate_reality_keys(self) -> Dict[str, str]:
        """Генерация Reality ключей через Xray"""
        try:
            result = subprocess.run(["/usr/local/bin/xray", "x25519"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                private_key = lines[0].split(': ')[1]
                public_key = lines[1].split(': ')[1]
                
                # Генерируем короткий ID
                short_id = secrets.token_hex(1)
                
                return {
                    "private_key": private_key,
                    "public_key": public_key,
                    "short_id": short_id
                }
            else:
                logger.error(f"Ошибка генерации ключей: {result.stderr}")
                # Генерируем случайные fallback ключи
                return {
                    "private_key": secrets.token_urlsafe(32),
                    "public_key": secrets.token_urlsafe(32),
                    "short_id": secrets.token_hex(1)
                }
        except Exception as e:
            logger.error(f"Ошибка генерации Reality ключей: {e}")
            # Генерируем случайные fallback ключи
            return {
                "private_key": secrets.token_urlsafe(32),
                "public_key": secrets.token_urlsafe(32),
                "short_id": secrets.token_hex(1)
            }

# Глобальный экземпляр API
xray_api = XrayAPI()

@app.route('/api/clients', methods=['POST'])
def add_client():
    """Добавление клиента"""
    try:
        data = request.get_json()
        email = data.get('email')
        client_id = data.get('id') or data.get('client_id')
        expires_at = data.get('expires_at')
        devices = data.get('devices', 1)
        
        # Если нет client_id, генерируем UUID
        if not client_id:
            client_id = str(uuid.uuid4())
            
        # Если нет expires_at, устанавливаем на 30 дней
        if not expires_at:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
            
        config = xray_api.add_client(email, client_id, expires_at, devices)
        
        return jsonify({
            "success": True,
            "config": config,
            "email": email,
            "expires_at": expires_at
        })
        
    except Exception as e:
        logger.error(f"Ошибка API добавления клиента: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Получение списка клиентов"""
    try:
        clients = xray_api.config["inbounds"][0]["settings"]["clients"]
        return jsonify(clients)
    except Exception as e:
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

@app.route('/api/clients/stats', methods=['GET'])
def get_all_clients_stats():
    """Статистика всех клиентов"""
    try:
        clients = []
        for email in xray_api.clients:
            stats = xray_api.get_client_stats(email)
            # Симуляция активных подключений
            import random
            stats['active_connections'] = random.randint(1, 3) if stats.get('is_active') else 0
            clients.append(stats)
        return jsonify({"clients": clients})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/client/disable', methods=['POST'])
def disable_client():
    """Отключение клиента"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email required"}), 400
            
        # Находим клиента и отключаем
        clients = xray_api.config["inbounds"][0]["settings"]["clients"]
        for client in clients:
            if client["email"] == email:
                client["enable"] = False
                break
                
        xray_api.save_config()
        return jsonify({"success": True, "message": f"Client {email} disabled"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/client/enable', methods=['POST'])
def enable_client():
    """Включение клиента"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email required"}), 400
            
        # Находим клиента и включаем
        clients = xray_api.config["inbounds"][0]["settings"]["clients"]
        for client in clients:
            if client["email"] == email:
                client["enable"] = True
                break
                
        xray_api.save_config()
        return jsonify({"success": True, "message": f"Client {email} enabled"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    import os
    if os.getenv('FLASK_ENV') == 'production':
        from waitress import serve
        serve(app, host='0.0.0.0', port=8080)
    else:
        app.run(host='0.0.0.0', port=8080, debug=False)