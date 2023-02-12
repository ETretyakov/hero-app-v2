from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.base import SessionFactory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session
