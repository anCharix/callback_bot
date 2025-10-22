import asyncio
import os
from dotenv import load_dotenv
from bot import router

from database.session import engine, Base

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("БД запущена...")
    await on_startup()

    print("Бот запущен...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())