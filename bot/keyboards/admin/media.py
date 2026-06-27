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

VIDEO_LABELS = {
    "case_1_video": "🥉 Кейс Бронза",
    "case_3_video": "🥈 Кейс Серебро",
    "case_5_video": "🥇 Кейс Золото",
    "wheel_video_50x": "🎰 Колесо: Джекпот (50x)",
    "wheel_video_01x": "🎰 Колесо: Проигрыш (0.1x)",
}


def media_list_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in KEY_LABELS.items():
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin:media_edit:{key}"))
    builder.row(InlineKeyboardButton(text="🎬 Видео", callback_data="admin:video_list"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main"))
    return builder.as_markup()


def video_list_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in VIDEO_LABELS.items():
        builder.row(InlineKeyboardButton(text=label, callback_data=f"admin:video_upload:{key}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin:media"))
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
