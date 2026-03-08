# src/handlers/student.py

from aiogram import Bot, Router, F
from aiogram.types import KeyboardButton, Message, CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.files.s3_client import get_s3
from src.db.models import AnswerStatus
from src.states.student_states import StudentStudyMode
from src.keyboards.student_kb import confirm_show_answer_kb, mode_selection_kb, study_after_hint_kb, study_menu_kb, study_waiting_photo_kb, study_wrong_first_kb, study_wrong_second_kb, study_wrong_third_kb, themes_kb, skip_kb
from src.services.user_service import get_user_by_telegram_id
from src.services.task_service import get_all_themes, get_task_by_id, get_test_results, get_theme_by_id,get_next_task, save_answer
from src.services.llm_service import check_answer
from aiogram.types import FSInputFile
import os



router = Router()

TESTING_LIMIT = 10


# МОК ПИКЧА К ЗАДАНИЮ ЗАМЕНИТЬ ПОТОМ
TEST_IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "testimage.png"))

async def get_photo_url(image_url: str | None) -> str | FSInputFile:
    """Возвращает presigned URL из S3 или заглушку"""
    if image_url:
        s3 = get_s3()
        return await s3.get_presigned_url(image_url, expires=3600)
    return FSInputFile(TEST_IMAGE_PATH)


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
        
        await callback.message.answer(
            "📝 Тестирование начинается!",
            reply_markup=ReplyKeyboardRemove()  
        )
        
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

    await state.update_data(
        current_task_id=task.id,
        wrong_attempts=0,
        hint_used=False,
        last_answer_key=None
    )
    await state.set_state(StudentStudyMode.studying_waiting_photo)

    await message.answer_photo(
        photo=await get_photo_url(task.image_url),
        caption=(
            "📌 <b>Задание</b>\n\n"
            "⚠️ У вас <b>3 попытки</b> на это задание.\n\n"
            "Сфотографируйте ответ и отправьте боту."
        ),
        reply_markup=study_menu_kb()
    )


@router.message(F.text == "⏸ Прервать обучение", StudentStudyMode.studying)
async def pause_study(message: Message, state: FSMContext):
    await state.set_state(StudentStudyMode.choosing_mode)
    await message.answer("⏸ Обучение приостановлено.", reply_markup=mode_selection_kb())


@router.message(F.text == "⏸ Прервать обучение", StudentStudyMode.studying_waiting_photo)
async def pause_study_waiting(message: Message, state: FSMContext):
    await state.set_state(StudentStudyMode.choosing_mode)
    await message.answer("⏸ Обучение приостановлено.", reply_markup=mode_selection_kb())


@router.message(F.text == "➡️ Следующее задание", StudentStudyMode.studying_waiting_photo)
async def skip_from_waiting_photo(message: Message, state: FSMContext, session: AsyncSession):
    """Студент пропускает задание не отправив ответ"""
    data = await state.get_data()
    current_task_id = data.get("current_task_id")

    if current_task_id:
        user = await get_user_by_telegram_id(session, str(message.from_user.id))
        await save_answer(
            session=session,
            student_id=user.id,
            task_id=current_task_id,
            status=AnswerStatus.SKIPPED,
            student_response_image=None,
            llm_verdict="Студент пропустил задание без ответа"
        )

    await state.update_data(current_task_id=None, wrong_attempts=0, hint_used=False, last_answer_key=None)
    await state.set_state(StudentStudyMode.studying)
    await next_study_task(message, state, session)
    

async def send_next_test_task(message: Message, state: FSMContext, session: AsyncSession, user_id: int, theme_id: int):
    data = await state.get_data()
    task_count = data.get("task_count", 0)

    if task_count >= TESTING_LIMIT:
        stats = await get_test_results(session, user_id, theme_id)
        await message.answer(
            "✅ <b>Тестирование завершено!</b>\n\n"
            f"📊 Выполнено заданий: <b>{stats['total']}</b>\n"
            f"✅ Правильно: <b>{stats['correct']}</b>\n"
            f"❌ Неправильно: <b>{stats['incorrect']}</b>\n"
            f"⏭ Пропущено: <b>{stats['skipped']}</b>",
            reply_markup=mode_selection_kb()
        )
        await state.set_state(StudentStudyMode.choosing_mode)
        return

    task = await get_next_task(session, user_id, theme_id, mode="test")

    if not task:
        stats = await get_test_results(session, user_id, theme_id)
        await message.answer(
            "📭 Задания по этой теме закончились.\n\n"
            f"📊 Выполнено заданий: <b>{stats['total']}</b>\n"
            f"✅ Правильно: <b>{stats['correct']}</b>\n"
            f"❌ Неправильно: <b>{stats['incorrect']}</b>\n"
            f"⏭ Пропущено: <b>{stats['skipped']}</b>",
            reply_markup=mode_selection_kb()
        )
        await state.set_state(StudentStudyMode.choosing_mode)
        return

    await state.update_data(current_task_id=task.id, task_count=task_count + 1)

    await message.answer_photo(
        photo=await get_photo_url(task.image_url),
        caption=f"📝 Задание {task_count + 1}/10\n\nОтправьте фото с ответом или пропустите.",
        reply_markup=skip_kb()
    )
    

@router.message(F.photo, StudentStudyMode.studying_waiting_photo)
async def handle_study_answer(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    wrong_attempts = data.get("wrong_attempts", 0)
    hint_used = data.get("hint_used", False)

    user = await get_user_by_telegram_id(session, str(message.from_user.id))
    task = await get_task_by_id(session, current_task_id)

    bot_file = await bot.get_file(message.photo[-1].file_id)
    downloaded = await bot.download_file(bot_file.file_path)
    image_bytes = downloaded.read()

    await message.answer("🔍 Проверяю ответ...")
    result = await check_answer(
        correct_answer=task.correct_answer,
        student_image_bytes=image_bytes,
    )

    if result.get("unreadable"):
        await message.answer(
            "📷 Не могу разобрать что написано на фото.\n\n"
            "Пожалуйста, сфотографируйте ответ чётче и отправьте ещё раз.",
            reply_markup=study_waiting_photo_kb()
        )
        return

    s3 = get_s3()
    key = s3.key_for_answer(user.id, current_task_id)
    await s3.upload_file(image_bytes, key, content_type="image/jpeg")

    is_correct = result.get("correct", False)
    comment = result.get("comment", "")

    if is_correct:
        await save_answer(
            session=session,
            student_id=user.id,
            task_id=current_task_id,
            status=AnswerStatus.CORRECT,
            student_response_image=key,
            llm_verdict=comment
        )
        await state.update_data(current_task_id=None, wrong_attempts=0, hint_used=False)
        await state.set_state(StudentStudyMode.studying)
        await message.answer(
            f"🎉 Правильно! {comment}\n\nВыберите действие:",
            reply_markup=study_menu_kb()
        )
    else:
        wrong_attempts += 1
        await state.update_data(wrong_attempts=wrong_attempts, last_answer_key=key)
        await state.set_state(StudentStudyMode.studying)

        error_text = f"❌ Неверно. {comment}\n\n"

        if wrong_attempts == 1:
            await message.answer(
                error_text + "Нажмите <b>«🔄 Попробовать ещё раз»</b> чтобы отправить новое фото.",
                reply_markup=study_wrong_first_kb()
            )
        elif wrong_attempts == 2:
            await message.answer(
                error_text + "Нажмите <b>«🔄 Попробовать ещё раз»</b> чтобы отправить новое фото.",
                reply_markup=study_wrong_second_kb(hint_used=hint_used)
            )
        else:
            await message.answer(
                error_text + "Попытки исчерпаны.",
                reply_markup=study_wrong_third_kb()
            )


@router.message(F.photo, StudentStudyMode.studying)
async def ignore_photo_studying(message: Message, state: FSMContext):
    data = await state.get_data()
    wrong_attempts = data.get("wrong_attempts", 0)

    if wrong_attempts == 0:
        await message.answer(
            "Нажмите <b>«➡️ Следующее задание»</b> чтобы получить задание."
        )
    else:
        await message.answer(
            "Нажмите <b>«🔄 Попробовать ещё раз»</b> чтобы отправить новый ответ."
        )


# Обработка фото от студента в режиме ТЕСТИРОВАНИЯ
@router.message(F.photo, StudentStudyMode.testing) #поменять при проверке 
async def handle_test_answer(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    theme_id = data.get("theme_id")

    if not current_task_id:
        return

    user = await get_user_by_telegram_id(session, str(message.from_user.id))

    s3 = get_s3()
    bot_file = await bot.get_file(message.photo[-1].file_id)
    downloaded = await bot.download_file(bot_file.file_path)
    key = s3.key_for_answer(user.id, current_task_id)
    await s3.upload_file(downloaded.read(), key, content_type="image/jpeg")

    # МОК: любое фото = правильный ответ
    await save_answer(
        session=session,
        student_id=user.id,
        task_id=current_task_id,
        status=AnswerStatus.CORRECT,
        student_response_image=key,  
        llm_verdict="Мок: засчитано автоматически"
    )

    await state.update_data(current_task_id=None)
    await send_next_test_task(message, state, session, user.id, theme_id)


# пропуск задания в режиме ТЕСТИРОВАНИЯ
@router.callback_query(F.data == "skip_test", StudentStudyMode.testing)
async def skip_test_task(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    theme_id = data.get("theme_id")

    user = await get_user_by_telegram_id(session, str(callback.from_user.id))

    if current_task_id:
        await save_answer(
            session=session,
            student_id=user.id,
            task_id=current_task_id,
            status=AnswerStatus.SKIPPED,
            student_response_image=None,
            llm_verdict=None
        )

    await state.update_data(current_task_id=None)
    await callback.answer()
    await send_next_test_task(callback.message, state, session, user.id, theme_id)


#показываем подсказку 
@router.message(F.text == "💡 Подсказка", StudentStudyMode.studying)
async def show_hint(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    if not current_task_id:
        return

    task = await get_task_by_id(session, current_task_id)
    await message.answer(f"💡 <b>Подсказка:</b>\n\n{task.hint or 'Подсказка не указана'}")

    await state.update_data(hint_used=True)
    await message.answer(
        "Нажмите <b>«🔄 Попробовать ещё раз»</b> чтобы отправить новый ответ:",
        reply_markup=study_after_hint_kb()
    )


@router.message(F.text == "🔄 Попробовать ещё раз", StudentStudyMode.studying)
async def retry_task(message: Message, state: FSMContext):
    await state.set_state(StudentStudyMode.studying_waiting_photo)
    await message.answer("📸 Отправьте фото с новым ответом.", reply_markup=study_waiting_photo_kb())


@router.message(F.text == "✅ Просмотреть правильный ответ", StudentStudyMode.studying)
async def confirm_show_answer(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    wrong_attempts = data.get("wrong_attempts", 0)

    if wrong_attempts >= 3:
        #попытки исчерпаны
        current_task_id = data.get("current_task_id")
        last_answer_key = data.get("last_answer_key")

        user = await get_user_by_telegram_id(session, str(message.from_user.id))
        task = await get_task_by_id(session, current_task_id)

        await save_answer(
            session=session,
            student_id=user.id,
            task_id=current_task_id,
            status=AnswerStatus.INCORRECT,
            student_response_image=last_answer_key,
            llm_verdict="Попытки исчерпаны"
        )

        await message.answer(
            f"✅ <b>Правильный ответ:</b>\n\n{task.correct_answer or 'не указан'}"
        )
        await state.update_data(current_task_id=None, wrong_attempts=0, hint_used=False, last_answer_key=None)
        await state.set_state(StudentStudyMode.studying)
        await message.answer("Выберите действие:", reply_markup=study_menu_kb())
    else:
        #попытки есть
        await message.answer(
            "⚠️ <b>Внимание!</b>\n\n"
            "После просмотра правильного ответа это задание будет засчитано как невыполненное "
            "и больше не будет доступно.\n\n"
            "Вы уверены?",
            reply_markup=confirm_show_answer_kb()
        )


@router.callback_query(F.data == "confirm_answer_yes", StudentStudyMode.studying)
async def show_correct_answer(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    last_answer_key = data.get("last_answer_key")

    user = await get_user_by_telegram_id(session, str(callback.from_user.id))
    task = await get_task_by_id(session, current_task_id)

    await save_answer(
        session=session,
        student_id=user.id,
        task_id=current_task_id,
        status=AnswerStatus.INCORRECT,
        student_response_image=last_answer_key,
        llm_verdict="Студент просмотрел правильный ответ"
    )

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"✅ <b>Правильный ответ:</b>\n\n{task.correct_answer or 'не указан'}"
    )
    await state.update_data(current_task_id=None, wrong_attempts=0, hint_used=False, last_answer_key=None)
    await state.set_state(StudentStudyMode.studying)
    await callback.message.answer("Выберите действие:", reply_markup=study_menu_kb())
    await callback.answer()


#не показывать ответ 
@router.callback_query(F.data == "confirm_answer_no", StudentStudyMode.studying)
async def cancel_show_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    hint_used = data.get("hint_used", False)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Хорошо, продолжайте решать.",
        reply_markup=study_wrong_second_kb(hint_used=hint_used)
    )
    await callback.answer()


# следующее задание из состояния неправильного ответа
@router.message(F.text == "➡️ Следующее задание", StudentStudyMode.studying)
async def next_from_wrong(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    current_task_id = data.get("current_task_id")
    last_answer_key = data.get("last_answer_key")

    if current_task_id:
        user = await get_user_by_telegram_id(session, str(message.from_user.id))
        await save_answer(
            session=session,
            student_id=user.id,
            task_id=current_task_id,
            status=AnswerStatus.SKIPPED,
            student_response_image=last_answer_key,
            llm_verdict="Студент пропустил задание"
        )

    await state.update_data(current_task_id=None, wrong_attempts=0, hint_used=False, last_answer_key=None)
    await next_study_task(message, state, session)


