from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDBase:
    """Базовый класс операций CRUD."""

    def __init__(
            self,
            model):
        self.model = model

    async def get_all(
            self,
            session: AsyncSession,
    ):
        """Получение всех записей таблицы из ДБ."""

        return ((await session.execute(
            select(self.model))).all())

    async def get_by_attr(
            self,
            attr_name,
            attr_value,
            session: AsyncSession,
    ):
        """Получение значения из ДБ по атрибуту."""

        attr = getattr(self.model, attr_name)
        return ((await session.execute(
            select(self.model).where(
                attr == attr_value))).first())

    async def create(
            self,
            obj,
            session: AsyncSession,
    ):
        """Создание объектов ДБ."""

        db_obj = self.model(**obj)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def set_update(
            self,
            attr_name,
            attr_value,
            obj_in: dict,
            session: AsyncSession,
    ):
        """Обновление Объектов в ДБ."""

        db = await session.execute(
            update(
                self.model).values(
                **obj_in).where(
                    getattr(self.model, attr_name) == attr_value))
        await session.commit()
        return db

    async def remove(
            self,
            attr_name,
            attr_value,
            session: AsyncSession,
    ):
        """Удаление объекта из DB."""

        if not attr_name or not attr_value:
            return False
        
        print(attr_name, attr_value)

        await session.execute(
            delete(self.model).where(
                getattr(self.model, attr_name) == attr_value)
        )
        await session.commit()
        return
