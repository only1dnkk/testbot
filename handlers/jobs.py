from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
import random
from utils.sql import DateBase

router = Router()
db = DateBase()

class JobStates(StatesGroup):
    working = State()

# Эмодзи для работы
JOB_EMOJIS = ["🎵", "🎹", "🎼"]

# Опыт необходимый для каждого уровня
LEVEL_XP = {
    1: 0,
    2: 100,
    3: 300,
    4: 600,
    5: 1000,
    6: 1500,
    7: 2100,
    8: 2800,
    9: 3600,
    10: 4500
}

# Базовая зарплата и множитель для каждого уровня
BASE_SALARY = 10
SALARY_MULTIPLIER = 1.5

@router.message(Command("work"))
async def job_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Проверяем существует ли запись в my_job
    job_data = await db.cmd(f"SELECT last_work, xp, lvl FROM my_job WHERE UserID = {user_id}")
    
    if not job_data:
        # Создаем новую запись если пользователь впервые работает
        await db.cmd(f"""
            INSERT INTO my_job (UserID, Username, xp, lvl)
            VALUES ({user_id}, '@{username}', 0, 1)
        """)
        job_data = [(None, 0, 1)]
    
    last_work = datetime.fromisoformat(job_data[0][0]) if job_data[0][0] else None
    
    if last_work and datetime.now() - last_work < timedelta(hours=4):
        remaining = timedelta(hours=4) - (datetime.now() - last_work)
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        await message.reply(f"⏳ Вы устали! Отдохните ещё {hours}ч {minutes}мин")
        return
        
    await start_work_shift(message, state)

async def start_work_shift(message: types.Message, state: FSMContext):
    current_step = 0
    
    kb = InlineKeyboardBuilder()
    correct_emoji = random.choice(JOB_EMOJIS)
    
    for emoji in JOB_EMOJIS:
        kb.button(text=emoji, callback_data=f"work:{emoji}:{current_step}:{correct_emoji}")
    kb.adjust(2)
    
    # Получаем уровень пользователя
    user_data = await db.cmd(f"SELECT lvl FROM my_job WHERE UserID = {message.from_user.id}")
    user_level = user_data[0][0] if user_data else 1
    
    # Рассчитываем зарплату на основе уровня
    salary = int(BASE_SALARY * (SALARY_MULTIPLIER ** (user_level - 1)))
    
    await state.set_state(JobStates.working)
    await state.update_data(
        current_step=current_step,
        correct_emoji=correct_emoji,
        start_time=datetime.now().isoformat(),
        salary=salary
    )
    
    await message.reply(
        f"📋 Смена началась! Нажимайте на {correct_emoji}\n"
        f"💰 Ваша ставка: {salary} монет за смену",
        reply_markup=kb.as_markup()
    )

@router.callback_query(JobStates.working)
async def work_process(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_emoji = callback.data.split(":")[1]
    current_step = int(callback.data.split(":")[2])
    correct_emoji = callback.data.split(":")[3]
    
    if selected_emoji != correct_emoji:
        await callback.answer("❌ Неверно! Попробуйте ещё раз", show_alert=True)
        return
        
    current_step += 1
    if current_step >= 3:
        # Смена закончена
        salary = data['salary']
        
        # Получаем текущий опыт
        user_data = await db.cmd(f"SELECT xp, lvl FROM my_job WHERE UserID = {callback.from_user.id}")
        current_xp = user_data[0][0]
        current_level = user_data[0][1]
        
        # Начисляем опыт (20-50 за смену)
        xp_gain = random.randint(20, 50)
        new_xp = current_xp + xp_gain
        
        # Проверяем повышение уровня
        new_level = current_level
        level_up_text = ""
        
        while new_level < 10 and new_xp >= LEVEL_XP[new_level + 1]:
            new_level += 1
            level_up_text = f"\n🎊 Поздравляем! Вы достигли {new_level} уровня!"
        
        await db.cmd(f"""
            UPDATE my_job 
            SET xp = {new_xp},
                lvl = {new_level},
                last_work = '{datetime.now().isoformat()}'
            WHERE UserID = {callback.from_user.id}
        """)
        
        await state.clear()
        await callback.message.edit_text(
            f"✅ Смена завершена!\n"
            f"Заработано: {salary}💰\n"
            f"Получено опыта: +{xp_gain}📊"
            f"{level_up_text}"
        )
        return
        
    # Следующий шаг
    kb = InlineKeyboardBuilder()
    new_correct_emoji = random.choice(JOB_EMOJIS)
    
    for emoji in JOB_EMOJIS:
        kb.button(text=emoji, callback_data=f"work:{emoji}:{current_step}:{new_correct_emoji}")
    kb.adjust(2)
    
    await state.update_data(current_step=current_step, correct_emoji=new_correct_emoji)
    await callback.message.edit_text(
        f"📋 Нажмите на {new_correct_emoji}",
        reply_markup=kb.as_markup()
    )
