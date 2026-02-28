# src/handlers/teacher.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.states.teacher_states import TeacherGenerateTask
from src.keyboards.teacher_kb import (
    teacher_main_kb, teacher_mode_kb,
    teacher_count_kb, task_approve_kb, teacher_after_review_kb
)
from src.keyboards.student_kb import themes_kb
from src.services.user_service import get_user_by_telegram_id
from src.services.task_service import get_all_themes, get_theme_by_id, save_task
from src.db.models import TaskType
from aiogram.types import FSInputFile
import os


router = Router()


@router.message(F.text == "➕ Сгенерировать задания")
async def generate_start(message: Message, state: FSMContext, session: AsyncSession):
    themes = await get_all_themes(session)
    await state.set_state(TeacherGenerateTask.choosing_theme)
    await message.answer("Выберите тему для генерации заданий:", reply_markup=themes_kb(themes))


@router.callback_query(F.data.startswith("theme_"), TeacherGenerateTask.choosing_theme)
async def teacher_theme_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    theme_id = int(callback.data.split("_")[1])
    theme = await get_theme_by_id(session, theme_id)
    await state.update_data(theme_id=theme_id, theme_name=theme.name)
    await state.set_state(TeacherGenerateTask.choosing_mode)

    await callback.message.answer(
        f"Тема: <b>{theme.name}</b>\n\nВыберите тип заданий:",
        reply_markup=teacher_mode_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tmode_"), TeacherGenerateTask.choosing_mode)
async def teacher_mode_chosen(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split("_")[1]  
    await state.update_data(mode=mode)
    await state.set_state(TeacherGenerateTask.choosing_count)

    mode_label = "Обучение" if mode == "study" else "Тестирование"
    await callback.message.answer(
        f"Режим: <b>{mode_label}</b>\n\nСколько заданий сгенерировать? (1-10)",
        reply_markup=teacher_count_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tcount_"), TeacherGenerateTask.choosing_count)
async def teacher_count_chosen(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    count = int(callback.data.split("_")[1])
    await state.update_data(count=count, pending_tasks=[], approved_count=0, rejected_count=0)
    await state.set_state(TeacherGenerateTask.generating)

    data = await state.get_data()
    await callback.message.answer(
        f"⏳ Генерирую <b>{count}</b> заданий по теме «{data['theme_name']}»..."
    )
    await callback.answer()

    #генерация пока заглушка
    await _generate_and_send_tasks(callback.message, state, session, count)


async def _generate_and_send_tasks(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    count: int
):
    data = await state.get_data()
    theme_name = data["theme_name"]

    
    test_image_path = os.path.join(os.path.dirname(__file__), "..", "testimage.png")
    test_image_path = os.path.abspath(test_image_path)

    generated = [
        {
            "index": i,
            "image_url": None,
            "description": f"Вычислить интеграл (заглушка #{i + 1}) по теме «{theme_name}»",
            "hint": f"Подсказка к заданию #{i + 1}",
            "correct_answer": f"Ответ к заданию #{i + 1}",
        }
        for i in range(count)
    ]

    await state.update_data(generated_tasks=generated)
    await state.set_state(TeacherGenerateTask.reviewing_tasks)
    await message.answer(
        f"✅ Сгенерировано <b>{count}</b> заданий. Просмотрите каждое и одобрите или отклоните:"
    )

    for task in generated:
        await message.answer_photo(
            photo=FSInputFile(test_image_path),
            caption=(
                f"📌 <b>Задание {task['index'] + 1}</b>\n\n"
                f"📝 {task['description']}\n\n"
                f"💡 Подсказка: {task['hint']}\n"
                f"✅ Ответ: {task['correct_answer']}"
            ),
            reply_markup=task_approve_kb(task["index"])
        )


@router.callback_query(F.data.startswith("tapprove_"), TeacherGenerateTask.reviewing_tasks)
async def approve_task(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    task_index = int(callback.data.split("_")[1])
    data = await state.get_data()
    generated_tasks = data.get("generated_tasks", [])
    user = await get_user_by_telegram_id(session, str(callback.from_user.id))

    task_data = next((t for t in generated_tasks if t["index"] == task_index), None)
    if not task_data:
        await callback.answer("Задание не найдено.")
        return

    task_type = TaskType.TRAINING if data["mode"] == "study" else TaskType.TESTING

    await save_task(
        session=session,
        theme_id=data["theme_id"],
        creator_id=user.id,
        task_type=task_type,
        image_url=task_data["image_url"],
        description=task_data["description"],
        hint=task_data["hint"],
        correct_answer=task_data["correct_answer"],
    )

    approved_count = data.get("approved_count", 0) + 1
    await state.update_data(approved_count=approved_count)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Задание {task_index + 1} одобрено и сохранено в пул.")
    await callback.answer()

    await _check_review_complete(callback.message, state, approved_count)


@router.callback_query(F.data.startswith("treject_"), TeacherGenerateTask.reviewing_tasks)
async def reject_task(callback: CallbackQuery, state: FSMContext):
    task_index = int(callback.data.split("_")[1])
    data = await state.get_data()

    rejected_count = data.get("rejected_count", 0) + 1
    await state.update_data(rejected_count=rejected_count)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Задание {task_index + 1} отклонено.")
    await callback.answer()

    approved_count = data.get("approved_count", 0)
    await _check_review_complete(callback.message, state, approved_count)


async def _check_review_complete(message: Message, state: FSMContext, approved_count: int):
    """проверяем - все ли задания просмотрены, предлагаем продолжить или закончить"""
    data = await state.get_data()
    total = data.get("count", 0)
    rejected_count = data.get("rejected_count", 0)

    if approved_count + rejected_count >= total:
        await message.answer(
            f"📊 Итог: одобрено <b>{approved_count}</b>, отклонено <b>{rejected_count}</b>.\n\n"
            "Хотите сгенерировать ещё задания по этой же теме?",
            reply_markup=teacher_after_review_kb()
        )


@router.callback_query(F.data == "tgenerate_more", TeacherGenerateTask.reviewing_tasks)
async def generate_more(callback: CallbackQuery, state: FSMContext):
    """сгенерировать ещё - возвращаем к выбору количества"""
    await state.set_state(TeacherGenerateTask.choosing_count)
    await callback.message.answer(
        "Сколько ещё заданий сгенерировать?",
        reply_markup=teacher_count_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "tfinish", TeacherGenerateTask.reviewing_tasks)
async def finish_generation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "🏁 Генерация завершена. Задания сохранены в пул.",
        reply_markup=teacher_main_kb()
    )
    await callback.answer()