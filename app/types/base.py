from enum import Enum

from sqlalchemy import Enum as SaEnum
from sqlalchemy.dialects.postgresql import ENUM


class BaseEnum(Enum):
    """Base class for PostgreSQL-backed enums.

    Subclasses gain ``values()`` for raw string extraction and ``as_pg_enum()``
    to produce a SQLAlchemy ``Enum`` type ready for column definitions.
    The actual ``CREATE TYPE`` DDL is deferred to a ``before_create`` event
    listener so the type is created with ``checkfirst=True`` rather than
    being re-created on every migration run.
    """

    @classmethod
    def values(cls) -> list[str]:
        """Return all enum member values as a plain string list."""
        return [member.value for member in cls]

    @classmethod
    def as_pg_enum(cls, name: str) -> SaEnum:
        """Build a SQLAlchemy ``Enum`` type for use in ``mapped_column`` definitions.

        Uses the generic ``Enum`` (not PostgreSQL-dialect ``ENUM``) so that
        SQLAlchemy correctly builds both ``_valid_lookup`` (Python → DB) and
        ``_object_lookup`` (DB → Python).  ``native_enum=True`` keeps the
        PostgreSQL native ``ENUM`` storage; ``create_constraint=False`` skips
        the redundant ``CHECK`` constraint since we already have the PG type.
        Type creation is handled by the ``before_create`` event (see heroes.py).
        """
        return SaEnum(
            cls,
            name=name,
            native_enum=True,
            create_constraint=False,
            values_callable=lambda x: [e.value for e in x],
        )
