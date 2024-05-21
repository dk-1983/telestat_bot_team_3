import os
import glob
import asyncio
import argparse

from pyrogram import Client
from settings import Config, logger

from crud.userstg import userstg_crud
from core.db import async_session, engine


API_ID = Config.API_ID
API_HASH = Config.API_HASH


async def register_sessions():
    """
    Функция создания сессии подключения к telegram.

    Возвращает username созданной сессии.
    """

    if not API_ID or not API_HASH:
        raise ValueError("API_ID или API_HASH не найдены в файле .env")

    session_name = input('\nВведите имя сессии (нажмите Enter после ввода): ')

    if not session_name:
        return None

    if not os.path.isdir('sessions'):
        os.mkdir('sessions')

    session = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        workdir="sessions/"
    )

    async with session:
        user_data = await session.get_me()

    logger.success(
        f'Сессия успешно добавлена @{user_data.username} | '
        f'{user_data.first_name} {user_data.last_name}')

    return session_name


async def get_username_from_session_name(session_name):
    """
    Функция получения username из сохраненной сессии.
    Принимает обязательным аргументом имя сессии session_name.
    """

    session = Client(session_name)

    async with session:
        user_data = await session.get_me()
    return user_data.username


async def get_session_name():
    """Функция проверяет наличие файла сессии, возвращает имя сессии."""

    file = glob.glob('/sessions/*.session')

    if not file:
        session_name = None
    else:
        session_name = os.path.splitext(os.path.basename(file[0]))[0]
        logger.debug(f'Сессия уже создана: {session_name}')
    return session_name


async def get_superuser():
    """
    Функция получения суперюзера из базы данных.

    Возвращает username суперюзера.
    Если суперюзера в базе нет, то возвращает None.
    """

    async with engine.connect() as session:
        superuser = await userstg_crud.get_by_attr(
            attr_name='is_superuser',
            attr_value=True,
            session=session
        )
    return superuser


async def create_superuser(username=None):
    """
    Функция создания суперюзера.

    Функция ждет ввода username телеграмма для регистрации его в качестве
    суперюзера.
    """

    if not username:
        username = input('Введите username телеграм без символа @: ')
        if username.startswith('@'):
            username.strip('@')

    user = {
        'username': username,
        'is_superuser': True,
        'is_active': True,
        'is_admin': True,
    }
    async with async_session() as session:
        async with engine.connect():
            await userstg_crud.create(user, session=session)


async def run_initialization():
    """
    Основная логика процесса инициализации.

    Проверяется наличие файла сессии в проекте.
    Проверяется наличие суперпользователя в базе данных.
    При необходимости запускается процесс создания сессии подключения телеграм
    и добавление пользователя в качестве суперпользователя.
    """

    logger.debug('Запуск инициализатора')
    session_name = await get_session_name()
    if not session_name:
        session_name = await register_sessions()
    username = await get_username_from_session_name(session_name)
    logger.debug(f'Cессия: {session_name}, username: {username}')
    superuser = await get_superuser()
    if not superuser:
        logger.debug('Создание суперюзера')
        await create_superuser(username)
        logger.debug(f'Суперюзер {username} успешно создан')
    logger.debug('Работа инициализатора окончена')


async def init_process() -> None:
    """Функция назначения и проверки аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Бот для сбора аналитики')
    parser.add_argument(
        '-i', '--init',
        action='store_true',
        help='initial launch'
    )

    args = parser.parse_args()

    if args.init:
        await run_initialization()
