from aiogram import Router, F, types
from aiogram.filters import Command
from utils.sql import DateBase
from utils.ftl import GetFluentLocalization
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
db = DateBase()
text = GetFluentLocalization('ru')

@router.message(Command("help"))
async def help_command(message: types.Message):
        
    user = await db.get_user('users', message.from_user.id)
    if user == 'unregister':
        await db.cmd(f"INSERT INTO users (UserID, last_card_time) VALUES ({message.from_user.id}, NULL)")
        
    help_text = (
        "🌟 <b>Доступные команды</b> 🌟\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🎮 <b>Основные команды:</b>\n"
        "🥕 /get_cards - Получить новую карту\n" 
        "🥬 /my_cards - Посмотреть свою коллекцию\n"
        "💰 /bal - Проверить баланс монет\n"
        "🏪 /market - Открыть рынок карт\n"
        "📖 /rules - Открыть правила\n"
        "🐛 /sendbug - Отправить баг\n"
        "📚 /albums - Проверить альбомы\n\n"
        "🎁 <b>Промокоды:</b>\n"
        "🔑 /promo [код] - Активировать промокод\n\n"
        "❓ Используйте эти команды для взаимодействия с ботом!\n"
        "━━━━━━━━━━━━━━━"
    )
    
    await message.reply(help_text)
