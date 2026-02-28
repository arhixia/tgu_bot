# src/keyboards/teacher_kb.py

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def teacher_main_kb() -> ReplyKeyboardMarkup:
    """главное меню преподавателя"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Сгенерировать задания")],
        ],
        resize_keyboard=True
    )


def teacher_mode_kb() -> InlineKeyboardMarkup:
    """выбор режима задания: обучение или тест"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Обучение", callback_data="tmode_study")],
        [InlineKeyboardButton(text="📝 Тестирование", callback_data="tmode_test")],
    ])


def teacher_count_kb() -> InlineKeyboardMarkup:
    """выбор количества заданий 1-10"""
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"tcount_{i}")
        for i in range(1, 11)
    ]
    rows = [buttons[:5], buttons[5:]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_approve_kb(task_index: int) -> InlineKeyboardMarkup:
    """кнопки одобрения/отклонения под каждым заданием"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"tapprove_{task_index}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"treject_{task_index}"),
        ]
    ])

def teacher_after_review_kb() -> InlineKeyboardMarkup:
    """после просмотра всей пачки — сгенерировать ещё или закончить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Сгенерировать ещё", callback_data="tgenerate_more")],
        [InlineKeyboardButton(text="🏁 Завершить", callback_data="tfinish")],
    ])