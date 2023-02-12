from typing import TYPE_CHECKING, Any

from sqlalchemy import text


if TYPE_CHECKING:
    from sqlalchemy import TextClause


def scalar_order_by(
    order_by: list | Any,
) -> list["TextClause"]:
    if not isinstance(order_by, list):
        order_by = [order_by]

    items = []

    for item in order_by:
        if item.desc:
            items.append(text(f"{item.field} DESC"))
        else:
            items.append(text(item.field))

    return items
