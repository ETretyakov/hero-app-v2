from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgresql.base import Base
from app.db.postgresql.models import Deleted, ID, Timestamp
from app.types.heroes import RoleType


class Hero(Base, Deleted, Timestamp, ID):
    """ORM model for the ``hrs_heroes`` table.

    Inherits ``uuid`` (PK) from ``ID``, audit timestamps from ``Timestamp``,
    and soft-delete support from ``Deleted``.
    """

    __tablename__ = "hrs_heroes"

    # Convenience alias so callers can write Hero.ROLE.MAGE instead of importing RoleType directly
    ROLE = RoleType

    nickname: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # The PostgreSQL ENUM type is pre-created via a before_create event in app/types/heroes.py
    role: Mapped[RoleType] = mapped_column(RoleType.as_pg_enum(name=RoleType.pg_name()))

    def __repr__(self) -> str:
        return f"<Hero uuid={self.uuid} nickname={self.nickname}>"
