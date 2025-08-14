from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import json

from config import ADMIN_IDS, SUBSCRIPTION_PLANS
from database import Database
from plan_manager import plan_manager

router = Router()
db = Database()

class AdminStates(StatesGroup):
    main_menu = State()
    manage_plans = State()
    add_plan = State()
    edit_plan = State()
    broadcast_message = State()
    give_subscription = State()
    cancel_subscription = State()

def get_admin_main_keyboard():
    """Главная админ клавиатура"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 Управление тарифами", callback_data="admin_plans")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_users_management_keyboard():
    """Клавиатура управления пользователями"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin_give_sub")],
        [InlineKeyboardButton(text="❌ Отменить подписку", callback_data="admin_cancel_sub")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_plans_management_keyboard():
    """Клавиатура управления тарифами"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить тариф", callback_data="admin_add_plan")],
        [InlineKeyboardButton(text="✏️ Изменить тариф", callback_data="admin_edit_plan")],
        [InlineKeyboardButton(text="🗑 Удалить тариф", callback_data="admin_delete_plan")],
        [InlineKeyboardButton(text="📋 Текущие тарифы", callback_data="admin_current_plans")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_plans_list_keyboard(action_prefix=""):
    """Клавиатура со списком тарифов"""
    keyboard = []
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']} ₽",
                callback_data=f"{action_prefix}{plan_id}" if action_prefix else f"plan_info_{plan_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_plans")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Главная админ панель"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Нет доступа")
        return
    
    stats = await db.get_stats()
    
    admin_text = (
        f"👑 Административная панель\n\n"
        f"📊 Статистика:\n"
        f"👥 Пользователей: {stats.get('users', 0)}\n"
        f"✅ Активных подписок: {stats.get('active_subscriptions', 0)}\n"
        f"💰 Доход за месяц: {stats.get('monthly_revenue', 0)} ₽\n\n"
        f"Выберите действие:"
    )
    
    await message.answer(admin_text, reply_markup=get_admin_main_keyboard())
    await state.set_state(AdminStates.main_menu)

@router.callback_query(F.data == "admin_main")
async def admin_main_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное админ меню"""
    await cmd_admin(callback.message, state)

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery, state: FSMContext):
    """Управление пользователями"""
    await callback.message.edit_text(
        "👥 Управление пользователями\n\n"
        "Выберите действие:",
        reply_markup=get_users_management_keyboard()
    )

@router.callback_query(F.data == "admin_plans")
async def admin_plans_callback(callback: CallbackQuery, state: FSMContext):
    """Управление тарифами"""
    await callback.message.edit_text(
        "💰 Управление тарифными планами\n\n"
        "Выберите действие:",
        reply_markup=get_plans_management_keyboard()
    )

@router.callback_query(F.data == "admin_current_plans")
async def admin_current_plans_callback(callback: CallbackQuery):
    """Показать текущие тарифы"""
    plans_text = "📋 Текущие тарифные планы:\n\n"
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        plans_text += f"🔹 {plan['name']}\n"
        plans_text += f"   💰 Цена: {plan['price']} ₽\n"
        plans_text += f"   📅 Срок: {plan['duration']} дней\n"
        plans_text += f"   🆔 ID: {plan_id}\n\n"
    
    await callback.message.edit_text(
        plans_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_plans")]
        ])
    )

@router.callback_query(F.data == "admin_give_sub")
async def admin_give_sub_callback(callback: CallbackQuery, state: FSMContext):
    """Выдача подписки"""
    await callback.message.edit_text(
        "➕ Выдача подписки\n\n"
        "Отправьте ID пользователя или username (@username):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")]
        ])
    )
    await state.set_state(AdminStates.give_subscription)

@router.message(AdminStates.give_subscription)
async def process_give_subscription(message: Message, state: FSMContext):
    """Обработка выдачи подписки"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_input = message.text.strip()
    
    # Определяем пользователя
    user = None
    if user_input.startswith('@'):
        username = user_input[1:]
        user = await db.get_user_by_username(username)
    elif user_input.isdigit():
        user_id = int(user_input)
        user = await db.get_user_by_telegram_id(user_id)
    
    if not user:
        await message.answer(
            "❌ Пользователь не найден\n\n"
            "Попробуйте еще раз или отмените операцию:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")]
            ])
        )
        return
    
    # Сохраняем пользователя и показываем тарифы
    await state.update_data(target_user=user)
    
    await message.answer(
        f"✅ Пользователь найден: {user.get('first_name', 'Неизвестно')} (@{user.get('username', 'нет')})\n\n"
        f"Выберите тарифный план:",
        reply_markup=get_plans_list_keyboard("admin_give_plan_")
    )

@router.callback_query(F.data.startswith("admin_give_plan_"))
async def admin_give_plan_callback(callback: CallbackQuery, state: FSMContext):
    """Выдача конкретного плана"""
    plan_id = callback.data.split("_")[-1]
    data = await state.get_data()
    user = data.get('target_user')
    
    if not user or plan_id not in SUBSCRIPTION_PLANS:
        await callback.answer("❌ Ошибка данных")
        return
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    
    # Создаем подписку
    subscription = await db.create_subscription(
        user_id=user['id'],
        plan_id=plan_id,
        duration_days=plan['duration']
    )
    
    if subscription:
        await callback.message.edit_text(
            f"✅ Подписка выдана!\n\n"
            f"👤 Пользователь: {user.get('first_name', 'Неизвестно')}\n"
            f"📦 План: {plan['name']}\n"
            f"📅 Срок: {plan['duration']} дней\n"
            f"💰 Стоимость: {plan['price']} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
            ])
        )
        
        # Уведомляем пользователя
        try:
            from main import bot
            await bot.send_message(
                user['telegram_id'],
                f"🎉 Вам выдана подписка!\n\n"
                f"📦 План: {plan['name']}\n"
                f"📅 Срок: {plan['duration']} дней\n\n"
                f"Используйте /start для получения VPN ключа"
            )
        except:
            pass
    else:
        await callback.answer("❌ Ошибка создания подписки")
    
    await state.clear()

@router.callback_query(F.data == "admin_cancel_sub")
async def admin_cancel_sub_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена подписки"""
    await callback.message.edit_text(
        "❌ Отмена подписки\n\n"
        "Отправьте ID пользователя или username (@username):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_users")]
        ])
    )
    await state.set_state(AdminStates.cancel_subscription)

@router.message(AdminStates.cancel_subscription)
async def process_cancel_subscription(message: Message, state: FSMContext):
    """Обработка отмены подписки"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    user_input = message.text.strip()
    
    # Определяем пользователя
    user = None
    if user_input.startswith('@'):
        username = user_input[1:]
        user = await db.get_user_by_username(username)
    elif user_input.isdigit():
        user_id = int(user_input)
        user = await db.get_user_by_telegram_id(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден")
        return
    
    # Отменяем подписку
    result = await db.cancel_user_subscription(user['id'])
    
    if result:
        await message.answer(
            f"✅ Подписка отменена!\n\n"
            f"👤 Пользователь: {user.get('first_name', 'Неизвестно')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
            ])
        )
        
        # Уведомляем пользователя
        try:
            from main import bot
            await bot.send_message(
                user['telegram_id'],
                "❌ Ваша подписка была отменена администратором"
            )
        except:
            pass
    else:
        await message.answer("❌ У пользователя нет активной подписки")
    
    await state.clear()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Рассылка сообщений"""
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_main")]
        ])
    )
    await state.set_state(AdminStates.broadcast_message)

@router.message(AdminStates.broadcast_message)
async def process_broadcast(message: Message, state: FSMContext):
    """Обработка рассылки"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    broadcast_text = message.text
    users = await db.get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    await message.answer("📤 Начинаю рассылку...")
    
    from main import bot
    
    for user in users:
        try:
            await bot.send_message(user['telegram_id'], f"📢 Уведомление:\n\n{broadcast_text}")
            sent_count += 1
        except:
            failed_count += 1
    
    await message.answer(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Отправлено: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
        ])
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Подробная статистика"""
    stats = await db.get_detailed_stats()
    
    stats_text = (
        f"📊 Подробная статистика\n\n"
        f"👥 Всего пользователей: {stats.get('total_users', 0)}\n"
        f"✅ Активных подписок: {stats.get('active_subscriptions', 0)}\n"
        f"❌ Истекших подписок: {stats.get('expired_subscriptions', 0)}\n\n"
        f"💰 Финансы:\n"
        f"📈 Доход за день: {stats.get('daily_revenue', 0)} ₽\n"
        f"📈 Доход за неделю: {stats.get('weekly_revenue', 0)} ₽\n"
        f"📈 Доход за месяц: {stats.get('monthly_revenue', 0)} ₽\n"
        f"📈 Общий доход: {stats.get('total_revenue', 0)} ₽\n\n"
        f"📦 По тарифам:\n"
    )
    
    plan_stats = stats.get('plan_stats', {})
    for plan_id, count in plan_stats.items():
        plan_name = SUBSCRIPTION_PLANS.get(plan_id, {}).get('name', plan_id)
        stats_text += f"• {plan_name}: {count}\n"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
        ])
    )

@router.callback_query(F.data == "admin_add_plan")
async def admin_add_plan_callback(callback: CallbackQuery, state: FSMContext):
    """Добавление нового тарифа"""
    await callback.message.edit_text(
        "➕ Добавление нового тарифа\n\n"
        "Отправьте данные в формате:\n"
        "ID|Название|Цена|Дни\n\n"
        "Пример: premium|Premium план|199|30",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_plans")]
        ])
    )
    await state.set_state(AdminStates.add_plan)

@router.message(AdminStates.add_plan)
async def process_add_plan(message: Message, state: FSMContext):
    """Обработка добавления плана"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        parts = message.text.strip().split('|')
        if len(parts) != 4:
            await message.answer("❌ Неверный формат. Попробуйте еще раз")
            return
        
        plan_id, name, price, duration = parts
        price = int(price)
        duration = int(duration)
        
        if plan_manager.add_plan(plan_id, name, price, duration):
            await message.answer(
                f"✅ Тариф добавлен!\n\n"
                f"🆔 ID: {plan_id}\n"
                f"📝 Название: {name}\n"
                f"💰 Цена: {price} ₽\n"
                f"📅 Срок: {duration} дней",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
                ])
            )
        else:
            await message.answer("❌ Тариф с таким ID уже существует")
    
    except ValueError:
        await message.answer("❌ Неверные числовые значения")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

@router.callback_query(F.data == "admin_edit_plan")
async def admin_edit_plan_callback(callback: CallbackQuery):
    """Редактирование тарифа"""
    await callback.message.edit_text(
        "✏️ Выберите тариф для редактирования:",
        reply_markup=get_plans_list_keyboard("admin_edit_plan_")
    )

@router.callback_query(F.data.startswith("admin_edit_plan_"))
async def admin_edit_plan_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор плана для редактирования"""
    plan_id = callback.data.split("_")[-1]
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    
    if not plan:
        await callback.answer("❌ Тариф не найден")
        return
    
    await state.update_data(edit_plan_id=plan_id)
    
    await callback.message.edit_text(
        f"✏️ Редактирование тарифа\n\n"
        f"🆔 Текущие данные:\n"
        f"Название: {plan['name']}\n"
        f"Цена: {plan['price']} ₽\n"
        f"Срок: {plan['duration']} дней\n\n"
        f"Отправьте новые данные в формате:\n"
        "Название|Цена|Дни\n\n"
        f"Пример: {plan['name']}|{plan['price']}|{plan['duration']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_plans")]
        ])
    )
    await state.set_state(AdminStates.edit_plan)

@router.message(AdminStates.edit_plan)
async def process_edit_plan(message: Message, state: FSMContext):
    """Обработка редактирования плана"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        data = await state.get_data()
        plan_id = data.get('edit_plan_id')
        
        parts = message.text.strip().split('|')
        if len(parts) != 3:
            await message.answer("❌ Неверный формат")
            return
        
        name, price, duration = parts
        price = int(price)
        duration = int(duration)
        
        if plan_manager.update_plan(plan_id, name, price, duration):
            await message.answer(
                f"✅ Тариф обновлен!\n\n"
                f"🆔 ID: {plan_id}\n"
                f"📝 Название: {name}\n"
                f"💰 Цена: {price} ₽\n"
                f"📅 Срок: {duration} дней",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
                ])
            )
        else:
            await message.answer("❌ Ошибка обновления")
    
    except ValueError:
        await message.answer("❌ Неверные числовые значения")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()

@router.callback_query(F.data == "admin_delete_plan")
async def admin_delete_plan_callback(callback: CallbackQuery):
    """Удаление тарифа"""
    await callback.message.edit_text(
        "🗑 Выберите тариф для удаления:",
        reply_markup=get_plans_list_keyboard("admin_delete_plan_")
    )

@router.callback_query(F.data.startswith("admin_delete_plan_"))
async def admin_delete_plan_confirm(callback: CallbackQuery):
    """Подтверждение удаления"""
    plan_id = callback.data.split("_")[-1]
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    
    if not plan:
        await callback.answer("❌ Тариф не найден")
        return
    
    await callback.message.edit_text(
        f"⚠️ Подтвердите удаление\n\n"
        f"📝 Тариф: {plan['name']}\n"
        f"💰 Цена: {plan['price']} ₽\n\n"
        f"⚠️ Это действие нельзя отменить!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{plan_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_plans")]
        ])
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_plan(callback: CallbackQuery):
    """Окончательное удаление"""
    plan_id = callback.data.split("_")[-1]
    
    if plan_manager.delete_plan(plan_id):
        await callback.message.edit_text(
            f"✅ Тариф {plan_id} удален!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="admin_main")]
            ])
        )
    else:
        await callback.answer("❌ Ошибка удаления")

@router.callback_query(F.data == "admin_close")
async def admin_close_callback(callback: CallbackQuery, state: FSMContext):
    """Закрытие админ панели"""
    await callback.message.delete()
    await state.clear()