from aiogram import Router, F, types
from aiogram.filters import Command
from utils.sql import DateBase
from utils.ftl import GetFluentLocalization
from utils import config

router = Router()
db = DateBase()
text = GetFluentLocalization('ru')

@router.message(Command("rules"))
async def rules_command(message: types.Message):
        
    user = await db.get_user('users', message.from_user.id)
    if user == 'unregister':
        await db.cmd(f"INSERT INTO users (UserID, last_card_time) VALUES ({message.from_user.id}, NULL)")

    rules_text = (
        "<b>Правила бота</b>\n\n"
        "<b>Основные правила:</b>\n"
        "  Запрещено использовать баги/эксплойты\n"
        "  Запрещена продажа карт за реальные деньги\n"
        "  Будьте вежливы с другими коллекционерами\n\n"
        "<b>Правила торговли:</b>\n"
        "  Рекомендуемые цены на карты:\n\n"
        f"   {config.CardsStatus['Common']['Emoji']} {config.CardsStatus['Common']['Ru-Name']}: 20-50 монет\n"
        f"   {config.CardsStatus['Rare']['Emoji']} {config.CardsStatus['Rare']['Ru-Name']}: 100-250 монет\n"
        f"   {config.CardsStatus['Epic']['Emoji']} {config.CardsStatus['Epic']['Ru-Name']}: 500-1.000 монет\n"
        f"   {config.CardsStatus['Legendary']['Emoji']} {config.CardsStatus['Legendary']['Ru-Name']}: 5.000-10.000 монет\n\n"
        "  Не завышайте цены необоснованно\n"
        "  Торгуйтесь уважительно\n\n"
        "❗️ Нарушение правил может привести к ограничениям\n"
        "━━━━━━━━━━━━━━━"
    )
    
    await message.reply(rules_text)
