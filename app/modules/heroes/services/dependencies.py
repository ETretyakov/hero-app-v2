from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.dependencies import get_async_session
from app.modules.heroes.services import HeroServices


async def get_hero_services(
    session: AsyncSession = Depends(get_async_session),
) -> HeroServices:
    """FastAPI dependency that provides a ``HeroServices`` instance for the current request.

    The session is injected by ``get_async_session`` and shared across all
    service and CRUD calls within the same request, ensuring they participate
    in the same database transaction.
    """
    return HeroServices(session)
