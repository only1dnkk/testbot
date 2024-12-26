from aiogram import Router, F, types
from aiogram.filters import Command
from utils.sql import DateBase
from utils.ftl import GetFluentLocalization
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils import config

router = Router()
db = DateBase()
text = GetFluentLocalization('ru')

@router.message(Command("sendbug", ignore_case=True))
async def send_bug_command(message: types.Message):
    try:
        user = await db.get_user('users', message.from_user.id)
        if user == 'unregister':
            await db.cmd(f"INSERT INTO users (UserID, last_card_time) VALUES ({message.from_user.id}, NULL)")

        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            await message.reply("❌ Пожалуйста, опишите баг после команды /sendbug")
            return
            
        bug_text = command_parts[1]
        
        # Формируем предварительное сообщение о баге
        preview_report = (
            "📋 <b>Проверьте информацию перед отправкой тикета:</b>\n\n"
            f"👤 Отправитель: @{message.from_user.username}\n"
            f"📝 Текст: {bug_text}\n"
            f"📅 Дата: {message.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"💭 Чат: {message.chat.title if message.chat.title else 'Личные сообщения'}"
        )
        
        # Создаем клавиатуру с кнопками подтверждения и отмены
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Отправить", callback_data=f"send_ticket:{message.from_user.id}:{message.message_id}:{bug_text}")
        kb.button(text="❌ Отклонить", callback_data=f"cancel_ticket:{message.from_user.id}")
        kb.adjust(2)
        
        await message.reply(
            text=preview_report,
            reply_markup=kb.as_markup()
        )
        
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при создании тикета: {str(e)}")

@router.callback_query(F.data.startswith("send_ticket:"))
async def send_ticket_handler(callback: types.CallbackQuery):
    try:
        data = callback.data.split(":")
        user_id = int(data[1])
        message_id = int(data[2])
        bug_text = data[3]
        
        if callback.from_user.id != user_id:
            await callback.answer("Это не ваш тикет!", show_alert=True)
            return
        
        bug_report = (
            "🐛 <b>Найден баг!</b>\n\n"
            f"👤 Отправитель: @{callback.from_user.username} (ID: {user_id})\n"
            f"📝 Текст: {bug_text}\n"
            f"🔗 <a href='https://t.me/c/{str(callback.message.chat.id)[4:]}/{message_id}'>Ссылка на сообщение</a>"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Принять тикет", callback_data=f"accept_ticket:{user_id}")
        
        await callback.message.bot.send_message(
            chat_id=-1002416611310,
            text=bug_report,
            reply_markup=kb.as_markup()
        )
        
        await callback.message.edit_text(
            "✅ Ваше сообщение о баге успешно отправлено! Ожидайте ответа от администратора.",
            reply_markup=None
        )
        
    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("cancel_ticket:"))
async def cancel_ticket_handler(callback: types.CallbackQuery):
    try:
        user_id = int(callback.data.split(":")[1])
        
        if callback.from_user.id != user_id:
            await callback.answer("Это не ваш тикет!", show_alert=True)
            return
            
        await callback.message.edit_text(
            "❌ Отправка тикета отменена.",
            reply_markup=None
        )
        
    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("accept_ticket:"))
async def accept_ticket_handler(callback: types.CallbackQuery):
    try:
        user_id = int(callback.data.split(":")[1])
        
        kb = InlineKeyboardBuilder()
        kb.button(
            text=f"✅ Принято: @{callback.from_user.username}",
            callback_data="ticket_accepted"
        )
        
        await callback.message.edit_reply_markup(
            reply_markup=kb.as_markup()
        )
        
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"✅ Администратор @{callback.from_user.username} принял ваш тикет!"
        )
        
        await callback.answer("Вы приняли тикет!")
    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

@router.message(Command("ans", ignore_case=True))
async def answer_to_user(message: types.Message):
    try:
        if message.from_user.id not in config.ADMINS:
            await message.reply("❌ У вас нет прав для использования этой команды!")
            return

        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            await message.reply("❌ Используйте формат: /ans @username текст_сообщения")
            return

        username = parts[1].replace("@", "")
        answer_text = parts[2]

        user_info = await db.cmd(f"SELECT UserID FROM users WHERE Username = '{username}' OR Username = '@{username}'")
        if not user_info:
            await message.reply("❌ Пользователь не найден!")
            return

        user_id = user_info[0][0]

        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"📨 <b>Ответ от администратора</b> @{message.from_user.username}:\n\n{answer_text}"
            )
            await message.reply("✅ Ответ успешно отправлен!")
        except Exception as e:
            await message.reply(f"❌ Не удалось отправить сообщение пользователю. Возможно, бот заблокирован.")
            
    except Exception as e:
        await message.reply(f"❌ Произошла ошибка при отправке ответа: {str(e)}")
