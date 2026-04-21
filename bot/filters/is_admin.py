from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from db.repository import UserRepo


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        repo = UserRepo(session)
        return await repo.is_admin(message.from_user.id)
