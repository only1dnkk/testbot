import sys, os
sys.dont_write_bytecode = True
try:
    os.system('cls')
except:
    os.system('clear')
try:
    import asyncio
    import logging
    from aiogram import Bot, Dispatcher, DefaultBotProperties
    from utils.ftl import GetFluentLocalization
    from utils import config
    from utils.sql import DateBase
    from aiogram.exceptions import TelegramNetworkError
    import time
except:
    os.system(f"pip install -r utils/requirements.txt")

async def main():
    from app import router
    from handlers.cards import router as cards_router
    from handlers.promo import router as promo_router
    from handlers.market import router as market_router
    from handlers.sendbug import router as sendbug_router
    from handlers.jobs import router as jobs_router
    from handlers.rating import router as rating_router
    
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode='html', link_preview_is_disabled=True))
            dp = Dispatcher()
            db = DateBase()
            await db.table()
            text = GetFluentLocalization('ru')
            dp.include_routers(
                market_router, router, cards_router, promo_router, sendbug_router, jobs_router, rating_router)
            
            # Пробуем удалить вебхук с повторными попытками
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except TelegramNetworkError as e:
                logging.error(f"Ошибка при удалении вебхука: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise
                
            await dp.start_polling(bot, text=text, db=db)
            break
            
        except TelegramNetworkError as e:
            logging.error(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logging.error("Достигнуто максимальное количество попыток. Выход.")
                raise
        finally:
            if 'bot' in locals():
                await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
