from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.decorators import transaction
from app.db.postgresql.utils import scalar_order_by
from app.modules.heroes.crud import HeroCRUD
from app.modules.heroes.crud.models import Hero
from app.utils.decorators import duplicate, not_found


if TYPE_CHECKING:
    from app.modules.heroes.services.schemas import (
        HeroCreate,
        HeroPatch,
        HeroSearch,
        HeroUpdate,
    )


class HeroServices:
    """Business logic layer for hero management.

    Each mutating method is wrapped with ``@transaction``: it commits on
    success by default. Pass ``_commit=False`` to flush only — useful when
    chaining multiple service calls inside a single outer transaction.

    Methods decorated with ``@not_found`` raise HTTP 404 when the result is
    ``None``. Pass ``_one_or_none=True`` to suppress the error and get ``None``
    back instead (e.g. for optional lookups inside other service methods).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.heroes = HeroCRUD(session)

    @transaction
    @duplicate(detail="The hero already exists!")
    async def create(
        self,
        schema: "HeroCreate",
        _commit: bool = True,
    ) -> Hero:
        """Insert a new hero and return the persisted instance."""
        return await self.heroes.insert(data=schema.model_dump())

    @not_found(detail="The hero hasn't been found!")
    async def get(
        self,
        hero_id: UUID | str,
        as_staff: bool = False,
        _one_or_none: bool = False,
    ) -> Hero | None:
        """Fetch a single hero by PK.

        Soft-deleted heroes are excluded unless ``as_staff=True``.
        """
        filters = [Hero.uuid == hero_id]
        if not as_staff:
            filters.append(Hero.deleted_at.is_(None))
        return await self.heroes.select(*filters, one_or_none=True)

    @transaction
    @duplicate(detail="The hero already exists!")
    @not_found(detail="The hero hasn't been found!")
    async def update(
        self,
        hero_id: UUID | str,
        schema: "HeroUpdate | HeroPatch",
        patch: bool = False,
        _one_or_none: bool = False,
        _commit: bool = True,
    ) -> Hero | None:
        """Update a hero's fields and return the refreshed instance.

        Pass ``patch=True`` to skip unset fields (PATCH semantics).
        """
        # exclude_unset=True keeps only fields explicitly provided in the request
        return await self.heroes.update(
            id_=hero_id,
            data=schema.model_dump(exclude_unset=patch),
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
        """Delete a hero, either permanently or via soft-delete.

        Soft-delete sets ``deleted_at`` to the current UTC timestamp.
        Returns ``True`` on success; ``None`` propagates to ``@not_found``
        which raises HTTP 404.
        """
        if permanent:
            await self.heroes.delete(id_=hero_id)
        else:
            hero = await self.heroes.update(
                id_=hero_id,
                # TIMESTAMP column has no timezone — strip tzinfo after obtaining UTC time
                data={"deleted_at": datetime.now(timezone.utc).replace(tzinfo=None)},
            )
            if hero is None:
                return None

        return True

    async def search(
        self,
        schema: "HeroSearch",
        as_staff: bool = False,
    ) -> tuple[int, Sequence[Hero]]:
        """Return a paginated (total_count, items) tuple matching the search criteria."""
        filters = []

        if schema.nickname:
            filters.append(Hero.nickname.ilike(f"%{schema.nickname}%"))

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
