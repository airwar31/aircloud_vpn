import asyncio
import time
import psutil
import logging
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from database_mysql import DatabaseMySQL
from xray_manager import XrayManager
from config import XRAY_API_URL
import os

logger = logging.getLogger(__name__)

# Метрики Prometheus
active_users = Gauge('vpn_active_users_total', 'Количество активных пользователей')
total_users = Gauge('vpn_total_users', 'Общее количество пользователей')
expired_users = Gauge('vpn_expired_users', 'Количество истекших пользователей')
cpu_usage = Gauge('system_cpu_percent', 'Использование CPU в процентах')
memory_usage = Gauge('system_memory_percent', 'Использование памяти в процентах')
disk_usage = Gauge('system_disk_percent', 'Использование диска в процентах')
network_bytes_sent = Counter('network_bytes_sent_total', 'Отправлено байт по сети')
network_bytes_recv = Counter('network_bytes_received_total', 'Получено байт по сети')
api_response_time = Histogram('xray_api_response_seconds', 'Время ответа Xray API')

class MonitoringService:
    def __init__(self):
        self.db = DatabaseMySQL()
        
    async def collect_metrics(self):
        """Сбор всех метрик"""
        try:
            # Системные метрики
            cpu_usage.set(psutil.cpu_percent())
            memory_usage.set(psutil.virtual_memory().percent)
            disk_usage.set(psutil.disk_usage('/').percent)
            
            # Сетевые метрики
            net_io = psutil.net_io_counters()
            network_bytes_sent._value._value = net_io.bytes_sent
            network_bytes_recv._value._value = net_io.bytes_recv
            
            # VPN метрики
            await self.collect_vpn_metrics()
            
            # Метрики API
            await self.collect_api_metrics()
            
        except Exception as e:
            logger.error(f"Ошибка сбора метрик: {e}")
    
    async def collect_vpn_metrics(self):
        """Сбор метрик VPN пользователей"""
        try:
            now = datetime.now()
            
            # Активные пользователи
            active_count = await self.db.execute_query(
                "SELECT COUNT(*) as count FROM vpn_keys WHERE expires_at > %s",
                (now,)
            )
            active_users.set(active_count[0]['count'] if active_count else 0)
            
            # Общее количество
            total_count = await self.db.execute_query("SELECT COUNT(*) as count FROM vpn_keys")
            total_users.set(total_count[0]['count'] if total_count else 0)
            
            # Истекшие
            expired_count = await self.db.execute_query(
                "SELECT COUNT(*) as count FROM vpn_keys WHERE expires_at <= %s",
                (now,)
            )
            expired_users.set(expired_count[0]['count'] if expired_count else 0)
            
        except Exception as e:
            logger.error(f"Ошибка сбора VPN метрик: {e}")
    
    async def collect_api_metrics(self):
        """Проверка времени ответа API"""
        try:
            start_time = time.time()
            async with XrayManager(XRAY_API_URL) as xray:
                # Простой health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{XRAY_API_URL}/health") as resp:
                        response_time = time.time() - start_time
                        api_response_time.observe(response_time)
        except Exception as e:
            logger.error(f"Ошибка проверки API: {e}")
            api_response_time.observe(30)  # Таймаут как максимальное время

async def main():
    """Основной цикл мониторинга"""
    monitoring = MonitoringService()
    
    # Запуск HTTP сервера для Prometheus
    start_http_server(8090)
    logger.info("Мониторинг запущен на порту 8090")
    
    while True:
        await monitoring.collect_metrics()
        await asyncio.sleep(30)  # Сбор метрик каждые 30 секунд

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())