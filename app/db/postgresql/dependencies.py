from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.base import SessionFactory


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a scoped async database session.

    The session is closed automatically when the request finishes.
    Commit/rollback are not performed here — that is the responsibility
    of the ``@transaction`` decorator on individual service methods.
    """
    async with SessionFactory() as session:
        yield session
