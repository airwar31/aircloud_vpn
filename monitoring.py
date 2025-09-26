import asyncio
import time
import psutil
import logging
import aiohttp
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from config import XRAY_API_URL
import os

logger = logging.getLogger(__name__)

# Метрики Prometheus
cpu_usage = Gauge('system_cpu_percent', 'Использование CPU в процентах')
memory_usage = Gauge('system_memory_percent', 'Использование памяти в процентах')
disk_usage = Gauge('system_disk_percent', 'Использование диска в процентах')
network_bytes_sent = Counter('network_bytes_sent_total', 'Отправлено байт по сети')
network_bytes_recv = Counter('network_bytes_received_total', 'Получено байт по сети')
api_response_time = Histogram('xray_api_response_seconds', 'Время ответа Xray API')
api_status = Gauge('xray_api_status', 'Статус Xray API (1=работает, 0=не работает)')



async def collect_system_metrics():
    """Сбор системных метрик"""
    try:
        cpu_usage.set(psutil.cpu_percent())
        memory_usage.set(psutil.virtual_memory().percent)
        disk_usage.set(psutil.disk_usage('/').percent)
        
        net_io = psutil.net_io_counters()
        network_bytes_sent._value._value = net_io.bytes_sent
        network_bytes_recv._value._value = net_io.bytes_recv
    except Exception as e:
        logger.error(f"Ошибка сбора системных метрик: {e}")

async def collect_api_metrics():
    """Проверка API"""
    try:
        start_time = time.time()
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{XRAY_API_URL}/health") as resp:
                response_time = time.time() - start_time
                api_response_time.observe(response_time)
                api_status.set(1 if resp.status == 200 else 0)
                logger.info(f"API статус: {resp.status}, время: {response_time:.3f}s")
    except Exception as e:
        logger.error(f"Ошибка проверки API: {e}")
        api_response_time.observe(30)
        api_status.set(0)

async def main():
    """Основной цикл мониторинга"""
    start_http_server(8090)
    logger.info("Мониторинг запущен на порту 8090")
    
    while True:
        await collect_system_metrics()
        await collect_api_metrics()
        await asyncio.sleep(30)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())