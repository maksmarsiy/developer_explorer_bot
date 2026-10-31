from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.callbacks import DirectionCb, LanguageCb, RetrySearchCb
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

    builder.row(
        InlineKeyboardButton(
            text='🏠 Главное меню',
            callback_data='back_to_main',
        )
    )

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

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text='⬅️ Назад к направлениям',
                callback_data='back_to_directions',
            )
        ]
    )

    keyboard.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text='🏠 Главное меню',
                callback_data='back_to_main',
            )
        ]
    )

    return keyboard


def get_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='🏠 Главное меню',
                    callback_data='back_to_main',
                )
            ]
        ]
    )


def get_results_keyboard(
        search_type: str,
        direction: str = '',
        language: str = '',
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='🔄 Искать ещё',
                    callback_data=RetrySearchCb(
                        search_type=search_type,
                        direction=direction,
                        language=language,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text='🏠 Главное меню',
                    callback_data='back_to_main',
                )
            ],
        ]
    )