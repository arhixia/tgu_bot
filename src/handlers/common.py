# src/handlers/common.py  — обновлённая версия

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_service import get_user_by_telegram_id
from src.keyboards.student_kb import mode_selection_kb
from src.states.student_states import StudentStudyMode
from src.db.models import UserRole
from src.keyboards.teacher_kb import teacher_main_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_user_by_telegram_id(session, str(message.from_user.id))

    if not user:
        await message.answer(
            "❌ Вы не зарегистрированы в системе.\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
            "Обратитесь к администратору."
        )
        return

    if user.role == UserRole.STUDENT:
        await state.set_state(StudentStudyMode.choosing_mode)
        await message.answer(
            f"👋 Привет, <b>{user.name}</b>!\n\n"
            "Выберите режим работы:",
            reply_markup=mode_selection_kb()
        )

    elif user.role == UserRole.TEACHER:
        await message.answer(
            f"👋 Привет, <b>{user.name}</b>!\n\nПанель преподавателя:",
            reply_markup=teacher_main_kb()
    )
