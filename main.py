import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import cart, catalog, orders, start, support, admin
from bot.middlewares.session import DbSessionMiddleware
from config import settings
from db.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # База данных
    engine = create_async_engine(settings.db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # FSM хранилище в Redis
    # Не забыть поменять, после тестирования
    # storage = RedisStorage.from_url(settings.REDIS_URL)
    storage = MemoryStorage()
    # Бот и диспетчер
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Middleware (сессия БД для каждого апдейта)
    dp.update.middleware(DbSessionMiddleware(session_factory))

    # Регистрация роутеров (порядок важен: admin проверяет фильтр)
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(orders.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)

    logger.info("Бот запускается...")

    if settings.WEBHOOK_HOST:
        # Продакшн: webhook
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        from aiohttp import web

        await bot.set_webhook(settings.webhook_url)
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        web.run_app(app, host=settings.WEBAPP_HOST, port=settings.WEBAPP_PORT)
    else:
        # Разработка: polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
