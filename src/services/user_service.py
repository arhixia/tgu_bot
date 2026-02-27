# src/services/user_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import User

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: str) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()