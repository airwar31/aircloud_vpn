import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from database import db
from xray_manager import XrayManager

# Импортируем список админов из конфига
from config import ADMIN_IDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_price_change = State()
    waiting_gift_user = State()
    waiting_gift_days = State()

class AdminPanel:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.setup_handlers()
        
    def is_admin(self, user_id: int) -> bool:
        return user_id in ADMIN_IDS
        
    def setup_handlers(self):
        self.dp.message.register(self.cmd_admin, Command("admin"))
        self.dp.callback_query.register(self.show_broadcast, F.data == "broadcast")
        self.dp.callback_query.register(self.show_prices, F.data == "prices")
        self.dp.callback_query.register(self.show_gift, F.data == "gift")
        self.dp.callback_query.register(self.show_stats, F.data == "stats")
        self.dp.callback_query.register(self.edit_price, F.data.startswith("edit_price_"))
        self.dp.message.register(self.process_broadcast, AdminStates.waiting_broadcast)
        self.dp.message.register(self.process_price_change, AdminStates.waiting_price_change)
        self.dp.message.register(self.process_gift_user, AdminStates.waiting_gift_user)
        self.dp.message.register(self.process_gift_days, AdminStates.waiting_gift_days)
        
    async def cmd_admin(self, message: types.Message):
        if not self.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к админ панели")
            return
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
            [InlineKeyboardButton(text="💰 Цены", callback_data="prices")],
            [InlineKeyboardButton(text="🎁 Подарить подписку", callback_data="gift")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")]
        ])
        
        await message.answer(
            "🔧 <b>Админ панель</b>\n\n"
            "Выберите действие:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def show_broadcast(self, callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(AdminStates.waiting_broadcast)
        await callback.message.edit_text(
            "📢 <b>Рассылка сообщения</b>\n\n"
            "Отправьте сообщение для рассылки всем пользователям:",
            parse_mode="HTML"
        )
        
    async def process_broadcast(self, message: types.Message, state: FSMContext):
        if not self.is_admin(message.from_user.id):
            return
            
        users = db.get_all_users()
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await self.bot.send_message(user['telegram_id'], message.text)
                sent += 1
                await asyncio.sleep(0.05)  # Избегаем лимитов
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {user['telegram_id']}: {e}")
                failed += 1
                
        await message.answer(
            f"✅ Рассылка завершена!\n"
            f"📤 Отправлено: {sent}\n"
            f"❌ Не доставлено: {failed}"
        )
        await state.clear()
        
    async def show_prices(self, callback: types.CallbackQuery):
        keyboard_buttons = []
        for plan_id, plan in VPN_PLANS.items():
            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']}₽",
                callback_data=f"edit_price_{plan_id}"
            )])
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            "💰 <b>Управление ценами</b>\n\n"
            "Выберите тариф для изменения цены:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    async def edit_price(self, callback: types.CallbackQuery, state: FSMContext):
        plan_id = callback.data.split("_")[2]
        plan = VPN_PLANS.get(plan_id)
        
        if not plan:
            await callback.answer("❌ Тариф не найден")
            return
            
        await state.update_data(plan_id=plan_id)
        await state.set_state(AdminStates.waiting_price_change)
        
        await callback.message.edit_text(
            f"💰 <b>Изменение цены</b>\n\n"
            f"Тариф: {plan['name']}\n"
            f"Текущая цена: {plan['price']}₽\n\n"
            "Введите новую цену:",
            parse_mode="HTML"
        )
        
    async def process_price_change(self, message: types.Message, state: FSMContext):
        if not self.is_admin(message.from_user.id):
            return
            
        try:
            new_price = int(message.text)
            data = await state.get_data()
            plan_id = data.get('plan_id')
            
            # Обновляем цену в конфиге (в реальном проекте лучше использовать БД)
            VPN_PLANS[plan_id]['price'] = new_price
            
            await message.answer(
                f"✅ Цена тарифа {VPN_PLANS[plan_id]['name']} "
                f"изменена на {new_price}₽"
            )
            await state.clear()
            
        except ValueError:
            await message.answer("❌ Введите корректную цену (число)")
            
    async def show_gift(self, callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(AdminStates.waiting_gift_user)
        await callback.message.edit_text(
            "🎁 <b>Подарить подписку</b>\n\n"
            "Введите username (без @) или Telegram ID пользователя:",
            parse_mode="HTML"
        )
        
    async def process_gift_user(self, message: types.Message, state: FSMContext):
        if not self.is_admin(message.from_user.id):
            return
            
        user_input = message.text.strip()
        user = None
        
        # Поиск по ID
        if user_input.isdigit():
            user = db.get_user(int(user_input))
        else:
            # Поиск по username
            user = db.get_user_by_username(user_input)
            
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
            
        await state.update_data(gift_user_id=user['telegram_id'])
        await state.set_state(AdminStates.waiting_gift_days)
        
        await message.answer(
            f"👤 Пользователь найден: {user.get('username', user.get('first_name', 'Без имени'))}\n\n"
            "Введите количество дней подписки:"
        )
        
    async def process_gift_days(self, message: types.Message, state: FSMContext):
        if not self.is_admin(message.from_user.id):
            return
            
        try:
            days = int(message.text)
            data = await state.get_data()
            user_id = data.get('gift_user_id')
            
            # Создаем подарочную подписку
            success = await self.create_gift_subscription(user_id, days)
            
            if success:
                await message.answer(f"✅ Подписка на {days} дней подарена!")
                # Уведомляем пользователя
                try:
                    await self.bot.send_message(
                        user_id,
                        f"🎁 Вам подарена VPN подписка на {days} дней!\n"
                        "Используйте /start для получения ключа."
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления о подарке пользователю {user_id}: {e}")
            else:
                await message.answer("❌ Ошибка создания подписки")
                
            await state.clear()
            
        except ValueError:
            await message.answer("❌ Введите корректное количество дней")
            
    async def create_gift_subscription(self, user_id: int, days: int) -> bool:
        try:
            # Создаем фиктивный заказ
            order_id = db.create_order(user_id, "gift", f"gift_{user_id}_{datetime.now().timestamp()}", 0)
            
            # Создаем VPN ключ
            user = db.get_user(user_id)
            username = user.get('username') if user else None
            
            if username:
                email = f"{username}_gift_{datetime.now().strftime('%m%d')}"
            else:
                email = f"gift_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
            plan = {"days": days}
            
            async with XrayManager(XRAY_API_URL) as xray:
                result = await xray.add_client(email, plan)
                
                if result:
                    expires_at = datetime.now() + timedelta(days=days)
                    db.add_vpn_key(
                        user_id=user_id,
                        order_id=order_id,
                        email=email,
                        config=result["config"],
                        expires_at=expires_at,
                        traffic_limit=0
                    )
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Ошибка создания подарочной подписки: {e}")
            return False
            
    async def show_stats(self, callback: types.CallbackQuery):
        stats = db.get_stats()
        
        text = (
            "📊 <b>Статистика бота</b>\n\n"
            f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
            f"💰 Оплаченных заказов: {stats.get('paid_orders', 0)}\n"
            f"🔑 Активных ключей: {stats.get('active_keys', 0)}\n"
            f"💵 Общая выручка: {stats.get('total_revenue', 0)}₽\n\n"
            f"📈 Рефералы: {db.get_total_referrals()}\n"
            f"💸 Выплачено бонусов: {db.get_total_referral_payouts()}₽"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="stats")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    async def start_polling(self):
        logger.info("Запуск админ панели...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка при запуске админ панели: {e}")
        finally:
            await self.bot.session.close()

async def main():
    admin = AdminPanel()
    await admin.start_polling()

if __name__ == "__main__":
    asyncio.run(main())