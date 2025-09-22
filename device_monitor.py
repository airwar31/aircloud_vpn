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
                async with session.get(f"{XRAY_API_URL}/api/clients/stats") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        connections = {}
                        
                        for client in data.get('clients', []):
                            email = client.get('email', '')
                            active_connections = client.get('active_connections', 0)
                            if email and active_connections > 0:
                                connections[email] = active_connections
                        
                        return connections
                    else:
                        logger.info(f"Мониторинг работает в тестовом режиме (API {resp.status})")
                        return {}
                    
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
            
            user_id = vpn_key['user_id']
            
            if active_devices > allowed_devices:
                await self.send_warning(user_id, email, active_devices, allowed_devices)
                await self.block_user_if_needed(user_id, email, active_devices, allowed_devices)
            else:
                await self.unblock_user_if_needed(user_id, email)
                
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
            
    async def block_user_if_needed(self, user_id: int, email: str, active: int, allowed: int):
        """Блокировка пользователя"""
        if user_id in getattr(self, 'blocked_users', set()):
            return
            
        warning_count = getattr(self, 'warning_counts', {}).get(user_id, 0)
        
        if warning_count >= 3 or active > allowed * 2:
            try:
                await self.disable_vpn_key(email)
                
                await self.bot.send_message(
                    user_id,
                    f"🚫 <b>VPN ключ заблокирован!</b>\n\n"
                    f"🔑 Ключ: <code>{email}</code>\n"
                    f"⚠️ Причина: превышение лимита\n\n"
                    f"📞 Отключите лишние устройства для авторазблокировки",
                    parse_mode="HTML"
                )
                
                if not hasattr(self, 'blocked_users'):
                    self.blocked_users = set()
                self.blocked_users.add(user_id)
                
                logger.info(f"Пользователь {user_id} заблокирован")
                
            except Exception as e:
                logger.error(f"Ошибка блокировки {user_id}: {e}")
        else:
            if not hasattr(self, 'warning_counts'):
                self.warning_counts = {}
            self.warning_counts[user_id] = warning_count + 1
            
    async def unblock_user_if_needed(self, user_id: int, email: str):
        """Разблокировка пользователя"""
        if not hasattr(self, 'blocked_users') or user_id not in self.blocked_users:
            return
            
        try:
            await self.enable_vpn_key(email)
            
            await self.bot.send_message(
                user_id,
                f"✅ <b>VPN ключ разблокирован!</b>\n\n"
                f"🔑 Ключ: <code>{email}</code>\n"
                f"✅ Лимит соблюдается\n\n"
                f"📱 Вы можете снова использовать VPN",
                parse_mode="HTML"
            )
            
            self.blocked_users.remove(user_id)
            
            if hasattr(self, 'warning_counts') and user_id in self.warning_counts:
                del self.warning_counts[user_id]
                
            logger.info(f"Пользователь {user_id} разблокирован")
            
        except Exception as e:
            logger.error(f"Ошибка разблокировки {user_id}: {e}")
            
    async def disable_vpn_key(self, email: str):
        """Отключение VPN ключа"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{XRAY_API_URL}/api/client/disable", json={"email": email}) as resp:
                    if resp.status == 200:
                        logger.info(f"VPN ключ {email} отключен")
                    else:
                        logger.error(f"Ошибка отключения {email}: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка отключения VPN ключа {email}: {e}")
            
    async def enable_vpn_key(self, email: str):
        """Включение VPN ключа"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{XRAY_API_URL}/api/client/enable", json={"email": email}) as resp:
                    if resp.status == 200:
                        logger.info(f"VPN ключ {email} включен")
                    else:
                        logger.error(f"Ошибка включения {email}: {resp.status}")
        except Exception as e:
            logger.error(f"Ошибка включения VPN ключа {email}: {e}")
            
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