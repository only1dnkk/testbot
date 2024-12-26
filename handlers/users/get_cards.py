from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
from utils import config
async def GetCardsCommand(message: types.Message, text, db):
    cards = await db.get_lists(tables='cards', table='CardsID')
    my_cards = await db.get_lists(tables='my_cards', table='CardsID')
    full_cards = result = [card for card in cards if card not in my_cards]
    get_cards2=0
    while get_cards2 < 1:
        randoms = ['Common', 'Common', 'Common', 'Common', 'Common', 'Common', 'Rare', 'Rare', 'Rare', 'Epic', 'Epic', 'Legendary']
        pol_random = random.choice(randoms)
        get_cards = await db.cmd(f"SELECT * FROM cards WHERE CardsStatus='{pol_random}' ORDER BY RANDOM() LIMIT 1")
        for card in my_cards:
            try:
                if card == get_cards[0][0]:
                    pass
                else:
                    if len(get_cards) > 0:
                        get_cards2+=1
            except:
                pass
    if len(get_cards) > 0:
        await message.reply(f"Вы получили карточку {config.CardsStatus[pol_random]['Emoji']} {get_cards[0][2]} - {get_cards[0][3]}")