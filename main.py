import asyncio
import logging
import subprocess
from threading import Thread

from services.launcher import init_process
from settings import configure_logging

logging.basicConfig(level=logging.INFO)
# from core.base import Base
# from core.db import engine


logger = configure_logging()


# async def init_models():
#     """Для проверки создаём таблицу в ручную."""

#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#         await conn.run_sync(Base.metadata.create_all)


# init_process()

if __name__ == '__main__':

    Thread(target=subprocess.run, args=['py bot_1.py']).start()
    Thread(target=subprocess.run, args=['py bot_2.py']).start()
