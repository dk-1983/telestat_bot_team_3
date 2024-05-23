from pyrogram import Client, enums

from assistants.assistants import check_by_attr, get_user_session, user_bot
from core.db import async_session, engine
from crud.userstg import userstg_crud
from permissions.permissions import check_authorization
from settings import configure_logging

logger = configure_logging()


class ChatUserInfo():
    """Класс для информации о группе/канале"""

    def __init__(
        self,
        bot: Client,
        group_name: str,
        username: str = None
    ):
        self.bot = bot
        self.group_name = group_name
        self.username = username

    async def get_chat(self):
        """Получать объект канала/группы"""
        return await self.bot.get_chat(self.group_name)

    async def get_chat_users(self):
        """Метод получения списка подписчиков канала/группы"""
        subsribers = []
        for i in '0123456789_qwertyuiopasdfghjklzxcvbnm':
            async for subscriber in self.bot.get_chat_members(self.group_name, filter=enums.ChatMembersFilter.SEARCH, query=i):
                if subscriber not in subsribers:
                    subsribers.append(subscriber)
        return subsribers

    async def get_chat_members_count(self):
        """Метод получения количества подписчиков канала"""
        members_count = await self.bot.get_chat_members_count(self.group_name)
        logger.info(
            f'@{self.group_name} количество подписчиков: {members_count}'
        )
        return await self.bot.get_chat_members_count(self.group_name)

    async def get_info_chat_user(self):
        """"Метод получает информацию о конкретном подписчике чата"""
        chat_member = await self.bot.get_chat_member(
            self.group_name, self.username
        )
        logger.info(f'Информация об {chat_member.user.username} получена')
        return chat_member

    async def create_report(self):
        """Формирует словарь, в котором вся информация о подписчиках"""
        report_data = {}
        report_data[self.group_name] = {}
        report_data[self.group_name]['Активности'] = await self.get_activity()
        users_info = []
        for user in await self.get_chat_users():
            full_user_info = {}
            full_user_info['ID'] = user.user.id
            full_user_info['Username'] = user.user.username
            full_user_info['Имя'] = user.user.first_name
            full_user_info['Язык пользователя'] = user.user.language_code
            try:
                full_user_info[
                    'Дата вступления'
                ] = user.joined_date.strftime('%d-%m-%Y %H:%M:%S')
            except AttributeError:
                full_user_info['Дата вступления'] = 'Отсутствует для владельца'
            full_user_info['Статус подписчика'] = user.status.name
            full_user_info['Это бот ?'] = 'Да' if user.user.is_bot else 'Нет'
            try:
                full_user_info['Фото'] = user.user.photo.big_file_id
            except AttributeError:
                full_user_info['Фото'] = 'Фото отсутствует'
            users_info.append(full_user_info)
        report_data[self.group_name]['Подписчики'] = users_info
        logger.info('Информация по каждому подписчику собрана')
        return report_data

    @get_user_session
    async def get_chat_messages(self):
        """Возвращает последние 200 сообщений"""
        last_messages = []
        async for message in user_bot.get_chat_history(self.group_name):
            last_messages.append(message)
        logger.info(
            f'Получены последние 200 сообщений из группы {self.group_name}'
        )
        return last_messages

    async def get_activity(self):
        """Возвращает среднее количество просмотров/реакций/репостов"""
        reactions = []
        views = []
        forwards = []
        for activity in await self.get_chat_messages():
            if activity.reactions:
                for reaction in activity.reactions.reactions:
                    try:
                        if reaction.count:
                            reactions.append(reaction.count)
                    except AttributeError:
                        pass
            try:
                if activity.forwards:
                    forwards.append(activity.forwards)
            except AttributeError:
                pass
            try:
                if activity.views:
                    views.append(activity.views)
            except AttributeError:
                pass
        data = {
            'views': views,
            'reactions': reactions,
            'forwards': forwards,
            'avg': {
                'views': 0,
                'reactions': 0,
                'forwards': 0,
            }
        }
        for key, item in data.items():
            if key == 'avg':
                continue
            if len(item) > 0:
                data['avg'][key] = round(
                    sum(item) / len(item)
                )
        avg_results = {
            'Среднее количество просмотров': data['avg']['views'],
            'Среднее количество реакций': data['avg']['reactions'],
            'Среднее количество репостов': data['avg']['forwards']
        }
        print(avg_results)
        return avg_results


@get_user_session
async def get_channels(
    client: Client = user_bot
):
    """Получение телеграмм каналов."""

    channels = []
    async for dialog in client.get_dialogs():
        if dialog.chat.username and dialog.chat.title:
            channels.append(dialog)
    return channels


async def add_users(user_id: int,
                    users: list[dict] = None,
                    is_superuser: bool = False,
                    is_admin: bool = True,
                    is_active: bool = True
                    ):
    """Добавление пользователей в ДБ."""

    if (not await check_authorization(
            user_id,
            is_superuser=True
            ) or users is None):
        return False

    for user in users:
        async with async_session() as session:
            async with engine.connect():
                if await check_by_attr(
                        'user_id',
                        user['user_id'],
                        session
                        ):
                    return False

    users = [{
        'user_id': user['user_id'],
        'username': user['username'],
        'is_superuser': is_superuser,
        'is_admin': is_admin,
        'is_active': is_active
        } for user in users]

    db = ''
    async with async_session() as session:
        async with engine.connect():
            for user in users:
                db += (await userstg_crud.create(user, session)).username
                print(db)
    return db


async def update_users(
        user_id: int,
        users: list[dict] = None,
        is_superuser: bool = False,
        is_admin: bool = True,
        is_active: bool = False
        ):
    """Обновление данных о пользователях в ДБ."""

    if (not await check_authorization(
            user_id,
            is_superuser=True
            ) or users is None):
        return False

    for user in users:
        async with async_session() as session:
            async with engine.connect():
                if not await check_by_attr(
                        'user_id',
                        user['user_id'],
                        session
                        ):
                    return False

    users = [{
        'user_id': user['user_id'],
        'username': user['username'],
        'is_superuser': is_superuser,
        'is_admin': is_admin,
        'is_active': is_active
        } for user in users]

    db = 0
    async with async_session() as session:
        async with engine.connect():
            for user in users:
                db += (await userstg_crud.set_update(
                                            'user_id',
                                            user['user_id'],
                                            user,
                                            session)).rowcount
    return db


async def del_users():
    """Удаление пользователя из ДБ."""
    pass


async def set_settings_for_report(
    settings: dict,
    crud_name
):
    """
    Сохраняет установленные настройки для формирования отчёта
    один пользователь много каналов.
    """
    if not settings:
        return False

    async with async_session() as session:
        async with engine.connect():
            return await crud_name.create(settings, session)


async def get_settings_from_report(
        settings: dict
):
    """Получение настроек для управления ботом."""

    if not settings:
        return False

    async with engine.connect() as session:
        return (await (settings['crud_name']).get_settings_report(
            settings,
            session))


async def delete_settings_report(
        attr_name,
        attr_value,
        crud_name
):
    """Удаление записи из базы данных по окончании рекурсии."""

    if not attr_name or not attr_value:
        return False

    async with async_session() as session:
        async with engine.connect():
            return (await crud_name.remove(
                attr_name,
                attr_value,
                session))
