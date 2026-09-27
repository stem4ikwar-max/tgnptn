from aiogram.fsm.state import State, StatesGroup


class DialogStates(StatesGroup):
    ai_chat = State()  # пользователь находится в режиме "Задать вопрос"
