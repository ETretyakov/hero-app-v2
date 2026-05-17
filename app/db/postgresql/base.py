from typing import cast

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import config


# cast: SQLAlchemy's stub types naming_convention as Dict[str, str], but the key
# "all_column_names" accepts a callable at runtime — cast silences the false positive.
METADATA = MetaData(
    naming_convention=cast(dict[str, str], {
        "all_column_names": lambda constraint, table: "_".join(
            [column.name for column in constraint.columns.values()],
        ),
        "pk": "pk__%(table_name)s",
        "ix": "ix__%(table_name)s__%(all_column_names)s",
        "fk": "fk__%(table_name)s__%(all_column_names)s__"
        "%(referred_table_name)s",
        "uq": "uq__%(table_name)s__%(all_column_names)s",
        "ck": "ck__%(table_name)s__%(constraint_name)s",
    }),
)


engine: AsyncEngine = create_async_engine(
    url=config.postgresql.using_async_driver,
    echo=config.app.debug,
)

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    autoflush=False,
    # Keeps attributes accessible after commit without an active session.
    # Without this, accessing any attribute outside a transaction raises DetachedInstanceError.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models. Shares a single MetaData with constraint naming conventions."""

    metadata = METADATA
