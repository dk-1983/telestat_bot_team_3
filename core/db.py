from sqlalchemy import Column, Integer, Sequence
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base, declared_attr, sessionmaker

from settings import Config, configure_logging

logger = configure_logging()


class PreBase:

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=PreBase)

engine = create_async_engine(
    Config.DB_URI,
    echo=True)

async_session = AsyncSession(engine)

async_session = async_sessionmaker(engine)
