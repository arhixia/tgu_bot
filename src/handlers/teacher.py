# src/handlers/teacher.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.files.s3_client import get_s3
from src.services.llm_service import generate_task
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
import logging



router = Router()
logger = logging.getLogger(__name__)

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
    theme = await get_theme_by_id(session, data["theme_id"])

    generated = []
    previous_answers = []

    for i in range(count):
        await message.answer(f"⏳ Генерирую задание {i + 1}/{count}...")
        try:
            result = await generate_task(theme.llm_prompt, previous_tasks=previous_answers)
            previous_answers.append(result["correct_answer"])
            generated.append({
                "index": i,
                "image_path": result["image_path"],
                "image_url": None,
                "hint": result["hint"],
                "correct_answer": result["correct_answer"],
                "description": f"Задание #{i + 1} по теме «{data['theme_name']}»",
            })
        except Exception as e:
            await message.answer(f"⚠️ Не удалось сгенерировать задание {i + 1}: {e}")
            continue

    if not generated:
        await message.answer("❌ Не удалось сгенерировать ни одного задания.")
        await state.set_state(TeacherGenerateTask.choosing_count)
        return

    actual_count = len(generated)
    await state.update_data(generated_tasks=generated, count=actual_count)
    await state.set_state(TeacherGenerateTask.reviewing_tasks)

    await message.answer(
        f"✅ Сгенерировано <b>{actual_count}</b> заданий. Просмотрите и одобрите:"
    )

    for task in generated:
        await message.answer_photo(
            photo=FSInputFile(task["image_path"]),
            caption=(
                f"📌 <b>Задание {task['index'] + 1}</b>\n\n"
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
    
    s3 = get_s3()
    with open(task_data["image_path"], "rb") as f:
        image_bytes = f.read()
    s3_key = s3.key_for_task()
    await s3.upload_file(image_bytes, s3_key, content_type="image/png")

    os.remove(task_data["image_path"])

    task_type = TaskType.TRAINING if data["mode"] == "study" else TaskType.TESTING

    await save_task(
        session=session,
        theme_id=data["theme_id"],
        creator_id=user.id,
        task_type=task_type,
        image_url=s3_key,
        description=task_data["description"],
        hint=task_data["hint"],
        correct_answer=task_data["correct_answer"],
    )

    approved_count = data.get("approved_count", 0) + 1
    await state.update_data(approved_count=approved_count)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"✅ Задание {task_index + 1} одобрено и сохранено.")
    await callback.answer()
    await _check_review_complete(callback.message, state)


@router.callback_query(F.data.startswith("treject_"), TeacherGenerateTask.reviewing_tasks)
async def reject_task(callback: CallbackQuery, state: FSMContext):
    task_index = int(callback.data.split("_")[1])
    data = await state.get_data()

    # Удаляем временный файл при отклонении
    task_data = next((t for t in data.get("generated_tasks", []) if t["index"] == task_index), None)
    if task_data and task_data.get("image_path") and os.path.exists(task_data["image_path"]):
        os.remove(task_data["image_path"])

    rejected_count = data.get("rejected_count", 0) + 1
    await state.update_data(rejected_count=rejected_count)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Задание {task_index + 1} отклонено.")
    await callback.answer()

    await _check_review_complete(callback.message, state)


async def _check_review_complete(message: Message, state: FSMContext):
    data = await state.get_data()
    total = data.get("count", 0)
    approved_count = data.get("approved_count", 0)
    rejected_count = data.get("rejected_count", 0)
    
    logger.info(f"_check_review_complete: approved={approved_count}, rejected={rejected_count}, total={total}")
    
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