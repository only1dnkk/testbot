from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from utils.sql import DateBase
from datetime import datetime

router = Router()
db = DateBase()

@router.message(Command("albums"))
async def check_albums_command(message: types.Message):
    user_id = message.from_user.id
    
    # Получаем все альбомы из album_list
    albums = await db.cmd("SELECT * FROM album_list")
    if not albums:
        await message.reply("🐰 Фрр... Пока нет доступных альбомов!")
        return
        
    # Получаем карты пользователя
    user_cards = await db.cmd(f"""
        SELECT CardsID FROM my_cards 
        WHERE UserID = {user_id}
    """)
    user_cards = [card[0] for card in user_cards] if user_cards else []
    
    # Получаем уже полученные альбомы пользователя
    completed_albums = await db.cmd(f"""
        SELECT AlbumID FROM my_album 
        WHERE UserID = {user_id}
    """)
    completed_albums = [album[0] for album in completed_albums] if completed_albums else []
    
    albums_text = "📚 Проверка альбомов:\n\n"
    albums_changed = False
    
    for album in albums:
        album_id = album[0]
        album_name = album[1]
        album_author = album[2]
        required_cards = [int(card_id) for card_id in album[3].split(',')]
        
        # Проверяем наличие всех необходимых карт
        missing_cards = [card_id for card_id in required_cards if card_id not in user_cards]
        
        if album_id in completed_albums and missing_cards:
            # Если альбом был получен, но теперь не хватает карт - забираем его
            await db.cmd(f"""
                DELETE FROM my_album 
                WHERE UserID = {user_id} AND AlbumID = {album_id}
            """)
            albums_text += f"❌ {album_author} - {album_name} (Альбом изъят - не хватает карт)\n"
            albums_changed = True
            completed_albums.remove(album_id)
        elif album_id in completed_albums:
            albums_text += f"✅ {album_author} - {album_name} (Получен)\n"
        elif not missing_cards:
            # Если все карты есть - выдаем альбом
            await db.cmd(f"""
                INSERT INTO my_album (UserID, AlbumID) 
                VALUES ({user_id}, {album_id})
            """)
            albums_text += f"🎉 {album_author} - {album_name} (Новый!)\n"
            albums_changed = True
        else:
            # Подсчитываем прогресс
            cards_collected = len(required_cards) - len(missing_cards)
            progress = f"{cards_collected}/{len(required_cards)}"
            albums_text += f"📝 {album_author} - {album_name} ({progress})\n"
    
    if albums_changed:
        albums_text = "⚠️ Обнаружены изменения в ваших альбомах!\n\n" + albums_text
    
    await message.reply(albums_text)
