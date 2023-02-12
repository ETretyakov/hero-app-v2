from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql.crud import Table


class Factory:
    """Factory to create database records from JSON data."""

    def __init__(
        self,
        async_session: AsyncSession,
        model: Table,
        data: list,
    ):
        if not data:
            raise ValueError("There is no any data for creating objects!")

        self.session = async_session
        self.model = model
        self.data = data

        self.items = []

    async def populate_data(self, many: bool = False):
        if len(self.data) == 0:
            raise ValueError("There is no any data for creating objects!")

        self.items = []

        for item in self.data:
            model_item = self.model(**item)
            self.items.append(model_item)
            self.session.add(model_item)

        await self.session.commit()

        for item in self.items:
            await self.session.refresh(item)

        if many:
            return self.items
        else:
            return self.items[0]

    async def get_one(self):
        if self.items:
            return self.items[0]
        return await self.populate_data(many=False)

    async def get_all(self):
        if self.items:
            return self.items
        return await self.populate_data(many=True)
