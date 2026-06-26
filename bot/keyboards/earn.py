from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def earn_kb(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🚀 Поделиться ссылкой",
        url=f"https://t.me/share/url?url={ref_link}&text=Присоединяйся+к+боту!",
    ))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main"))
    return builder.as_markup()
