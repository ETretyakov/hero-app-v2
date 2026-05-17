# FastAPI + Clean Architecture: a production-ready template walkthrough

Once a project outgrows a tutorial, the question inevitably comes up: how do you organise the code so it stays readable, testable, and extensible? This article walks through a concrete FastAPI template where every architectural layer has a clear responsibility — and where several design decisions come with trade-offs worth knowing upfront.

Source code: **https://github.com/ETretyakov/hero-app-v2**

---

## Project structure: what lives where

```
app/
├── config/          # Configuration loading
├── db/postgresql/   # Engine, sessions, base CRUD
├── modules/
│   └── heroes/
│       ├── api/     # HTTP layer (FastAPI routers)
│       ├── crud/    # Data access
│       └── services/ # Business logic + schemas
├── routers/         # Router aggregation per API version
├── types/           # Base types and enums
└── utils/           # Shared schemas and helpers
tests/
├── conftest.py      # Test infrastructure
├── fixtures/        # Per-module fixtures
└── endpoints/       # Integration tests
```

The rule is simple: each layer only knows about what is below it. `api` → `services` → `crud` → `db`. Layers do not communicate horizontally and do not skip levels.

---

## Configuration loading

Configuration is split into independent sections using `pydantic-settings`. Each class is responsible for its own domain and reads environment variables with a unique prefix:

```python
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", ...)
    title: str = "FastAPI Service"
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False

class PostgreSQL(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRESQL_", ...)
    dsn: str = "postgresql+asyncpg://user:password@127.0.0.1:5432/db"
```

The final `Config` object is assembled via a factory method:

```python
class Config(BaseSettings):
    app: AppSettings
    prefixes: APIPrefixes
    postgresql: PostgreSQL
    security: Security

    @classmethod
    def create(cls) -> "Config":
        return Config(
            app=AppSettings(),
            prefixes=APIPrefixes(),
            postgresql=PostgreSQL(),
            security=Security(),
        )
```

**Pros:** each config section is isolated and easily testable; the IDE sees types everywhere. Pydantic validates values at startup — a typo in `.env` raises an exception immediately instead of surfacing at runtime.

**Cons:** adding a new section requires touching three places: the settings class, the `Config` class, and the `create()` method.

---

## Database layer

### Engine and session factory

```python
engine: AsyncEngine = create_async_engine(
    url=config.postgresql.using_async_driver,
    echo=config.app.debug,
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    autoflush=False,
    expire_on_commit=False,  # attributes stay accessible after commit without an active session
)
```

`expire_on_commit=False` is a deliberate choice. By default SQLAlchemy invalidates object attributes after a commit, and any access outside a transaction raises `DetachedInstanceError`. In async applications where an object is often returned from a service after the session has already been closed, this default behaviour is almost always undesirable.

### Model mixins

Instead of duplicating common fields across all tables, the project uses mixins:

```python
class ID:
    uuid: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,                           # Python-side: PK available before flush
        server_default=text("gen_random_uuid()"), # fallback for raw SQL inserts
    )

class Timestamp:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),  # ORM injects updated_at = now() on every UPDATE
    )

class Deleted:
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)  # soft delete
```

The Hero model is composed from these building blocks:

```python
class Hero(Base, Deleted, Timestamp, ID):
    __tablename__ = "hrs_heroes"
    nickname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[RoleType] = mapped_column(RoleType.as_pg_enum(name=RoleType.pg_name()))
```

### Constraint naming conventions

`MetaData` carries name templates for every constraint type:

```python
METADATA = MetaData(naming_convention={
    "pk": "pk__%(table_name)s",
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
})
```

This is critical for Alembic: without explicit names, migrations generate anonymous constraints that cannot be reliably dropped later.

### Generic base CRUD

```python
class CRUD(Generic[Table]):
    table: type[Table]

    async def insert(self, data: dict[str, Any]) -> Table:
        instance = self.table(**data)
        self.session.add(instance)
        await self.session.flush()           # sends INSERT so the DB populates defaults
        await self.session.refresh(instance) # re-reads server_default values
        return instance

    async def update(self, id_: UUID | str, data: dict[str, Any]) -> Table | None:
        instance = await self.get(id_)
        if instance is None:
            return None
        for k, v in data.items():
            setattr(instance, k, v)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
```

The concrete implementation for Hero is literally two lines:

```python
class HeroCRUD(CRUD[Hero]):
    table = Hero
```

### Transaction decorator

Transaction management is extracted from business logic into a decorator:

```python
def transaction(fn: F) -> F:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        commit = kwargs.pop("_commit", True)
        result = await fn(*args, **kwargs)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()  # for nested calls inside a larger transaction
        return result
    return wrapper
```

A service method is simply annotated:

```python
@transaction
@duplicate(detail="The hero already exists!")
async def create(self, schema: "HeroCreate", _commit: bool = True) -> Hero:
    return await self.heroes.insert(data=schema.model_dump())
```

---

## Serialisation and deserialisation

### Two base schema classes

Splitting input and output is one of the key decisions in this template:

```python
class BaseInput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.replace(tzinfo=None)  # TIMESTAMP column has no tz
        return values


class BaseOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # reads ORM objects directly

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.isoformat()
        return values
```

`use_enum_values=True` on `BaseInput` ensures that the dict passed to CRUD contains the string `"mage"` rather than `RoleType.MAGE`. `from_attributes=True` on `BaseOutput` lets Pydantic build a schema directly from a SQLAlchemy object — no manual `.dict()` call or field mapping needed.

### Hero schemas

```python
class HeroCreate(BaseInput, HeroBase):
    """Incoming data for creation."""

class HeroPatch(BaseInput):
    """Only mutable fields, all optional."""
    nickname: Optional[str] = None
    role: Optional[RoleType] = None

class HeroRetrieve(BaseOutput, HeroBase):
    """What is returned to the client."""
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
```

The difference between `PUT` and `PATCH` is handled via the `exclude_unset` flag:

```python
async def update(self, hero_id, schema, patch: bool = False) -> Hero | None:
    return await self.heroes.update(
        id_=hero_id,
        data=schema.model_dump(exclude_unset=patch),  # patch=True → only provided fields
    )
```

### Protection against ORDER BY injection

The sort field comes from user input, so it is validated against an allowlist:

```python
class OrderByField(BaseModel):
    allowed_fields: ClassVar[frozenset[str]] = frozenset()
    field: str = "updated_at"
    desc: bool = True

    @field_validator("field")
    @classmethod
    def validate_allowed_field(cls, v: str) -> str:
        if cls.allowed_fields and v not in cls.allowed_fields:
            raise ValueError(f"'{v}' is not a sortable field.")
        return v

class HeroOrderByField(OrderByField):
    allowed_fields: ClassVar[frozenset[str]] = frozenset({
        "uuid", "nickname", "role", "created_at", "updated_at", "deleted_at",
    })
```

---

## Session injection: convenience and its cost

In FastAPI, dependencies are the primary mechanism for passing context into handlers:

```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session

async def get_hero_services(
    session: AsyncSession = Depends(get_async_session),
) -> HeroServices:
    return HeroServices(session)
```

A handler receives a ready-to-use `HeroServices` object with the session already inside:

```python
@public_router.post("", response_model=HeroRetrieve, status_code=201)
async def create_hero(
    schema: HeroCreate,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.create(schema=schema)
```

**Pros:** the session is created once per request; all calls within a single handler participate in the same database transaction. Dependencies are trivially replaced in tests via `dependency_overrides`.

**An important trade-off:** the session lives exactly as long as the request — from the first use until the response is closed. If a handler runs heavy business logic, calls external APIs, or processes large datasets, the session holds a database connection for the entire duration. Under high load the PostgreSQL connection pool can be exhausted sooner than you expect.

The conclusion is straightforward: **handlers should be fast**. If an operation takes more than a few hundred milliseconds it should not run synchronously inside an HTTP request. Heavy work — image processing, sending emails, complex aggregations, calls to external services — should be handed off to background tasks (Celery, ARQ, FastAPI `BackgroundTasks`). The request returns immediately, and the session closes quickly.

If heavy logic must stay in the handler for architectural reasons, the session should be explicitly closed right after the last database call, without waiting for the end of the request.

---

## Tests

### Infrastructure

Tests spin up a real PostgreSQL instance via `testcontainers` — no database mocks:

```python
@pytest.fixture(scope="session")
def _postgres_container():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container
```

The schema is created once per session via a synchronous engine (DDL outside the event loop):

```python
@pytest.fixture(scope="session")
def _db_url(_postgres_container):
    psycopg2_url = _postgres_container.get_connection_url()
    sync_engine = create_sync_engine(psycopg2_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    yield psycopg2_url.replace("+psycopg2", "+asyncpg", 1)
```

### Isolation via SAVEPOINT

Each test receives a session wrapped in a transaction that is rolled back after the test:

```python
@pytest_asyncio.fixture(scope="function")
async def _async_session(_db_engine):
    async with _db_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        await session.close()
        await conn.rollback()  # everything the test did disappears
```

`join_transaction_mode="create_savepoint"` is the key setting here. When application code calls `session.commit()`, it becomes a `SAVEPOINT` release instead of a real commit. The outer connection-level transaction stays open and is rolled back by the fixture. Tests are fully isolated; the database is clean after every one of them.

`NullPool` on the engine is required because asyncpg binds connections to the event loop. Each test gets its own loop, so a pooled connection from a previous test would trigger `"Future attached to a different loop"` errors.

### HTTP client with dependency override

```python
@pytest_asyncio.fixture(scope="function")
async def _async_client(_async_session):
    app = create_app()
    app.dependency_overrides[get_async_session] = lambda: _async_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
```

One line of `dependency_overrides` and every request through the client shares the same rolled-back session as direct database calls in the test body. This makes it possible to verify database state immediately after an HTTP call:

```python
async def test_delete(self, _async_client, _async_session, _hero):
    await _async_client.delete(f"{self.base_url}/heroes/{_hero.uuid}")

    # The row must still exist — soft delete only sets deleted_at
    result = await _async_session.execute(select(Hero).where(Hero.uuid == _hero.uuid))
    hero = result.scalar_one()
    assert hero.deleted_at is not None
```

---

## Pros and cons of the template

**Pros:**

- **Explicit separation of concerns.** The API layer knows nothing about SQL; the service layer knows nothing about HTTP. Swapping SQLAlchemy for another ORM does not touch any handler.
- **Generic CRUD.** Adding a new entity means writing `MyCRUD(CRUD[MyModel])` with two lines of code.
- **Type safety end-to-end.** Pydantic validates at input; `from_attributes=True` eliminates manual mapping at output. Mypy and the IDE are happy.
- **Tests against a real database.** Testcontainers + SAVEPOINT isolation is the best available option: tests verify real PostgreSQL behaviour and leave no state behind.
- **Constraint naming conventions.** Automatic constraint names make Alembic migrations predictable and safe.

**Cons:**

- **Boilerplate when extending config.** Three places to change instead of one.
- **Session lives for the entire request.** Convenient, but can become a bottleneck under high load with heavy handlers — see the section above.
- **Two queries for paginated search.** `select_with_count` runs `COUNT` and `SELECT` separately. Fine for most cases, but for high-traffic search endpoints a window function approach is worth considering.
- **`@transaction` accesses `self` via `args[0]`.** This is an implicit convention. If the wrapped method is ever turned into a plain function or a classmethod, the decorator will break without an obvious error message.

---

## Running the project

**Docker** and **Docker Compose** must be installed.

**1. Clone the repository:**

```bash
git clone https://github.com/EugenyBobylev/hero-app-v2.git
cd hero-app-v2
```

**2. Create a `.env` file** (an `.env.example` is included in the repository):

```env
APP_TITLE=Hero Service
APP_DEBUG=false
POSTGRESQL_DSN=postgresql+asyncpg://hero:heroPass123@db:5432/heroes_db
SECURITY_API_KEY=your_secret_key
```

**3. Start the services:**

```bash
docker compose up --build
```

Docker Compose will start PostgreSQL and the application. The service will be available at `http://localhost:8080`.

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- Health check: `http://localhost:8080/health_check`

**4. Run the tests** (tests spin up their own PostgreSQL via testcontainers — no separate docker compose needed):

```bash
# Locally, with Python 3.12+ and Poetry installed
poetry install
poetry run pytest
```

---

## Summary

The template demonstrates a pragmatic approach to organising a FastAPI application: clear layers, type safety from request to database, and tests backed by real infrastructure. It is not a silver bullet, but it is a solid starting point for a service that needs to grow.

The most important thing to remember when using it: the session-injection architecture assumes that handlers are fast. The moment heavy logic appears inside a handler, move it to a background task. That way the connection pool stays your ally instead of becoming your bottleneck.
