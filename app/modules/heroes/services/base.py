from datetime import datetime
from typing import TYPE_CHECKING, Sequence, Union
from uuid import UUID

from sqlalchemy.sql.operators import ilike_op

from app.db.postgresql.decorators import transaction
from app.db.postgresql.utils import scalar_order_by
from app.modules.heroes.crud import HeroCRUD
from app.modules.heroes.crud.models import Hero
from app.utils.decorators import duplicate, not_found


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.heroes.services.schemas import (
        HeroCreate,
        HeroPatch,
        HeroSearch,
        HeroUpdate,
    )


class HeroServices:
    """Services to manage hero functionality."""

    def __init__(self, session: "AsyncSession"):
        self.session = session
        self.heroes = HeroCRUD(session=session)

    @transaction
    @duplicate(detail="The hero already exists!")
    async def create(
        self,
        schema: "HeroCreate",
        _commit: bool = True,
    ) -> Hero:
        return await self.heroes.insert(data=schema.dict())

    @not_found(detail="The hero hasn't been found!")
    async def get(
        self,
        hero_id: UUID | str,
        as_staff: bool = False,
        _one_or_none: bool = False,
    ) -> Hero:
        filters = [Hero.uuid == hero_id]
        if not as_staff:
            filters.append(Hero.deleted_at.is_(None))

        return await self.heroes.select(
            *filters,
            one_or_none=True,
        )

    @transaction
    @duplicate(detail="The hero already exists!")
    @not_found(detail="The hero hasn't been found!")
    async def update(
        self,
        hero_id: UUID | str,
        schema: Union["HeroUpdate", "HeroPatch"],
        patch: bool = False,
        _one_or_none: bool = False,
        _commit: bool = True,
    ) -> Hero:
        return await self.heroes.update(
            id_=hero_id,
            data=schema.dict(exclude_unset=patch),
        )

    @transaction
    @not_found(detail="The hero hasn't been found!")
    async def delete(
        self,
        hero_id: UUID | str,
        permanent: bool = False,
        _one_or_none: bool = False,
        _commit: bool = True,
    ) -> bool | None:
        if permanent:
            await self.heroes.delete(id_=hero_id)
        else:
            hero = await self.heroes.update(
                id_=hero_id,
                data={"deleted_at": datetime.utcnow()},
            )
            if hero is None:
                return hero

        return True

    async def search(
        self,
        schema: "HeroSearch",
        as_staff: bool = False,
    ) -> tuple[int, Sequence[Hero] | None]:
        filters = []

        if schema.nickname:
            filters.append(
                ilike_op(Hero.nickname, f"%{schema.nickname}%"),
            )

        if schema.role:
            filters.append(Hero.role == schema.role)

        if not as_staff:
            filters.append(Hero.deleted_at.is_(None))

        return await self.heroes.select_with_count(
            *filters,
            order_by=scalar_order_by(schema.order_by),
            limit=schema.limit,
            offset=schema.offset,
        )
