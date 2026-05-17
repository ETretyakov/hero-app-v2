from collections.abc import Sequence
from typing import Any, Generic, Literal, TypeVar, overload
from uuid import UUID

from sqlalchemy import TextClause, func, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.base import Base


Table = TypeVar("Table", bound=Base)


class CRUD(Generic[Table]):
    """Generic async CRUD interface. Subclasses must assign `table: type[Table]`."""

    table: type[Table]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: UUID | str) -> Table | None:
        """Fetch a single row by primary key; returns None if not found."""
        return await self.session.get(self.table, id_)

    async def insert(self, data: dict[str, Any], **kwargs: Any) -> Table:
        """Insert a row and return it populated with server-side defaults."""
        instance = self.table(**data, **kwargs)
        self.session.add(instance)
        # flush sends INSERT so the DB can populate defaults (e.g. generated PKs,
        # server_default timestamps); refresh re-reads those values into the instance
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    @overload
    async def select(
        self,
        *filters: Any,
        order_by: list[TextClause] | None = ...,
        offset: int = ...,
        limit: int = ...,
        one_or_none: Literal[True],
    ) -> Table | None: ...

    @overload
    async def select(
        self,
        *filters: Any,
        order_by: list[TextClause] | None = ...,
        offset: int = ...,
        limit: int = ...,
        one_or_none: Literal[False] = ...,
    ) -> Sequence[Table]: ...

    async def select(
        self,
        *filters: Any,
        order_by: list[TextClause] | None = None,
        offset: int = 0,
        limit: int = 10,
        one_or_none: bool = False,
    ) -> Sequence[Table] | Table | None:
        """Query rows with optional filtering, ordering, and pagination.

        Pass ``one_or_none=True`` to return a single instance (or None);
        raises ``MultipleResultsFound`` if more than one row matches.
        """
        statement = select(self.table).where(*filters)
        if order_by:
            statement = statement.order_by(*order_by)
        statement = statement.offset(offset).limit(limit)
        results = await self.session.scalars(statement)
        if one_or_none:
            return results.one_or_none()
        return results.all()

    async def update(self, id_: UUID | str, data: dict[str, Any]) -> Table | None:
        """Update a single row by PK via ORM; returns None if not found.

        Loads the instance first so ORM events and validators are triggered.
        Use ``update_many`` for bulk changes that don't need event hooks.
        """
        instance = await self.get(id_)
        if instance is None:
            return None
        for k, v in data.items():
            setattr(instance, k, v)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_many(self, *filters: Any, data: dict[str, Any]) -> None:
        """Bulk UPDATE via a single SQL statement; bypasses ORM instance loading and events."""
        statement = update(self.table).where(*filters).values(**data)
        await self.session.execute(statement)
        await self.session.flush()

    async def delete(self, id_: UUID | str) -> bool:
        """Delete a row by PK. Returns False if the row does not exist."""
        instance = await self.get(id_)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, *filters: Any) -> int:
        """Return the number of rows matching *filters*."""
        statement = select(
            func.count(inspect(self.table).primary_key[0]),
        ).where(*filters)
        return await self.session.scalar(statement) or 0  # scalar → None on empty result

    async def select_with_count(
        self,
        *filters: Any,
        order_by: list[TextClause] | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[int, Sequence[Table]]:
        """Return (total_count, page) using two separate queries."""
        return (
            await self.count(*filters),
            await self.select(*filters, order_by=order_by, offset=offset, limit=limit),
        )
