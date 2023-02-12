from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.dependencies import get_async_session
from app.modules.heroes.services import HeroServices


async def get_hero_services(
    session: AsyncSession = Depends(get_async_session),
) -> HeroServices:
    return HeroServices(session=session)
