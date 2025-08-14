import os
import secrets
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

class SecurityConfig:
    """Класс для генерации ключей безопасности Xray"""
    
    @staticmethod
    def generate_reality_keypair():
        """Генерация пары ключей для Reality"""
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        private_bytes = private_key.private_bytes(
            encoding=Encoding.Raw,
            format=PrivateFormat.Raw,
            encryption_algorithm=NoEncryption()
        )
        
        public_bytes = public_key.public_bytes(
            encoding=Encoding.Raw,
            format=Encoding.Raw
        )
        
        return {
            'private_key': base64.b64encode(private_bytes).decode(),
            'public_key': base64.b64encode(public_bytes).decode()
        }
    
    @staticmethod
    def generate_short_ids(count=8):
        """Генерация коротких ID для Reality"""
        short_ids = [""]  # Пустой ID всегда включен
        
        for _ in range(count - 1):
            short_id = secrets.token_hex(8)
            short_ids.append(short_id)
        
        return short_ids
    
    @staticmethod
    def get_secure_domains():
        """Список доменов для маскировки Reality (доступные в РФ)"""
        return [
            "www.google.com",
            "www.microsoft.com",
            "update.microsoft.com",
            "www.apple.com",
            "support.apple.com",
            "www.ubuntu.com",
            "releases.ubuntu.com",
            "www.debian.org",
            "www.mozilla.org"
        ]
    
    @staticmethod
    def generate_ws_path():
        """Генерация случайного пути для WebSocket"""
        return f"/{secrets.token_urlsafe(16)}"

# Генерация ключей при импорте модуля
reality_keys = SecurityConfig.generate_reality_keypair()
short_ids = SecurityConfig.generate_short_ids()
secure_domains = SecurityConfig.get_secure_domains()
ws_path = SecurityConfig.generate_ws_path()

print("=== XRAY SECURITY CONFIGURATION ===")
print(f"Reality Private Key: {reality_keys['private_key']}")
print(f"Reality Public Key: {reality_keys['public_key']}")
print(f"Short IDs: {short_ids}")
print(f"WebSocket Path: {ws_path}")
print("=====================================")