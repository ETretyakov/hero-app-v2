"""Pytest fixtures that seed Hero records via the Factory helper.

``_hero`` and ``_heroes`` are available to any test that requests them.
They delegate to ``HeroFactory``, which reads the ``init_data.heroes`` list
from the test's ``data.json`` file and inserts the rows inside the current
rolled-back transaction.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.heroes.crud.models import Hero
from tests.factory import Factory


class HeroFactory(Factory):
    """Specialisation of :class:`Factory` for ``Hero`` records.

    Reads ``init_data.heroes`` from *data* and passes the items to the
    generic :class:`Factory` parent.
    """

    def __init__(self, async_session: AsyncSession, data: dict) -> None:
        items = data.get("init_data", {}).get("heroes", [])
        super().__init__(async_session=async_session, model=Hero, data=items)


@pytest_asyncio.fixture
async def _heroes(
    _async_session: AsyncSession,
    _test_data: dict,
) -> list[Hero]:
    """Seed *all* heroes from ``init_data`` and return them as a list."""
    factory = HeroFactory(async_session=_async_session, data=_test_data)
    return await factory.populate_data(many=True)  # type: ignore[return-value]


@pytest_asyncio.fixture
async def _hero(
    _async_session: AsyncSession,
    _test_data: dict,
) -> Hero:
    """Seed heroes from ``init_data`` and return the first one."""
    factory = HeroFactory(async_session=_async_session, data=_test_data)
    return await factory.populate_data(many=False)  # type: ignore[return-value]
