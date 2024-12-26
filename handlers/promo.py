from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.sql import DateBase
from datetime import datetime
from utils import config
router = Router()
db = DateBase()

@router.callback_query(F.data == "activate_promo")
async def activate_promo_handler(callback: types.CallbackQuery):
    await callback.message.reply("🎁 Введите промокод:\n━━━━━━━━━━━━━━━")
    await callback.answer()

async def ActivatePromoCommand(message: types.Message):
    if message.text.startswith("/promo"):
        promo_code = message.text.split()[1] if len(message.text.split()) > 1 else None
    else:
        promo_code = message.text
    
    if not promo_code:
        await message.reply("🐰 <b>Эй! Ты не указал промокод!</b>\n\n🔸 Попробуй использовать: /promo [код]")
        return

    # Проверяем промокод в базе
    promo = await db.cmd(f"""
        SELECT * FROM promos 
        WHERE PromoCode = '{promo_code}' 
        AND (UsesLeft > 0 OR UsesLeft = -1)
        AND (ExpiryDate > '{datetime.now()}' OR ExpiryDate IS NULL)
    """)

    if not promo:
        await message.reply("❌ <b>Я не нашёл такой промокод!</b>\n\n🔸 Возможно он уже использован.")
        return

    # Проверяем, использовал ли пользователь этот промокод
    used = await db.cmd(f"""
        SELECT * FROM promo_uses 
        WHERE PromoID = {promo[0][0]} AND UserID = {message.from_user.id}
    """)

    if used:
        await message.reply("⚠️ <b>Эй! Не пытайся обхитрить!</b>\n\n🔸 Ты уже использовал этот промокод!")
        return

    # Активируем промокод
    reward_type = promo[0][3] 
    reward_amount = promo[0][4] 
    if reward_type == "coins":
        # Выдаем монеты
        await db.cmd(f"""
            UPDATE users 
            SET coins = coins + {reward_amount} 
            WHERE UserID = {message.from_user.id}
        """)

    # Отмечаем использование промокода
    await db.cmd(f"""
        INSERT INTO promo_uses (PromoID, UserID) 
        VALUES ({promo[0][0]}, {message.from_user.id})
    """)

    # Уменьшаем количество доступных использований
    if promo[0][2] > 0:  # если не бесконечный (-1)
        await db.cmd(f"""
            UPDATE promos 
            SET UsesLeft = UsesLeft - 1 
            WHERE PromoID = {promo[0][0]}
        """)

    await message.reply(f"✅ <b>Промокод успешно активирован!</b>\n\n💎 Награда: {reward_amount} {reward_type}\n━━━━━━━━━━━━━━━")

async def create_promo_handler(message: types.Message):
    if message.from_user.id not in config.ADMINS:  # замените на список админов
        return
        
    args = message.text.split()[1:]
    if len(args) < 4:
        await message.reply(
            "📝 <b>Создание промокода</b>\n\n"
            "🔸 Формат команды:\n"
            "/createpromo [код] [использования] [тип_награды] [количество] [срок_действия]\n\n"
            "📌 Пример:\n"
            "/createpromo COINS500 -1 coins 500 2024-12-31\n"
            "━━━━━━━━━━━━━━━",
            parse_mode=None
        )
        return

    code, uses, reward_type, amount = args[:4]
    expiry = args[4] if len(args) > 4 else None

    await db.cmd(f"""
        INSERT INTO promos (PromoCode, UsesLeft, RewardType, RewardAmount, ExpiryDate)
        VALUES ('{code}', {uses}, '{reward_type}', {amount}, {'NULL' if not expiry else f"'{expiry}'"})
    """)

    await message.reply(f"✅ <b>Промокод успешно создан!</b>\n\n🎁 Код: {code}\n━━━━━━━━━━━━━━━", parse_mode=None)

