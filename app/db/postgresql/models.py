from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, func, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column


class ID:
    """Mixin that adds a UUID primary key column named ``uuid``."""

    uuid: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        # Python-side default so the PK is available on the instance before flush;
        # server_default is a fallback for raw SQL inserts that bypass the ORM.
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )


class Timestamp:
    """Mixin that adds ``created_at`` and ``updated_at`` audit columns."""

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        # onupdate (ORM-side) injects updated_at = now() into every UPDATE statement.
        # server_onupdate would only tell SQLAlchemy to re-fetch the value but does
        # not create any PostgreSQL trigger — the column would never actually change.
        onupdate=func.now(),
    )


class Deleted:
    """Mixin that adds a soft-delete ``deleted_at`` column (NULL means not deleted)."""

    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
