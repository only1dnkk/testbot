from aiogram import types
from datetime import datetime
import json
import os
import asyncio
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils import config
import aiosqlite
import platform
import sys
import aiohttp
backup_data = {
                'users': [],  # [UserID, username, ref, UUID, balance, rubl, level, plus, plus_time, expi, expi_nado, bonus_cd, bonus_id, bonus_days, keys, bank_kredit, eterlit]
                'cards': [], # [id, rarity, artist, name, image, description]
                'market': [], # [user_id, card_id, price]
                'promos': [], # [id, code, uses_left, type, amount, expires]
                'my_cards': [] # [user_id, card_id]
            }

async def backup_database(message, db, bot, text):
    """
    Создает резервную копию всех данных из базы данных, кроме игровых таблиц
    """

    # Очищаем предыдущие данные
    for key in backup_data:
        backup_data[key] = []

    # Получаем данные из всех таблиц
    async with aiosqlite.connect('Users.db') as db:
        db.row_factory = aiosqlite.Row
        for table in backup_data.keys():
            async with db.execute(f"SELECT * FROM {table}") as cursor:
                rows = await cursor.fetchall()
                if rows:
                    for row in rows:
                        backup_data[table].append(dict(row))

    # Создаем временный файл в директории utils/logs
    os.makedirs('utils/logs', exist_ok=True)
    backup_path = f'utils/logs/backup_{message.from_user.id}.json'

    # Сохраняем данные в JSON файл
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)

    # Отправляем файл в чат
    with open(backup_path, 'rb') as f:
        file_id = await message.reply_document(
            document=types.FSInputFile(backup_path),
            caption=f"💾 Резервная копия базы "
        )
        await file_id.edit_caption(caption=f"💾 Резервная копия базы от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nFile ID: {file_id.document.file_id}")

    os.remove(backup_path)


async def restore_database(message, db, bot, text):
    """
    Восстанавливает данные из резервной копии в базу данных
    """
    # Проверяем что сообщение содержит ссылку на файл
    if not message.text.startswith('/restore '):
        return await message.reply("❌ Укажите ссылку на файл резервной копии\nПример: /restore BQACAgI****")

    file_id = message.text.split(' ')[1]
    
    try:
        # Скачиваем файл по file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Создаем временный файл для сохранения данных
        import os
        import json
        import aiosqlite
        from datetime import datetime
        
        temp_path = f'utils/logs/restore_{message.from_user.id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        os.makedirs('utils/logs', exist_ok=True)
        
        # Скачиваем файл
        await bot.download_file(file_path, temp_path)
        
        # Читаем JSON данные из файла
        with open(temp_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        # Восстанавливаем данные в БД
        async with aiosqlite.connect('Users.db') as conn:
            for table in backup_data:
                # Получаем текущую структуру таблицы
                cursor = await conn.execute(f"PRAGMA table_info({table})")
                table_columns = [col[1] for col in await cursor.fetchall()]

                # Очищаем таблицу перед вставкой данных
                await conn.execute(f"DELETE FROM {table}")
                await conn.commit()
                
                # Вставляем данные из бэкапа
                for row in backup_data[table]:
                    # Преобразуем список в словарь с индексами как ключами
                    row_dict = {str(i): val for i, val in enumerate(row)}
                    
                    # Фильтруем только существующие колонки
                    filtered_row = {str(i): v for i, v in row_dict.items() if i < len(table_columns)}
                    
                    if filtered_row:
                        columns = ', '.join(table_columns[:len(filtered_row)])
                        values = tuple(filtered_row.values())
                        placeholders = ', '.join(['?' for _ in values])
                        
                        await conn.execute(
                            f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
                            values
                        )
                await conn.commit()

        # Удаляем временный файл
        os.remove(temp_path)
                
        await message.reply("✅ База данных успешно восстановлена из резервной копии")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка при восстановлении: {str(e)}")
        print(f"Restore error: {str(e)}")