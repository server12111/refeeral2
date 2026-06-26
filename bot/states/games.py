from aiogram.fsm.state import State, StatesGroup


class GameStates(StatesGroup):
    enter_bet = State()
    choose_dice_side = State()
    choose_football_side = State()
    choose_basketball_side = State()
    choose_bowling_side = State()
    choose_darts_side = State()


class WheelStates(StatesGroup):
    entering_bet = State()


class MinesStates(StatesGroup):
    choose_bet = State()
    choose_mines = State()
    playing = State()


class TowerStates(StatesGroup):
    choose_bet = State()
    playing = State()


class AuctionStates(StatesGroup):
    enter_custom_bid = State()
