from aiogram.fsm.state import State, StatesGroup

class TeacherGenerateTask(StatesGroup):
    choosing_theme = State()      # выбор темы
    choosing_mode = State()       # обучение или тест
    choosing_count = State()      # кол-во заданий (1-10)
    reviewing_tasks = State()     # просмотр и одобрение сгенерированных заданий
    generating = State()