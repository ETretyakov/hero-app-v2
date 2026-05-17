"""Generic database factory for seeding test records.

Usage::

    factory = HeroFactory(async_session=session, data=test_data)
    hero = await factory.populate_data(many=False)   # single item
    heroes = await factory.populate_data(many=True)  # list of items
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.crud import Table


class Factory:
    """Seed ORM records from a list of plain dictionaries.

    Each dictionary in *data* is unpacked as keyword arguments into
    *model*, added to the session, flushed, and refreshed so that
    server-side defaults (e.g. UUID, timestamps) are populated on the
    returned instances.

    Args:
        async_session: The SQLAlchemy async session to use for DB operations.
        model: The ORM model class to instantiate.
        data: Non-empty list of attribute dictionaries — one dict per row.

    Raises:
        ValueError: If *data* is empty at construction time.
    """

    def __init__(
        self,
        async_session: AsyncSession,
        model: type[Table],
        data: list[dict],
    ) -> None:
        if not data:
            raise ValueError("Factory received an empty data list.")

        self.session = async_session
        self.model = model
        self.data = data
        self.items: list[Table] = []

    async def populate_data(self, many: bool = False) -> Table | list[Table]:
        """Insert all rows from *self.data* and return the created instances.

        Args:
            many: When *True* return the full list; when *False* return only
                  the first item.

        Returns:
            A single ORM instance or a list of instances, depending on *many*.
        """
        self.items = []

        for attrs in self.data:
            instance = self.model(**attrs)
            self.items.append(instance)
            self.session.add(instance)

        # flush sends the INSERTs; commit releases the savepoint (test-mode)
        await self.session.commit()

        for instance in self.items:
            await self.session.refresh(instance)

        return self.items if many else self.items[0]

    async def get_one(self) -> Table:
        """Return the first item, seeding the database if not yet populated."""
        if self.items:
            return self.items[0]
        return await self.populate_data(many=False)  # type: ignore[return-value]

    async def get_all(self) -> list[Table]:
        """Return all items, seeding the database if not yet populated."""
        if self.items:
            return self.items
        return await self.populate_data(many=True)  # type: ignore[return-value]
