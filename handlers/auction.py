from aiogram import types, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import asyncio
from utils.sql import DateBase
from utils import config

router = Router()
db = DateBase()
active_auctions = {}  # {auction_id: {card_id, seller_id, current_price, end_time, highest_bidder}}

@router.message(lambda msg: msg.text.startswith('/createauction'))
async def create_auction(message: types.Message):
    try:
        # Парсим команду /createauction <card_id> <start_price> <duration_hours>
        args = message.text.split()[1:]
        if len(args) != 3:
            await message.reply("❌ Использование: /createauction <ID карты> <начальная цена> <длительность в часах>")
            return
            
        card_id = int(args[0])
        start_price = int(args[1])
        duration = int(args[2])
        
        if duration < 1 or duration > 48:
            await message.reply("❌ Длительность аукциона должна быть от 1 до 48 часов")
            return
            
        # Проверяем владение картой
        card = await db.cmd(f"""
            SELECT c.* FROM cards c
            JOIN my_cards mc ON c.CardsID = mc.CardsID
            WHERE mc.UserID = {message.from_user.id} AND c.CardsID = {card_id}
        """)
        
        if not card:
            await message.reply("❌ У вас нет этой карты!")
            return
            
        # Создаем аукцион
        auction_id = len(active_auctions) + 1
        end_time = datetime.now() + timedelta(hours=duration)
        
        active_auctions[auction_id] = {
            "card_id": card_id,
            "seller_id": message.from_user.id,
            "current_price": start_price,
            "end_time": end_time,
            "highest_bidder": None
        }
        
        # Удаляем карту у продавца
        await db.cmd(f"""
            DELETE FROM my_cards 
            WHERE UserID = {message.from_user.id} AND CardsID = {card_id}
        """)
        
        card_info = card[0]
        await message.reply(
            f"🔨 Создан аукцион #{auction_id}\n"
            f"Карта: {card_info[2]} - {card_info[3]} ({card_info[1]})\n"
            f"Начальная цена: {start_price} монет\n"
            f"Окончание через: {duration} ч.\n\n"
            f"Делайте ставки командой:\n/auction {auction_id} <сумма>"
        )
        
        # Запускаем таймер окончания
        asyncio.create_task(end_auction(auction_id, message))
        
    except ValueError:
        await message.reply("❌ Некорректные параметры аукциона")

@router.message(lambda msg: msg.text.startswith('/auction'))        
async def make_bet(message: types.Message):
    try:
        # Парсим команду /auction <auction_id> <bet>
        args = message.text.split()[1:]
        if len(args) != 2:
            await message.reply("❌ Использование: /auction <ID аукциона> <ставка>")
            return
            
        auction_id = int(args[0])
        bet = int(args[1])
        
        if auction_id not in active_auctions:
            await message.reply("❌ Аукцион не найден или уже завершен")
            return
            
        auction = active_auctions[auction_id]
        
        # Проверяем что это не продавец
        if message.from_user.id == auction["seller_id"]:
            await message.reply("❌ Вы не можете делать ставки на свой аукцион")
            return
            
        # Проверяем минимальную ставку
        if bet <= auction["current_price"]:
            await message.reply(f"❌ Ставка должна быть выше текущей цены ({auction['current_price']} монет)")
            return
            
        # Проверяем баланс
        user_balance = await db.cmd(f"SELECT coins FROM users WHERE UserID = {message.from_user.id}")
        if not user_balance or user_balance[0][0] < bet:
            await message.reply("❌ У вас недостаточно монет!")
            return
            
        # Возвращаем монеты предыдущему участнику
        if auction["highest_bidder"]:
            await db.cmd(f"""
                UPDATE users 
                SET coins = coins + {auction['current_price']}
                WHERE UserID = {auction['highest_bidder']}
            """)
            
        # Списываем монеты у нового участника
        await db.cmd(f"""
            UPDATE users 
            SET coins = coins - {bet}
            WHERE UserID = {message.from_user.id}
        """)
        
        # Обновляем информацию об аукционе
        auction["current_price"] = bet
        auction["highest_bidder"] = message.from_user.id
        
        await message.reply(f"✅ Ваша ставка {bet} монет принята!")
        
    except ValueError:
        await message.reply("❌ Некорректные параметры ставки")
        
async def end_auction(auction_id: int, message: types.Message):
    auction = active_auctions[auction_id]
    await asyncio.sleep((auction["end_time"] - datetime.now()).total_seconds())
    
    if auction_id not in active_auctions:
        return
        
    if auction["highest_bidder"]:
        # Передаем карту победителю
        await db.cmd(f"""
            INSERT INTO my_cards (UserID, CardsID)
            VALUES ({auction['highest_bidder']}, {auction['card_id']})
        """)
        
        # Передаем монеты продавцу
        await db.cmd(f"""
            UPDATE users 
            SET coins = coins + {auction['current_price']}
            WHERE UserID = {auction['seller_id']}
        """)
        
        await message.bot.send_message(
            auction["seller_id"],
            f"🔨 Аукцион #{auction_id} завершен!\n"
            f"Карта продана за {auction['current_price']} монет"
        )
        
        await message.bot.send_message(
            auction["highest_bidder"],
            f"🎉 Поздравляем! Вы выиграли аукцион #{auction_id}!\n"
            f"Карта добавлена в вашу коллекцию"
        )
    else:
        # Возвращаем карту продавцу
        await db.cmd(f"""
            INSERT INTO my_cards (UserID, CardsID)
            VALUES ({auction['seller_id']}, {auction['card_id']})
        """)
        
        await message.bot.send_message(
            auction["seller_id"],
            f"❌ Аукцион #{auction_id} завершен без ставок.\n"
            f"Карта возвращена в вашу коллекцию"
        )
        
    del active_auctions[auction_id]
