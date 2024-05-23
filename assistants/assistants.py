from functools import wraps

from pyrogram import Client
from pyrogram.errors.exceptions.bad_request_400 import ReplyMarkupInvalid
from pyrogram.types import KeyboardButton, ReplyKeyboardMarkup

from crud.userstg import userstg_crud
from settings import Config, logger

user_bot = Client(
    Config.USER_ACCOUNT_NAME,
    api_hash=Config.API_HASH,
    api_id=Config.API_ID,
    phone_number=Config.PHONE_NUMBER
)


class DotNotationDict(dict):
    """
    Класс добавления магических атрибутов к словарю.
    """

    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


async def check_by_attr(attr_name, attr_value, session) -> bool:
    """Проверка id на наличие в ДБ."""

    if await userstg_crud.get_by_attr(
            attr_name,
            attr_value,
            session
            ) is None:
        return False
    return True


def dinamic_keyboard(objs, attr_name, keyboard_row=2):
    """
    Динамическая клавиатура для вывода в телеграм.
    objs: list[dict] - итерируемый объект или объекты ,
    attr_name - атрибут который из текущего объекта будет
        отображаться в виде названия кнопки,
    ceyboard_row - пределитель колличества кнопок на одну строку.
    """
    logger.info('Процесс построения динамической клавиатуры запущен!')
    try:
        if not objs or objs is None:
            raise TypeError
    except TypeError:
        logger.error('Проверьте входной объект objs он пуст или None')
        return False
    btn_row = []
    btn_many = []
    counter = keyboard_row
    for obj in objs:
        try:
            if not hasattr(obj, attr_name):
                raise KeyError
        except KeyError:
            logger.error('Отсутствует ключ: attr_name')
            return False
        counter -= 1
        btn_row.append(KeyboardButton(
            text=getattr(obj, attr_name))
            )
        if counter == 0:
            counter = keyboard_row
            btn_many.append(btn_row)
            btn_row = []

    try:
        if not btn_many:
            keyboard = ReplyKeyboardMarkup(keyboard=[
                btn_row
            ], resize_keyboard=True)
        else:
            if btn_row:
                btn_many.append(btn_row)
            keyboard = ReplyKeyboardMarkup(
                keyboard=btn_many,
                resize_keyboard=True)
    except ReplyMarkupInvalid as e:
        logger.error(f'Ошибка клавиатуры:\n {e}')
        return False
    logger.info('Динамическая клавиатура сформирована успешно.')
    return keyboard


def get_user_session(func):
    """Пользовательская сессия от имени человека."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await user_bot.start()
        logger.info('Открыта сессия от имени пользователя.')
        try:
            result = await func(*args, **kwargs)
            logger.info('Данные получены')
            return result
        finally:
            await user_bot.stop()
            logger.info('Сессия от имени пользователя закрыта.')
    return wrapper
