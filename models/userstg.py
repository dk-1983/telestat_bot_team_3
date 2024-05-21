from datetime import datetime as dt

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Column, DateTime,
                        Integer, String)

from core.db import Base


class UsersTG(Base):
    """Модель пользователя ТГ."""

    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100), unique=True)
    create_date = Column(DateTime, default=dt.now)
    is_superuser = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f'{self.id},'
            f'{self.user_id}'
            f'{self.username},'
            f'{self.create_date},'
            f'{self.is_superuser},'
            f'{self.is_admin},'
            f'{self.is_active}')
