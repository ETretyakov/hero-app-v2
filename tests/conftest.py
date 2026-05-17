"""Root conftest: shared fixtures for the entire test suite.

Database lifecycle
------------------
A real PostgreSQL instance is started inside Docker via *testcontainers* at
session scope (sync fixture — no event loop involved).  The schema is applied
once via a **synchronous** SQLAlchemy engine so the DDL step itself is also
loop-free.

Transaction isolation strategy
-------------------------------
Each test function receives a fresh ``AsyncSession`` bound to a brand-new
asyncpg connection (opened in the test's own event loop).  The async engine
uses ``NullPool`` so connections are never cached across tests — this is the
only reliable way to avoid "Future attached to a different loop" errors when
asyncpg is combined with per-test event loops.

``AsyncSession`` is created with ``join_transaction_mode="create_savepoint"``.
This turns every ``session.commit()`` call inside the application code into a
``SAVEPOINT`` release instead of a real database commit.  The outer
connection-level transaction is rolled back by the fixture at teardown, so no
state leaks between tests.

HTTP clients
-------------
Two ``AsyncClient`` fixtures are provided:
- ``_async_client``          — public (non-admin) API, no extra headers
- ``_async_client_as_staff`` — admin API with the ``access_token`` header set

Both inject the test session via FastAPI's ``dependency_overrides`` so every
in-process database call uses the same rolled-back transaction.
"""

import json
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.config import config
from app.db.postgresql.base import Base
from app.db.postgresql.dependencies import get_async_session
from app.entrypoints.main import create_app


# ---------------------------------------------------------------------------
# Platform tweaks applied before testcontainers touches Docker
# ---------------------------------------------------------------------------

# On macOS with Colima, Docker exposes its socket at a non-standard path.
# If DOCKER_HOST is not already set, fall back to the Colima socket so that
# testcontainers can reach the Docker daemon without manual env configuration.
_COLIMA_SOCK = os.path.expanduser("~/.colima/default/docker.sock")
if not os.environ.get("DOCKER_HOST") and os.path.exists(_COLIMA_SOCK):
    os.environ["DOCKER_HOST"] = f"unix://{_COLIMA_SOCK}"

# Ryuk (the testcontainers resource reaper) tries to bind-mount the Docker
# socket into a helper container.  On Colima the socket path cannot be used
# as a mount source, which causes a 500 from the daemon.  Disabling Ryuk is
# safe here because our pytest session fixture manages the container lifecycle
# explicitly via the context-manager protocol.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


# ---------------------------------------------------------------------------
# Auto-discover fixture modules under tests/fixtures/
# ---------------------------------------------------------------------------

fixtures_folder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures"
)

pytest_plugins = [
    f"tests.fixtures.{filename.split('.')[0]}"
    for filename in os.listdir(fixtures_folder)
    if not filename.startswith("_")
]


# ---------------------------------------------------------------------------
# Database infrastructure (session-scoped, fully synchronous)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start a PostgreSQL container for the entire test session.

    The container is stopped automatically when the session ends, regardless
    of whether tests pass or fail.
    """
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest.fixture(scope="session")
def _db_url(_postgres_container: PostgresContainer) -> Generator[str, None, None]:
    """Apply the full schema once via a *synchronous* psycopg2 engine.

    Using a sync engine here keeps the DDL step completely outside any
    asyncio event loop, which avoids loop-lifecycle complications.

    Yields the asyncpg-dialect URL so per-test async fixtures can build
    connections against the same database.
    """
    psycopg2_url = _postgres_container.get_connection_url()
    asyncpg_url = psycopg2_url.replace("+psycopg2", "+asyncpg", 1)

    sync_engine = create_sync_engine(psycopg2_url, echo=False)
    # before_create event in app/types/heroes.py creates the PostgreSQL ENUM
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    yield asyncpg_url

    sync_engine = create_sync_engine(psycopg2_url, echo=False)
    Base.metadata.drop_all(sync_engine)
    sync_engine.dispose()


@pytest.fixture(scope="session")
def _db_engine(_db_url: str) -> Generator[AsyncEngine, None, None]:
    """Create a session-scoped async engine.

    ``NullPool`` is used intentionally: without it, asyncpg would cache
    connections in the pool.  Those cached connections are bound to the event
    loop that opened them.  Since each test function gets its own event loop,
    reusing a pooled connection from a previous test triggers asyncpg's
    "Future attached to a different loop" error.  ``NullPool`` ensures every
    ``engine.connect()`` call opens a fresh connection in the caller's loop.
    """
    engine = create_async_engine(_db_url, poolclass=NullPool, echo=False)
    yield engine
    # NullPool holds no connections — sync disposal is sufficient
    engine.sync_engine.dispose()


# ---------------------------------------------------------------------------
# Per-test transactional session (function-scoped)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def _async_session(
    _db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session whose changes are rolled back after each test.

    A new connection is acquired from ``_db_engine`` in the **current test's
    event loop** (guaranteed fresh because of ``NullPool``).  An outer
    transaction is started immediately; the session uses
    ``join_transaction_mode="create_savepoint"`` so any ``session.commit()``
    inside application code becomes a ``SAVEPOINT`` release rather than a
    real commit.  After the test, the outer transaction is rolled back.
    """
    async with _db_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await conn.rollback()


# ---------------------------------------------------------------------------
# HTTP clients
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def _async_client(
    _async_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient pre-configured for the public API.

    ``get_async_session`` is overridden so all requests made through this
    client share the same rolled-back session as the rest of the test.

    ``base_url="http://testserver"`` — tests supply full paths (including the
    ``/public/v1`` prefix) so the router can match them correctly.
    """
    app = create_app()
    app.dependency_overrides[get_async_session] = lambda: _async_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def _async_client_as_staff(
    _async_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient pre-configured for the admin API.

    Sends ``access_token`` on every request so endpoints protected by
    ``get_api_key`` pass authentication without additional setup.
    """
    app = create_app()
    app.dependency_overrides[get_async_session] = lambda: _async_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"access_token": config.security.api_key},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Test-data loader
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def _test_data() -> dict:
    """Load ``data.json`` from the ``data/`` directory next to the running test file.

    ``PYTEST_CURRENT_TEST`` is set by pytest to a value like::

        tests/endpoints/heroes/v1/tests.py::TestHero::test_create (call)

    The fixture strips the node-id suffix to find the file path, then looks
    for ``data/data.json`` in the same directory as the test file.
    """
    raw = os.getenv("PYTEST_CURRENT_TEST", "")
    # Split off the pytest node-id suffix (e.g. "::TestClass::test_method (call)")
    file_path = raw.split("::")[0]
    directory = os.path.dirname(os.path.abspath(file_path)) if file_path else "."
    data_path = os.path.join(directory, "data", "data.json")

    if not os.path.exists(data_path):
        data_path = os.path.join("data", "data.json")

    with open(data_path) as fh:
        return json.load(fh)
