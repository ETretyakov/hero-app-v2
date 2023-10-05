from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.heroes.crud.models import Hero
from tests.utils.assertions import assert_response


class TestHero:
    """Tests for hero module."""

    base_url = "/v1"

    # |Tests|
    @pytest.mark.asyncio
    async def test_create(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _test_data: dict,
    ):
        payload = _test_data["cases"]["create"]["payload"]

        response = await _async_client.post(
            f"{self.base_url}/heroes",
            json=payload,
        )

        assert response.status_code == 201

        got = response.json()
        want = _test_data["cases"]["create"]["want"]

        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == got["uuid"])
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_get(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        response = await _async_client.get(
            f"{self.base_url}/heroes/{_hero.uuid}",
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["get"]["want"]

        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == got["uuid"])
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_update(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        payload = _test_data["cases"]["update"]["payload"]

        response = await _async_client.put(
            f"{self.base_url}/heroes/{_hero.uuid}",
            json=payload,
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["update"]["want"]

        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == got["uuid"])
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_patch(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        payload = _test_data["cases"]["patch"]["payload"]

        response = await _async_client.patch(
            f"{self.base_url}/heroes/{_hero.uuid}",
            json=payload,
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["patch"]["want"]

        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == got["uuid"])
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_delete(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        response = await _async_client.delete(
            f"{self.base_url}/heroes/{_hero.uuid}",
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["delete"]["want"]

        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == _hero.uuid)
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero
        assert hero.deleted_at is not None

    @pytest.mark.asyncio
    async def test_search(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        payload = _test_data["cases"]["search"]["payload"]

        response = await _async_client.post(
            f"{self.base_url}/heroes/search",
            json=payload,
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["search"]["want"]

        assert_response(got=got, want=want)

    @pytest.mark.asyncio
    async def test_search_no_results(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        payload = _test_data["cases"]["search_no_results"]["payload"]

        response = await _async_client.post(
            f"{self.base_url}/heroes/search",
            json=payload,
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["search_no_results"]["want"]

        assert_response(got=got, want=want)


class TestHeroAsStaff:
    """Tests for hero module as staff."""

    base_url = "/v1"

    # |Fixtures|
    @pytest_asyncio.fixture
    async def _deleted_hero(
        self,
        _async_session: "AsyncSession",
        _hero: "Hero",
    ):
        _hero.deleted_at = datetime.utcnow()
        await _async_session.commit()
        await _async_session.refresh(_hero)
        return _hero

    # |Tests|
    @pytest.mark.asyncio
    async def test_get(
        self,
        _async_client: "AsyncClient",
        _async_session: "AsyncSession",
        _deleted_hero: "Hero",
        _test_data: dict,
    ):
        response = await _async_client.get(
            f"{self.base_url}/heroes/{_deleted_hero.uuid}",
        )

        assert response.status_code == 404

        statement = select(Hero).where(Hero.uuid == _deleted_hero.uuid)
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_get_as_staff(
        self,
        _async_client_as_staff: "AsyncClient",
        _async_session: "AsyncSession",
        _deleted_hero: "Hero",
        _test_data: dict,
    ):
        response = await _async_client_as_staff.get(
            f"{self.base_url}/heroes/{_deleted_hero.uuid}",
        )

        assert response.status_code == 200

        statement = select(Hero).where(Hero.uuid == _deleted_hero.uuid)
        results = await _async_session.execute(statement=statement)
        hero: Hero = results.scalar_one()

        assert hero

    @pytest.mark.asyncio
    async def test_delete_permanently(
        self,
        _async_client_as_staff: "AsyncClient",
        _async_session: "AsyncSession",
        _hero: "Hero",
        _test_data: dict,
    ):
        hero_uuid = _hero.uuid
        response = await _async_client_as_staff.delete(
            f"{self.base_url}/heroes/{hero_uuid}",
            params={"permanent": True},
        )

        assert response.status_code == 200

        statement = select(Hero).where(Hero.uuid == hero_uuid)
        results = await _async_session.execute(statement=statement)
        hero: Hero | None = results.scalar_one_or_none()

        assert hero is None
