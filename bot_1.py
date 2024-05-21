from asyncio import sleep
import datetime
import re
from enum import Enum
from sqlalchemy.exc import IntegrityError
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import (UsernameNotOccupied,
                                                        UserNotParticipant)
from pyrogram.types import ReplyKeyboardRemove, messages_and_media

from assistants.assistants import dinamic_keyboard, DotNotationDict
from buttons import bot_keys
from logic import (add_admin, choise_channel, del_admin, set_channel_data,
                   set_settings_for_analitics,
                   get_channels_from_db, get_run_status)
from permissions.permissions import check_authorization
from services.google_api_service import get_report
from services.telegram_service import (ChatUserInfo, get_settings_from_report,
                                       delete_settings_report)
from settings import Config, configure_logging


logger = configure_logging()


async def custom_sleep(channel, period):
    time_now = datetime.datetime.now()
    time_next = datetime.datetime.now() + datetime.timedelta(seconds=period)
    while time_next > time_now:
        run_status = await get_run_status(channel)
        if run_status:
            await sleep(60)
        else:
            return


class Commands(Enum):
    add_admin = 'Добавить администратора'
    del_admin = 'Удалить администратора'
    choise_channel = 'Выбрать телеграм канал'
    set_period = 'Установить период сбора данных'
    run_collect_analitics = 'Начать сбор аналитики'
    user_period = 'Свой вариант'
    stop_channel = 'Остановить сбор аналитики'


class BotManager:
    """Конфигурация глобальных настроек бота."""
    add_admin_flag = False
    del_admin_flag = False
    choise_channel_flag = False
    set_period_flag = False
    stop_channel_flag = True
    owner_or_admin = ''
    chanel = ''
    period = 120
    work_period = 240


bot_1 = Client(
    Config.BOT_ACCOUNT_NAME,
    api_hash=Config.API_HASH,
    api_id=Config.API_ID,
    bot_token=Config.BOT_TOKEN
)

manager = BotManager()


@bot_1.on_message(filters.command('start'))
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
                objs=bot_keys[:3] + bot_keys[14:15],
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
                objs=bot_keys[2:3] + bot_keys[14:15],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.owner_or_admin = 'admin'
        logger.debug(f'{message.chat.username} авторизован как администратор бота!')
    else:
        await client.send_message(
            message.chat.id,
            'У вас нет прав, вы не авторизованы, пожалуйста авторизуйтесь.'
            )


@bot_1.on_message(filters.regex(Commands.add_admin.value))
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


@bot_1.on_message(filters.regex(Commands.del_admin.value))
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


@bot_1.on_message(filters.regex(Commands.run_collect_analitics.value))
async def generate_report(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Отправляет отчёт."""

    try:
        if not manager.chanel:
            return

        settings = {
            'usertg_id': (await client.get_users(message.from_user.username)).id,
            'channel_name': manager.chanel,
            'period': manager.period,
            'work_period': datetime.datetime.now() + datetime.timedelta(seconds=manager.work_period),
            'started_at': datetime.datetime.now(),
            'run_status': True,
            'run': True
        }
        await set_settings_for_analitics(client, message, settings)
    except IntegrityError:
        logger.info(
            'Процесс сбора аналитики в этом канале уже запущен!\n'
            f'Обновляем период сбора аналитики в канале {manager.chanel} '
            f'на {manager.period}'
        )

        await set_channel_data(manager.chanel, manager.period)

    period = manager.period
    usertg_id = (await client.get_users(message.from_user.username)).id
    channel_name = manager.chanel

    await client.send_message(
        message.chat.id,
        f'Бот выполняет сбор аналитики на канале: {channel_name} '
        f'с заданым периодом {period}. Желаете запустить другой '
        'канал? Выполните команду старт: /start',
        reply_markup=ReplyKeyboardRemove()
    )

    async def recursion_func(usertg_id, channel_name, period):
        logger.info('Рекурсия началась')

        chat = ChatUserInfo(bot_1, channel_name)
        logger.info('Бот начал работу')
        report = await chat.create_report()
        reports_url = await get_report(report)
        for msg in reports_url:
            await client.send_message(
                message.chat.id,
                msg
            )

        logger.info(f'Рекурсия, контрольная точка: {datetime.datetime.now()}')
        db = await get_settings_from_report(
                {
                    'usertg_id': usertg_id,
                    'channel_name': channel_name
                })
        if db is not None or db:
            # await custom_sleep(channel_name, period)
            await sleep(period)
            if (not db.run or db.work_period <= datetime.datetime.now()):
                logger.info(f'Удаляем запись о канале: {db.channel_name} '
                            'в базе данных, Бот закончил свою работу.')
                await delete_settings_report('id', db.id)
                return
            await recursion_func(db.usertg_id, db.channel_name, db.period)

    await recursion_func(usertg_id, channel_name, period)


@bot_1.on_message(filters.regex(Commands.choise_channel.value))
async def choise_channel_cmd(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Находит все каналы владельца."""

    logger.info('Выбираем телеграм канал')
    await client.send_message(
            message.chat.id,
            'Идёт процесс получения каналов, пожалуйста, подождите...',
            reply_markup=ReplyKeyboardRemove()
        )
    if manager.owner_or_admin == 'owner' or manager.owner_or_admin == 'admin':
        await choise_channel(client, message)
        manager.choise_channel_flag = True


@bot_1.on_message(filters.regex(Commands.set_period.value))
async def set_period_cmd(
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


@bot_1.on_message(filters.regex(Commands.user_period.value))
async def set_user_period(
    client: Client,
    message: messages_and_media.message.Message
):
    """Устанавливает пользовательское время периода опроса."""

    logger.info('Пользователь вручную выбирает время опроса')
    await client.send_message(
        message.chat.id,
        'Укажите произвольное время в часах:',
        reply_markup=ReplyKeyboardRemove()
    )


@bot_1.on_message(filters.regex(Commands.stop_channel.value))
async def stop_channel(
    client: Client,
    message: messages_and_media.message.Message,
    manager=manager
):
    """Функция для остановки запущенных процессов сбора аналитики в каналах."""
    logger.info('Запущен процесс остановки сбора аналитики канала')
    channel_btns = []
    channels = get_channels_from_db()

    if not channels:
        await client.send_message(
            message.chat.id,
            'Нет запущеных задач по сбору аналитики!',
            reply_markup=dinamic_keyboard(
                objs=(
                    [bot_keys[2:3] + bot_keys[14:15]],
                    bot_keys[:3] + bot_keys[14:15]
                )[manager.owner_or_admin == 'owner'],
                attr_name='key_name'
            )
        )
    for channel in await channels:
        channel_btns.append(DotNotationDict({'channel': channel}))
    await client.send_message(
        message.chat.id,
        'Выберите канал для остановки сбора аналитики:',
        reply_markup=dinamic_keyboard(
            objs=channel_btns,
            attr_name='channel'
        )
    )
    manager.stop_channel_flag = True


@bot_1.on_message()
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

    elif manager.choise_channel_flag:
        try:
            if ((await client.get_chat_member(
                message.text,
                Config.BOT_ACCOUNT_NAME)
                    ).privileges.can_restrict_members):
                manager.chanel = message.text
                await client.send_message(
                    message.chat.id,
                    'Выберете периодичность сбора аналитики.',
                    reply_markup=dinamic_keyboard(
                        objs=bot_keys[3:5],
                        attr_name='key_name',
                        keyboard_row=2
                    )
                )
        except UsernameNotOccupied as e:
            logger.error(f'Название канала введено не корректно или не занято!\n {e}')
            await client.send_message(
                    message.chat.id,
                    'Вероятно В ведённом канале "Бот" не зарегистрирован!',
                    reply_markup=dinamic_keyboard(
                        objs=[bot_keys[2]],
                        attr_name='key_name'
                    )
                )
        except UserNotParticipant as e:
            logger.error(f'В ведённом канале "Бот" не зарегистрирован!\n {e}')
            await client.send_message(
                message.chat.id,
                'Вероятно В ведённом канале "Бот" не зарегистрирован!',
                reply_markup=dinamic_keyboard(
                    objs=([bot_keys[2]],
                          bot_keys[:3])[manager.owner_or_admin == 'owner'],
                    attr_name='key_name'
                )
            )
        manager.choise_channel_flag = False

    elif manager.set_period_flag:
        logger.info('Проверка и сохранение периода опроса в manager')
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
            'Для запуска сбора статистики нажмите кнопку.',
            reply_markup=dinamic_keyboard(
                objs=[bot_keys[4]],
                attr_name='key_name',
                keyboard_row=2
            )
        )
        manager.period = int(period) * 3600
        manager.set_period_flag = False
        logger.info(f'Выбран период опроса {manager.period}')

    elif manager.stop_channel_flag:
        channel = message.text
        await set_channel_data(channel)
        logger.info(f'Сбор канала {channel} остановлен')
        await delete_settings_report('channel_name', channel)
        await client.send_message(
            message.chat.id,
            f'Остановлен сбор аналитики канала {channel}',
            reply_markup=dinamic_keyboard(
                objs=(
                    [bot_keys[2:3] + bot_keys[14:15]],
                    bot_keys[:3] + bot_keys[14:15]
                )[manager.owner_or_admin == 'owner'],
                attr_name='key_name'
            )
        )
        manager.stop_channel_flag = True
    else:
        await client.send_message(
            message.chat.id,
            'Упс, этого действия мы от вас не ожидали! \n'
            'Или вы пытаетесь выполнить действие на которое '
            'у вас нет прав, "Авторизуйтесь", командой: /start'
        )
        manager.owner_or_admin = ''


if __name__ == '__main__':
    logger.info(' Бот запущен')
    bot_1.run()