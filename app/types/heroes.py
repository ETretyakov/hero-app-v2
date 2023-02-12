from sqlalchemy import event

from app.db.postgresql.base import Base
from app.types.base import BaseEnum


# |Declaration|
class RoleType(BaseEnum):
    """Enum for role type."""

    MAGE = "mage"
    ASSASSIN = "assassin"
    WARRIOR = "warrior"
    PRIEST = "priest"
    TANK = "tank"

    @classmethod
    def pg_name(cls) -> str:
        return "hrs_roles"


# |Events|
@event.listens_for(Base.metadata, "before_create")
def _create_enums(metadata, conn, **kwargs):  # noqa: keep parameters
    RoleType.as_pg_enum(name=RoleType.pg_name()).create(conn, checkfirst=True)
