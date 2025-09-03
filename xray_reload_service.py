#!/usr/bin/env python3
"""HTTP сервис для перезагрузки Xray"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReloadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/reload_xray':
            try:
                # Перезагружаем Xray
                result = subprocess.run(['systemctl', 'restart', 'xray'], 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "success"}')
                    logger.info("Xray успешно перезагружен")
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status": "error"}')
                    logger.error(f"Ошибка перезагрузки Xray: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"Исключение при перезагрузке: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "error"}')
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 9998), ReloadHandler)
    logger.info("Сервис перезагрузки Xray запущен на порту 9998")
    server.serve_forever()