from datetime import datetime as dt

from sqlalchemy import (BigInteger, Boolean, CheckConstraint, Column, DateTime,
                        ForeignKey, Integer, String)

from core.db import Base


class ChannelSettings(Base):
    """Модель настроек пользователя для каналов."""

    usertg_id = Column(
        BigInteger,
        ForeignKey(
            'userstg.user_id',
            ondelete='CASCADE'))
    channel_name = Column(String(100), nullable=False, unique=True)
    period = Column(Integer, default=3600)
    work_period = Column(DateTime, nullable=False)
    created = Column(DateTime, default=dt.now)
    refreshed = Column(DateTime, default=dt.now, onupdate=dt.now)
    started_at = Column(DateTime, nullable=False)
    run_status = Column(Boolean, default=False)
    run = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return (
            f'{self.id}'
            f'{self.usertg_id}'
            f'{self.channel_name},'
            f'{self.period},'
            f'{self.work_period},'
            f'{self.created}'
            f'{self.refreshed},'
            f'{self.started_at},'
            f'{self.run_status},'
            f'{self.run}')
