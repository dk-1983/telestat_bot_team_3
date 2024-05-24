import datetime
from asyncio import sleep

from logic import get_run_status
from settings import configure_logging

logger = configure_logging()


async def custom_sleep(
        channel,
        period,
        crud_name
):
    """
    Вручную меняет время паузы в случае ошибки пользователя при вводе данных
    периода между опросами иначе бот может на месяцы уйти в сон.
    """
    time_next = datetime.datetime.now() + datetime.timedelta(seconds=period)
    while (time_next > datetime.datetime.now()):
        channel = await get_run_status(
            channel=channel,
            crud_name=crud_name
            )
        logger.debug(
            f'Слип получил запрос из ДБ в: {datetime.datetime.now()}'
            )
        if channel.run is not None or channel.run:
            await sleep(60)
            logger.debug(
                f'Слип вышел из сна в: {datetime.datetime.now()} '
                f'Пользователь: {channel.usertg_id}, канал '
                f'{channel.channel_name}'
                )
        else:
            logger.debug(f'Слип закончил работу в: {datetime.datetime.now()}')
            return
