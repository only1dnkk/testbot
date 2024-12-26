from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
async def StartCommand(message: types.Message, text):
    if message.chat.id != message.from_user.id:
        return await message.reply(text.format_value('start-2'))
    await message.reply(text.format_value('start'), reply_markup=ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=f"🧀 Получить карту"),
         KeyboardButton(text=f"🍟 Мои карты")
        ]
    ], resize_keyboard=True))