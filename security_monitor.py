#!/usr/bin/env python3
"""
Мониторинг безопасности и автоматическая блокировка атак
"""
import re
import time
import subprocess
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityMonitor:
    def __init__(self):
        self.attack_patterns = [
            r'CONNECT.*:443',
            r'SSH-2\.0',
            r'\\x04\\x01\\x00',  # SOCKS4
            r'\\x05\\x01\\x00',  # SOCKS5
            r'\.git/config',
            r'/cgi-bin/',
            r'/login',
            r'PRI \* HTTP/2\.0'
        ]
        
        self.ip_requests = defaultdict(lambda: deque(maxlen=100))
        self.blocked_ips = set()
        self.attack_threshold = 5  # атак за минуту
        
    def analyze_log_line(self, line):
        """Анализ строки лога"""
        # Извлекаем IP адрес
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
        if not ip_match:
            return
            
        ip = ip_match.group(1)
        
        # Проверяем на подозрительные паттерны
        for pattern in self.attack_patterns:
            if re.search(pattern, line):
                self.record_attack(ip, pattern)
                break
    
    def record_attack(self, ip, pattern):
        """Записываем атаку"""
        now = datetime.now()
        self.ip_requests[ip].append(now)
        
        # Считаем атаки за последнюю минуту
        recent_attacks = sum(1 for attack_time in self.ip_requests[ip] 
                           if now - attack_time < timedelta(minutes=1))
        
        logger.warning(f"Атака от {ip}: {pattern} (всего за минуту: {recent_attacks})")
        
        # Блокируем если превышен порог
        if recent_attacks >= self.attack_threshold and ip not in self.blocked_ips:
            self.block_ip(ip)
    
    def block_ip(self, ip):
        """Блокировка IP через iptables"""
        try:
            # Добавляем правило iptables
            subprocess.run([
                'iptables', '-I', 'INPUT', '-s', ip, '-j', 'DROP'
            ], check=True)
            
            self.blocked_ips.add(ip)
            logger.error(f"🚫 IP {ip} заблокирован через iptables")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка блокировки {ip}: {e}")
        except FileNotFoundError:
            logger.warning("iptables не найден, блокировка недоступна")
    
    def monitor_logs(self, log_file="/var/log/nginx/access.log"):
        """Мониторинг логов в реальном времени"""
        try:
            # Используем tail -f для мониторинга
            process = subprocess.Popen(
                ['tail', '-f', log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            logger.info(f"Начинаем мониторинг {log_file}")
            
            for line in iter(process.stdout.readline, ''):\
                if line:
                    self.analyze_log_line(line.strip())
                    
        except FileNotFoundError:
            logger.error(f"Лог файл {log_file} не найден")
        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен")
        except Exception as e:
            logger.error(f"Ошибка мониторинга: {e}")
    
    def show_stats(self):
        """Показать статистику"""
        logger.info("=== Статистика безопасности ===")
        logger.info(f"Заблокировано IP: {len(self.blocked_ips)}")
        logger.info(f"Отслеживается IP: {len(self.ip_requests)}")
        
        if self.blocked_ips:
            logger.info("Заблокированные IP:")
            for ip in list(self.blocked_ips)[:10]:
                logger.info(f"  - {ip}")

def main():
    monitor = SecurityMonitor()
    
    try:
        # Показываем текущую статистику
        monitor.show_stats()
        
        # Запускаем мониторинг
        monitor.monitor_logs()
        
    except KeyboardInterrupt:
        logger.info("Завершение работы...")
        monitor.show_stats()

if __name__ == "__main__":
    main()