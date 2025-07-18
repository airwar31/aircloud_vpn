import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from config import ADMIN_IDS, SUBSCRIPTION_PLANS
from database import Database
from xray_api import XrayAPI
from utils import safe_edit_message

# Инициализация логгера
logger = logging.getLogger(__name__)

# Инициализация базы данных и API Xray
db = Database()
xray = XrayAPI()

# Создаем роутер для административной панели
router = Router()

# Состояния для FSM административной панели
class AdminStates(StatesGroup):
    main_menu = State()
    user_management = State()
    subscription_management = State()
    stats_view = State()
    waiting_for_user_id = State()
    waiting_for_days = State()
    confirm_action = State()

# Функции для создания клавиатур
def get_admin_main_keyboard():
    """Получение основной клавиатуры административной панели"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔑 Управление подписками", callback_data="admin_subscriptions")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_management_keyboard():
    """Получение клавиатуры управления пользователями"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_find_user")],
        [InlineKeyboardButton(text="➕ Добавить пользователя", callback_data="admin_add_user")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subscription_management_keyboard():
    """Получение клавиатуры управления подписками"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Выдать подписку", callback_data="admin_give_sub")],
        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="admin_extend_sub")],
        [InlineKeyboardButton(text="❌ Отменить подписку", callback_data="admin_cancel_sub")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_stats_keyboard():
    """Получение клавиатуры статистики"""
    keyboard = [
        [InlineKeyboardButton(text="📈 Общая статистика", callback_data="admin_general_stats")],
        [InlineKeyboardButton(text="💰 Финансовая статистика", callback_data="admin_financial_stats")],
        [InlineKeyboardButton(text="👥 Статистика пользователей", callback_data="admin_user_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_keyboard(action, user_id=None, plan_id=None):
    """Получение клавиатуры подтверждения действия"""
    data = f"{action}"
    if user_id:
        data += f"_{user_id}"
    if plan_id:
        data += f"_{plan_id}"
    
    keyboard = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{data}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_plans_selection_keyboard(action, user_id):
    """Получение клавиатуры выбора тарифного плана"""
    keyboard = []
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']} руб.", 
                callback_data=f"admin_select_plan_{action}_{plan_id}_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_subscriptions")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Обработчики команд
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Обработчик команды /admin - главная страница административной панели"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для доступа к административной панели.")
        return
    
    await message.answer(
        "🔐 <b>Административная панель AirCloud VPN</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.main_menu)

# Обработчики кнопок главного меню
@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки управления пользователями"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await safe_edit_message(callback.message, "У вас нет прав для доступа к этому разделу.")
        return
    
    await safe_edit_message(
        callback.message,
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_user_management_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.user_management)

@router.callback_query(F.data == "admin_subscriptions")
async def admin_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки управления подписками"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await safe_edit_message(callback.message, "У вас нет прав для доступа к этому разделу.")
        return
    
    await safe_edit_message(
        callback.message,
        "🔑 <b>Управление подписками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_subscription_management_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.subscription_management)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки просмотра статистики"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await safe_edit_message(callback.message, "У вас нет прав для доступа к этому разделу.")
        return
    
    await safe_edit_message(
        callback.message,
        "📊 <b>Статистика</b>\n\n"
        "Выберите тип статистики:",
        reply_markup=get_stats_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.stats_view)

@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(callback: CallbackQuery):
    """Обработчик кнопки обновления административной панели"""
    await callback.answer("Панель обновлена")
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await safe_edit_message(callback.message, "У вас нет прав для доступа к этому разделу.")
        return
    
    await safe_edit_message(
        callback.message,
        "🔐 <b>Административная панель AirCloud VPN</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_back_to_main")
async def admin_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата в главное меню"""
    await callback.answer()
    
    await safe_edit_message(
        callback.message,
        "🔐 <b>Административная панель AirCloud VPN</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.main_menu)

# Обработчики кнопок управления пользователями
@router.callback_query(F.data == "admin_list_users")
async def admin_list_users(callback: CallbackQuery):
    """Обработчик кнопки списка пользователей"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        # Получаем список пользователей из базы данных
        db_conn = await db.connect()
        async with db_conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT 10") as cursor:
            users = await cursor.fetchall()
        
        if users:
            users_text = "📋 <b>Список последних 10 пользователей:</b>\n\n"
            for user in users:
                user_dict = dict(user)
                users_text += f"ID: {user_dict['telegram_id']}\n"
                users_text += f"Имя: {user_dict['first_name'] or 'Не указано'}\n"
                users_text += f"Юзернейм: @{user_dict['username'] or 'Не указан'}\n"
                users_text += f"Дата регистрации: {user_dict['created_at']}\n\n"
            
            # Добавляем кнопку "Назад"
            keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]]
            
            await callback.message.edit_text(
                users_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "Пользователи не найдены.",
                reply_markup=get_user_management_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
        await callback.message.edit_text(
            f"Произошла ошибка при получении списка пользователей: {str(e)}",
            reply_markup=get_user_management_keyboard()
        )

@router.callback_query(F.data == "admin_find_user")
async def admin_find_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки поиска пользователя"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    await callback.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_user_id)

@router.message(AdminStates.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext):
    """Обработчик ввода ID пользователя"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        user_id = int(message.text)
        
        # Получаем информацию о пользователе
        user = await db.get_user(user_id)
        
        if user:
            # Получаем информацию о подписке пользователя
            subscription = await db.get_user_subscription(user_id)
            
            user_info = f"👤 <b>Информация о пользователе:</b>\n\n"
            user_info += f"ID: {user['telegram_id']}\n"
            user_info += f"Имя: {user['first_name'] or 'Не указано'}\n"
            user_info += f"Фамилия: {user['last_name'] or 'Не указано'}\n"
            user_info += f"Юзернейм: @{user['username'] or 'Не указан'}\n"
            user_info += f"Дата регистрации: {user['created_at']}\n\n"
            
            if subscription and subscription['active']:
                expiry_date = subscription['expiry_date']
                days_left = (expiry_date - datetime.now()).days
                
                user_info += f"<b>Подписка:</b> Активна\n"
                user_info += f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
                user_info += f"Осталось дней: {days_left}\n"
            else:
                user_info += "<b>Подписка:</b> Отсутствует\n"
            
            # Создаем клавиатуру с действиями для пользователя
            keyboard = [
                [InlineKeyboardButton(text="➕ Выдать подписку", callback_data=f"admin_give_sub_to_{user_id}")],
                [InlineKeyboardButton(text="❌ Отменить подписку", callback_data=f"admin_cancel_sub_for_{user_id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
            ]
            
            await message.answer(
                user_info,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
            
            await state.set_state(AdminStates.user_management)
        else:
            await message.answer(
                f"Пользователь с ID {user_id} не найден.",
                reply_markup=get_user_management_keyboard()
            )
            
            await state.set_state(AdminStates.user_management)
    
    except ValueError:
        await message.answer(
            "ID пользователя должен быть числом. Попробуйте снова:",
            reply_markup=get_user_management_keyboard()
        )
        
        await state.set_state(AdminStates.user_management)

# Обработчики кнопок управления подписками
@router.callback_query(F.data == "admin_give_sub")
async def admin_give_sub(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки выдачи подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    await callback.message.edit_text(
        "➕ <b>Выдача подписки</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await state.update_data(action="give_sub")

@router.callback_query(F.data.startswith("admin_give_sub_to_"))
async def admin_give_sub_to_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки выдачи подписки конкретному пользователю"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.split("_")[-1])
    
    # Проверяем, существует ли пользователь
    user = await db.get_user(user_id)
    if not user:
        await callback.message.edit_text(
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Показываем клавиатуру с выбором тарифного плана
    await callback.message.edit_text(
        f"Выберите тарифный план для пользователя {user_id}:",
        reply_markup=get_plans_selection_keyboard("give", user_id)
    )

@router.callback_query(F.data.startswith("admin_select_plan_give_"))
async def admin_select_plan_give(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора тарифного плана для выдачи подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    # Получаем данные из callback_data
    parts = callback.data.split("_")
    plan_id = parts[4]
    user_id = int(parts[5])
    
    # Проверяем, существует ли такой тарифный план
    if plan_id not in SUBSCRIPTION_PLANS:
        await callback.message.edit_text(
            "Выбран несуществующий тарифный план.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Получаем информацию о тарифном плане
    plan = SUBSCRIPTION_PLANS[plan_id]
    
    # Сохраняем данные в состоянии
    await state.update_data(user_id=user_id, plan_id=plan_id)
    
    # Запрашиваем подтверждение
    await callback.message.edit_text(
        f"Вы собираетесь выдать подписку на <b>{plan['name']}</b> "
        f"пользователю с ID <b>{user_id}</b>.\n\n"
        f"Стоимость: {plan['price']} руб.\n"
        f"Срок: {plan['days']} дней\n\n"
        "Подтвердите действие:",
        reply_markup=get_confirm_keyboard("give_sub", user_id, plan_id),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.confirm_action)

@router.callback_query(F.data.startswith("admin_confirm_give_sub_"))
async def admin_confirm_give_sub(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения выдачи подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    # Получаем данные из callback_data
    parts = callback.data.split("_")
    user_id = int(parts[3])
    plan_id = parts[4] if len(parts) > 4 else None
    
    # Проверяем, существует ли пользователь
    user = await db.get_user(user_id)
    if not user:
        await callback.message.edit_text(
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Проверяем, существует ли такой тарифный план
    if plan_id not in SUBSCRIPTION_PLANS:
        await callback.message.edit_text(
            "Выбран несуществующий тарифный план.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Получаем информацию о тарифном плане
    plan = SUBSCRIPTION_PLANS[plan_id]
    days = plan["days"]
    
    try:
        # Создаем VPN ключ через Xray API
        user_data = await xray.create_user(email=f"tg_{user_id}")
        
        if user_data and "link" in user_data:
            # Сохраняем информацию о подписке в базу данных
            expiry_date = datetime.now() + timedelta(days=days)
            await db.create_subscription(user_id, user_data["link"], expiry_date)
            
            await callback.message.edit_text(
                f"✅ Подписка на <b>{plan['name']}</b> успешно выдана пользователю <b>{user_id}</b>.\n\n"
                f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}",
                reply_markup=get_subscription_management_keyboard(),
                parse_mode="HTML"
            )
            
            # Отправляем уведомление пользователю
            try:
                from main import bot
                await bot.send_message(
                    user_id,
                    f"Вам выдана подписка на {plan['name']}!\n"
                    f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
                    "Используйте команду /start для просмотра ключа и инструкции по настройке."
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")
        else:
            await callback.message.edit_text(
                f"❌ Произошла ошибка при создании VPN ключа для пользователя {user_id}.",
                reply_markup=get_subscription_management_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при выдаче подписки: {str(e)}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при выдаче подписки: {str(e)}",
            reply_markup=get_subscription_management_keyboard()
        )
    
    await state.set_state(AdminStates.subscription_management)

@router.callback_query(F.data == "admin_cancel_sub")
async def admin_cancel_sub(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    await callback.message.edit_text(
        "❌ <b>Отмена подписки</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await state.update_data(action="cancel_sub")

@router.callback_query(F.data.startswith("admin_cancel_sub_for_"))
async def admin_cancel_sub_for_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены подписки конкретному пользователю"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.split("_")[-1])
    
    # Проверяем, существует ли пользователь
    user = await db.get_user(user_id)
    if not user:
        await callback.message.edit_text(
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Проверяем, есть ли у пользователя активная подписка
    subscription = await db.get_user_subscription(user_id)
    if not subscription or not subscription['active']:
        await callback.message.edit_text(
            f"У пользователя с ID {user_id} нет активной подписки.",
            reply_markup=get_subscription_management_keyboard()
        )
        return
    
    # Запрашиваем подтверждение
    await callback.message.edit_text(
        f"Вы собираетесь отменить подписку пользователя с ID <b>{user_id}</b>.\n\n"
        "Подтвердите действие:",
        reply_markup=get_confirm_keyboard("cancel_sub", user_id),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.confirm_action)

@router.callback_query(F.data.startswith("admin_confirm_cancel_sub_"))
async def admin_confirm_cancel_sub(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения отмены подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    # Получаем ID пользователя из callback_data
    user_id = int(callback.data.split("_")[-1])
    
    try:
        # Получаем информацию о подписке пользователя
        subscription = await db.get_user_subscription(user_id)
        
        if subscription and subscription['active']:
            # Деактивируем подписку
            db_conn = await db.connect()
            await db_conn.execute(
                "UPDATE subscriptions SET active = 0 WHERE id = ?",
                (subscription['id'],)
            )
            await db_conn.commit()
            
            await callback.message.edit_text(
                f"✅ Подписка пользователя с ID <b>{user_id}</b> успешно отменена.",
                reply_markup=get_subscription_management_keyboard(),
                parse_mode="HTML"
            )
            
            # Отправляем уведомление пользователю
            try:
                from main import bot
                await bot.send_message(
                    user_id,
                    "Ваша подписка была отменена администратором.\n"
                    "Для получения новой подписки используйте команду /start."
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")
        else:
            await callback.message.edit_text(
                f"У пользователя с ID {user_id} нет активной подписки.",
                reply_markup=get_subscription_management_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при отмене подписки: {str(e)}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при отмене подписки: {str(e)}",
            reply_markup=get_subscription_management_keyboard()
        )
    
    await state.set_state(AdminStates.subscription_management)

@router.callback_query(F.data == "admin_extend_sub")
async def admin_extend_sub(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки продления подписки"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    await callback.message.edit_text(
        "🔄 <b>Продление подписки</b>\n\n"
        "Введите ID пользователя:",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await state.update_data(action="extend_sub")

@router.message(AdminStates.waiting_for_user_id, lambda message: "action" in message.bot.get("state_data", {}))
async def process_user_id_with_action(message: Message, state: FSMContext):
    """Обработчик ввода ID пользователя с действием"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        user_id = int(message.text)
        
        # Получаем информацию о пользователе
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer(
                f"Пользователь с ID {user_id} не найден.",
                reply_markup=get_subscription_management_keyboard()
            )
            await state.set_state(AdminStates.subscription_management)
            return
        
        # Получаем действие из состояния
        data = await state.get_data()
        action = data.get("action")
        
        if action == "give_sub":
            # Показываем клавиатуру с выбором тарифного плана
            await message.answer(
                f"Выберите тарифный план для пользователя {user_id}:",
                reply_markup=get_plans_selection_keyboard("give", user_id)
            )
        
        elif action == "extend_sub":
            # Проверяем, есть ли у пользователя активная подписка
            subscription = await db.get_user_subscription(user_id)
            
            if subscription and subscription['active']:
                # Показываем клавиатуру с выбором тарифного плана
                await message.answer(
                    f"Выберите тарифный план для продления подписки пользователя {user_id}:",
                    reply_markup=get_plans_selection_keyboard("extend", user_id)
                )
            else:
                await message.answer(
                    f"У пользователя с ID {user_id} нет активной подписки.",
                    reply_markup=get_subscription_management_keyboard()
                )
                await state.set_state(AdminStates.subscription_management)
        
        elif action == "cancel_sub":
            # Проверяем, есть ли у пользователя активная подписка
            subscription = await db.get_user_subscription(user_id)
            
            if subscription and subscription['active']:
                # Запрашиваем подтверждение
                await message.answer(
                    f"Вы собираетесь отменить подписку пользователя с ID <b>{user_id}</b>.\n\n"
                    "Подтвердите действие:",
                    reply_markup=get_confirm_keyboard("cancel_sub", user_id),
                    parse_mode="HTML"
                )
                
                await state.set_state(AdminStates.confirm_action)
            else:
                await message.answer(
                    f"У пользователя с ID {user_id} нет активной подписки.",
                    reply_markup=get_subscription_management_keyboard()
                )
                await state.set_state(AdminStates.subscription_management)
    
    except ValueError:
        await message.answer(
            "ID пользователя должен быть числом. Попробуйте снова:",
            reply_markup=get_subscription_management_keyboard()
        )
        await state.set_state(AdminStates.subscription_management)

# Обработчики кнопок статистики
@router.callback_query(F.data == "admin_general_stats")
async def admin_general_stats(callback: CallbackQuery):
    """Обработчик кнопки общей статистики"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        db_conn = await db.connect()
        
        # Получаем общее количество пользователей
        async with db_conn.execute("SELECT COUNT(*) as count FROM users") as cursor:
            result = await cursor.fetchone()
            total_users = result['count'] if result else 0
        
        # Получаем количество активных подписок
        async with db_conn.execute("SELECT COUNT(*) as count FROM subscriptions WHERE active = 1") as cursor:
            result = await cursor.fetchone()
            active_subscriptions = result['count'] if result else 0
        
        # Получаем количество новых пользователей за последние 24 часа
        async with db_conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE created_at >= datetime('now', '-1 day')"
        ) as cursor:
            result = await cursor.fetchone()
            new_users_24h = result['count'] if result else 0
        
        # Получаем количество новых подписок за последние 24 часа
        async with db_conn.execute(
            "SELECT COUNT(*) as count FROM subscriptions WHERE created_at >= datetime('now', '-1 day')"
        ) as cursor:
            result = await cursor.fetchone()
            new_subscriptions_24h = result['count'] if result else 0
        
        stats_text = "📊 <b>Общая статистика</b>\n\n"
        stats_text += f"👥 Всего пользователей: {total_users}\n"
        stats_text += f"🔑 Активных подписок: {active_subscriptions}\n"
        stats_text += f"👤 Новых пользователей за 24ч: {new_users_24h}\n"
        stats_text += f"🆕 Новых подписок за 24ч: {new_subscriptions_24h}\n"
        
        # Добавляем кнопку "Назад"
        keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats")]]
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении общей статистики: {str(e)}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при получении статистики: {str(e)}",
            reply_markup=get_stats_keyboard()
        )

@router.callback_query(F.data == "admin_financial_stats")
async def admin_financial_stats(callback: CallbackQuery):
    """Обработчик кнопки финансовой статистики"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        db_conn = await db.connect()
        
        # Получаем общую сумму платежей
        async with db_conn.execute(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'succeeded'"
        ) as cursor:
            result = await cursor.fetchone()
            total_amount = result['total'] if result and result['total'] else 0
        
        # Получаем сумму платежей за последние 24 часа
        async with db_conn.execute(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'succeeded' AND created_at >= datetime('now', '-1 day')"
        ) as cursor:
            result = await cursor.fetchone()
            amount_24h = result['total'] if result and result['total'] else 0
        
        # Получаем сумму платежей за последние 7 дней
        async with db_conn.execute(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'succeeded' AND created_at >= datetime('now', '-7 day')"
        ) as cursor:
            result = await cursor.fetchone()
            amount_7d = result['total'] if result and result['total'] else 0
        
        # Получаем сумму платежей за последние 30 дней
        async with db_conn.execute(
            "SELECT SUM(amount) as total FROM payments WHERE status = 'succeeded' AND created_at >= datetime('now', '-30 day')"
        ) as cursor:
            result = await cursor.fetchone()
            amount_30d = result['total'] if result and result['total'] else 0
        
        stats_text = "💰 <b>Финансовая статистика</b>\n\n"
        stats_text += f"💵 Общая сумма платежей: {total_amount} руб.\n"
        stats_text += f"📅 За последние 24 часа: {amount_24h} руб.\n"
        stats_text += f"📆 За последние 7 дней: {amount_7d} руб.\n"
        stats_text += f"🗓 За последние 30 дней: {amount_30d} руб.\n"
        
        # Добавляем кнопку "Назад"
        keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats")]]
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении финансовой статистики: {str(e)}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при получении статистики: {str(e)}",
            reply_markup=get_stats_keyboard()
        )

@router.callback_query(F.data == "admin_user_stats")
async def admin_user_stats(callback: CallbackQuery):
    """Обработчик кнопки статистики пользователей"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для доступа к этому разделу.")
        return
    
    try:
        db_conn = await db.connect()
        
        # Получаем количество пользователей по дням за последнюю неделю
        async with db_conn.execute(
            "SELECT date(created_at) as date, COUNT(*) as count FROM users "
            "WHERE created_at >= datetime('now', '-7 day') "
            "GROUP BY date(created_at) ORDER BY date"
        ) as cursor:
            users_by_day = await cursor.fetchall()
        
        # Получаем количество подписок по тарифным планам
        stats_text = "👥 <b>Статистика пользователей</b>\n\n"
        
        if users_by_day:
            stats_text += "<b>Новые пользователи по дням:</b>\n"
            for day in users_by_day:
                stats_text += f"{day['date']}: {day['count']} пользователей\n"
        else:
            stats_text += "Нет данных о новых пользователях за последнюю неделю.\n"
        
        # Добавляем кнопку "Назад"
        keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats")]]
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователей: {str(e)}")
        await callback.message.edit_text(
            f"❌ Произошла ошибка при получении статистики: {str(e)}",
            reply_markup=get_stats_keyboard()
        )

# Общие обработчики
@router.callback_query(F.data == "admin_cancel_action")
async def admin_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены действия"""
    await callback.answer("Действие отменено")
    
    # Возвращаемся в меню управления подписками
    await callback.message.edit_text(
        "🔑 <b>Управление подписками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_subscription_management_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.subscription_management)

@router.callback_query(F.data == "admin_back_to_subscriptions")
async def admin_back_to_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата в меню управления подписками"""
    await callback.answer()
    
    await callback.message.edit_text(
        "🔑 <b>Управление подписками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_subscription_management_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.subscription_management)