import os
import re
from enum import Enum

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardRemove, messages_and_media

from assistants.assistants import dinamic_keyboard
from buttons import bot_keys
from logic import (add_admin, auto_report, del_admin, generate_report,
                   get_channel_report, scheduling)
from permissions.permissions import check_authorization
from services.google_api_service import get_one_spreadsheet, get_report
from settings import Config, configure_logging


class Commands(Enum):
    add_admin = 'Добавить администратора'
    del_admin = 'Удалить администратора'
    auto_report = 'Автоматическое формирование отчёта'
    generate_report = 'Формирование отчёта'
    scheduling = 'Формирование графика'


logger = configure_logging()
bot_2 = Client(
    Config.BOT2_ACCOUNT_NAME,
    api_hash=Config.API_HASH,
    api_id=Config.API_ID,
    bot_token=Config.BOT2_TOKEN
)


class BotManager:
    """Конфигурация глобальных настроек бота."""
    add_admin_flag = False
    del_admin_flag = False
    choise_report_flag = False
    choise_auto_report_flag = False
    scheduling_flag = False
    owner_or_admin = ''
    channel = ''
    link = ''
    db = []
    period = 10
    work_period = 60


manager = BotManager()


@bot_2.on_message(filters.command('start'))
async def command_start(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Обработчик команды на запуск бота по сбору данных."""

    logger.info('Проверка авторизации.')

    if await check_authorization(message.from_user.id, is_superuser=True):
        await client.send_message(
            message.chat.id,
            f'{message.chat.username} вы авторизованы как владелец!',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[:2] + bot_keys[5:8],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.owner_or_admin = 'owner'
        logger.debug(f'{message.chat.username} авторизован как владелец!')
    elif await check_authorization(message.from_user.id):
        await client.send_message(
            message.chat.id,
            f'{message.chat.username} вы авторизованы как администратор бота!',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[5:8],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.owner_or_admin = 'admin'
        logger.debug(
            f'{message.chat.username} авторизован как администратор бота!'
            )
    else:
        await client.send_message(
            message.chat.id,
            'У вас нет прав, вы не авторизованы, пожалуйста авторизуйтесь.'
            )


@bot_2.on_message(filters.regex(Commands.add_admin.value))
async def command_add_admin(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Добавление администратора в ДБ."""

    if manager.owner_or_admin == 'owner':
        logger.info('Добавляем администратора')

        await client.send_message(
            message.chat.id,
            'Укажите никнеймы пользователей, которых хотите добавить '
            'в качестве администраторов, в формате: '
            '@nickname1, @nickname2, @nickname3',
            reply_markup=ReplyKeyboardRemove()
        )
        manager.add_admin_flag = True


@bot_2.on_message(filters.regex(Commands.del_admin.value))
async def command_del_admin(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Блокирует администраторов бота в ДБ."""

    if manager.owner_or_admin == 'owner':
        logger.info('Блокируем администратора(ов) бота')
        await client.send_message(
            message.chat.id,
            'Укажите никнеймы администраторов, которых хотите деактивировать, '
            'в формате @nickname1, @nickname2, @nickname3',
            reply_markup=ReplyKeyboardRemove()
        )
        manager.del_admin_flag = True


@bot_2.on_message(filters.regex(Commands.generate_report.value))
async def command_generate_report(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Создаёт отчёт вручную."""

    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        manager.db = await get_channel_report(client, message)

        manager.choise_report_flag = True


@bot_2.on_message(filters.regex(Commands.auto_report.value))
async def command_auto_report(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Создаёт отчёт автоматически."""

    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        await auto_report(client, message)
        manager.choise_auto_report_flag = True


@bot_2.on_message(filters.regex(Commands.scheduling.value))
async def command_sheduling(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Создаёт графики."""

    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        await auto_report(client, message)
        manager.scheduling_flag = True


@bot_2.on_message()
async def all_incomming_messages(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Здесь обрабатываем все входящие сообщения."""

    if manager.add_admin_flag:
        await add_admin(client, message)
        manager.add_admin_flag = False

    elif manager.del_admin_flag:
        await del_admin(client, message)
        manager.del_admin_flag = False

    elif manager.choise_report_flag:
        logger.info('Приняли команду на формирование отчёта')
        if message.text:
            manager.channel = message.text
        await client.send_message(
            message.chat.id,
            f'Вы выбрали канал: {message.text}\n'
            'Выберете желаемый формат для сохранения файла на клавиатуре.',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[15:17],
                attr_name='key_name'
            )
        )
        manager.choise_report_flag = False

    elif message.text == 'CSV':
        if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
            logger.info('Готовим ваш CSV файл для отправки в Телеграм.')
            for report in manager.db:
                if report.group == manager.channel:
                    await client.send_message(
                        message.chat.id,
                        f'Пожалуйста подождите, ваш файл: {report.group}.csv '
                        'загружается из пространства Google Drive...',
                        reply_markup=ReplyKeyboardRemove()
                        )
                    await get_one_spreadsheet(
                        report.sheet_id,
                        f'{Config.PATH_TO_DOWNLOADS}{report.group}',
                        format='CSV'
                        )
                    if os.path.exists(
                            f'{Config.PATH_TO_DOWNLOADS}{report.group}.csv'
                            ):
                        await client.send_message(
                            message.chat.id,
                            f'Пожалуйста подождите, ваш файл: {report.group}'
                            '.CSV загружается в Телеграм...'
                        )
                        await client.send_document(
                            message.chat.id,
                            f'{Config.PATH_TO_DOWNLOADS}{report.group}.csv'
                            )
                        break
                    else:
                        logger.error(f'При скачивании файла: {report.group}.'
                                     'CSV с Google Drive чтото пошло не так!')

    elif message.text == 'xlsx':
        if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
            logger.info('Готовим ваш xlsx файл для отправки в Телеграм.')
            for report in manager.db:
                if report.group == manager.channel:
                    await client.send_message(
                        message.chat.id,
                        f'Пожалуйста подождите, ваш файл: {report.group}.xlsx '
                        'загружается из пространства Google Drive...',
                        reply_markup=ReplyKeyboardRemove()
                        )
                    await get_one_spreadsheet(
                        report.sheet_id,
                        f'{Config.PATH_TO_DOWNLOADS}{report.group}'
                        )
                    if os.path.exists(
                            f'{Config.PATH_TO_DOWNLOADS}{report.group}.xlsx'
                            ):
                        await client.send_message(
                            message.chat.id,
                            f'Пожалуйста подождите, ваш файл: {report.group}'
                            '.xlsx загружается в Телеграм...'
                        )
                        await client.send_document(
                            message.chat.id,
                            f'{Config.PATH_TO_DOWNLOADS}{report.group}.xlsx'
                            )
                        break
                    else:
                        logger.error(f'При скачивании файла: {report.group}.'
                                     'xlsx с Google Drive чтото пошло не так!')
            # await generate_report(client, message)

    elif manager.choise_auto_report_flag:
        logger.info('Приняли команду на aвтоматическое формирование отчёта')
        manager.choise_auto_report_flag = False
    elif manager.scheduling_flag:
        logger.info('Приняли команду на создание графика.')
        manager.scheduling_flag = False
    else:
        await client.send_message(
            message.chat.id,
            'Упс, этого действия мы от вас не ожидали! \n'
            'Или вы пытаетесь выполнить действие на которое '
            'у вас нет прав, "Авторизуйтесь", командой: /start'
        )
        manager.owner_or_admin = ''


if __name__ == '__main__':
    logger.info('Bot 2 is started.')
    bot_2.run()
