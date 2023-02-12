import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.heroes.crud.models import Hero
from tests.factory import Factory


class HeroFactory(Factory):
    def __init__(self, async_session: AsyncSession, data: dict):
        data = data.get("init_data", {}).get("heroes", [])
        model = Hero
        super().__init__(async_session, model, data)


@pytest_asyncio.fixture
async def _heroes(_async_session: AsyncSession, _test_data: dict):
    factory = HeroFactory(async_session=_async_session, data=_test_data)
    return await factory.populate_data(many=True)


@pytest_asyncio.fixture
async def _hero(_async_session: AsyncSession, _test_data: dict):
    factory = HeroFactory(async_session=_async_session, data=_test_data)
    return await factory.populate_data(many=False)
