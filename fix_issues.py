#!/usr/bin/env python3
"""
Скрипт для быстрого исправления основных проблем
"""
import os
import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(cmd, description):
    """Выполнение команды с логированием"""
    logger.info(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ {description} - успешно")
            return True
        else:
            logger.error(f"❌ {description} - ошибка: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ {description} - исключение: {e}")
        return False

def fix_yookassa():
    """Исправление проблем с YooKassa"""
    logger.info("=== Исправление YooKassa ===")
    
    # Проверяем переменные окружения
    if not os.getenv("YOOKASSA_SHOP_ID"):
        logger.error("❌ YOOKASSA_SHOP_ID не найден в .env")
        return False
    
    if not os.getenv("YOOKASSA_SECRET_KEY"):
        logger.error("❌ YOOKASSA_SECRET_KEY не найден в .env")
        return False
    
    # Тестируем подключение
    logger.info("🔍 Тестирование YooKassa...")
    return run_command("python test_yookassa.py", "Тест YooKassa API")

def fix_security():
    """Настройка базовой безопасности"""
    logger.info("=== Настройка безопасности ===")
    
    fixes = [
        # Блокируем подозрительные IP
        ("iptables -I INPUT -s 90.151.171.108 -j DROP", "Блокировка атакующего IP 90.151.171.108"),
        ("iptables -I INPUT -s 90.151.171.106 -j DROP", "Блокировка атакующего IP 90.151.171.106"),
        ("iptables -I INPUT -s 196.251.81.30 -j DROP", "Блокировка SSH атакующего IP"),
        
        # Ограничиваем подключения
        ("iptables -A INPUT -p tcp --dport 8080 -m connlimit --connlimit-above 10 -j DROP", 
         "Ограничение подключений к API"),
        ("iptables -A INPUT -p tcp --dport 8444 -m connlimit --connlimit-above 50 -j DROP", 
         "Ограничение подключений к VPN"),
    ]
    
    success_count = 0
    for cmd, desc in fixes:
        if run_command(cmd, desc):
            success_count += 1
    
    logger.info(f"✅ Применено {success_count}/{len(fixes)} правил безопасности")
    return success_count > 0

def fix_docker():
    """Исправление проблем с Docker"""
    logger.info("=== Исправление Docker ===")
    
    fixes = [
        ("docker system prune -f", "Очистка неиспользуемых ресурсов Docker"),
        ("docker-compose down", "Остановка сервисов"),
        ("docker-compose up -d --build", "Пересборка и запуск сервисов"),
    ]
    
    success_count = 0
    for cmd, desc in fixes:
        if run_command(cmd, desc):
            success_count += 1
    
    return success_count == len(fixes)

def check_services():
    """Проверка состояния сервисов"""
    logger.info("=== Проверка сервисов ===")
    
    checks = [
        ("docker ps", "Статус контейнеров"),
        ("curl -s http://localhost:8080/health", "Проверка Xray API"),
        ("curl -s http://localhost:8081/agreement", "Проверка Agreement сервера"),
    ]
    
    for cmd, desc in checks:
        run_command(cmd, desc)

def main():
    logger.info("🚀 Запуск исправления проблем...")
    logger.info(f"Время: {datetime.now()}")
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists("docker-compose.yml"):
        logger.error("❌ docker-compose.yml не найден. Запустите скрипт из корневой директории проекта.")
        sys.exit(1)
    
    success = True
    
    # Исправляем проблемы по порядку
    if not fix_yookassa():
        logger.warning("⚠️ Проблемы с YooKassa не исправлены")
        success = False
    
    if not fix_security():
        logger.warning("⚠️ Не все правила безопасности применены")
    
    if not fix_docker():
        logger.warning("⚠️ Проблемы с Docker не исправлены")
        success = False
    
    # Проверяем результат
    check_services()
    
    if success:
        logger.info("✅ Основные проблемы исправлены!")
    else:
        logger.warning("⚠️ Некоторые проблемы остались. Проверьте логи выше.")
    
    logger.info("🏁 Исправление завершено")

if __name__ == "__main__":
    main()