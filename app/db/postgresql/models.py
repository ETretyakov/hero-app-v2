from datetime import datetime
from uuid import uuid4

from sqlalchemy import TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class ID:
    """Mixin class for SQLAlchemy models uuid field."""

    uuid: Mapped[UUID] = mapped_column(
        "uuid",
        UUID(as_uuid=True),
        default=uuid4,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        unique=True,
        nullable=False,
        index=True,
    )


class Timestamp:
    """Mixin class for SQLAlchemy models created_at & updated_at fields."""

    created_at: Mapped[datetime] = mapped_column(
        "created_at",
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        TIMESTAMP,
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )


class Deleted:
    """Mixin class for SQLAlchemy models deleted_at field."""

    deleted_at: Mapped[datetime] = mapped_column(
        "deleted_at",
        TIMESTAMP,
        nullable=True,
    )
