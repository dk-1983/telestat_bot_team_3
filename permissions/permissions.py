from crud.userstg import userstg_crud
from core.db import engine


async def check_authorization(
        user_id=None,
        is_superuser=False):
    """Проверка пользователя бота."""

    if user_id is None:
        return False

    async with engine.connect() as session:
        db = await userstg_crud.get_by_attr(
            'user_id',
            user_id,
            session
            )

    if (db is not None and
            user_id == db.user_id and
            db.is_admin and
            db.is_active):
        if (is_superuser and
                is_superuser == db.is_superuser or
                not is_superuser):
            return True
    return False
