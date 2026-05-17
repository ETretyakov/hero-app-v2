# hero-app-v2

A template for building production-ready REST API services with Python. Demonstrates a clean layered architecture: **API → Services → CRUD → Database**, built on FastAPI, SQLAlchemy 2.0, and PostgreSQL.

## Features

- **Async-first** — FastAPI + asyncpg + SQLAlchemy async sessions throughout
- **Layered architecture** — strict separation of API, business logic, and data access
- **Generic CRUD base** — reusable class with insert, select, update, delete, count, and paginated search
- **Soft deletes** — records are marked with `deleted_at` instead of being removed
- **Role-based access** — public endpoints for regular users, admin endpoints protected by API key
- **Migrations** — Alembic with auto-generated naming conventions for constraints and indexes
- **Docker-ready** — `Dockerfile` + `docker-compose.yml` for one-command startup
- **Testcontainers** — integration tests spin up a real PostgreSQL container automatically

---

## Stack

| Layer | Technology |
|---|---|
| Web framework | [FastAPI](https://fastapi.tiangolo.com) |
| ORM | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) (async) |
| Database | PostgreSQL 16 |
| Async driver | asyncpg |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Tests | pytest + pytest-asyncio + httpx + testcontainers |
| Packaging | Poetry |

---

## Project structure

```
app/
├── config/          # Application settings via pydantic-settings
├── db/
│   └── postgresql/
│       ├── base.py          # SQLAlchemy engine & session factory
│       ├── crud.py          # Generic CRUD base class
│       ├── decorators.py    # @transaction decorator
│       ├── dependencies.py  # FastAPI dependency injection for session
│       ├── models.py        # Reusable ORM mixins (ID, Timestamp, Deleted)
│       └── migrations/      # Alembic migrations
├── entrypoints/     # App factory & uvicorn runner
├── exceptions/      # Typed HTTP exceptions (403, 404, 409)
├── modules/
│   ├── auth/        # API key authentication
│   └── heroes/      # Feature module: API, services, CRUD, schemas
├── routers/         # Router registration with prefix configuration
├── types/           # Enums with PostgreSQL ENUM support
└── utils/           # Base Pydantic schemas, decorators
tests/
├── conftest.py      # Fixtures: testcontainers DB, async session, HTTP clients
├── endpoints/       # Integration tests
├── factory.py       # Test data factory
└── fixtures/        # pytest fixtures per module
```

---

## Getting started

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for running the app and tests via testcontainers)

### Environment variables

Copy `.env-example` to `.env` and adjust values:

```bash
cp .env-example .env
```

| Variable | Default | Description |
|---|---|---|
| `APP_TITLE` | `FastAPI Service` | Service title shown in Swagger |
| `APP_HOST` | `0.0.0.0` | Uvicorn bind host |
| `APP_PORT` | `8080` | Uvicorn bind port |
| `APP_DEBUG` | `false` | Enable SQLAlchemy query logging |
| `APP_RELOAD` | `false` | Uvicorn auto-reload on code change |
| `PREFIX_PUBLIC` | `/public` | Prefix for public API routes |
| `PREFIX_ADMIN` | `/admin` | Prefix for admin API routes |
| `POSTGRESQL_DSN` | — | Full DSN, e.g. `postgresql+asyncpg://user:pass@host:5432/db` |
| `SECURITY_API_KEY` | `secret_key` | Token for admin endpoints (`access_token` header) |

---

## Makefile

All common tasks are available via `make`. Run `make help` to see the full list.

```
make help
```

```
  install              Create .venv and install all dependencies via pip
  install-deps         Install/sync dependencies into an existing .venv (no poetry)
  lint                 Run flake8 linter
  format               Auto-format code with black and sort imports with isort
  format-check         Check formatting without modifying files (CI-friendly)
  test                 Run the full test suite (requires Docker for testcontainers)
  test-fast            Run tests, stop on first failure
  test-cov             Run tests with coverage report
  migrate              Apply all pending Alembic migrations
  migrate-down         Roll back the last Alembic migration
  migrate-create       Generate a new migration (see usage below)
  migrate-history      Show migration history
  up                   Start all services (db + app) in the background
  up-db                Start only the database service
  down                 Stop and remove all containers (keeps volumes)
  down-v               Stop containers and delete volumes (full reset)
  logs                 Tail logs from all running services
  build                Re-build the app Docker image
  run                  Run the app locally (requires a running DB and .env file)
  clean                Remove __pycache__ and .pytest_cache directories
```

### Quick start with Make

```bash
# 1. Create the virtual environment and install dependencies
make install

# 2. Start the database
make up-db

# 3. Apply migrations
make migrate

# 4. Run the service locally
make run
```

### Common workflows

```bash
# Run all tests (Docker must be running — testcontainers handles the DB)
make test

# Stop on first failure
make test-fast

# Check and fix code style
make format
make lint

# Create a new migration after changing a model
make migrate-create name="add_hero_level_column"

# Full Docker reset (removes volumes)
make down-v
```

---

## Running with Docker

The fastest way to get the service running:

```bash
make up
```

Or without Make:

```bash
docker compose up --build
```

This starts PostgreSQL and the app. Migrations run automatically on startup via `entrypoint.sh`.

The API will be available at `http://localhost:8080`.

---

## Running locally

```bash
make install   # create .venv and install deps
make up-db     # start only the database in Docker
make migrate   # apply migrations
make run       # start the service
```

---

## API

Interactive docs are available at `http://localhost:8080/docs` (Swagger UI) and `http://localhost:8080/redoc`.

### Public endpoints — `/public/v1/heroes`

| Method | Path | Description |
|---|---|---|
| `POST` | `/heroes` | Create a hero |
| `GET` | `/heroes/{hero_id}` | Get a hero by UUID |
| `PUT` | `/heroes/{hero_id}` | Full update |
| `PATCH` | `/heroes/{hero_id}` | Partial update |
| `DELETE` | `/heroes/{hero_id}` | Soft delete |
| `POST` | `/heroes/search` | Search with filters and pagination |

### Admin endpoints — `/admin/v1/heroes`

Require the `access_token` header with the value of `SECURITY_API_KEY`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/heroes/{hero_id}` | Get a hero (including soft-deleted) |
| `DELETE` | `/heroes/{hero_id}?permanent=true` | Hard delete |
| `POST` | `/heroes/search` | Search including deleted records |

### Hero model

```json
{
  "uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "nickname": "Gandalf",
  "role": "mage",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00",
  "deleted_at": null
}
```

Available roles: `mage`, `assassin`, `warrior`, `priest`, `tank`.

### Search request example

```json
{
  "nickname": "gan",
  "role": "mage",
  "offset": 0,
  "limit": 10,
  "order_by": [{"field": "created_at", "desc": true}]
}
```

---

## Tests

Tests use [testcontainers](https://testcontainers-python.readthedocs.io/) to spin up a real PostgreSQL instance in Docker — no external database setup required.

```bash
make test
```

Each test runs inside a rolled-back transaction so tests are fully isolated and leave no data behind. Docker must be running.

---

## Migrations

```bash
# Apply all migrations
make migrate

# Create a new migration after model changes
make migrate-create name="add_hero_level_column"

# Rollback one step
make migrate-down

# Show history
make migrate-history
```

---

## License

MIT
