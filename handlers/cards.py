from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.sql import DateBase
from app import SearchStates
from utils import config

router = Router()
db=DateBase()

@router.callback_query(F.data.startswith("search_cards:"))
async def search_cards_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    
    if callback.from_user.id != user_id:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return
        
    await callback.message.reply("🔍 Введите название или исполнителя для поиска:")
    await state.set_state(SearchStates.waiting_for_search)
    await callback.answer()

@router.callback_query(F.data.startswith("show_desc:"))
async def show_desc_handler(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    user_id = int(callback.data.split(":")[2])
    search_query = callback.data.split(":")[3] if len(callback.data.split(":")) > 3 else None
    
    if callback.from_user.id != user_id:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return
        
    if search_query:
        cards = await db.cmd(f"""
            SELECT c.* 
            FROM cards c
            JOIN my_cards mc ON c.CardsID = mc.CardsID
            WHERE mc.UserID = {callback.from_user.id}
            AND (LOWER(c.CardsNAME) LIKE LOWER('%{search_query}%') 
            OR LOWER(c.CardsAUTHOR) LIKE LOWER('%{search_query}%'))
            ORDER BY c.CardsID
        """)
    else:
        cards = await db.cmd(f"""
            SELECT c.* 
            FROM cards c
            JOIN my_cards mc ON c.CardsID = mc.CardsID
            WHERE mc.UserID = {callback.from_user.id}
            ORDER BY c.CardsID
        """)
    
    if not cards:
        await callback.answer("У вас нет карточек", show_alert=True)
        return
        
    if page >= len(cards):
        page = 0  # Reset to first page if out of bounds
        
    info = {
        'CardsID': cards[page][0],
        'CardsStatus': cards[page][1],
        'CardsAUTHOR': cards[page][2],
        'CardsNAME': cards[page][3],
        'CardsURL': cards[page][4],
        'CardsDesc': cards[page][5] if len(cards[page]) > 5 else "Описание отсутствует"
    }
    
    my_cards = InlineKeyboardBuilder()
    my_cards.button(text="◀️ Назад к коллекции", callback_data=f"cards_page:{page}:{user_id}")
    my_cards.button(text="💰 Продать карту боту", callback_data=f"confirm_sell:{info['CardsID']}:{page}:{user_id}:{search_query if search_query else ''}:{info['CardsAUTHOR']}:{info['CardsNAME']}")
    my_cards.adjust(1)
    
    card_text = f"💿 {info['CardsAUTHOR']} - {info['CardsNAME']}\n\n"
    card_text += f"📝 Описание:\n{info['CardsDesc']}\n\n"
    card_text += f"✨ Редкость: {config.CardsStatus[info['CardsStatus']]['Emoji']} ({config.CardsStatus[info['CardsStatus']]['Ru-Name']})"
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=info['CardsURL'],
        caption=card_text,
        reply_markup=my_cards.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_sell:"))
async def confirm_sell_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    card_id = int(data[1])
    page = int(data[2])
    user_id = int(data[3])
    search_query = data[4] if data[4] else None
    author = data[5]
    name = data[6]
    
    if callback.from_user.id != user_id:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return

    confirm_kb = InlineKeyboardBuilder()
    confirm_kb.button(text="✅ Да, продать", callback_data=f"sell_to_bot:{card_id}:{page}:{user_id}:{search_query}")
    confirm_kb.button(text="❌ Отмена", callback_data=f"show_desc:{page}:{user_id}:{search_query if search_query else ''}")
    confirm_kb.adjust(2)

    await callback.message.edit_caption(
        caption=f"❓ Вы уверены, что хотите продать карту {author} - {name}?",
        reply_markup=confirm_kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sell_to_bot:"))
async def sell_to_bot_handler(callback: types.CallbackQuery):
    card_id = int(callback.data.split(":")[1])
    page = int(callback.data.split(":")[2])
    user_id = int(callback.data.split(":")[3])
    search_query = callback.data.split(":")[4] if len(callback.data.split(":")) > 4 else None
    
    if callback.from_user.id != user_id:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return

    # Получаем информацию о карте
    card_info = await db.cmd(f"SELECT CardsStatus FROM cards WHERE CardsID = {card_id}")
    if not card_info:
        await callback.answer("Карта не найдена!", show_alert=True)
        return
        
    # Определяем цену в зависимости от редкости
    rarity = card_info[0][0]
    prices = {
        'Common': 10,
        'Rare': 80,
        'Epic': 250,
        'Legendary': 3000
    }
    price = prices.get(rarity, 50)
    
    # Удаляем карту из инвентаря
    await db.cmd(f"DELETE FROM my_cards WHERE UserID = {user_id} AND CardsID = {card_id}")
    
    # Начисляем деньги пользователю
    await db.cmd(f"UPDATE users SET coins = coins + {price} WHERE UserID = {user_id}")
    
    await callback.message.delete()
    await callback.message.answer(
        text=f"""
🎉 <b>Успешная продажа!</b> 🎉

👤 Пользователь: @{callback.from_user.username}
💫 Статус: <i>Карта продана боту</i>
💰 Получено монет: <b>{price}</b>

━━━━━━━━━━━━━━━
🤖 <i>Спасибо за сделку!</i>
        """,
        reply_markup=InlineKeyboardBuilder().button(
            text="◀️ Вернуться к коллекции",
            callback_data=f"cards_page:{page}:{user_id}"
        ).as_markup()
    )
    await callback.answer("✨ Карта успешно продана!", show_alert=True)
