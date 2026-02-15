"""
ПОЛНЫЙ ПРИМЕР ИНТЕГРАЦИИ ПЛАТЕЖНОЙ СИСТЕМЫ В MAIN.PY

Этот файл показывает, как интегрировать все платежные модули в основной bot.py

Замечание: Это ПРИМЕР! Адаптируйте под ваш существующий код!
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime

# Импорты aiogram
from aiogram import Dispatcher, Router, Bot, F
from aiogram.types import BotCommand, Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# Импорты приложения
from bot_app.config import BotConfig, PaymentConfig, ServerConfig
from bot_app.database import Database
from bot_app.xray_api import XrayAPI

# Импорты платежной системы
from bot_app.yookassa_payment import YooKassaAPI
from bot_app.payment_handler import PaymentHandler, init_payment_handler
from bot_app.bot_payment import payment_router, PaymentStates
from bot_app.crypto_payment import CryptoPaymentProcessor, BlockchainMonitor, crypto_router
from bot_app.webhook_handler import YooKassaWebhookHandler, init_webhook_handler

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VPNBotApplication:
    """Главное приложение VPN бота с платежной системой"""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.db: Optional[Database] = None
        self.payment_handler: Optional[PaymentHandler] = None
        self.crypto_processor: Optional[CryptoPaymentProcessor] = None
        self.blockchain_monitor: Optional[BlockchainMonitor] = None
        self.webhook_app: Optional[web.Application] = None
        self.webhook_server: Optional[web.AppRunner] = None
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def init(self):
        """Инициализировать все компоненты приложения"""
        try:
            logger.info("Initializing VPN Bot Application...")
            
            # 1. Инициализируем БД
            self.db = Database("bot.db")
            await self.db.init()
            logger.info("Database initialized")
            
            # 2. Инициализируем бот
            self.bot = Bot(
                token=BotConfig.TOKEN,
                parse_mode="HTML"
            )
            logger.info(f"Bot initialized: {BotConfig.TOKEN[:20]}...")
            
            # 3. Инициализируем диспетчер
            storage = MemoryStorage()
            self.dp = Dispatcher(storage=storage)
            logger.info("Dispatcher initialized")
            
            # 4. Инициализируем платежную систему
            await self._init_payment_system()
            logger.info("Payment system initialized")
            
            # 5. Регистрируем роутеры
            self._register_routers()
            logger.info("Routers registered")
            
            # 6. Инициализируем вебхук обработчик
            init_webhook_handler(
                payment_h=self.payment_handler,
                database=self.db,
                bot_instance=self.bot
            )
            logger.info("Webhook handler initialized")
            
            # 7. Устанавливаем команды бота
            await self._setup_bot_commands()
            logger.info("Bot commands configured")
            
            logger.info("✅ All components initialized successfully!")
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize application: {e}", exc_info=True)
            raise
    
    async def _init_payment_system(self):
        """Инициализировать платежную систему"""
        try:
            # Инициализируем YooKassa
            await init_payment_handler(
                bot_instance=self.bot,
                yookassa_shop_id=os.getenv("YOOKASSA_SHOP_ID"),
                yookassa_secret_key=os.getenv("YOOKASSA_SECRET_KEY"),
                database=self.db
            )
            
            # Получаем глобальный экземпляр payment_handler
            from bot_app.bot_payment import payment_handler as global_payment_handler
            self.payment_handler = global_payment_handler
            
            logger.info("YooKassa initialized")
            
            # Инициализируем крипто-процессор
            self.crypto_processor = CryptoPaymentProcessor(database=self.db)
            logger.info("Crypto processor initialized")
            
            # Инициализируем монитор блокчейна (опционально)
            if os.getenv("ENABLE_BLOCKCHAIN_MONITOR", "false").lower() == "true":
                self.blockchain_monitor = BlockchainMonitor(self.crypto_processor, self.bot)
                logger.info("Blockchain monitor enabled")
            else:
                logger.info("Blockchain monitor disabled (set ENABLE_BLOCKCHAIN_MONITOR=true to enable)")
        
        except Exception as e:
            logger.error(f"Failed to initialize payment system: {e}")
            raise
    
    def _register_routers(self):
        """Зарегистрировать все роутеры"""
        # Регистрируем платежные роутеры
        self.dp.include_routers(
            payment_router,   # Основные платежные команды
            crypto_router     # Крипто платежи
        )
        
        logger.info("Payment routers registered")
    
    async def _setup_bot_commands(self):
        """Установить команды бота"""
        commands = [
            BotCommand(command="start", description="🚀 Начало работы"),
            BotCommand(command="pay", description="💳 Оплаты и подписки"),
            BotCommand(command="my_keys", description="🔑 Мои VPN ключи"),
            BotCommand(command="profile", description="👤 Мой профиль"),
            BotCommand(command="help", description="❓ Справка"),
            BotCommand(command="support", description="🆘 Поддержка"),
        ]
        
        await self.bot.set_my_commands(commands)
    
    async def start_webhook_server(self, port: int = 8080):
        """Запустить вебхук сервер для YooKassa"""
        try:
            # Создаем веб приложение
            self.webhook_app = web.Application()
            self.webhook_app.router.add_post(
                "/yookassa-webhook",
                YooKassaWebhookHandler.handle_webhook
            )
            self.webhook_app.router.add_get("/health", self._health_check)
            
            # Запускаем сервер
            self.webhook_server = web.AppRunner(self.webhook_app)
            await self.webhook_server.setup()
            
            site = web.TCPSite(self.webhook_server, "0.0.0.0", port)
            await site.start()
            
            logger.info(f"✅ Webhook server started on port {port}")
        
        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}")
            raise
    
    async def start_blockchain_monitor(self):
        """Запустить монитор блокчейна"""
        if not self.blockchain_monitor:
            logger.warning("Blockchain monitor not initialized")
            return
        
        try:
            self.monitor_task = asyncio.create_task(
                self.blockchain_monitor.start_monitoring()
            )
            logger.info("✅ Blockchain monitor started")
        
        except Exception as e:
            logger.error(f"Failed to start blockchain monitor: {e}")
    
    async def run(self, start_webhook: bool = True, start_monitor: bool = False):
        """
        Запустить приложение
        
        Args:
            start_webhook: Запустить вебхук сервер (для YooKassa)
            start_monitor: Запустить монитор блокчейна
        """
        tasks = []
        
        try:
            # Инициализируем приложение
            await self.init()
            
            # Запускаем вебхук сервер если нужен
            if start_webhook:
                await self.start_webhook_server(port=int(os.getenv("WEBHOOK_PORT", 8080)))
            
            # Запускаем монитор блокчейна если нужен
            if start_monitor:
                await self.start_blockchain_monitor()
            
            logger.info("🚀 Starting bot polling...")
            
            # Основной цикл бота
            await self.dp.start_polling(self.bot)
        
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}", exc_info=True)
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Очистить ресурсы"""
        try:
            logger.info("Cleaning up resources...")
            
            # Останавливаем монитор блокчейна
            if self.blockchain_monitor:
                await self.blockchain_monitor.stop_monitoring()
            
            # Отменяем задачу монитора если она есть
            if self.monitor_task:
                self.monitor_task.cancel()
            
            # Закрываем вебхук сервер
            if self.webhook_server:
                await self.webhook_server.cleanup()
            
            # Закрываем платежный обработчик
            if self.payment_handler:
                await self.payment_handler.cleanup()
            
            # Закрываем сессию бота
            if self.bot:
                await self.bot.session.close()
            
            # Закрываем БД
            if self.db:
                await self.db.close()
            
            logger.info("✅ Cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    @staticmethod
    async def _health_check(request: web.Request) -> web.Response:
        """Проверка здоровья вебхука"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "aircloud-vpn-bot"
        })


# Главная функция

async def main():
    """Главная функция"""
    app = VPNBotApplication()
    
    # Определяем, нужно ли запускать вебхук сервер
    # Установите WEBHOOK_ENABLED=true в .env для включения
    start_webhook = os.getenv("WEBHOOK_ENABLED", "true").lower() == "true"
    start_monitor = os.getenv("ENABLE_BLOCKCHAIN_MONITOR", "false").lower() == "true"
    
    await app.run(start_webhook=start_webhook, start_monitor=start_monitor)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


# КОНФИГУРАЦИЯ .env
"""
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database
DATABASE_PATH=./bot.db

# YooKassa Payment
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_API_TIMEOUT=30
YOOKASSA_RETRIES=3

# Webhook Server
WEBHOOK_ENABLED=true
WEBHOOK_PORT=8080
WEBHOOK_HOST=https://your-domain.com

# Blockchain Monitor (optional)
ENABLE_BLOCKCHAIN_MONITOR=false
ETHERSCAN_API_KEY=optional
BSCSCAN_API_KEY=optional
TONAPI_API_KEY=optional

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/bot.log

# Server Configuration
NL_SERVER_IP=85.239.56.174
NL_SERVER_PORT=8443
NL_SERVER_USERNAME=admin
NL_SERVER_PASSWORD=your_password

VK_SERVER_IP=89.208.86.167
VK_SERVER_PORT=443
VK_SERVER_USERNAME=admin
VK_SERVER_PASSWORD=your_password
"""


# ЗАПУСК И ОТЛАДКА
"""
# Запустить обычный режим (с polling)
python run_bot.py

# Запустить с включенным вебхуком и мониторингом
WEBHOOK_ENABLED=true ENABLE_BLOCKCHAIN_MONITOR=true python run_bot.py

# Если используется Docker Compose
docker-compose -f docker-compose.yml up -d bot

# Просмотр логов
docker logs -f bot_container_name

# Или локально
tail -f logs/bot.log | grep "Payment"
"""
