from sqlalchemy import MetaData
from sqlalchemy.ext import asyncio as sa_async
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import config


METADATA = MetaData(
    naming_convention={
        "all_column_names": lambda constraint, table: "_".join(
            [column.name for column in constraint.columns.values()],
        ),
        "pk": "pk__%(table_name)s",
        "ix": "ix__%(table_name)s__%(all_column_names)s",
        "fk": "fk__%(table_name)s__%(all_column_names)s__"
        "%(referred_table_name)s",
        "uq": "uq__%(table_name)s__%(all_column_names)s",
        "ck": "ck__%(table_name)s__%(constraint_name)s",
    },
)


engine: sa_async.AsyncEngine = sa_async.create_async_engine(
    url=config.postgresql.using_async_driver,
    echo=config.app.debug,
    future=True,
)

SessionFactory = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=sa_async.AsyncSession,
)

Base = declarative_base(metadata=METADATA)
