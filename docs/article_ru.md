# FastAPI + Clean Architecture: разбираем production-ready шаблон

Когда проект вырастает за пределы туториала, возникает вопрос: как организовать код так, чтобы он оставался понятным, тестируемым и расширяемым? В этой статье разберём конкретный шаблон на FastAPI, где каждый слой архитектуры имеет чёткую ответственность — и где есть несколько решений, о компромиссах которых стоит знать заранее.

Код доступен на GitHub: **https://github.com/ETretyakov/hero-app-v2**

---

## Структура проекта: что где живёт

```
app/
├── config/          # Считывание конфигурации
├── db/postgresql/   # Движок, сессии, базовый CRUD
├── modules/
│   └── heroes/
│       ├── api/     # HTTP-слой (роутеры FastAPI)
│       ├── crud/    # Доступ к данным
│       └── services/ # Бизнес-логика + схемы
├── routers/         # Агрегация роутеров по версиям
├── types/           # Базовые типы и enum-ы
└── utils/           # Общие схемы и хелперы
tests/
├── conftest.py      # Инфраструктура тестов
├── fixtures/        # Фикстуры по модулям
└── endpoints/       # Интеграционные тесты
```

Принцип прост: каждый слой знает только о том, что находится ниже него. `api` → `services` → `crud` → `db`. Слои не общаются по горизонтали и не обращаются «через голову».

---

## Считывание конфигурации

Конфигурация разбита на независимые секции с помощью `pydantic-settings`. Каждый класс отвечает за свою область и читает переменные окружения с уникальным префиксом:

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

Финальный объект `Config` собирается фабричным методом:

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

**Плюсы:** каждый раздел конфига изолирован, легко тестируется, IDE видит типы. Pydantic валидирует значения при старте — опечатка в `.env` сразу поднимает исключение, а не проявляется в рантайме.

**Минусы:** при добавлении нового раздела нужно помнить про три места: класс настроек, класс `Config` и метод `create()`.

---

## Работа с базой данных

### Движок и фабрика сессий

```python
engine: AsyncEngine = create_async_engine(
    url=config.postgresql.using_async_driver,
    echo=config.app.debug,
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    autoflush=False,
    expire_on_commit=False,  # атрибуты доступны после commit без активной сессии
)
```

`expire_on_commit=False` — принципиальное решение. По умолчанию SQLAlchemy инвалидирует атрибуты объекта после коммита, и любое обращение к ним вне транзакции бросает `DetachedInstanceError`. Для async-приложений, где объект часто возвращается из сервиса уже после закрытия сессии, это поведение почти всегда нежелательно.

### Миксины для моделей

Вместо дублирования общих полей во всех таблицах — миксины:

```python
class ID:
    uuid: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,                           # Python-side: PK готов до flush
        server_default=text("gen_random_uuid()"), # fallback для сырого SQL
    )

class Timestamp:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now(),  # ORM автоматически обновляет при UPDATE
    )

class Deleted:
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)  # soft delete
```

Модель героя собирается из этих блоков:

```python
class Hero(Base, Deleted, Timestamp, ID):
    __tablename__ = "hrs_heroes"
    nickname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[RoleType] = mapped_column(RoleType.as_pg_enum(name=RoleType.pg_name()))
```

### Соглашения об именовании ограничений

В `MetaData` прописаны шаблоны имён для всех типов ограничений:

```python
METADATA = MetaData(naming_convention={
    "pk": "pk__%(table_name)s",
    "ix": "ix__%(table_name)s__%(all_column_names)s",
    "fk": "fk__%(table_name)s__%(all_column_names)s__%(referred_table_name)s",
    "uq": "uq__%(table_name)s__%(all_column_names)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
})
```

Это критично для Alembic: без явных имён миграции генерируют анонимные ограничения, которые невозможно надёжно дропнуть в будущем.

### Базовый CRUD через Generic

```python
class CRUD(Generic[Table]):
    table: type[Table]

    async def insert(self, data: dict[str, Any]) -> Table:
        instance = self.table(**data)
        self.session.add(instance)
        await self.session.flush()           # INSERT уходит в БД
        await self.session.refresh(instance) # читаем server_default значения
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

Конкретная реализация для героя — буквально две строки:

```python
class HeroCRUD(CRUD[Hero]):
    table = Hero
```

### Транзакционный декоратор

Управление транзакциями вынесено из бизнес-логики в декоратор:

```python
def transaction(fn: F) -> F:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        commit = kwargs.pop("_commit", True)
        result = await fn(*args, **kwargs)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()  # для вложенных вызовов внутри большой транзакции
        return result
    return wrapper
```

Сервисный метод просто помечается декоратором:

```python
@transaction
@duplicate(detail="The hero already exists!")
async def create(self, schema: "HeroCreate", _commit: bool = True) -> Hero:
    return await self.heroes.insert(data=schema.model_dump())
```

---

## Сериализация и десериализация

### Два базовых класса для схем

Разделение input/output — одно из ключевых решений в шаблоне:

```python
class BaseInput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.replace(tzinfo=None)  # TIMESTAMP без tz
        return values


class BaseOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # читает ORM-объекты напрямую

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.isoformat()
        return values
```

`use_enum_values=True` в `BaseInput` гарантирует, что в словарь, который пойдёт в CRUD, попадёт строка `"mage"`, а не `RoleType.MAGE`. `from_attributes=True` в `BaseOutput` позволяет Pydantic создавать схему прямо из SQLAlchemy-объекта — без явного `.dict()` и ручного маппинга.

### Схемы героя

```python
class HeroCreate(BaseInput, HeroBase):
    """Входящие данные для создания."""

class HeroPatch(BaseInput):
    """Только изменяемые поля, все опциональные."""
    nickname: Optional[str] = None
    role: Optional[RoleType] = None

class HeroRetrieve(BaseOutput, HeroBase):
    """То, что возвращается клиенту."""
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
```

Разница между `PUT` и `PATCH` реализована через флаг `exclude_unset`:

```python
async def update(self, hero_id, schema, patch: bool = False) -> Hero | None:
    return await self.heroes.update(
        id_=hero_id,
        data=schema.model_dump(exclude_unset=patch),  # patch=True → только то, что пришло
    )
```

### Защита от ORDER BY injection

Поле сортировки пользователь передаёт сам, поэтому оно валидируется через allowlist:

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

## Инъекция сессии: удобство и его цена

В FastAPI зависимости — основной механизм передачи контекста в хэндлеры:

```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session

async def get_hero_services(
    session: AsyncSession = Depends(get_async_session),
) -> HeroServices:
    return HeroServices(session)
```

Хэндлер получает уже готовый объект `HeroServices` с сессией внутри:

```python
@public_router.post("", response_model=HeroRetrieve, status_code=201)
async def create_hero(
    schema: HeroCreate,
    heroes: HeroServices = Depends(get_hero_services),
):
    return await heroes.create(schema=schema)
```

**Плюсы:** сессия создаётся один раз на запрос, все вызовы внутри одного хэндлера участвуют в одной транзакции. Зависимости легко подменяются в тестах через `dependency_overrides`.

**Важный компромисс:** сессия живёт ровно столько, сколько живёт запрос — от первого обращения до закрытия ответа. Если хэндлер выполняет тяжёлую бизнес-логику, вызывает внешние API или обрабатывает большие данные, сессия держит соединение с базой данных на всё это время. При высокой нагрузке пул соединений PostgreSQL может исчерпаться раньше, чем вы ожидаете.

Правильный вывод здесь прямолинеен: **хэндлеры не должны быть тяжёлыми**. Если операция занимает больше нескольких сотен миллисекунд, она не должна выполняться синхронно в рамках HTTP-запроса. Тяжёлые операции — обработка изображений, отправка писем, сложные агрегации, взаимодействие с внешними сервисами — должны передаваться в фоновые задачи (Celery, ARQ, FastAPI `BackgroundTasks`). Запрос в таком случае отвечает немедленно, а сессия закрывается быстро.

Если же по архитектурным причинам тяжёлая логика всё-таки остаётся в хэндлере, сессию стоит явно закрывать сразу после последнего обращения к базе данных, не дожидаясь конца запроса.

---

## Тесты

### Инфраструктура

Тесты поднимают реальный PostgreSQL через `testcontainers` — никаких моков базы данных:

```python
@pytest.fixture(scope="session")
def _postgres_container():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container
```

Схема создаётся один раз за сессию через синхронный движок (DDL вне event loop):

```python
@pytest.fixture(scope="session")
def _db_url(_postgres_container):
    psycopg2_url = _postgres_container.get_connection_url()
    sync_engine = create_sync_engine(psycopg2_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    yield psycopg2_url.replace("+psycopg2", "+asyncpg", 1)
```

### Изоляция через SAVEPOINT

Каждый тест получает сессию, обёрнутую в транзакцию, которая откатывается после теста:

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
        await conn.rollback()  # всё, что сделал тест — исчезает
```

`join_transaction_mode="create_savepoint"` — ключевое. Когда приложение вызывает `session.commit()`, вместо реального коммита выполняется `SAVEPOINT release`. Внешняя транзакция остаётся открытой и откатывается фикстурой. Тесты полностью изолированы, база чистая после каждого.

`NullPool` на движке нужен потому, что asyncpg привязывает соединения к event loop. Каждый тест получает свой loop, поэтому пул был бы источником ошибок `"Future attached to a different loop"`.

### HTTP-клиент с переопределением зависимостей

```python
@pytest_asyncio.fixture(scope="function")
async def _async_client(_async_session):
    app = create_app()
    app.dependency_overrides[get_async_session] = lambda: _async_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
```

Одна строка `dependency_overrides` — и все запросы через клиент используют ту же изолированную тестовую сессию, что и прямые вызовы к БД в теле теста. Это позволяет проверять состояние базы напрямую после HTTP-запроса:

```python
async def test_delete(self, _async_client, _async_session, _hero):
    await _async_client.delete(f"{self.base_url}/heroes/{_hero.uuid}")

    # Проверяем, что строка осталась (soft delete, не hard delete)
    result = await _async_session.execute(select(Hero).where(Hero.uuid == _hero.uuid))
    hero = result.scalar_one()
    assert hero.deleted_at is not None
```

---

## Плюсы и минусы шаблона

**Плюсы:**

- **Явное разделение ответственности.** API-слой не знает о SQL, сервисный слой не знает о HTTP. Замена SQLAlchemy на другой ORM не затрагивает хэндлеры.
- **Generic CRUD.** Новая сущность — новый класс `MyCRUD(CRUD[MyModel])` с двумя строками кода.
- **Типобезопасность.** Pydantic валидирует на входе, `from_attributes=True` исключает ручной маппинг на выходе. Mypy и IDE счастливы.
- **Тесты с реальной БД.** Testcontainers + SAVEPOINT-изоляция — лучший из возможных вариантов: тесты проверяют реальное поведение PostgreSQL, но не оставляют мусора.
- **Соглашения об именовании.** Автоматические имена ограничений делают Alembic-миграции предсказуемыми.

**Минусы:**

- **Бойлерплейт при расширении конфига.** Три места для изменения вместо одного.
- **Сессия на весь запрос.** Удобно, но может стать проблемой при высокой нагрузке и тяжёлых хэндлерах — подробнее выше.
- **Два запроса на поиск с подсчётом.** `select_with_count` выполняет `COUNT` и `SELECT` раздельно. Для большинства случаев это нормально, но для высоконагруженных ручек поиска стоит рассмотреть `window function`.
- **Декоратор `@transaction` через `args[0]`.** Доступ к `self` через `args[0]` — негласное соглашение. Если метод переименуют в функцию или перепишут на classmethod, декоратор сломается без внятной ошибки.

---

## Запуск проекта

Для запуска нужны **Docker** и **Docker Compose**.

**1. Клонируйте репозиторий:**

```bash
git clone https://github.com/EugenyBobylev/hero-app-v2.git
cd hero-app-v2
```

**2. Создайте `.env` файл** (пример уже есть в репозитории как `.env.example`):

```env
APP_TITLE=Hero Service
APP_DEBUG=false
POSTGRESQL_DSN=postgresql+asyncpg://hero:heroPass123@db:5432/heroes_db
SECURITY_API_KEY=your_secret_key
```

**3. Поднимите сервисы:**

```bash
docker compose up --build
```

Docker Compose запустит PostgreSQL и само приложение. Сервис будет доступен на `http://localhost:8080`.

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- Health check: `http://localhost:8080/health_check`

**4. Запуск тестов** (тесты сами поднимают PostgreSQL через testcontainers, отдельный docker compose не нужен):

```bash
# Локально, если установлен Python 3.12+ и Poetry
poetry install
poetry run pytest
```

---

## Итого

Шаблон демонстрирует практичный подход к организации FastAPI-приложения: чёткие слои, типобезопасность от запроса до базы данных, тесты с реальной инфраструктурой. Это не Silver Bullet, но хорошая отправная точка для сервиса, который должен жить и развиваться.

Главное, что стоит помнить при его использовании: архитектура с инъекцией сессии через зависимость FastAPI предполагает, что хэндлеры быстрые. Как только в них появляется тяжёлая логика — выносите её в фоновые задачи. Тогда пул соединений будет вашим другом, а не узким местом.
