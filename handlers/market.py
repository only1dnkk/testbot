from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.sql import DateBase
from datetime import datetime
from aiogram.filters import Command
from utils import config
from aiogram import Bot, DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode='html', link_preview_is_disabled=True))
router = Router()
db = DateBase()

ITEMS_PER_PAGE = 8  # Количество элементов на странице

class SearchStates2(StatesGroup):
    waiting_for_search_market = State()

@router.callback_query(F.data.startswith("sell_card:"))
async def sell_card_handler(callback: types.CallbackQuery, state: FSMContext):
    # Получаем ID карты и пользователя из callback_data
    data = callback.data.split(":")
    card_id = int(data[1])
    owner_id = int(data[2])
    user_id = callback.from_user.id

    # Проверяем, является ли пользователь владельцем кнопки
    if user_id != owner_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Проверяем владение картой
    card = await db.cmd(f"""
        SELECT c.* FROM cards c
        JOIN my_cards mc ON c.CardsID = mc.CardsID 
        WHERE mc.UserID = {user_id} AND c.CardsID = {card_id}
    """)

    if not card:
        await callback.answer("❌ У вас нет этой карты!", show_alert=True)
        return

    await state.update_data(card_id=card_id)
    
    # Получаем эмодзи и русское название для редкости
    card_status = card[0][3]
    status_info = config.CardsStatus.get(card_status, {})
    status_emoji = status_info.get('Emoji', '')
    status_ru = status_info.get('Ru-Name', card_status)
    
    await callback.message.edit_text(
        text=f"💫 Редкость карты: {status_emoji} {status_ru}\n\n💰 Введите цену, за которую хотите продать карту (от 1 до 50.000 монет):",
        reply_markup=None
    )
    await state.set_state("waiting_for_price")
    await callback.answer()

async def process_sell_price(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != "waiting_for_price":
        return

    try:
        price = int(message.text)
        if price <= 0:
            await message.reply("❌ Цена должна быть положительным числом!")
            return
        if price > 50000:
            await message.reply("❌ Максимальная цена продажи - 50.000 монет!")
            return
            
        data = await state.get_data()
        card_id = data["card_id"]
        user_id = message.from_user.id
        username = message.from_user.username
        seller_username = f"@{username}" if username else str(user_id)

        # Выставляем карту на продажу
        await db.cmd(f"""
            INSERT INTO market (SellerID, SellerUsername, CardsID, Price)
            VALUES ({user_id}, '{seller_username}', {card_id}, {price})
        """)

        # Убираем карту из инвентаря продавца
        await db.cmd(f"DELETE FROM my_cards WHERE UserID = {user_id} AND CardsID = {card_id}")

        await message.reply("✅ Карта успешно выставлена на продажу!")
        await state.clear()
        
    except ValueError:
        await message.reply("❌ Пожалуйста, введите корректное число!")

@router.callback_query(F.data.startswith("buy_listing:"))
async def buy_listing_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    listing_id = int(data[1])
    owner_id = int(data[2])
    buyer_id = callback.from_user.id

    # Проверяем, является ли пользователь владельцем кнопки
    if buyer_id != owner_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Получаем информацию о лоте и карте
    listing = await db.cmd(f"""
        SELECT m.*, c.CardsAUTHOR, c.CardsNAME, c.CardsStatus
        FROM market m
        JOIN cards c ON m.CardsID = c.CardsID
        WHERE m.ListingID = {listing_id}
    """)

    if not listing:
        await callback.answer("❌ Этот лот уже не доступен!", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    
    # Проверяем, является ли пользователь продавцом
    if buyer_id == listing[0][1]:
        kb.button(text="❌ Убрать с продажи", callback_data=f"remove_listing:{listing_id}:{owner_id}")
    else:
        kb.button(text="💰 Купить", callback_data=f"confirm_buy:{listing_id}:{owner_id}")
    kb.button(text="🔙 Назад", callback_data=f"market:0:{owner_id}")
    kb.adjust(1)

    seller_name = listing[0][2]  # Берем SellerUsername из таблицы market
    
    # Получаем эмодзи и русское название для редкости
    card_status = listing[0][8]
    status_info = config.CardsStatus.get(card_status, {})
    status_emoji = status_info.get('Emoji', '')
    status_ru = status_info.get('Ru-Name', card_status)

    await callback.message.edit_text(
        text=f"🎫 Название карты: {listing[0][6]} - {listing[0][7]}\n"
             f"🐰 Продавец: {seller_name}\n"
             f"💫 Редкость: {status_emoji} {status_ru}\n"
             f"💸 Цена: {listing[0][4]} монет",
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remove_listing:"))
async def remove_listing_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    listing_id = int(data[1])
    owner_id = int(data[2])
    user_id = callback.from_user.id

    if user_id != owner_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Получаем информацию о лоте
    listing = await db.cmd(f"SELECT * FROM market WHERE ListingID = {listing_id}")
    if not listing or listing[0][1] != user_id:
        await callback.answer("❌ Этот лот уже не доступен или не принадлежит вам!", show_alert=True)
        return

    # Возвращаем карту в инвентарь продавца
    await db.cmd(f"""
        INSERT INTO my_cards (UserID, CardsID) 
        VALUES ({user_id}, {listing[0][3]})
    """)
    await db.cmd(f"DELETE FROM market WHERE ListingID = {listing_id}")

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data=f"market:0:{owner_id}")
    
    await callback.message.edit_text(
        text="✅ Карта успешно снята с продажи!",
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy_handler(callback: types.CallbackQuery):
    data = callback.data.split(":")
    listing_id = int(data[1])
    owner_id = int(data[2])
    buyer_id = callback.from_user.id

    if buyer_id != owner_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Получаем информацию о лоте
    listing = await db.cmd(f"SELECT * FROM market WHERE ListingID = {listing_id}")
    if not listing:
        await callback.answer("❌ Этот лот уже не доступен!", show_alert=True)
        return

    seller_id = listing[0][1]
    card_id = listing[0][3]  # CardsID
    price = listing[0][4]    # Price

    if buyer_id == seller_id:
        await callback.answer("❌ Вы не можете купить свою же карту!", show_alert=True)
        return

    # Проверяем есть ли уже такая карта у покупателя
    existing_card = await db.cmd(f"""
        SELECT * FROM my_cards 
        WHERE UserID = {buyer_id} AND CardsID = {card_id}
    """)
    
    if existing_card:
        await callback.answer("❌ У вас уже есть эта карта!", show_alert=True)
        return

    # Проверяем баланс покупателя
    buyer = await db.get_user('users', buyer_id)
    if buyer['coins'] < price:
        await callback.answer("❌ Недостаточно монет для покупки!", show_alert=True)
        return

    # Проводим транзакцию
    await db.cmd(f"UPDATE users SET coins = coins - {price} WHERE UserID = {buyer_id}")
    await db.cmd(f"UPDATE users SET coins = coins + {price} WHERE UserID = {seller_id}")
    await db.cmd(f"INSERT INTO my_cards (UserID, CardsID) VALUES ({buyer_id}, {card_id})")
    await db.cmd(f"DELETE FROM market WHERE ListingID = {listing_id}")

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data=f"market:0:{buyer_id}")
    
    await callback.message.edit_text(
        text=f"✅ Карта успешно куплена за {price} монет!",
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("market:"))
async def show_market(callback: types.CallbackQuery):
    data = callback.data.split(":")
    page = int(data[1])
    user_id = int(data[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Получаем все активные лоты с пагинацией
    offset = page * ITEMS_PER_PAGE
    listings = await db.cmd(f"""
        SELECT m.ListingID, m.Price, c.CardsAUTHOR, c.CardsNAME, c.CardsStatus, m.SellerUsername
        FROM market m
        JOIN cards c ON m.CardsID = c.CardsID
        ORDER BY m.ListedAt DESC
        LIMIT {ITEMS_PER_PAGE} OFFSET {offset}
    """)
    
    # Получаем общее количество лотов
    total_listings = await db.cmd("SELECT COUNT(*) FROM market")
    total_pages = (total_listings[0][0] + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    market = InlineKeyboardBuilder()
    
    if not listings:
        await callback.message.edit_text(
            text="🏪 Рынок пуст\nПока никто не выставил карты на продажу",
            reply_markup=market.as_markup()
        )
        return

    for listing in listings:
        # Получаем эмодзи и русское название для редкости
        status_info = config.CardsStatus.get(listing[4], {})
        status_emoji = status_info.get('Emoji', '')
        status_ru = status_info.get('Ru-Name', listing[4])
        
        market.button(
            text=f"{listing[2]} - {listing[3]} ({status_emoji} {status_ru}) ({listing[1]} 💰)\n{listing[5]}", 
            callback_data=f"buy_listing:{listing[0]}:{user_id}"
        )
    
    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"market:{page-1}:{user_id}"))
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"market:{page+1}:{user_id}"))
    
    for text, callback_data in nav_buttons:
        market.button(text=text, callback_data=callback_data)
        
    market.button(
        text="📤 Выставить карту",
        callback_data=f"list_cards_for_sale:0:{user_id}"
    )
    
    market.adjust(1)
    
    await callback.message.edit_text(
        text=f"🏪 Рынок карт (Страница {page + 1}/{total_pages})\n\nВыберите карту для покупки:",
        reply_markup=market.as_markup()
    )
    await callback.answer()

async def market_command(message: types.Message):
    user_id = message.from_user.id
    # Получаем первую страницу лотов
    listings = await db.cmd(f"""
        SELECT m.ListingID, m.Price, c.CardsAUTHOR, c.CardsNAME, c.CardsStatus, c.CardsURL, m.SellerUsername
        FROM market m
        JOIN cards c ON m.CardsID = c.CardsID
        ORDER BY m.ListedAt DESC
        LIMIT {ITEMS_PER_PAGE}
    """)
    
    # Получаем общее количество лотов
    total_listings = await db.cmd("SELECT COUNT(*) FROM market")
    total_pages = (total_listings[0][0] + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    market = InlineKeyboardBuilder()
    
    if not listings:
        market.button(
            text="📤 Выставить карту на продажу",
            callback_data=f"list_cards_for_sale:0:{user_id}"
        )
        await message.reply(
            "🏪 Рынок пуст\nПока никто не выставил карты на продажу",
            reply_markup=market.as_markup()
        )
        return

    for listing in listings:
        # Получаем эмодзи и русское название для редкости
        status_info = config.CardsStatus.get(listing[4], {})
        status_emoji = status_info.get('Emoji', '')
        status_ru = status_info.get('Ru-Name', listing[4])
        
        market.button(
            text=f"{listing[2]} - {listing[3]} ({listing[1]}💰)\n{listing[6]}", 
            callback_data=f"buy_listing:{listing[0]}:{user_id}"
        )
    
    # Добавляем кнопку "Вперед" если есть следующая страница
    if total_pages > 1:
        market.button(text="➡️", callback_data=f"market:1:{user_id}")
        
    market.button(
        text="📤 Выставить карту",
        callback_data=f"list_cards_for_sale:0:{user_id}"
    )
    market.adjust(1)
    
    await message.reply(
        f"🏪 Рынок карт (Страница 1/{total_pages})\n\nВыберите карту для покупки:",
        reply_markup=market.as_markup()
    )

@router.callback_query(F.data.startswith("list_cards_for_sale:"))
async def list_cards_for_sale(callback: types.CallbackQuery):
    data = callback.data.split(":")
    page = int(data[1])
    author_id = int(data[2])
    
    if callback.from_user.id != author_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Получаем карты пользователя с пагинацией
    offset = page * ITEMS_PER_PAGE
    user_cards = await db.cmd(f"""
        SELECT c.CardsID, c.CardsAUTHOR, c.CardsNAME, c.CardsStatus, c.CardsURL
        FROM cards c
        JOIN my_cards mc ON c.CardsID = mc.CardsID
        WHERE mc.UserID = {callback.from_user.id}
        ORDER BY c.CardsStatus DESC
        LIMIT {ITEMS_PER_PAGE} OFFSET {offset}
    """)

    if not user_cards:
        if page == 0:
            await callback.answer("У вас нет карт для продажи!", show_alert=True)
        return

    # Получаем общее количество карт пользователя
    total_cards = await db.cmd(f"""
        SELECT COUNT(*) FROM my_cards 
        WHERE UserID = {callback.from_user.id}
    """)
    total_pages = (total_cards[0][0] + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    cards_kb = InlineKeyboardBuilder()
    
    for card in user_cards:
        # Получаем эмодзи и русское название для редкости
        status_info = config.CardsStatus.get(card[3], {})
        status_emoji = status_info.get('Emoji', '')
        status_ru = status_info.get('Ru-Name', card[3])
        
        cards_kb.button(
            text=f"{card[1]} - {card[2]} ({status_emoji} {status_ru})",
            callback_data=f"sell_card:{card[0]}:{author_id}"
        )
    
    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(("⬅️", f"list_cards_for_sale:{page-1}:{author_id}"))
    if page < total_pages - 1:
        nav_buttons.append(("➡️", f"list_cards_for_sale:{page+1}:{author_id}"))
    
    for text, callback_data in nav_buttons:
        cards_kb.button(text=text, callback_data=callback_data)
    cards_kb.button(text="🔍 Поиск", callback_data=f"search_card_market:{author_id}")
    cards_kb.button(text="🔙 Назад", callback_data=f"market:0:{author_id}")
    cards_kb.adjust(1)

    await callback.message.edit_text(
        text=f"📤 Выберите карту для продажи (Страница {page + 1}/{total_pages}):",
        reply_markup=cards_kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_market:"))
async def back_to_market(callback: types.CallbackQuery):
    author_id = int(callback.data.split(":")[1])
    if callback.from_user.id != author_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return

    # Перенаправляем на первую страницу рынка
    await show_market(callback)

@router.callback_query(F.data.startswith("search_card_market:"))
async def search_card_market(callback: types.CallbackQuery, state: FSMContext):
    author_id = int(callback.data.split(":")[1])
    if callback.from_user.id != author_id:
        await callback.answer("❌ Вы не можете использовать чужие кнопки!", show_alert=True)
        return
    # Запрашиваем текст для поиска
    await callback.message.edit_text("Введите название карточки для поиска:")
    await state.set_state(SearchStates2.waiting_for_search_market)
@router.message(SearchStates2.waiting_for_search_market)
async def search_card_market_handler(message: types.Message, state: FSMContext):
    search_query = message.text
    # Ищем карточки пользователя по запросу
    user_cards = await db.cmd(f"""
        SELECT * FROM cards 
        WHERE CardsNAME LIKE '%{search_query}%' AND CardsID IN (
            SELECT CardsID FROM my_cards WHERE UserID={message.from_user.id}
        )
    """)
    if not user_cards:
        await message.answer("🔍 Ничего не найдено по вашему запросу!")
        await state.clear()
        return

    cards_kb = InlineKeyboardBuilder()
    
    for card in user_cards:
        # Получаем эмодзи и русское название для редкости
        status_info = config.CardsStatus.get(card[3], {})
        status_emoji = status_info.get('Emoji', '')
        status_ru = status_info.get('Ru-Name', card[3])
        
        cards_kb.button(
            text=f"{card[1]} - {card[2]} ({status_emoji} {status_ru})",
            callback_data=f"sell_card:{card[0]}:{message.from_user.id}"
        )

    await message.answer(
        text="📤 Выберите карточку для продажи:",
        reply_markup=cards_kb.as_markup()
    )
    await state.clear()