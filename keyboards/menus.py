from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from data.dictionaries import LANGUAGES


find_projects_button = KeyboardButton(text='🚀 Найти проекты')
search_button = KeyboardButton(text='🔎 Поиск')
history_button = KeyboardButton(text='🕘 История')
help_button = KeyboardButton(text='❓ Помощь')

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [find_projects_button, search_button],
        [history_button, help_button],
    ]
)

backend_button = InlineKeyboardButton(
    text='⚙️ Backend',
    callback_data='backend',
)
frontend_button = InlineKeyboardButton(
    text='🎨 Frontend',
    callback_data='frontend'
)
ai_ml_button = InlineKeyboardButton(
    text='🤖 AI / ML',
    callback_data='ai_ml'
)
data_button = InlineKeyboardButton(
    text='📊 Data',
    callback_data='data'
)
dev_ops_button = InlineKeyboardButton(
    text='☁️ DevOps',
    callback_data='dev_ops'
)
mobile_button = InlineKeyboardButton(
    text='📱 Mobile',
    callback_data='mobile'
)
game_dev_button = InlineKeyboardButton(
    text='🎮 Game Development',
    callback_data='game_dev'
)

directions_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [backend_button, frontend_button],
        [ai_ml_button, data_button],
        [dev_ops_button, mobile_button],
        [game_dev_button],
    ]
)


def get_languages_keyboard(
        direction: str,
        languages: list[str],
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text = LANGUAGES[language],
                    callback_data=f'language:{direction}:{language}',
                )
            ]
            for language in languages
        ]
    )

    return keyboard
