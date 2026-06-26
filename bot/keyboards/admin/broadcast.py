from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def broadcast_preview_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить всем", callback_data="admin:broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:main"),
    )
    return builder.as_markup()


def broadcast_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:main"),
    ]])
