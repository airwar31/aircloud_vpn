#!/usr/bin/env python3
import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def notify_expiring_keys():
    """Уведомления о скором истечении VPN ключей"""
    try:
        db = Database("/shared/vpn_bot.db")
        bot = Bot(token=BOT_TOKEN)
        
        # Получаем ключи, которые истекают в течение 3 дней
        expiring_keys = db.get_expiring_vpn_keys(3)
        
        if not expiring_keys:
            logger.info("Нет ключей для уведомления об истечении")
            return
            
        logger.info(f"Найдено {len(expiring_keys)} ключей для уведомления")
        
        for key in expiring_keys:
            try:
                expires_at = datetime.fromisoformat(key['expires_at'])
                days_left = (expires_at - datetime.now()).days
                
                # Определяем текст в зависимости от количества дней
                if days_left <= 0:
                    time_text = "сегодня"
                elif days_left == 1:
                    time_text = "завтра"
                else:
                    time_text = f"через {days_left} дня"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data=f"extend_{key['id']}")],
                    [InlineKeyboardButton(text="👤 Мои ключи", callback_data="my_keys")]
                ])
                
                message_text = (
                    f"⚠️ <b>Ваша VPN подписка истекает {time_text}!</b>\n\n"
                    f"🔑 <b>Ключ:</b> {key['email']}\n"
                    f"📅 <b>Истекает:</b> {expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"💡 <b>Продлите подписку</b>, чтобы не потерять доступ к VPN!"
                )
                
                await bot.send_message(
                    chat_id=key['telegram_id'],
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                
                # Отмечаем что уведомление отправлено
                db.mark_notification_sent(key['id'])
                logger.info(f"Уведомление отправлено пользователю {key['telegram_id']} о ключе {key['email']}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления пользователю {key['telegram_id']}: {e}")
                
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Общая ошибка уведомлений: {e}")

if __name__ == "__main__":
    asyncio.run(notify_expiring_keys())