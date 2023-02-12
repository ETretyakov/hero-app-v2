from functools import wraps
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import Callable


def transaction(fn: "Callable"):
    """Class method decorator to control session transaction."""

    @wraps(fn)
    async def wrapper(*args, **kwargs):
        commit = kwargs.pop("_commit", True)
        result = await fn(*args, **kwargs)

        self = args[0]
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

        return result

    return wrapper
