from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.base import CRUDBase
from models.userstg import UsersTG


class CRUDUsersTG(CRUDBase):
    """Класс CRUD для дополнительных методов USERSTG."""
    pass


userstg_crud = CRUDUsersTG(UsersTG)
