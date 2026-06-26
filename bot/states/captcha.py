from aiogram.fsm.state import State, StatesGroup


class CaptchaStates(StatesGroup):
    waiting = State()
