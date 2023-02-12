from sqlalchemy import String

from app.db.postgresql.base import Base

from sqlalchemy.orm import Mapped, mapped_column

from app.db.postgresql.models import ID, Timestamp, Deleted
from app.types.heroes import RoleType


class Hero(Base, Deleted, Timestamp, ID):
    """Declaration of the hero model that reflects as database table."""

    __tablename__ = "hrs_heroes"

    # |Types|
    ROLE = RoleType

    # |Fields|
    nickname: Mapped[str] = mapped_column(
        "nickname",
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    role: Mapped[RoleType] = mapped_column(
        "role",
        RoleType.as_pg_enum(name=RoleType.pg_name()),
        nullable=False,
    )

    def __repr__(self):
        return f"<Hero uuid={self.uuid} nickname={self.nickname}>"
