# src/handlers/student.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.states.student_states import StudentStudyMode
from src.keyboards.student_kb import mode_selection_kb, study_menu_kb, themes_kb, skip_kb
from src.services.user_service import get_user_by_telegram_id
from src.services.task_service import get_all_themes, get_theme_by_id,get_next_task

router = Router()

TESTING_LIMIT = 10


@router.message(F.text == "📚 Режим обучения")
async def start_study_mode(message: Message, state: FSMContext, session: AsyncSession):
    themes = await get_all_themes(session)
    await state.set_state(StudentStudyMode.choosing_theme)
    await state.update_data(mode="study")
    await message.answer("📚 <b>Режим обучения</b>\n\nВыберите тему:", reply_markup=themes_kb(themes))


@router.message(F.text == "📝 Режим тестирования")
async def start_test_mode(message: Message, state: FSMContext, session: AsyncSession):
    themes = await get_all_themes(session)
    await state.set_state(StudentStudyMode.choosing_theme)
    await state.update_data(mode="test")
    await message.answer("📝 <b>Режим тестирования</b>\n\nВыберите тему:", reply_markup=themes_kb(themes))


@router.callback_query(F.data.startswith("theme_"), StudentStudyMode.choosing_theme)
async def theme_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    theme_id = int(callback.data.split("_")[1])
    theme = await get_theme_by_id(session, theme_id)
    data = await state.get_data()
    mode = data.get("mode")

    await state.update_data(theme_id=theme_id, task_count=0)

    if mode == "study":
        theory_text = theme.theory or "📖 Теория по данной теме пока не добавлена."
        await callback.message.answer(theory_text)

        await state.set_state(StudentStudyMode.studying)
        await callback.message.answer(
            "Теория показана. Нажмите «Следующее задание» когда будете готовы.",
            reply_markup=study_menu_kb()
        )

    elif mode == "test":
        await state.set_state(StudentStudyMode.testing)
        user = await get_user_by_telegram_id(session, str(callback.from_user.id))
        await send_next_test_task(callback.message, state, session, user.id, theme_id)

    await callback.answer()


@router.message(F.text == "➡️ Следующее задание", StudentStudyMode.studying)
async def next_study_task(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    theme_id = data.get("theme_id")
    user = await get_user_by_telegram_id(session, str(message.from_user.id))

    task = await get_next_task(session, user.id, theme_id, mode="study")

    if not task:
        await message.answer(
            "🎉 Вы решили все доступные задания по этой теме!",
            reply_markup=mode_selection_kb()
        )
        await state.set_state(StudentStudyMode.choosing_mode)
        return

    await state.update_data(current_task_id=task.id)

    # В режиме обучения показываем картинку + подсказку + правильный ответ
    await message.answer_photo(
        photo=task.image_url,
        caption=(
            f"📌 <b>Задание</b>\n\n"
            f"💡 <b>Подсказка:</b> {task.hint or 'не указана'}\n\n"
            f"✅ <b>Правильный ответ:</b> {task.correct_answer or 'не указан'}\n\n"
            "Сфотографируйте своё решение и отправьте боту."
        )
    )


@router.message(F.text == "⏸ Прервать обучение", StudentStudyMode.studying)
async def pause_study(message: Message, state: FSMContext):
    await state.set_state(StudentStudyMode.choosing_mode)
    await message.answer("⏸ Обучение приостановлено.", reply_markup=mode_selection_kb())


async def send_next_test_task(message: Message, state: FSMContext, session: AsyncSession, user_id: int, theme_id: int):
    data = await state.get_data()
    task_count = data.get("task_count", 0)

    if task_count >= TESTING_LIMIT:
        await message.answer(
            "✅ Тестирование завершено! Все 10 заданий пройдены.",
            reply_markup=mode_selection_kb()
        )
        await state.set_state(StudentStudyMode.choosing_mode)
        return

    task = await get_next_task(session, user_id, theme_id, mode="test")

    if not task:
        await message.answer(
            "Задания по этой теме закончились.",
            reply_markup=mode_selection_kb()
        )
        await state.set_state(StudentStudyMode.choosing_mode)
        return

    await state.update_data(current_task_id=task.id, task_count=task_count + 1)

    # В режиме тестирования — только картинка
    await message.answer_photo(
        photo=task.image_url,
        caption=f"📝 Задание {task_count + 1}/10\n\nОтправьте фото с решением или пропустите.",
        reply_markup=skip_kb()
    )