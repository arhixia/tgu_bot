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
    """меню во время обучения — базовое"""
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

def study_after_hint_kb() -> ReplyKeyboardMarkup:
    """после нажатия подсказки — только retry и след задание"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Попробовать ещё раз")],
            [KeyboardButton(text="➡️ Следующее задание")],
        ],
        resize_keyboard=True
    )

def study_wrong_first_kb() -> ReplyKeyboardMarkup:
    """после первого неправильного ответа - с подсказкой"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💡 Подсказка")],
            [KeyboardButton(text="🔄 Попробовать ещё раз")],
            [KeyboardButton(text="➡️ Следующее задание")],
        ],
        resize_keyboard=True
    )

def study_wrong_second_kb(hint_used: bool) -> ReplyKeyboardMarkup:
    """после второго неправильного ответа"""
    keyboard = []
    if not hint_used:
        keyboard.append([KeyboardButton(text="💡 Подсказка")])
    keyboard.append([KeyboardButton(text="✅ Просмотреть правильный ответ")])
    keyboard.append([KeyboardButton(text="🔄 Попробовать ещё раз")])
    keyboard.append([KeyboardButton(text="➡️ Следующее задание")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def study_wrong_third_kb() -> ReplyKeyboardMarkup:
    """после третьего неправильного ответа - только ответ и след задание"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Просмотреть правильный ответ")],
            [KeyboardButton(text="➡️ Следующее задание")],
        ],
        resize_keyboard=True
    )

def confirm_show_answer_kb() -> InlineKeyboardMarkup:
    """подтверждение показа правильного ответа"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, показать", callback_data="confirm_answer_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="confirm_answer_no"),
        ]
    ])


def study_waiting_photo_kb() -> ReplyKeyboardMarkup:
    """ожидаем фото — только прервать"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏸ Прервать обучение")]],
        resize_keyboard=True
    )