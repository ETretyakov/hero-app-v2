from typing import Any

from sqlalchemy import MetaData, event
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.engine import Connection

from app.db.postgresql.base import Base
from app.types.base import BaseEnum


class RoleType(BaseEnum):
    """Possible roles a hero can be assigned."""

    MAGE = "mage"
    ASSASSIN = "assassin"
    WARRIOR = "warrior"
    PRIEST = "priest"
    TANK = "tank"

    @classmethod
    def pg_name(cls) -> str:
        """Return the name of the PostgreSQL ENUM type for this role."""
        return "hrs_roles"


@event.listens_for(Base.metadata, "before_create")
def _create_enums(_metadata: MetaData, conn: Connection, **kwargs: Any) -> None:
    """Ensure all PostgreSQL ENUM types exist before any table DDL runs.

    ``checkfirst=True`` makes the CREATE TYPE a no-op if the type already
    exists, so this is safe to run on every application start and migration.
    """
    ENUM(*RoleType.values(), name=RoleType.pg_name()).create(conn, checkfirst=True)
