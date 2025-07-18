import logging
import asyncio
from datetime import datetime, timedelta
from utils import safe_edit_message

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, SUBSCRIPTION_PRICE, ADMIN_IDS, SUBSCRIPTION_PLANS
from database import Database
from xray_api import XrayAPI
from payment import YooKassaPayment
from admin_panel import router as admin_router

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Инициализация базы данных и API Xray
db = Database()
xray = XrayAPI()

# Состояния для FSM
class UserStates(StatesGroup):
    start = State()
    payment = State()
    confirm = State()
    admin_give_subscription = State()
    admin_select_plan = State()

# Словарь с планами подписок импортирован из config.py

# Клавиатуры
def get_main_keyboard(has_subscription=False):
    """Получение основной клавиатуры"""
    if has_subscription:
        keyboard = [
            [InlineKeyboardButton(text="Продлить подписку", callback_data="extend")],
            [InlineKeyboardButton(text="Мой VPN ключ", callback_data="show_key")],
            [InlineKeyboardButton(text="Инструкция по настройке", callback_data="instructions")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="Выбрать тариф", callback_data="select_plan")],
            [InlineKeyboardButton(text="Инструкция по настройке", callback_data="instructions")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_plans_keyboard():
    """Получение клавиатуры с тарифными планами"""
    keyboard = []
    
    logger.info(f"get_plans_keyboard: Доступные планы: {list(SUBSCRIPTION_PLANS.keys())}")
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        logger.info(f"get_plans_keyboard: Добавляю кнопку для плана {plan_id}: {plan['name']}")
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']} руб.", 
                callback_data=f"buy_{plan_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(payment_url):
    """Получение клавиатуры для оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="Я оплатил", callback_data="check_payment")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_plans_keyboard(user_id):
    """Получение клавиатуры с тарифными планами для админа"""
    keyboard = []
    
    for plan_id, plan in SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price']} руб.", 
                callback_data=f"admin_give_{plan_id}_{user_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = message.from_user
    logger.info(f"Пользователь {user.id} запустил бота")
    
    # Создаем пользователя в базе данных
    await db.create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Проверяем, есть ли у пользователя активная подписка
    subscription = await db.get_user_subscription(user.id)
    
    if subscription and subscription['active']:
        # Если есть активная подписка, показываем информацию о ней
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await message.answer(
            f"Привет, {user.first_name}! У вас есть активная подписка.\n"
            f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left}",
            reply_markup=get_main_keyboard(has_subscription=True)
        )
    else:
        # Если нет активной подписки, предлагаем купить
        await message.answer(
            f"Привет, {user.first_name}! Добро пожаловать в AirCloud VPN.\n"
            f"Здесь вы можете приобрести доступ к быстрому и безопасному VPN.",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
    
    await state.set_state(UserStates.start)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/status - Проверить статус подписки\n"
        "/support - Связаться с поддержкой"
    )
    
    # Добавляем команды для администраторов
    if message.from_user.id in ADMIN_IDS:
        help_text += (
            "\n\nКоманды администратора:\n"
            "/admin - Открыть административную панель\n"
            "/give_subscription <user_id> - Выдать подписку пользователю\n"
            "/users - Список пользователей\n"
            "/stats - Статистика бота"
        )
    
    await message.answer(help_text)

@router.message(Command("status"))
async def cmd_status(message: Message):
    """Обработчик команды /status"""
    user_id = message.from_user.id
    subscription = await db.get_user_subscription(user_id)
    
    if subscription and subscription['active']:
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await message.answer(
            f"Статус вашей подписки: Активна\n"
            f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left}"
        )
    else:
        await message.answer(
            "У вас нет активной подписки. Используйте /start для покупки."
        )

@router.message(Command("support"))
async def cmd_support(message: Message):
    """Обработчик команды /support"""
    await message.answer(
        "Для связи с поддержкой напишите на email: support@aircloud-vpn.com\n"
        "Или в Telegram: @aircloud_support"
    )

# Административные команды
@router.message(Command("give_subscription"))
async def cmd_give_subscription(message: Message, command: CommandObject, state: FSMContext):
    """Обработчик команды /give_subscription для администраторов"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return
    
    # Проверяем, указан ли ID пользователя
    if not command.args:
        await message.answer(
            "Пожалуйста, укажите ID пользователя.\n"
            "Пример: /give_subscription 123456789"
        )
        return
    
    try:
        user_id = int(command.args)
        
        # Проверяем, существует ли пользователь
        user = await db.get_user(user_id)
        if not user:
            await message.answer(f"Пользователь с ID {user_id} не найден.")
            return
        
        # Сохраняем ID пользователя в состоянии
        await state.update_data(target_user_id=user_id)
        
        # Показываем клавиатуру с выбором тарифного плана
        await message.answer(
            f"Выберите тарифный план для пользователя {user_id}:",
            reply_markup=get_admin_plans_keyboard(user_id)
        )
        
        await state.set_state(UserStates.admin_select_plan)
    
    except ValueError:
        await message.answer("ID пользователя должен быть числом.")

@router.message(Command("users"))
async def cmd_users(message: Message):
    """Обработчик команды /users для администраторов"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return
    
    # Здесь должна быть реализация получения списка пользователей из базы данных
    # Для примера просто отправляем заглушку
    await message.answer(
        "Функция получения списка пользователей находится в разработке."
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats для администраторов"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return
    
    # Здесь должна быть реализация получения статистики бота
    # Для примера просто отправляем заглушку
    await message.answer(
        "Функция получения статистики находится в разработке."
    )

# Обработчики кнопок
@router.callback_query(F.data == "select_plan")
async def select_plan(callback: CallbackQuery):
    """Обработчик кнопки выбора тарифного плана"""
    await callback.answer()
    
    # Отладочная информация
    logger.info(f"select_plan: Доступные планы: {list(SUBSCRIPTION_PLANS.keys())}")
    
    await safe_edit_message(
        callback.message,
        "Выберите тарифный план:",
        reply_markup=get_plans_keyboard()
    )

@router.callback_query(F.data.startswith("buy_"))
async def buy_plan(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки покупки тарифного плана"""
    await callback.answer()
    
    # Получаем ID тарифного плана из callback_data
    plan_id = callback.data.split("_")[1]
    
    # Отладочная информация
    logger.info(f"buy_plan: Выбран план {plan_id}")
    logger.info(f"buy_plan: Доступные планы: {list(SUBSCRIPTION_PLANS.keys())}")
    
    # Проверяем, существует ли такой тарифный план
    if plan_id not in SUBSCRIPTION_PLANS:
        logger.error(f"buy_plan: План {plan_id} не найден в SUBSCRIPTION_PLANS")
        await safe_edit_message(
            callback.message,
            "Выбран несуществующий тарифный план. Пожалуйста, попробуйте снова.",
            reply_markup=get_plans_keyboard()
        )
        return
    
    # Получаем информацию о тарифном плане
    plan = SUBSCRIPTION_PLANS[plan_id]
    user_id = callback.from_user.id
    price = plan["price"]
    days = plan["days"]
    
    logger.info(f"buy_plan: Выбран план {plan_id}: {plan['name']}, {price} руб., {days} дней")
    
    # Сохраняем информацию о плане в состоянии
    await state.update_data(plan_id=plan_id, days=days)
    
    # Временно пропускаем создание платежа для тестирования
    # Создаем фиктивный платеж для тестирования
    payment_data = {
        "payment_id": f"test_{user_id}_{plan_id}",
        "payment_url": "https://example.com/payment",
        "status": "pending"
    }
    
    # Сохраняем информацию о платеже в базу данных
    await db.create_payment(user_id, price, payment_data["payment_id"], payment_data["status"])
    
    # Сохраняем ID платежа в состоянии
    await state.update_data(payment_id=payment_data["payment_id"])
    
    await safe_edit_message(
        callback.message,
        f"Стоимость подписки на {plan['name']}: {price} руб.\n"
        f"Для оплаты перейдите по ссылке.",
        reply_markup=get_payment_keyboard(payment_data["payment_url"])
    )
    
    await state.set_state(UserStates.payment)

@router.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки проверки оплаты"""
    await callback.answer()
    
    # Получаем данные из состояния
    data = await state.get_data()
    payment_id = data.get("payment_id")
    plan_id = data.get("plan_id")
    days = data.get("days", 30)  # По умолчанию 30 дней
    
    logger.info(f"check_payment: payment_id={payment_id}, plan_id={plan_id}, days={days}")
    
    if not payment_id:
        await safe_edit_message(
            callback.message,
            "Информация о платеже не найдена. Пожалуйста, начните процесс покупки заново."
        )
        return
    
    # Для тестовых платежей сразу считаем оплату успешной
    if payment_id.startswith("test_"):
        payment_data = {"status": "succeeded"}
        await db.update_payment_status(payment_id, "succeeded")
    else:
        # Проверяем статус платежа
        payment_data = await YooKassaPayment.check_payment(payment_id)
    
    if payment_data and payment_data["status"] == "succeeded":
        # Обновляем статус платежа в базе данных
        if not payment_id.startswith("test_"):
            await db.update_payment_status(payment_id, "succeeded")
        
        user_id = callback.from_user.id
        
        # Для тестирования создаем фиктивный VPN ключ
        user_data = {"link": f"vless://test-key@example.com:443?security=tls&type=tcp&headerType=none#{user_id}"}
        
        if user_data and "link" in user_data:
            # Сохраняем информацию о подписке в базу данных
            expiry_date = datetime.now() + timedelta(days=days)
            await db.create_subscription(user_id, user_data["link"], expiry_date)
            
            keyboard = [
                [InlineKeyboardButton(text="Показать мой ключ", callback_data="show_key")],
                [InlineKeyboardButton(text="Инструкция по настройке", callback_data="instructions")]
            ]
            
            plan_name = SUBSCRIPTION_PLANS[plan_id]["name"] if plan_id in SUBSCRIPTION_PLANS else f"{days} дней"
            
            await safe_edit_message(
                callback.message,
                f"Оплата успешно проведена! Ваш VPN ключ создан на {plan_name}.\n"
                "Вы можете посмотреть его и инструкцию по настройке.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.set_state(UserStates.start)
        else:
            await safe_edit_message(
                callback.message,
                "Произошла ошибка при создании VPN ключа. Пожалуйста, обратитесь в поддержку."
            )
    elif payment_data and payment_data["status"] == "pending":
        await safe_edit_message(
            callback.message,
            "Ваш платеж еще обрабатывается. Пожалуйста, подождите немного и проверьте снова.",
            reply_markup=get_payment_keyboard(callback.message.reply_markup.inline_keyboard[0][0].url)
        )
    else:
        await safe_edit_message(
            callback.message,
            "Платеж не найден или был отменен. Пожалуйста, попробуйте снова.",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
        
        await state.set_state(UserStates.start)

@router.callback_query(F.data == "show_key")
async def show_key(callback: CallbackQuery):
    """Обработчик кнопки показа VPN ключа"""
    await callback.answer()
    
    user_id = callback.from_user.id
    subscription = await db.get_user_subscription(user_id)
    
    logger.info(f"show_key: user_id={user_id}, subscription={subscription}")
    
    if subscription and subscription['active']:
        keyboard = [
            [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
        ]
        
        await safe_edit_message(
            callback.message,
            f"Ваш VPN ключ:\n\n`{subscription['vpn_key']}`\n\n"
            f"Срок действия: до {subscription['expiry_date'].strftime('%d.%m.%Y')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await safe_edit_message(
            callback.message,
            "У вас нет активной подписки. Используйте /start для покупки."
        )

@router.callback_query(F.data == "instructions")
async def instructions(callback: CallbackQuery):
    """Обработчик кнопки инструкции по настройке"""
    await callback.answer()
    
    # Инструкция по настройке VPN
    instructions_text = (
        "Инструкция по настройке VPN:\n\n"
        "1. Скачайте приложение V2rayNG для Android или Shadowrocket для iOS\n"
        "2. Откройте приложение и нажмите на кнопку добавления конфигурации\n"
        "3. Выберите 'Импорт из буфера обмена' и вставьте ваш VPN ключ\n"
        "4. Сохраните конфигурацию и подключитесь к VPN\n\n"
        "Подробная инструкция с картинками: https://aircloud-vpn.com/instructions"
    )
    
    keyboard = [[InlineKeyboardButton(text="Назад", callback_data="back_to_main")]]
    
    await safe_edit_message(
        callback.message,
        instructions_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки возврата в главное меню"""
    await callback.answer()
    
    # Проверяем, есть ли у пользователя активная подписка
    user_id = callback.from_user.id
    subscription = await db.get_user_subscription(user_id)
    
    logger.info(f"back_to_main: user_id={user_id}, subscription={subscription}")
    
    if subscription and subscription['active']:
        # Если есть активная подписка, показываем информацию о ней
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await safe_edit_message(
            callback.message,
            f"У вас есть активная подписка.\n"
            f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left}",
            reply_markup=get_main_keyboard(has_subscription=True)
        )
    else:
        # Если нет активной подписки, предлагаем купить
        await safe_edit_message(
            callback.message,
            f"Добро пожаловать в AirCloud VPN.\n"
            f"Здесь вы можете приобрести доступ к быстрому и безопасному VPN.",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
    
    await state.set_state(UserStates.start)

@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены"""
    await callback.answer()
    
    await safe_edit_message(
        callback.message,
        "Операция отменена. Используйте /start для возврата в главное меню."
    )
    
    await state.clear()

@router.callback_query(F.data == "extend")
async def extend(callback: CallbackQuery):
    """Обработчик кнопки продления подписки"""
    await callback.answer()
    
    await safe_edit_message(
        callback.message,
        "Выберите тарифный план для продления:",
        reply_markup=get_plans_keyboard()
    )

@router.callback_query(F.data.startswith("admin_give_"))
async def admin_give_subscription(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки выдачи подписки администратором"""
    await callback.answer()
    
    # Проверяем, является ли пользователь администратором
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.edit_text("У вас нет прав для выполнения этой операции.")
        return
    
    # Получаем данные из callback_data
    parts = callback.data.split("_")
    if len(parts) < 4:
        await callback.message.edit_text("Неверный формат данных.")
        return
    
    plan_id = parts[2]
    try:
        user_id = int(parts[3])
    except ValueError:
        await callback.message.edit_text("Неверный ID пользователя.")
        return
    
    # Проверяем, существует ли такой тарифный план
    if plan_id not in SUBSCRIPTION_PLANS:
        await callback.message.edit_text("Выбран несуществующий тарифный план.")
        return
    
    # Получаем информацию о тарифном плане
    plan = SUBSCRIPTION_PLANS[plan_id]
    days = plan["days"]
    
    # Создаем VPN ключ через Xray API
    user_data = await xray.create_user(email=f"tg_{user_id}")
    
    if user_data and "link" in user_data:
        # Сохраняем информацию о подписке в базу данных
        expiry_date = datetime.now() + timedelta(days=days)
        await db.create_subscription(user_id, user_data["link"], expiry_date)
        
        # Отправляем уведомление пользователю
        try:
            await bot.send_message(
                user_id,
                f"Вам выдана подписка на {plan['name']}!\n"
                f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
                "Используйте команду /start для просмотра ключа и инструкции по настройке."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")
        
        await callback.message.edit_text(
            f"Подписка на {plan['name']} успешно выдана пользователю {user_id}.\n"
            f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}"
        )
    else:
        await callback.message.edit_text(
            f"Произошла ошибка при создании VPN ключа для пользователя {user_id}."
        )

# Обработчик для вебхуков от ЮKassa
async def yookassa_webhook_handler(request):
    """Обработчик вебхуков от ЮKassa"""
    try:
        # Получаем данные запроса
        request_body = await request.json()
        
        # Обрабатываем уведомление
        notification = YooKassaPayment.process_webhook(request_body)
        
        if notification and notification["status"] == "succeeded":
            # Получаем ID пользователя из метаданных платежа
            user_id = int(notification["metadata"].get("user_id"))
            
            # Обновляем статус платежа в базе данных
            await db.update_payment_status(notification["payment_id"], "succeeded")
            
            # Проверяем, есть ли у пользователя активная подписка
            subscription = await db.get_user_subscription(user_id)
            
            if subscription:
                # Если есть активная подписка, продлеваем ее
                # Получаем количество дней из метаданных платежа или используем 30 дней по умолчанию
                days = int(notification["metadata"].get("days", 30))
                new_expiry = subscription['expiry_date'] + timedelta(days=days)
                await db.extend_subscription(user_id, new_expiry)
                
                # Отправляем уведомление пользователю
                await bot.send_message(
                    user_id,
                    f"Ваша подписка успешно продлена до {new_expiry.strftime('%d.%m.%Y')}!"
                )
            else:
                # Если нет активной подписки, создаем новую
                # Получаем количество дней из метаданных платежа или используем 30 дней по умолчанию
                days = int(notification["metadata"].get("days", 30))
                user_data = await xray.create_user(email=f"tg_{user_id}")
                
                if user_data and "link" in user_data:
                    # Сохраняем информацию о подписке в базу данных
                    expiry_date = datetime.now() + timedelta(days=days)
                    await db.create_subscription(user_id, user_data["link"], expiry_date)
                    
                    # Отправляем уведомление пользователю
                    await bot.send_message(
                        user_id,
                        "Оплата успешно проведена! Ваш VPN ключ создан.\n"
                        "Используйте команду /start для просмотра ключа и инструкции по настройке."
                    )
        
        return web.Response(status=200, text="OK")
    
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука от ЮKassa: {str(e)}")
        return web.Response(status=500, text="Error")

# Регистрация роутеров
dp.include_router(router)
dp.include_router(admin_router)

# Запуск бота
async def main():
    # Инициализация базы данных
    await db.init_db()
    
    # Запуск бота в режиме long polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

# Запуск бота в режиме webhook
async def main_webhook():
    # Инициализация базы данных
    await db.init_db()
    
    # Создаем приложение aiohttp
    app = web.Application()
    
    # Настраиваем вебхук для бота
    webhook_path = f"/webhook/{BOT_TOKEN}"
    await bot.set_webhook(url=f"https://your-domain.com{webhook_path}")
    
    # Настраиваем обработчики запросов
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path=webhook_path)
    
    # Добавляем обработчик вебхуков от ЮKassa
    app.router.add_post("/yookassa-webhook", yookassa_webhook_handler)
    
    # Запускаем приложение
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()
    
    # Ждем завершения
    try:
        await asyncio.Future()
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        # Используйте main() для long polling или main_webhook() для webhook
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
    finally:
        # Закрываем соединения
        asyncio.run(db.close())