#!/usr/bin/env python3
"""
Простой фильтр безопасности для блокировки подозрительных запросов
"""
import logging
from flask import Flask, request, abort
from functools import wraps

logger = logging.getLogger(__name__)

# Подозрительные паттерны в запросах
SUSPICIOUS_PATTERNS = [
    b'\x04\x01\x00',  # SOCKS4
    b'\x05\x01\x00',  # SOCKS5
    b'SSH-2.0',       # SSH
    b'\x16\x03\x01',  # TLS handshake
    'CONNECT',        # HTTP CONNECT
    '.git/config',    # Git файлы
    '/cgi-bin/',      # CGI уязвимости
    '/login',         # Попытки входа
    'PRI * HTTP/2.0', # HTTP/2
]

BLOCKED_IPS = set()

def security_filter():
    """Декоратор для фильтрации подозрительных запросов"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
            
            # Проверяем заблокированные IP
            if client_ip in BLOCKED_IPS:
                logger.warning(f"Заблокированный IP {client_ip} пытается подключиться")
                abort(403)
            
            # Проверяем подозрительные паттерны
            raw_data = request.get_data()
            request_line = f"{request.method} {request.path}"
            
            for pattern in SUSPICIOUS_PATTERNS:
                if isinstance(pattern, bytes):
                    if pattern in raw_data:
                        logger.warning(f"Подозрительный запрос от {client_ip}: {pattern}")
                        BLOCKED_IPS.add(client_ip)
                        abort(400)
                else:
                    if pattern in request_line:
                        logger.warning(f"Подозрительный запрос от {client_ip}: {pattern}")
                        BLOCKED_IPS.add(client_ip)
                        abort(404)
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def init_security(app: Flask):
    """Инициализация системы безопасности"""
    
    @app.before_request
    def security_check():
        client_ip = request.environ.get('REMOTE_ADDR', 'unknown')
        
        # Проверяем заблокированные IP
        if client_ip in BLOCKED_IPS:
            logger.warning(f"Заблокированный IP {client_ip}")
            abort(403)
        
        # Проверяем подозрительные паттерны
        raw_data = request.get_data()
        request_line = f"{request.method} {request.path}"
        
        for pattern in SUSPICIOUS_PATTERNS:
            if isinstance(pattern, bytes):
                if pattern in raw_data:
                    logger.warning(f"Блокируем IP {client_ip} за подозрительный запрос")
                    BLOCKED_IPS.add(client_ip)
                    abort(400)
            else:
                if pattern in request_line:
                    logger.warning(f"Блокируем IP {client_ip} за подозрительный запрос: {pattern}")
                    BLOCKED_IPS.add(client_ip)
                    abort(404)
    
    logger.info("Система безопасности инициализирована")