from collections.abc import Sequence

from sqlalchemy import TextClause, text

from app.utils.schemas import OrderByField


def scalar_order_by(order_by: Sequence[OrderByField] | OrderByField) -> list[TextClause]:
    """Convert one or more ``OrderByField`` items into SQLAlchemy ``TextClause`` order expressions.

    Accepts either a single ``OrderByField`` or a list; always returns a list
    ready to be unpacked into ``statement.order_by(*...)``.

    Note: ``item.field`` is interpolated directly into SQL. Use ``OrderByField``
    subclasses with ``allowed_fields`` defined to prevent ORDER BY injection.
    """
    if not isinstance(order_by, Sequence):
        order_by = [order_by]

    return [
        text(f"{item.field} DESC") if item.desc else text(item.field)
        for item in order_by
    ]
