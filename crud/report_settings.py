from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.report_settings import ReportSettings


class CRUDReportSettings(CRUDBase):
    """Класс CRUD для дополнительных методов REPORTSettings."""

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


report_settings_crud = CRUDReportSettings(ReportSettings)
