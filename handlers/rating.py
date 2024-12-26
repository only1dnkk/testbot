from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.sql import DateBase

router = Router()
db = DateBase()

@router.message(Command("rating"))
async def show_rating(message: types.Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 По балансу", callback_data="rating_balance")
    kb.button(text="🎴 По количеству карточек", callback_data="rating_cards") 
    kb.button(text="📊 По уровню", callback_data="rating_level")
    kb.adjust(1)
    
    await message.answer("Выберите тип рейтинга:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("rating_"))
async def process_rating(callback: types.CallbackQuery):
    rating_type = callback.data.split("_")[1]
    
    if rating_type == "balance":
        query = """
            SELECT COALESCE(Username, CAST(UserID AS TEXT)) as name, coins 
            FROM users 
            WHERE Username IS NOT NULL
            ORDER BY coins DESC 
            LIMIT 10
        """
        title = "Топ 10 по балансу:"
        format_str = "#{pos}. {name}: {value}💰"
        
    elif rating_type == "cards":
        query = """
            SELECT COALESCE(u.Username, CAST(u.UserID AS TEXT)) as name, 
                COUNT(mc.CardsID) as card_count 
            FROM users u
            LEFT JOIN my_cards mc ON u.UserID = mc.UserID
            WHERE u.Username IS NOT NULL
            GROUP BY u.UserID, u.Username
            ORDER BY card_count DESC 
            LIMIT 10
        """
        title = "Топ 10 по количеству карточек:"
        format_str = "#{pos}. {name}: {value}🎴"
        
    else:  # level
        query = """
            SELECT COALESCE(Username, CAST(UserID AS TEXT)) as name, 
                   COALESCE(lvl, 1) as level
            FROM my_job 
            WHERE Username IS NOT NULL
            ORDER BY level DESC, xp DESC 
            LIMIT 10
        """
        title = "Топ 10 по уровню:"
        format_str = "#{pos}. {name}: {value}📊"

    results = await db.cmd(query)
    
    text = [title]
    for pos, (name, value) in enumerate(results, 1):
        text.append(format_str.format(
            pos=pos,
            name=name,
            value=value
        ))
    
    await callback.message.edit_text(
        "\n".join(text),
        reply_markup=callback.message.reply_markup
    )
