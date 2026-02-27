from aiogram.types import ReplyKeyboardMarkup,KeyboardButton,InlineKeyboardMarkup,InlineKeyboardButton


def mode_selection_kb() -> ReplyKeyboardMarkup:
    """выборка студента"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Режим обучения")],
            [KeyboardButton(text="📝 Режим тестирования")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def study_menu_kb() -> ReplyKeyboardMarkup:
    """меню во время обучения"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➡️ Следующее задание")],
            [KeyboardButton(text="⏸ Прервать обучение")],
        ],
        resize_keyboard=True
    )


def answer_options_kb() -> InlineKeyboardMarkup:
    """кнопки после неправильного ответа в режиме обучения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Подсказка", callback_data="hint")],
        [InlineKeyboardButton(text="🔄 Попробовать ещё раз", callback_data="retry")],
        [InlineKeyboardButton(text="⏭ Пропустить задание", callback_data="skip")],
    ])


def skip_kb() -> InlineKeyboardMarkup:
    """кнопка пропуска в режиме тестирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_test")],
    ])

def themes_kb(themes: list) -> InlineKeyboardMarkup:
    """клавиатура выбора темы -  темы берём из БД"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=theme.name, callback_data=f"theme_{theme.id}")]
        for theme in themes
    ])