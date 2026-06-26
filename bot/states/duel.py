from aiogram.fsm.state import State, StatesGroup


class DuelStates(StatesGroup):
    enter_amount = State()
