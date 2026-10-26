from aiogram.filters.callback_data import CallbackData


class DirectionCb(CallbackData, prefix='direction'):
    direction: str


class LanguageCb(CallbackData, prefix='lang'):
    direction: str
    language: str