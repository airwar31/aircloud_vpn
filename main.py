import logging
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, SUBSCRIPTION_PRICE, ADMIN_IDS
from database import Database
from xray_api import XrayAPI
from payment import YooKassaPayment

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
            [InlineKeyboardButton(text="Купить VPN на 1 месяц", callback_data="buy_month")],
            [InlineKeyboardButton(text="Инструкция по настройке", callback_data="instructions")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_keyboard(payment_url):
    """Получение клавиатуры для оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="Оплатить", url=payment_url)],
        [InlineKeyboardButton(text="Я оплатил", callback_data="check_payment")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
    ]
    
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

# Обработчики кнопок
@router.callback_query(F.data == "buy_month")
async def buy_month(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки покупки подписки на месяц"""
    await callback.answer()
    
    user_id = callback.from_user.id
    price = SUBSCRIPTION_PRICE["1_month"]
    
    # Создаем платеж через ЮKassa
    payment_data = await YooKassaPayment.create_payment(
        amount=price,
        description=f"air cloud на 1 месяц для пользователя {user_id}",
        user_id=user_id
    )
    
    if payment_data:
        # Сохраняем информацию о платеже в базу данных
        await db.create_payment(user_id, price, payment_data["payment_id"], payment_data["status"])
        
        # Сохраняем ID платежа в состоянии
        await state.update_data(payment_id=payment_data["payment_id"])
        
        await callback.message.edit_text(
            f"Стоимость подписки на 1 месяц: {price} руб.\n"
            f"Для оплаты перейдите по ссылке.",
            reply_markup=get_payment_keyboard(payment_data["payment_url"])
        )
        
        await state.set_state(UserStates.payment)
    else:
        await callback.message.edit_text(
            "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )

@router.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки проверки оплаты"""
    await callback.answer()
    
    # Получаем ID платежа из состояния
    data = await state.get_data()
    payment_id = data.get("payment_id")
    
    if not payment_id:
        await callback.message.edit_text(
            "Информация о платеже не найдена. Пожалуйста, начните процесс покупки заново."
        )
        return
    
    # Проверяем статус платежа
    payment_data = await YooKassaPayment.check_payment(payment_id)
    
    if payment_data and payment_data["status"] == "succeeded":
        # Обновляем статус платежа в базе данных
        await db.update_payment_status(payment_id, "succeeded")
        
        user_id = callback.from_user.id
        
        # Создаем VPN ключ через Xray API
        user_data = await xray.create_user(email=f"tg_{user_id}")
        
        if user_data and "link" in user_data:
            # Сохраняем информацию о подписке в базу данных
            expiry_date = datetime.now() + timedelta(days=30)
            await db.create_subscription(user_id, user_data["link"], expiry_date)
            
            keyboard = [
                [InlineKeyboardButton(text="Показать мой ключ", callback_data="show_key")],
                [InlineKeyboardButton(text="Инструкция по настройке", callback_data="instructions")]
            ]
            
            await callback.message.edit_text(
                "Оплата успешно проведена! Ваш VPN ключ создан.\n"
                "Вы можете посмотреть его и инструкцию по настройке.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
            await state.set_state(UserStates.start)
        else:
            await callback.message.edit_text(
                "Произошла ошибка при создании VPN ключа. Пожалуйста, обратитесь в поддержку."
            )
    elif payment_data and payment_data["status"] == "pending":
        await callback.message.edit_text(
            "Ваш платеж еще обрабатывается. Пожалуйста, подождите немного и проверьте снова.",
            reply_markup=get_payment_keyboard(callback.message.reply_markup.inline_keyboard[0][0].url)
        )
    else:
        await callback.message.edit_text(
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
    
    if subscription and subscription['active']:
        keyboard = [
            [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
        ]
        
        await callback.message.edit_text(
            f"Ваш VPN ключ:\n\n`{subscription['vpn_key']}`\n\n"
            f"Срок действия: до {subscription['expiry_date'].strftime('%d.%m.%Y')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback.message.edit_text(
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
    
    await callback.message.edit_text(
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
    
    if subscription and subscription['active']:
        # Если есть активная подписка, показываем информацию о ней
        expiry_date = subscription['expiry_date']
        days_left = (expiry_date - datetime.now()).days
        
        await callback.message.edit_text(
            f"У вас есть активная подписка.\n"
            f"Срок действия: до {expiry_date.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left}",
            reply_markup=get_main_keyboard(has_subscription=True)
        )
    else:
        # Если нет активной подписки, предлагаем купить
        await callback.message.edit_text(
            f"Добро пожаловать в AirCloud VPN.\n"
            f"Здесь вы можете приобрести доступ к быстрому и безопасному VPN.",
            reply_markup=get_main_keyboard(has_subscription=False)
        )
    
    await state.set_state(UserStates.start)

@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены"""
    await callback.answer()
    
    await callback.message.edit_text(
        "Операция отменена. Используйте /start для возврата в главное меню."
    )
    
    await state.clear()

@router.callback_query(F.data == "extend")
async def extend(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки продления подписки"""
    await callback.answer()
    
    user_id = callback.from_user.id
    price = SUBSCRIPTION_PRICE["1_month"]
    
    # Создаем платеж через ЮKassa
    payment_data = await YooKassaPayment.create_payment(
        amount=price,
        description=f"Продление подписки VPN на 1 месяц для пользователя {user_id}",
        user_id=user_id
    )
    
    if payment_data:
        # Сохраняем информацию о платеже в базу данных
        await db.create_payment(user_id, price, payment_data["payment_id"], payment_data["status"])
        
        # Сохраняем ID платежа в состоянии
        await state.update_data(payment_id=payment_data["payment_id"])
        
        await callback.message.edit_text(
            f"Стоимость продления подписки на 1 месяц: {price} руб.\n"
            f"Для оплаты перейдите по ссылке.",
            reply_markup=get_payment_keyboard(payment_data["payment_url"])
        )
        
        await state.set_state(UserStates.payment)
    else:
        await callback.message.edit_text(
            "Произошла ошибка при создании платежа. Пожалуйста, попробуйте позже или обратитесь в поддержку."
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
                new_expiry = subscription['expiry_date'] + timedelta(days=30)
                await db.extend_subscription(user_id, new_expiry)
                
                # Отправляем уведомление пользователю
                await bot.send_message(
                    user_id,
                    f"Ваша подписка успешно продлена до {new_expiry.strftime('%d.%m.%Y')}!"
                )
            else:
                # Если нет активной подписки, создаем новую
                user_data = await xray.create_user(email=f"tg_{user_id}")
                
                if user_data and "link" in user_data:
                    # Сохраняем информацию о подписке в базу данных
                    expiry_date = datetime.now() + timedelta(days=30)
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

# Регистрация роутера
dp.include_router(router)

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