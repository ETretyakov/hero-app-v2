from app.db.postgresql.crud import CRUD
from app.modules.heroes.crud.models import Hero


class HeroCRUD(CRUD[Hero]):
    """CRUD operations for hero model."""

    table = Hero
