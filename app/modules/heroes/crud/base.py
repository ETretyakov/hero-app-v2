from app.db.postgresql.crud import CRUD
from app.modules.heroes.crud.models import Hero


class HeroCRUD(CRUD[Hero]):
    """Concrete CRUD implementation bound to the ``Hero`` table."""

    table = Hero
