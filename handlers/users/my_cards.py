from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import config

async def MyCardsCommand(message: types.Message, text, db):
    cards = await db.get_lists(tables='my_cards', table='CardsID')
    my_cards = InlineKeyboardBuilder()
    for card in cards:
        info=await db.get_user2(int(card[0]), tables='cards', where='CardsID')
        my_cards.button(
            text=f"{config.CardsStatus[info['CardsStatus']]['Emoji']} {info['CardsAUTHOR']} - {info['CardsNAME']}",
            callback_data=f"1"
        )
    await message.reply(text.format_value('vashi-kartochki'), reply_markup=my_cards.as_markup())