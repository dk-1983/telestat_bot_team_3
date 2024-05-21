from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.channel_settings import ChannelSettings


class CRUDChannelSettings(CRUDBase):
    """Класс CRUD для дополнительных методов CHANNELSettings."""

    async def get_settings_report(
            self,
            attrs,
            session: AsyncSession,
    ):
        """Получение настроек канала пользователя по атрибутам."""

        return (await session.execute(
            select(self.model).filter(
                self.model.usertg_id == attrs['usertg_id'],
                self.model.channel_name == attrs['channel_name']))).first()


channel_settings_crud = CRUDChannelSettings(ChannelSettings)
