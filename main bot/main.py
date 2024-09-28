import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from config_data.config import Config, load_config
from aiogram.client.default import DefaultBotProperties
# from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.storage.memory import MemoryStorage
from keyboards.set_menu import set_main_menu
from handlers import user_handlers, admin_handlers
from database import db_users

logger = logging.getLogger(__name__)


async def main():
    await db_users.connect()
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')
    logger.info('Starting bot')
    config: Config = load_config()
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    await set_main_menu(bot)
    dp.include_router(admin_handlers.admin_router)
    dp.include_router(user_handlers.router)


    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    await db_users.disconnect()

asyncio.run(main())


