from aiogram.fsm.state import State, StatesGroup


class PromoStates(StatesGroup):
    enter_code = State()
