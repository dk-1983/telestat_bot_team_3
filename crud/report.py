from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.report import Report


class CRUDReport(CRUDBase):
    """Класс CRUD для дополнительных методов CHANNELSettings."""

    pass


report_crud = CRUDReport(Report)
