import datetime
from asyncio import sleep

from logic import get_run_status


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
            channel,
            crud_name=crud_name
            )
        if channel.run is not None or channel.run:
            await sleep(60)
        else:
            return
