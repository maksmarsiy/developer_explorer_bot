from aiogram.filters.callback_data import CallbackData


class DirectionCb(CallbackData, prefix='direction'):
    direction: str


class LanguageCb(CallbackData, prefix='lang'):
    direction: str
    language: str


class RetrySearchCb(CallbackData, prefix='retry'):
    search_type: str
    direction: str = ''
    language: str = ''
    version: int = 0
