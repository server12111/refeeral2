from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

KEY_LABELS = {
    "welcome": "👋 Приветствие",
    "main_menu": "🏠 Главное меню",
    "earn": "💸 Заработать",
    "withdraw": "⭐ Вывод",
    "bonus": "🎁 Бонус",
    "tasks": "📋 Задания",
    "games": "🎮 Игры",
    "profile": "👤 Профиль",
    "top": "🏆 Топ",
}


def media_list_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in KEY_LABELS.items():
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin:media_edit:{key}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"))
    return builder.as_markup()


def media_edit_kb(key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"admin:media_text:{key}"),
        InlineKeyboardButton(text="🖼 Изменить фото", callback_data=f"admin:media_photo:{key}"),
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:media"))
    return builder.as_markup()


def media_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:media"),
    ]])
