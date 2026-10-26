from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.callbacks import DirectionCb, LanguageCb
from data.dictionaries import DIRECTIONS, LANGUAGES


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


def get_directions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for key, title in DIRECTIONS.items():
        builder.button(
            text=title,
            callback_data=DirectionCb(direction=key).pack(),
        )

    builder.adjust(2)

    return builder.as_markup()


def get_languages_keyboard(
        direction: str,
        languages: list[str],
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=LANGUAGES[language],
                    callback_data=LanguageCb(
                        direction=direction,
                        language=language,
                    ).pack(),
                )
            ]
            for language in languages
        ]
    )

    return keyboard