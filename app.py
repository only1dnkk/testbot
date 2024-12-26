from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberAdministrator, ChatMemberRestricted
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums.parse_mode import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramRetryAfter
from aiogram import types

from handlers.promo import ActivatePromoCommand, create_promo_handler
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from handlers.promo import ActivatePromoCommand, create_promo_handler
from handlers.market import market_command, process_sell_price
from handlers.backup import backup_database, restore_database
from handlers.albums import check_albums_command
from handlers.help import help_command
from handlers.rules import rules_command
from handlers.sendbug import send_bug_command, answer_to_user
from handlers.jobs import job_command
from handlers.rating import show_rating

from datetime import datetime, timedelta
import asyncio
import logging
import time
import random
from utils import config
from utils.sql import DateBase
from utils.ftl import FluentLocalization
from handlers.albums import router as albums_router

bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode='html', link_preview_is_disabled=True))
router = Router()
db = DateBase()

class SearchStates(StatesGroup):
    waiting_for_search = State()

async def GetCardsCommand(message: types.Message, text, db):
    # Проверяем время последнего использования команды
    last_use = await db.cmd(f"SELECT last_card_time FROM users WHERE UserID={message.from_user.id}")
    if last_use and last_use[0][0]:
        last_time = datetime.fromisoformat(last_use[0][0])
        time_passed = datetime.now() - last_time
        if time_passed < timedelta(hours=12):
            remaining = timedelta(hours=12) - time_passed
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            await message.reply(f"🐰 Фрр... Подожди еще {hours} ч. {minutes} мин. прежде чем получить новую карту!")
            return

    # Получаем все карты и карты пользователя
    cards = await db.get_lists(tables='cards', table='CardsID')
    my_cards = await db.cmd(f"SELECT CardsID FROM my_cards WHERE UserID={message.from_user.id}")
    my_cards = [card[0] for card in my_cards] if my_cards else []
    
    # Получаем список карт, которых нет у пользователя
    available_cards = [card[0] for card in cards if card[0] not in my_cards]
    
    if not available_cards:
        await message.reply("У вас уже есть все доступные карты!")
        return
        
    # Определяем редкость случайной карты и пытаемся получить карту
    while True:
        randoms = ['Common', 'Common', 'Common', 'Common', 'Common', 'Common', 'Common', 'Common',  # 8 Common - 50%
                  'Rare', 'Rare', 'Rare', 'Rare',  # 4 Rare - 25%
                  'Epic', 'Epic', 'Epic',  # 3 Epic - 18.75%
                  'Legendary']  # 1 Legendary - 6.25%
        pol_random = random.choice(randoms)
        
        # Получаем случайную карту выбранной редкости, которой нет у пользователя
        get_cards = await db.cmd(f"""
            SELECT c.* FROM cards c
            WHERE c.CardsStatus='{pol_random}' 
            AND c.CardsID NOT IN (
                SELECT CardsID FROM my_cards WHERE UserID={message.from_user.id}
            )
            ORDER BY RANDOM() LIMIT 1
        """)

        if get_cards:
            # Обновляем время последнего использования команды
            await db.cmd(f"""
                UPDATE users 
                SET last_card_time = '{datetime.now().isoformat()}' 
                WHERE UserID = {message.from_user.id}
            """)
            
            # Добавляем карту пользователю
            await db.cmd(f"INSERT INTO my_cards (CardsID, UserID) VALUES ({get_cards[0][0]}, {message.from_user.id})")
            await message.reply_photo(
                photo=get_cards[0][4],
                caption=f"💿 {get_cards[0][2]} - {get_cards[0][3]}\n\n"
                        f"🐰💭 Держи карточку, фрр.. Она уже в твоей коллекции!\n\n"
                        f"✨ Редкость: {config.CardsStatus[pol_random]['Emoji']} ({config.CardsStatus[pol_random]['Ru-Name']})\n\n"
                        f"<b><a href='https://t.me/lair_music'>SATURN CHANNEL</a></b>"
            )
            break
        else:
            # Если не нашли карту выбранной редкости
            continue

async def MyCardsCommand(message: types.Message, text, db, search_query=None):
    # Получаем карты пользователя с учетом поиска
    if search_query:
        # Формируем SQL запрос с поиском по автору и названию
        # Получаем все карты пользователя
        all_cards = await db.cmd(f"""
            SELECT c.* 
            FROM cards c
            JOIN my_cards mc ON c.CardsID = mc.CardsID
            WHERE mc.UserID = {message.from_user.id}
            ORDER BY c.CardsID
        """)
        
        # Фильтруем карты по поисковому запросу
        cards = []
        search_query = search_query.lower()
        for card in all_cards:
            if (search_query in card[2].lower() or  # CardsAUTHOR
                search_query in card[3].lower()):   # CardsNAME
                cards.append(card)
    else:
        # Если поиск не задан, получаем все карты пользователя
        cards = await db.cmd(f"""
            SELECT c.* 
            FROM cards c
            JOIN my_cards mc ON c.CardsID = mc.CardsID
            WHERE mc.UserID = {message.from_user.id}
            ORDER BY c.CardsID
        """)

    if not cards:
        if search_query:
            await message.reply("🔍 По вашему запросу ничего не найдено.")
        else:
            await message.reply(text.format_value('no-cards'))
        return

    page = 0
    info = {
        'CardsID': cards[page][0],
        'CardsStatus': cards[page][1],
        'CardsAUTHOR': cards[page][2],
        'CardsNAME': cards[page][3],
        'CardsURL': cards[page][4],
        'CardsDesc': cards[page][5] if len(cards[page]) > 5 else "Описание отсутствует"
    }

    my_cards = InlineKeyboardBuilder()
    
    # First row - navigation
    if page > 0:
        my_cards.button(text="⬅️ Назад", callback_data=f"cards_page:{page-1}:{message.from_user.id}")
    my_cards.button(text=f"📄 {page + 1}/{len(cards)}", callback_data=f"page:{message.from_user.id}")
    if page < len(cards) - 1:
        my_cards.button(text="Далее ➡️", callback_data=f"cards_page:{page+1}:{message.from_user.id}")
    
    # Second row - search
    my_cards.button(text="🔍 Поиск", callback_data=f"search_cards:{message.from_user.id}")
    
    # Third row - rarity
    my_cards.button(
        text=f"{config.CardsStatus[info['CardsStatus']]['Emoji']} {config.CardsStatus[info['CardsStatus']]['Ru-Name']}", 
        callback_data=f"show_desc:{page}:{message.from_user.id}"
    )
    
    my_cards.adjust(3, 1, 1)
    
    if search_query:
        card_text = f"💿 {info['CardsAUTHOR']} - {info['CardsNAME']}\n\n"
        card_text += f"🐰 Фрр, нашёл карточку по твоему запросу \"{search_query}\""
    else:
        # Подсчет карт по редкости
        rarity_counts = {
            'Legendary': 0,
            'Epic': 0, 
            'Rare': 0,
            'Common': 0
        }
        
        for card in cards:
            rarity_counts[card[1]] += 1
        
        total_cards = len(cards)
        
        card_text = f"💿 {info['CardsAUTHOR']} - {info['CardsNAME']}\n\n"
        card_text += f"{config.CardsStatus['Legendary']['Emoji']} {config.CardsStatus['Legendary']['Ru-Name']}: {rarity_counts['Legendary']}\n"
        card_text += f"{config.CardsStatus['Epic']['Emoji']} {config.CardsStatus['Epic']['Ru-Name']}: {rarity_counts['Epic']}\n"
        card_text += f"{config.CardsStatus['Rare']['Emoji']} {config.CardsStatus['Rare']['Ru-Name']}: {rarity_counts['Rare']}\n"
        card_text += f"{config.CardsStatus['Common']['Emoji']} {config.CardsStatus['Common']['Ru-Name']}: {rarity_counts['Common']}\n"
        card_text += f"Всего: {total_cards}\n\n"
        card_text += f"🐰 Фрр, это вся твоя коллекция!"
    
    await message.reply_photo(
        photo=info['CardsURL'],
        caption=card_text,
        reply_markup=my_cards.as_markup()
    )

async def StartCommand(message: types.Message, text):
    if message.chat.id != message.from_user.id:
        return await message.reply(text.format_value('start-2'))
    await message.reply(text.format_value('start'), reply_markup=ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=f"🥕 Получить карту"),
         KeyboardButton(text=f"🥬 Мои карты")
        ]
    ], resize_keyboard=True))

@router.message(F.text)
async def messages(message: types.Message, state: FSMContext, text: FluentLocalization):
    user = await db.get_user('users', message.from_user.id)
    if user == 'unregister':
        await db.cmd(f"INSERT INTO users (UserID, last_card_time) VALUES ({message.from_user.id}, NULL)")
    
    current_state = await state.get_state()
    if current_state == "SearchStates:waiting_for_search":
        # Обработка поискового запроса
        search_query = message.text.lower()
        await MyCardsCommand(message, text, db, search_query)
        await state.clear()
        return

    if current_state == "waiting_for_price":
        await process_sell_price(message, state)
        return
        
    UserID = message.from_user.id
    username = message.from_user.username
    ChatID = message.chat.id
    DataBot = await bot.get_me()
    data = await db.get_user('users', UserID)
    UserNameBot = DataBot.username
    command = message.text.lower().split('@')[0]  # Берем команду без юзернейма бота
    await db.cmd(f"UPDATE users SET Username='@{message.from_user.username}' WHERE UserID={UserID}")
    await db.cmd(f"UPDATE market SET SellerUsername='@{message.from_user.username}' WHERE SellerID={UserID}")

    # Проверяем альбомы при каждом сообщении
    user_cards = await db.cmd(f"SELECT CardsID FROM my_cards WHERE UserID = {UserID}")
    user_cards = [card[0] for card in user_cards] if user_cards else []
    
    completed_albums = await db.cmd(f"SELECT AlbumID FROM my_album WHERE UserID = {UserID}")
    if completed_albums:
        for album in completed_albums:
            album_id = album[0]
            album_cards = await db.cmd(f"SELECT RequiredCards FROM album_list WHERE AlbumID = {album_id}")
            if album_cards:
                required_cards = [int(card_id) for card_id in album_cards[0][0].split(',')]
                missing_cards = [card_id for card_id in required_cards if card_id not in user_cards]
                
                if missing_cards:
                    await db.cmd(f"DELETE FROM my_album WHERE UserID = {UserID} AND AlbumID = {album_id}")
                    await message.reply(f"❌ Альбом был изъят из-за отсутствия необходимых карт!")

    if command in ['/start', '🥬 мои карты']:
        await StartCommand(message=message, text=text)
    if command in ['/my_cards', '🥬 мои карты']:
        await MyCardsCommand(message=message, text=text, db=db)
    if command in ['/get_cards', '🥕 получить карту']:
        await GetCardsCommand(message=message, text=text, db=db)
    if command in ['/bal', '💰 мои монеты']:
        await message.reply(f"💰 У тебя {data['coins']} монет")
    elif command.lower().startswith('/promo'):
        await ActivatePromoCommand(message=message)
    elif command.lower().startswith('/createpromo'):
        await create_promo_handler(message=message)
    if command in ['/shop', '🏪 рынок']:
        await market_command(message=message)
    if command in ['/backup', '💾 резервная копия'] and UserID in config.ADMINS:
        await backup_database(message=message, db=db, bot=bot, text=text)
    if command.startswith('/restore') and UserID in config.ADMINS:
        await restore_database(message=message, db=db, bot=bot, text=text)
    if command in ['/albums', '📚 проверка альбомов']:
        await check_albums_command(message=message)
    if command == '/help':
        await help_command(message=message)
    if command == '/rules':
        await rules_command(message=message)
    if command.startswith('/sendbug'):
        await send_bug_command(message=message)
    if command.startswith('/ans'):
        await answer_to_user(message=message)
    if command in ['/work', '💼 работа']:
        await job_command(message=message, state=state)
    if command in ['/rating', '🏆 рейтинг']:
        await show_rating(message=message)

@router.callback_query(F.data.startswith("cards_page:"))
async def cards_page_handler(callback: types.CallbackQuery, text: FluentLocalization):
    page = int(callback.data.split(":")[1])
    user_id = int(callback.data.split(":")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("Эта кнопка не для вас!", show_alert=True)
        return
    
    # Получаем карты пользователя
    cards = await db.cmd(f"""
        SELECT c.* 
        FROM cards c
        JOIN my_cards mc ON c.CardsID = mc.CardsID
        WHERE mc.UserID = {callback.from_user.id}
        ORDER BY c.CardsID
    """)
    
    if not cards:
        await callback.answer(text.format_value('no-cards'))
        return
        
    if page >= len(cards):
        page = 0
        
    info = {
        'CardsID': cards[page][0],
        'CardsStatus': cards[page][1],
        'CardsAUTHOR': cards[page][2],
        'CardsNAME': cards[page][3],
        'CardsURL': cards[page][4],
        'CardsDesc': cards[page][5] if len(cards[page]) > 5 else "Описание отсутствует"
    }

    # Подсчет карт по редкости
    rarity_counts = {
        'Legendary': 0,
        'Epic': 0,
        'Rare': 0,
        'Common': 0
    }
    
    for card in cards:
        rarity_counts[card[1]] += 1
        
    total_cards = len(cards)
    
    my_cards = InlineKeyboardBuilder()
    
    # First row - navigation
    if page > 0:
        my_cards.button(text="⬅️ Назад", callback_data=f"cards_page:{page-1}:{user_id}")
    my_cards.button(text=f"📄 {page + 1}/{len(cards)}", callback_data=f"page:{user_id}")
    if page < len(cards) - 1:
        my_cards.button(text="Далее ➡️", callback_data=f"cards_page:{page+1}:{user_id}")
    
    # Second row - search
    my_cards.button(text="🔍 Поиск", callback_data=f"search_cards:{user_id}")
    
    # Third row - rarity and sell
    my_cards.button(
        text=f"{config.CardsStatus[info['CardsStatus']]['Emoji']} {config.CardsStatus[info['CardsStatus']]['Ru-Name']}", 
        callback_data=f"show_desc:{page}:{user_id}"
    )
    
    my_cards.adjust(3, 1, 1)
    
    card_text = f"💿 {info['CardsAUTHOR']} - {info['CardsNAME']}\n\n"
    card_text += f"{config.CardsStatus['Legendary']['Emoji']} {config.CardsStatus['Legendary']['Ru-Name']}: {rarity_counts['Legendary']}\n"
    card_text += f"{config.CardsStatus['Epic']['Emoji']} {config.CardsStatus['Epic']['Ru-Name']}: {rarity_counts['Epic']}\n"
    card_text += f"{config.CardsStatus['Rare']['Emoji']} {config.CardsStatus['Rare']['Ru-Name']}: {rarity_counts['Rare']}\n"
    card_text += f"{config.CardsStatus['Common']['Emoji']} {config.CardsStatus['Common']['Ru-Name']}: {rarity_counts['Common']}\n"
    card_text += f"Всего: {total_cards}\n\n"
    card_text += f"🐰 Фрр, это вся твоя коллекция!"
    
    await callback.message.edit_media(
        types.InputMediaPhoto(
            media=info['CardsURL'],
            caption=card_text
        ),
        reply_markup=my_cards.as_markup()
    )

router.include_router(albums_router)