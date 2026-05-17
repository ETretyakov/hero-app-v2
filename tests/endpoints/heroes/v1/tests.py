"""Integration tests for the Hero endpoints (public and admin).

Each test class covers one "actor" (anonymous public user vs. staff):

- ``TestHero``       — public CRUD and search via ``/public/v1/heroes``
- ``TestHeroAsStaff`` — admin-only endpoints via ``/admin/v1/heroes``,
                        including soft-deleted record visibility and
                        permanent deletion

All tests receive a rolled-back ``AsyncSession`` from conftest so that
database changes are never persisted between test runs.
"""

from datetime import datetime, timezone

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.modules.heroes.crud.models import Hero
from tests.utils.assertions import assert_response


class TestHero:
    """Public CRUD and search endpoints: no authentication required."""

    # Full path prefix so requests land on the correct FastAPI router.
    # ``_async_client`` uses ``base_url="http://testserver"`` and the client
    # receives absolute paths, so the prefix must be included here.
    base_url = f"{config.prefixes.public}/v1"

    async def test_create(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _test_data: dict,
    ):
        """POST /heroes creates a new hero and returns HTTP 201."""
        payload = _test_data["cases"]["create"]["payload"]

        response = await _async_client.post(
            f"{self.base_url}/heroes",
            json=payload,
        )

        assert response.status_code == 201

        got = response.json()
        want = _test_data["cases"]["create"]["want"]
        assert_response(got=got, want=want)

        # Verify the record actually exists in the database
        statement = select(Hero).where(Hero.uuid == got["uuid"])
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_get(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """GET /heroes/{uuid} returns the hero and HTTP 200."""
        response = await _async_client.get(
            f"{self.base_url}/heroes/{_hero.uuid}",
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["get"]["want"]
        assert_response(got=got, want=want)

        statement = select(Hero).where(Hero.uuid == got["uuid"])
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_update(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """PUT /heroes/{uuid} replaces all mutable fields and returns HTTP 200."""
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
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_patch(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """PATCH /heroes/{uuid} updates only the supplied fields and returns HTTP 200."""
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
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_delete(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """DELETE /heroes/{uuid} soft-deletes the hero (sets deleted_at) and returns HTTP 200."""
        response = await _async_client.delete(
            f"{self.base_url}/heroes/{_hero.uuid}",
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["delete"]["want"]
        assert_response(got=got, want=want)

        # The row must still exist — soft delete only sets deleted_at
        statement = select(Hero).where(Hero.uuid == _hero.uuid)
        result = await _async_session.execute(statement)
        hero = result.scalar_one()
        assert hero.deleted_at is not None

    async def test_search(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """POST /heroes/search returns matching heroes with count."""
        payload = _test_data["cases"]["search"]["payload"]

        response = await _async_client.post(
            f"{self.base_url}/heroes/search",
            json=payload,
        )

        assert response.status_code == 200

        got = response.json()
        want = _test_data["cases"]["search"]["want"]
        assert_response(got=got, want=want)

    async def test_search_no_results(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """POST /heroes/search returns count=0 and empty items when nothing matches."""
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
    """Admin-only hero endpoints: require a valid ``access_token`` header."""

    base_url = f"{config.prefixes.admin}/v1"

    # ------------------------------------------------------------------
    # Fixtures local to this class
    # ------------------------------------------------------------------

    @pytest_asyncio.fixture
    async def _deleted_hero(
        self,
        _async_session: AsyncSession,
        _hero: Hero,
    ) -> Hero:
        """Return a hero that has already been soft-deleted in the database."""
        _hero.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await _async_session.commit()
        await _async_session.refresh(_hero)
        return _hero

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    async def test_get_returns_404_for_deleted_hero_via_public_client(
        self,
        _async_client: AsyncClient,
        _async_session: AsyncSession,
        _deleted_hero: Hero,
        _test_data: dict,
    ):
        """The public GET endpoint returns 404 for soft-deleted heroes."""
        public_url = f"{config.prefixes.public}/v1"
        response = await _async_client.get(
            f"{public_url}/heroes/{_deleted_hero.uuid}",
        )

        assert response.status_code == 404

        # Confirm the row is still in the DB (soft delete, not hard delete)
        statement = select(Hero).where(Hero.uuid == _deleted_hero.uuid)
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_get_as_staff(
        self,
        _async_client_as_staff: AsyncClient,
        _async_session: AsyncSession,
        _deleted_hero: Hero,
        _test_data: dict,
    ):
        """The admin GET endpoint returns 200 even for soft-deleted heroes."""
        response = await _async_client_as_staff.get(
            f"{self.base_url}/heroes/{_deleted_hero.uuid}",
        )

        assert response.status_code == 200

        statement = select(Hero).where(Hero.uuid == _deleted_hero.uuid)
        result = await _async_session.execute(statement)
        assert result.scalar_one() is not None

    async def test_delete_permanently(
        self,
        _async_client_as_staff: AsyncClient,
        _async_session: AsyncSession,
        _hero: Hero,
        _test_data: dict,
    ):
        """DELETE /heroes/{uuid}?permanent=true removes the row from the database entirely."""
        hero_uuid = _hero.uuid

        response = await _async_client_as_staff.delete(
            f"{self.base_url}/heroes/{hero_uuid}",
            params={"permanent": True},
        )

        assert response.status_code == 200

        statement = select(Hero).where(Hero.uuid == hero_uuid)
        result = await _async_session.execute(statement)
        assert result.scalar_one_or_none() is None
