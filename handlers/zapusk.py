from aiogram import Router, F, types
from aiogram.filters import Command
from utils.sql import DateBase
from utils.ftl import GetFluentLocalization
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
db = DateBase()
text = GetFluentLocalization('ru')

@router.message(Command("zapusk"))
async def zapusk_cmd(message: types.Message):
    if message.from_user.id != 840183653:
        return
        
    user = await db.get_user('users', message.from_user.id)
    if user == 'unregister':
        await db.cmd(f"INSERT INTO users (UserID, last_card_time) VALUES ({message.from_user.id}, NULL)")

    help_text = (
        "🌟 *Добро пожаловать в мир коллекционирования!* 🌟\n\n"
        "Я — ваш персональный бот-помощник в увлекательном мире коллекционных карточек! \n\n"
        "*Что вас ждёт:*\n"
        "• 🎴 Уникальные коллекции карточек разной редкости\n"
        "• 💱 Динамичный рынок: покупайте, продавайте и обменивайтесь\n"
        "• 🎉 Эксклюзивные события и акции с особыми наградами\n"
        "• 🎁 Специальные предложения для коллекционеров\n\n"
        "*Подарок для новичков:*\n"
        "Используйте промокод `open` и получите 1000 монет на старт! 🎊\n\n"
        "Готовы начать своё коллекционное путешествие? Нажмите кнопку ниже! ⬇️"
    )
    
    await message.reply(help_text)
