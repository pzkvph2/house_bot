import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from database.db import init_db
from handlers.user import router as user_router
from handlers.admin import router as admin_router

async def health_check(request: web.Request) -> web.Response:
    """Эндпоинт для проверки здоровья сервера и предотвращения засыпания на Render"""
    return web.Response(text="OK: EdTech Arbitrage Bot is alive", status=200)

async def start_web_server() -> web.AppRunner:
    """Запуск легковесного HTTP-сервера для облачных хостингов (Render / Koyeb)"""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.PORT)
    await site.start()
    return runner

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting EdTech Arbitrage Bot (GEO KZ)...")

    # Инициализация базы данных (создание таблиц в Supabase / SQLite)
    await init_db()
    logger.info("Database initialized successfully.")

    # Запуск фонового веб-сервера для Render
    runner = await start_web_server()
    logger.info(f"Health-check web server started on port {settings.PORT}")

    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Регистрация роутеров
    dp.include_router(admin_router)
    dp.include_router(user_router)

    # Пропуск накопившихся апдейтов и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
