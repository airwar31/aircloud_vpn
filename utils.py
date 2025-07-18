import logging
from aiogram.types import Message, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

async def safe_edit_message(message: Message, text: str, reply_markup=None, parse_mode=None):
    """Безопасное обновление сообщения с обработкой ошибки 'message is not modified'"""
    try:
        await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Ошибка при обновлении сообщения: {str(e)}")
            return False
        return True  # Сообщение не изменилось, но это не ошибка