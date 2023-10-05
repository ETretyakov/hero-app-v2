from typing import Generic, Optional, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import TextClause, func, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.base import Base


Table = TypeVar("Table", bound=Base)


class CRUD(Generic[Table]):
    """Describes basic methods for managing table records."""

    table: Type[Table]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id_: UUID | str) -> Optional[Table]:
        return await self.session.get(self.table, id_)

    async def insert(self, data: dict, **kwargs) -> Table:
        instance = self.table(**data, **kwargs)

        self.session.add(instance=instance)
        await self.session.flush()
        await self.session.refresh(instance=instance)

        return instance

    async def select(
        self,
        *filters,
        order_by: Optional[list["TextClause"]] = None,
        offset: int = 0,
        limit: int = 10,
        one_or_none: bool = False,
    ) -> Sequence[Table] | Optional[Table]:
        statement = select(self.table).where(*filters)

        if order_by:
            statement = statement.order_by(*order_by)

        statement = statement.offset(offset=offset).limit(limit=limit)
        results = await self.session.scalars(statement=statement)

        if one_or_none:
            return results.one_or_none()
        else:
            return results.all()

    async def update(self, id_: UUID | str, data: dict) -> Optional[Table]:
        instance = await self.get(id_=id_)
        if instance is None:
            return None

        for k, v in data.items():
            setattr(instance, k, v)

        self.session.add(instance=instance)

        await self.session.flush()
        await self.session.refresh(instance=instance)

        return instance

    async def update_many(self, *filters, data: dict) -> bool:
        statement = update(self.table).where(*filters).values(data)
        await self.session.execute(statement=statement)
        await self.session.flush()

        return True

    async def delete(self, id_: UUID | str) -> Optional[bool]:
        instance = await self.get(id_=id_)
        if instance is None:
            return None

        await self.session.delete(instance=instance)
        await self.session.flush()

        return True

    async def count(
        self,
        *filters,
        order_by: Optional[list["TextClause"]] = None,
    ) -> int:
        statement = select(
            func.count(inspect(self.table).primary_key[0]),
        ).where(*filters)

        if order_by:
            statement = statement.order_by(*order_by)

        return await self.session.scalar(statement=statement)

    async def select_with_count(
        self,
        *filters,
        order_by: Optional[list["TextClause"]] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[int, Optional[Sequence[Table]]]:
        return (
            await self.count(*filters),
            await self.select(
                *filters,
                order_by=order_by,
                offset=offset,
                limit=limit,
            ),
        )
