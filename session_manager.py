import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, db_path: str = "aircloud_vpn.db"):
        self.db_path = db_path
    
    def generate_device_fingerprint(self, user_agent: str, client_ip: str) -> str:
        """Генерация отпечатка устройства"""
        fingerprint_data = f"{user_agent}:{client_ip}:{int(time.time() // 3600)}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    async def check_session_limit(self, xray_uuid: str, client_ip: str, 
                                 user_agent: str = "", max_sessions: int = None) -> Dict:
        """Проверка лимита одновременных сессий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем лимит устройств из подписки
            if max_sessions is None:
                cursor.execute('''
                    SELECT devices FROM subscriptions 
                    WHERE xray_uuid = ? AND is_active = TRUE
                ''', (xray_uuid,))
                result = cursor.fetchone()
                max_sessions = result[0] if result else 1
            
            device_fingerprint = self.generate_device_fingerprint(user_agent, client_ip)
            
            # Очищаем старые сессии (неактивные более 10 минут)
            cutoff_time = datetime.now() - timedelta(minutes=10)
            cursor.execute('''
                DELETE FROM active_sessions 
                WHERE xray_uuid = ? AND last_seen < ?
            ''', (xray_uuid, cutoff_time))
            
            # Проверяем текущие активные сессии
            cursor.execute('''
                SELECT COUNT(*), device_fingerprint FROM active_sessions 
                WHERE xray_uuid = ? 
                GROUP BY device_fingerprint
            ''', (xray_uuid,))
            
            sessions = cursor.fetchall()
            active_sessions_count = len(sessions)
            
            # Проверяем, есть ли уже сессия с этого устройства
            existing_session = False
            for count, fingerprint in sessions:
                if fingerprint == device_fingerprint:
                    existing_session = True
                    break
            
            if existing_session:
                # Обновляем время последней активности
                cursor.execute('''
                    UPDATE active_sessions 
                    SET last_seen = CURRENT_TIMESTAMP, client_ip = ?
                    WHERE xray_uuid = ? AND device_fingerprint = ?
                ''', (client_ip, xray_uuid, device_fingerprint))
                
                conn.commit()
                return {"allowed": True, "reason": "existing_session"}
            
            elif active_sessions_count < max_sessions:
                # Создаем новую сессию
                cursor.execute('''
                    INSERT INTO active_sessions (xray_uuid, client_ip, device_fingerprint)
                    VALUES (?, ?, ?)
                ''', (xray_uuid, client_ip, device_fingerprint))
                
                conn.commit()
                return {"allowed": True, "reason": "new_session"}
            
            else:
                # Превышен лимит сессий - блокируем и уведомляем пользователя
                await self._notify_user_limit_exceeded(xray_uuid, active_sessions_count, max_sessions)
                
                return {
                    "allowed": False, 
                    "reason": "session_limit_exceeded",
                    "active_sessions": active_sessions_count,
                    "max_sessions": max_sessions,
                    "blocked": True
                }
                
        except Exception as e:
            logger.error(f"Ошибка проверки сессии: {e}")
            return {"allowed": True, "reason": "error"}
        finally:
            conn.close()
    
    async def terminate_session(self, xray_uuid: str, device_fingerprint: str = None) -> bool:
        """Завершение сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if device_fingerprint:
                cursor.execute('''
                    DELETE FROM active_sessions 
                    WHERE xray_uuid = ? AND device_fingerprint = ?
                ''', (xray_uuid, device_fingerprint))
            else:
                # Завершить все сессии пользователя
                cursor.execute('''
                    DELETE FROM active_sessions WHERE xray_uuid = ?
                ''', (xray_uuid,))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Ошибка завершения сессии: {e}")
            return False
        finally:
            conn.close()
    
    async def get_active_sessions(self, xray_uuid: str) -> list:
        """Получение списка активных сессий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT client_ip, device_fingerprint, last_seen, created_at
                FROM active_sessions 
                WHERE xray_uuid = ?
                ORDER BY last_seen DESC
            ''', (xray_uuid,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'client_ip': row[0],
                    'device_fingerprint': row[1],
                    'last_seen': row[2],
                    'created_at': row[3]
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Ошибка получения сессий: {e}")
            return []
        finally:
            conn.close()
    
    async def _notify_user_limit_exceeded(self, xray_uuid: str, current_sessions: int, max_sessions: int):
        """Уведомление пользователя о превышении лимита"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем telegram_id пользователя
            cursor.execute('''
                SELECT u.telegram_id, u.first_name, s.plan_id 
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.xray_uuid = ?
            ''', (xray_uuid,))
            
            result = cursor.fetchone()
            if result:
                telegram_id, first_name, plan_id = result
                
                # Отправляем уведомление через бота
                await self._send_telegram_notification(
                    telegram_id, 
                    first_name,
                    current_sessions, 
                    max_sessions,
                    plan_id
                )
                
                # Блокируем все сессии пользователя
                await self.terminate_session(xray_uuid)
                
        except Exception as e:
            logger.error(f"Ошибка уведомления: {e}")
        finally:
            conn.close()
    
    async def _send_telegram_notification(self, telegram_id: int, first_name: str, 
                                        current_sessions: int, max_sessions: int, plan_id: str):
        """Отправка уведомления в Telegram"""
        try:
            # Импортируем бота для отправки сообщения
            from main import bot
            from config import SUBSCRIPTION_PLANS
            
            plan_name = SUBSCRIPTION_PLANS.get(plan_id, {}).get('name', 'Неизвестный план')
            
            message = (
                f"⚠️ {first_name}, превышен лимит устройств!\n\n"
                f"📦 Ваш тариф: {plan_name}\n"
                f"📱 Максимум устройств: {max_sessions}\n"
                f"❌ Подключено: {current_sessions}\n\n"
                f"🚫 VPN заблокирован до отключения лишних устройств\n\n"
                f"💡 Отключите VPN на {current_sessions - max_sessions} устройстве или обновите тариф"
            )
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Обновить тариф", callback_data="select_plan")],
                [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")]
            ])
            
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=keyboard
            )
            
            logger.info(f"Отправлено уведомление о превышении лимита пользователю {telegram_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    
    async def check_and_unblock_user(self, xray_uuid: str) -> bool:
        """Проверка и разблокировка пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Получаем лимит устройств
            cursor.execute('''
                SELECT devices FROM subscriptions 
                WHERE xray_uuid = ? AND is_active = TRUE
            ''', (xray_uuid,))
            result = cursor.fetchone()
            max_sessions = result[0] if result else 1
            
            # Проверяем текущие сессии
            cutoff_time = datetime.now() - timedelta(minutes=10)
            cursor.execute('''
                DELETE FROM active_sessions 
                WHERE xray_uuid = ? AND last_seen < ?
            ''', (xray_uuid, cutoff_time))
            
            cursor.execute('''
                SELECT COUNT(DISTINCT device_fingerprint) FROM active_sessions 
                WHERE xray_uuid = ?
            ''', (xray_uuid,))
            
            current_sessions = cursor.fetchone()[0]
            
            # Если количество сессий в пределах лимита - разблокируем
            if current_sessions <= max_sessions:
                await self._send_unblock_notification(xray_uuid)
                conn.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки разблокировки: {e}")
            return False
        finally:
            conn.close()
    
    async def _send_unblock_notification(self, xray_uuid: str):
        """Уведомление о разблокировке"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.telegram_id, u.first_name 
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.xray_uuid = ?
            ''', (xray_uuid,))
            
            result = cursor.fetchone()
            if result:
                telegram_id, first_name = result
                
                from main import bot
                
                message = (
                    f"✅ {first_name}, VPN разблокирован!\n\n"
                    f"🚀 Количество подключенных устройств соответствует вашему тарифу\n"
                    f"🔑 Можете пользоваться VPN"
                )
                
                await bot.send_message(chat_id=telegram_id, text=message)
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о разблокировке: {e}")
        finally:
            conn.close()