from aiogram.fsm.state import State, StatesGroup


class WithdrawStates(StatesGroup):
    enter_captcha = State()
