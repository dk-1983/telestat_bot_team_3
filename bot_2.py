import datetime
import re
from enum import Enum

from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardRemove, messages_and_media
from sqlalchemy.exc import IntegrityError

from assistants.assistants import DotNotationDict, dinamic_keyboard
from assistants.custom_sleep import custom_sleep
from buttons import bot_keys
from crud.channel_settings import channel_settings_crud
from crud.report_settings import report_settings_crud
from logic import (add_admin, auto_report, del_admin, generate_report,
                   get_channel_report, get_channels_settings_from_db,
                   scheduling, set_channel_data, set_settings_for_analitics)
from permissions.permissions import check_authorization
from services.google_api_service import get_one_spreadsheet, get_report
from services.telegram_service import (delete_settings_report,
                                       get_settings_from_report)
from settings import Config, configure_logging


class Commands(Enum):
    add_admin = 'Добавить администратора'
    del_admin = 'Удалить администратора'
    set_period = 'Установить период сбора данных'
    auto_report = 'Автоматическое формирование отчёта'
    run_collect_analitics = 'Начать сбор аналитики'
    generate_report = 'Формирование отчёта'
    scheduling = 'Формирование графика'
    user_period = 'Свой вариант'
    stop_channel = 'Остановить сбор аналитики'
    set_new_period = 'Изменить период сбора аналитики'


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
    auto_report_status_flag = False
    set_period_flag = False
    set_user_period_flag = False
    scheduling_flag = False
    stop_channel_flag = False
    set_new_period_flag = False
    set_channel_for_new_period = False
    owner_or_admin = ''
    format = ''
    channel = ''
    link = ''
    db = []
    period = 3600
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
                objs=bot_keys[:2] + bot_keys[5:8] + bot_keys[14:15] + bot_keys[17:18],
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
                objs=bot_keys[5:8] + bot_keys[14:15] + bot_keys[17:18],
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


@bot_2.on_message(filters.regex(Commands.run_collect_analitics.value))
async def command_run_collect_analitics(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Отправляет отчёт пользователю Телеграм автоматически."""

    logger.info('Начат процесс отправки собраной информации в Телеграм.')
    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        try:
            if not manager.channel:
                return

            settings = {
                'usertg_id': (await client.get_users(message.from_user.username)).id,
                'channel_name': manager.channel,
                'period': manager.period,
                'work_period': datetime.datetime.now() + datetime.timedelta(seconds=manager.work_period),
                'started_at': datetime.datetime.now(),
                'run': True
            }
            await set_settings_for_analitics(
                client,
                message,
                settings,
                crud_name=report_settings_crud
                )
        except IntegrityError:
            logger.info(
                'Процесс передачи аналитики в этом канале для Телеграм уже запущен!\n'
                f'Обновляем период сбора аналитики в канале {manager.channel} '
                f'на {manager.period}'
            )
            await set_channel_data(
                channel=manager.channel,
                period=manager.period,
                crud_name=report_settings_crud
                )

        period = manager.period
        usertg_id = (await client.get_users(message.from_user.username)).id
        channel_name = manager.channel

        await client.send_message(
            message.chat.id,
            f'Бот выполняет сбор аналитики на канале: {channel_name} '
            'из Google Spreadsheets для передачи файлов в Телеграм, '
            f'с заданым периодом {period}. Желаете запустить другой '
            'канал? Выполните команду старт: /start',
            reply_markup=ReplyKeyboardRemove()
        )

        async def recursion_func(usertg_id, channel_name, period):
            logger.info('Рекурсия началась')

            # logger.info('ПОЛЕЗНАЯ НАГРУЗКА!!!')
            # print(manager.format, manager.channel, manager.period)
            await generate_report(
                    client,
                    message,
                    manager=manager
                    )

            logger.info(
                f'Рекурсия, контрольная точка: {datetime.datetime.now()}\n'
                'Бот собрал аналитику в текущем цикле итерации.')

            db = await get_settings_from_report(
                    {
                        'usertg_id': usertg_id,
                        'channel_name': channel_name,
                        'crud_name': report_settings_crud
                    }
                )
            db_bot1 = await get_settings_from_report(
                    {
                        'usertg_id': usertg_id,
                        'channel_name': channel_name,
                        'crud_name': channel_settings_crud
                    }
                )
            if db_bot1 is None or not db_bot1.run:
                logger.info(
                    'Дальнейший сбор аналитики не имеет смысла, Бот 1 '
                    'больше не собирает статистику!'
                    )
                await client.send_message(
                    message.chat.id,
                    'Дальнейший сбор аналитики не имеет смысла, Бот 1 '
                    f'больше не собирает статистику на канале {db.channel_name}!'
                )
            if db is not None or db:
                await custom_sleep(
                    channel=channel_name,
                    period=period,
                    crud_name=report_settings_crud
                    )
                # await sleep(period)
                if (db is None or  # or db.work_period <= datetime.datetime.now()
                        not db.run or db_bot1 is None or not db_bot1.run):
                    logger.info(f'Удаляем запись о канале: {db.channel_name} '
                                'в базе данных, Бот 2 закончил свою работу.')
                    await client.send_message(
                        message.chat.id,
                        'Бот 2 закончил отправку собранной аналитики на '
                        f'канале {db.channel_name} в {datetime.datetime.now()}!'
                        )
                    await delete_settings_report(
                        'id',
                        db.id,
                        crud_name=report_settings_crud
                        )
                    return
                await recursion_func(
                    usertg_id=db.usertg_id,
                    channel_name=db.channel_name,
                    period=db.period
                    )

        await recursion_func(
            usertg_id=usertg_id,
            channel_name=channel_name,
            period=period
            )


@bot_2.on_message(filters.regex(Commands.set_new_period.value))
async def command_set_new_period(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Изменение периода сбора данных в процессе работы бота."""

    await client.send_message(
        message.chat.id,
        'Установите новый период в часах, введите новое значение в '
        'текстовое поле:',
        reply_markup=ReplyKeyboardRemove()
    )
    manager.set_new_period_flag = True


@bot_2.on_message(filters.regex(Commands.stop_channel.value))
async def stop_channel(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Функция для остановки запущенных процессов сбора аналитики в каналах."""

    logger.info('Запущен процесс остановки сбора аналитики канала')
    channels = await get_channels_settings_from_db(
        crud_name=report_settings_crud
    )

    if not channels:
        await client.send_message(
            message.chat.id,
            'Нет запущеных задач по сбору и передаче аналитики в Телеграм!',
            reply_markup=dinamic_keyboard(
                objs=(
                    bot_keys[5:8],
                    bot_keys[:2] + bot_keys[5:8]
                )[manager.owner_or_admin == 'owner'],
                attr_name='key_name'
            )
        )
    else:
        # for channel in channels:
        await client.send_message(
            message.chat.id,
            'Выберите канал для остановки сбора аналитики:',
            reply_markup=dinamic_keyboard(
                objs=([channels], channels)[isinstance(channels, list)],
                attr_name='channel_name'
            )
        )
        manager.stop_channel_flag = True


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
        manager.db = await get_channel_report(client, message)
        manager.choise_auto_report_flag = True


@bot_2.on_message(filters.regex(Commands.set_period.value))
async def command_set_period_cmd(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Устанавливает переиод сбора данных."""

    logger.info('Устананавливаем период сбора данных')
    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        await client.send_message(
            message.chat.id,
            'Установите период опроса списка пользователей группы:',
            reply_markup=dinamic_keyboard(
                objs=bot_keys[8:14],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.set_period_flag = True


@bot_2.on_message(filters.regex(Commands.user_period.value))
async def command_set_user_period(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Устанавливает пользовательское время периода опроса."""

    logger.info('Пользователь вручную выбирает время опроса')
    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        await client.send_message(
            message.chat.id,
            'Укажите произвольное время в часах:',
            reply_markup=ReplyKeyboardRemove()
        )


@bot_2.on_message(filters.regex(Commands.scheduling.value))
async def command_sheduling(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Создаёт графики."""

    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        # await scheduling(client, message)
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
                'Выбирите желаемый формат для сохранения файла на клавиатуре.',
                reply_markup=dinamic_keyboard(
                    objs=bot_keys[15:17],
                    attr_name='key_name'
                )
            )
        manager.choise_report_flag = False

    elif message.text == 'csv':
        if (manager.owner_or_admin == 'owner' or
                manager.owner_or_admin == 'admin'):
            manager.format = message.text
            if manager.auto_report_status_flag:
                manager.auto_report_status_flag = False
                logger.info(f'Выбрали формат {message.text} для автоотчёта.')
                await client.send_message(
                    message.chat.id,
                    'Выбирите желай интервал времени на клавиатуре:\n'
                    'или начните отправку аналитики...',
                    reply_markup=dinamic_keyboard(
                        objs=bot_keys[3:4] + bot_keys[4:5],
                        attr_name='key_name',
                        keyboard_row=2
                    )
                )
            else:
                await generate_report(
                    client,
                    message,
                    manager=manager
                    )

    elif message.text == 'xlsx':
        if (manager.owner_or_admin == 'owner' or
                manager.owner_or_admin == 'admin'):
            manager.format = message.text
            if manager.auto_report_status_flag:
                manager.auto_report_status_flag = False
                logger.info(f'Выбрали формат {message.text} для автоотчёта.')
                await client.send_message(
                    message.chat.id,
                    'Выбирите желай интервал времени на клавиатуре:\n'
                    'или начните отправку аналитики...',
                    reply_markup=dinamic_keyboard(
                        objs=bot_keys[3:4] + bot_keys[4:5],
                        attr_name='key_name',
                        keyboard_row=2
                    )
                )
            else:
                await generate_report(
                    client,
                    message,
                    manager=manager
                    )

    elif manager.choise_report_flag:
        logger.info('Приняли команду на установку периода отправки данных.')
        print(message.text)
        manager.choise_report_flag = False

    elif manager.choise_auto_report_flag:
        manager.auto_report_status_flag = True
        logger.info('Приняли команду на aвтоматическое формирование отчёта')
        if message.text:
            manager.channel = message.text
            await client.send_message(
                message.chat.id,
                'Выбирите желай формат отправляемых данных на клавиатуре:\n'
                'и начните отправку аналитики...',
                reply_markup=dinamic_keyboard(
                    objs=bot_keys[15:17],
                    attr_name='key_name',
                    keyboard_row=2
                )
            )
        manager.choise_auto_report_flag = False

    elif manager.scheduling_flag:
        logger.info('Приняли команду на создание графика.')
        manager.scheduling_flag = False

    elif manager.set_period_flag:
        logger.info(
            'Приняли команду на установку временного периода из списка '
            'или заданное пользователем.'
            )
        period = re.search('\d{,3}', message.text).group()
        if not period:
            await client.send_message(
                message.chat.id,
                'Проверьте правильность периода, должно быть целое число!\n'
                'Укажите произвольное время в часах:',
                reply_markup=ReplyKeyboardRemove()
            )
            return
        await client.send_message(
            message.chat.id,
            'Для запуска отправки статистики нажмите кнопку.',
            reply_markup=dinamic_keyboard(
                objs=[bot_keys[4]],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.period = int(period) * 3600
        logger.info(f'Выбран период опроса {manager.period}')
        manager.set_period_flag = False

    elif manager.set_new_period_flag:
        if not manager.set_channel_for_new_period:
            logger.info(
                'Устанавливаем новое кастомное время отправки аналитики.'
                )
            period = re.search('\d{,3}', message.text).group()
            if not period:
                await client.send_message(
                    message.chat.id,
                    'Проверьте правильность периода, должно быть целое число!\n'
                    'Укажите произвольное время в часах:',
                    reply_markup=ReplyKeyboardRemove()
                )
                return
            manager.period = int(period) * 3600
            logger.info(f'Выбран период опроса {manager.period}')
            channels = await get_channels_settings_from_db(
                crud_name=report_settings_crud
            )
            if channels is None or not channels:
                await client.send_message(
                    message.chat.id,
                    'Вероятно бот 2 не запущен, данная операция недоступна.'
                )
            else:
                await client.send_message(
                    message.chat.id,
                    'Требуется выбрать канал для изменения временных критериев:',
                    reply_markup=dinamic_keyboard(
                        objs=channels,
                        attr_name='channel_name',
                        keyboard_row=4
                    )
                )
                manager.set_channel_for_new_period = True
        else:
            await set_channel_data(
                channel=message.text,
                period=manager.period,
                crud_name=report_settings_crud
            )

            await client.send_message(
                    message.chat.id,
                    'Установлен новый период выборки данных из канала '
                    f'{message.text} успешно, новый период составляет: '
                    f'{manager.period / 3600} часов, для продолжения '
                    'нажмите старт: /start',
                    reply_markup=ReplyKeyboardRemove()
                    )
            manager.set_new_period_flag = False

    elif manager.stop_channel_flag:
        channel = message.text
        await set_channel_data(
            channel=channel,
            crud_name=report_settings_crud
            )
        logger.info(f'Сбор канала {channel} остановлен')
        await delete_settings_report(
            'channel_name',
            channel,
            crud_name=report_settings_crud
            )
        await client.send_message(
            message.chat.id,
            f'Остановлен сбор аналитики канала {channel}',
            reply_markup=dinamic_keyboard(
                objs=(
                    [bot_keys[5:8] + bot_keys[14:15]],
                    bot_keys[:2] + bot_keys[5:8] + bot_keys[14:15]
                )[manager.owner_or_admin == 'owner'],
                attr_name='key_name'
            )
        )
        manager.stop_channel_flag = False

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
