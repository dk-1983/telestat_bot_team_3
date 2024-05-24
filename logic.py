import os
from typing import Literal

from pyrogram.errors.exceptions.bad_request_400 import (ChatAdminRequired,
                                                        UsernameInvalid,
                                                        UsernameNotOccupied,
                                                        UserNotParticipant)
from pyrogram.errors.exceptions.flood_420 import FloodWait
from pyrogram.types import ReplyKeyboardRemove

from assistants.assistants import dinamic_keyboard
from buttons import bot_keys
from core.db import engine
from crud.channel_settings import channel_settings_crud
from crud.report import report_crud
from crud.report_settings import report_settings_crud
from services.google_api_service import (get_data_for_shedule,
                                         get_one_spreadsheet, get_report)
from services.sheduling import build_shedule
from services.telegram_service import (ChatUserInfo, add_users, get_channels,
                                       set_settings_for_report, update_users)
from settings import Config, configure_logging

logger = configure_logging()


async def manage_admin(client, message, act: Literal['add', 'del']):
    action = {
        'add': {
            't1': 'Добавляются',
            'msg_str': 'добавлении',
            'done_msg_str': 'добавлены',
        },
        'del': {
            't1': 'Удаляются',
            'msg_str': 'удалении',
            'done_msg_str': 'удалены',
        },
    }
    cur_msg_str = action[act]['msg_str']
    cur_t1 = action[act]['t1']
    cur_done = action[act]['done_msg_str']

    try:
        incom_users = await client.get_users(message.text.split(', '))
    except UsernameInvalid as error:
        logger.error(
            f'Ошибка при {cur_msg_str} админов {message.text}\n {error}'
        )
        await client.send_message(
            message.chat.id,
            f'Проверьте корректность написания пользователей {message.text}',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[:3],
                attr_name='key_name',
                keyboard_row=2
            )
        )
    except UsernameNotOccupied as error:
        logger.error(
            f'ошибка при {cur_msg_str} админов {message.text}\n {error}'
        )
        await client.send_message(
            message.chat.id,
            f'Проверьте правильность написания никнеймов {message.text}, '
            'один из никнеймов не существует',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[:3],
                attr_name='key_name',
                keyboard_row=2
            )
        )
    else:
        if act == 'del':
            logger.info(f'{cur_t1} администраторы {message.text}')
            deactivate_admins = [
                {
                    'user_id': user.id,
                    'username': user.username
                } for user in incom_users
            ]
            await update_users(
                user_id=message.from_user.id,
                users=deactivate_admins,
                is_active=False
            )
            await client.send_message(
                message.chat.id,
                f'Администраторы {message.text} успешно {cur_done}.',
                reply_markup=dinamic_keyboard(
                    objs=bot_keys[:3],
                    attr_name='key_name',
                    keyboard_row=2
                )
            )
            logger.info(
                f'Администраторы {message.text} успешно {cur_done}'
            )
        else:
            logger.info(f'{cur_t1} администраторы {message.text}')
            added_admins = [
                {
                    'user_id': user.id,
                    'username': user.username
                } for user in incom_users
            ]
            await add_users(
                user_id=message.from_user.id,
                users=added_admins,
                is_superuser=False,
                is_admin=True,
                is_active=True
            )
            await client.send_message(
                message.chat.id,
                f'Администраторы {message.text} успешно {cur_done}.',
                reply_markup=dinamic_keyboard(
                    objs=bot_keys[:3],
                    attr_name='key_name',
                    keyboard_row=2
                )
            )
            logger.info(
                f'Администраторы {message.text} успешно {cur_done}'
            )


async def add_admin(client, message):
    """Добавление администратора(ов) в ДБ."""

    await manage_admin(client, message, act='add')


async def del_admin(client, message):
    """Деактивация администратора(ов) в ДБ."""

    await manage_admin(client, message, act='del')


async def choise_channel(client, message):
    """Получение каналов и выбор неоходимого канала телеграм."""

    channels = []
    for channel in await get_channels():
        try:
            (await client.get_chat_member(
                channel.chat.username, Config.BOT_ACCOUNT_NAME))
            channels.append(channel.chat)
        except FloodWait as e:
            logger.error(f'У пользователя {Config.USER_ACCOUNT_NAME} '
                         'слишком много контактов, сработала защита '
                         f'"Телеграм"\n {e}')
            break
        except ChatAdminRequired:
            logger.error(f'Пользователю: {Config.BOT_ACCOUNT_NAME} '
                         'требуются права администратора на канал.'
                         f'{channel.chat.username}')
        except UserNotParticipant:
            logger.error(f'Пользователь: {Config.USER_ACCOUNT_NAME} '
                         'не является владельцем, а пользователь: '
                         f'{Config.BOT_ACCOUNT_NAME} администратором '
                         f'канала {channel.chat.username}.')
    if channels:
        await client.send_message(
            message.chat.id,
            'Выберете желаемый канал на клавиатуре, при его отсутствии '
            'введите канал вручную.',
            reply_markup=dinamic_keyboard(
                objs=channels,
                attr_name='username',
                keyboard_row=4
                )
            )
        return channels
    else:
        await client.send_message(
            message.chat.id,
            'Вероятно вы не являетесь владельцем ниодного канала! '
            'Заведите свои каналы или введите требуемый канал '
            'в текстовое поле и если "Бот" в нём зарегистрирован '
            'продолжайте работу с "Ботом.',
            reply_markup=dinamic_keyboard(
                objs=[bot_keys[2]],
                attr_name='key_name'
                )
            )
    return False


async def set_settings_for_analitics(client, message, settings, crud_name):
    await client.send_message(
        message.chat.id, '...Сохраняем настройки...'
    )
    print(await set_settings_for_report(settings, crud_name=crud_name))


async def auto_generate_report(client, message, bot_1):
    await client.send_message(
        message.chat.id, '...Автоматическое формирование отчёта...'
    )
    chat = ChatUserInfo(bot_1, 'vag_angar')
    logger.info('Бот начал работу')
    report = await chat.create_report()
    await get_report(report)
    await client.send_message(message.chat.id, type(await chat.create_report()))


async def get_channel_report(client, message):
    """Получение каналов из сохраненных в таблице репорт, собранных ботом 1."""

    async with engine.connect() as session:
        db = await report_crud.get_all(session)
        if db is not None and db:
            channel = []
            for report in db:
                channel.append(report)
            await client.send_message(
                message.chat.id,
                'Отчёт по какому каналу вы хотите получить? Выбирите '
                'на клавиатуре.',
                reply_markup=dinamic_keyboard(
                    objs=channel,
                    attr_name='group',
                    keyboard_row=4
                )
            )
            return db
        else:
            logger.error('У пользователя нет каналов сохранённых '
                         'в Spreadsheets Google.')
            await client.send_message(
                message.chat.id,
                'У вас нет информации о каналах сохранённой '
                'в Spreadsheets Google.'
            )


async def generate_report(client, message, manager):
    """Формирование отчёта для отправки в Телеграм."""

    logger.info(f'Готовим ваш {manager.format} файл для отправки в Телеграм.')
    for report in manager.db:
        if report.group == manager.channel:
            await client.send_message(
                message.chat.id,
                f'Пожалуйста подождите, ваш файл: {report.group}'
                f'.{manager.format} загружается из пространства Google Drive...',
                reply_markup=ReplyKeyboardRemove()
                )
            await get_one_spreadsheet(
                report.sheet_id,
                f'{Config.PATH_TO_DOWNLOADS}{report.group}',
                format=manager.format
                )
            if os.path.exists(
                    f'{Config.PATH_TO_DOWNLOADS}{report.group}.{manager.format}'
                    ):
                await client.send_message(
                    message.chat.id,
                    f'Пожалуйста подождите, ваш файл: {report.group}'
                    f'.{manager.format} загружается в Телеграм...'
                )
                await client.send_document(
                    message.chat.id,
                    f'{Config.PATH_TO_DOWNLOADS}{report.group}.{manager.format}'
                    )
                logger.info(
                    f'Файл {report.group}.{manager.format} успешно отправлен '
                    'в Телеграм.'
                    )
                os.remove(
                    f'{Config.PATH_TO_DOWNLOADS}{report.group}.{manager.format}'
                    )
                if os.path.exists(
                        f'{Config.PATH_TO_DOWNLOADS}{report.group}.xlsx'
                        ):
                    os.remove(f'{Config.PATH_TO_DOWNLOADS}{report.group}.xlsx')
                break
            else:
                logger.error(
                    f'При скачивании файла: {report.group}.'
                    f'{manager.format} с Google Drive чтото пошло не так!')


async def auto_report(client, message):
    await client.send_message(message.chat.id, '...Автоматическое формирование отчёта...')


async def scheduling(client, message, spreadsheetId):
    await client.send_message(message.chat.id, '...Формирование графика...')

    data = await get_data_for_shedule(spreadsheetId)
    await build_shedule(data[0], to_title='просмотров')
    await build_shedule(data[1], to_title='реакций')
    await build_shedule(data[2], to_title='репостов')
    await client.send_media_group(
        message.chat.id,
        media=[
            'График изменения просмотров',
            'График изменения реакций',
            'График изменения репостов',
        ]
    )


async def get_channels_settings_from_db(crud_name):
    async with engine.connect() as session:
        return await crud_name.get_all(session)


async def get_run_status(channel, crud_name):
    async with engine.connect() as session:
        obj_channel = await crud_name.get_by_attr(
            attr_name='channel_name',
            attr_value=channel,
            session=session
        )
        return obj_channel


async def set_channel_data(*, channel, period=None, crud_name):
    async with engine.connect() as session:
        if period:
            obj = {
                'period': period
            }
        else:
            obj = {
                'run': False
            }
        channel = await crud_name.set_update(
            attr_name='channel_name',
            attr_value=channel,
            obj_in=obj,
            session=session
        )
        return channel
