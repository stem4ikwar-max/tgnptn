"""
Точка входа бота rufivo.

Запуск:
    python bot.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import database as db
from config import config
from handlers import admin, user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await db.init_db()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.include_router(admin.router)
    dp.include_router(user.router)

    # Сбрасываем зависшие апдейты и любой ранее выставленный webhook,
    # чтобы long polling стартовал чисто и без дублей сообщений.
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот rufivo запущен и слушает обновления…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
