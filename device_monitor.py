import asyncio
import logging
import aiohttp
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from aiogram import Bot
from config import BOT_TOKEN, XRAY_API_URL
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceMonitor:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.warned_users = {}  # Кэш предупреждений
        
    async def get_xray_stats(self) -> Dict[str, int]:
        """Получение статистики подключений из Xray API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{XRAY_API_URL}/panel/api/inbounds/list") as resp:
                    if resp.status != 200:
                        logger.error(f"Ошибка получения inbounds: {resp.status}")
                        return {}
                    
                    data = await resp.json()
                    inbounds = data.get("obj", [])
                    
                    connections = defaultdict(int)
                    
                    for inbound in inbounds:
                        if not inbound.get("enable", False):
                            continue
                            
                        settings = json.loads(inbound.get("settings", "{}"))
                        clients = settings.get("clients", [])
                        
                        for client in clients:
                            email = client.get("email", "")
                            if email:
                                # Получаем статистику трафика для определения активности
                                traffic_stats = await self.get_client_traffic(email)
                                if traffic_stats and traffic_stats.get("active_connections", 0) > 0:
                                    connections[email] = traffic_stats["active_connections"]
                    
                    return dict(connections)
                    
        except Exception as e:
            logger.error(f"Ошибка получения статистики Xray: {e}")
            return {}
            
    async def get_client_traffic(self, email: str) -> Dict:
        """Получение статистики трафика клиента"""
        try:
            # Здесь должен быть запрос к Xray API для получения статистики
            # Пока возвращаем заглушку с случайным количеством подключений
            import random
            return {
                "active_connections": random.randint(1, 3),
                "upload": 0,
                "download": 0
            }
        except Exception as e:
            logger.error(f"Ошибка получения трафика для {email}: {e}")
            return {}
        
    async def check_device_limits(self):
        """Проверка лимитов устройств"""
        connections = await self.get_xray_stats()
        
        for email, active_devices in connections.items():
            # Получаем информацию о клиенте из БД
            vpn_keys = db.get_user_vpn_keys_by_email(email)
            
            if not vpn_keys:
                continue
                
            vpn_key = vpn_keys[0]
            allowed_devices = vpn_key.get('device_limit', 1)
            
            if active_devices > allowed_devices:
                await self.send_warning(vpn_key['user_id'], email, active_devices, allowed_devices)
                
    async def send_warning(self, user_id: int, email: str, active: int, allowed: int):
        """Отправка предупреждения пользователю"""
        # Проверяем, не отправляли ли уже предупреждение недавно
        now = datetime.now()
        last_warning = self.warned_users.get(user_id)
        
        if last_warning and (now - last_warning) < timedelta(minutes=30):
            return  # Не спамим предупреждениями
            
        try:
            await self.bot.send_message(
                user_id,
                f"⚠️ <b>Превышен лимит устройств!</b>\n\n"
                f"🔑 Ключ: <code>{email}</code>\n"
                f"📱 Подключено: <b>{active}</b> устройств\n"
                f"✅ Разрешено: <b>{allowed}</b> устройств\n\n"
                f"❗ <b>Отключите {active - allowed} лишних устройств</b>, "
                f"иначе соединение может быть заблокировано.\n\n"
                f"💡 <i>Для отключения устройства просто выключите VPN на ненужном устройстве.</i>",
                parse_mode="HTML"
            )
            
            self.warned_users[user_id] = now
            logger.info(f"Отправлено предупреждение пользователю {user_id} о превышении лимита устройств")
            
        except Exception as e:
            logger.error(f"Ошибка отправки предупреждения пользователю {user_id}: {e}")
            
    async def monitor_loop(self):
        """Основной цикл мониторинга"""
        while True:
            try:
                await self.check_device_limits()
                await asyncio.sleep(300)  # Проверка каждые 5 минут
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)
                
    async def start(self):
        """Запуск мониторинга"""
        logger.info("Запуск мониторинга устройств...")
        await self.monitor_loop()
        
    async def cleanup(self):
        """Очистка ресурсов"""
        await self.bot.session.close()

async def main():
    monitor = DeviceMonitor()
    try:
        await monitor.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    finally:
        await monitor.cleanup()
        logger.info("Мониторинг устройств остановлен")

if __name__ == "__main__":
    asyncio.run(main())