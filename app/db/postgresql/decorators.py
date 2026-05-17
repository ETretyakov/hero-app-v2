from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def transaction(fn: F) -> F:
    """Wrap an async service method in a session transaction.

    By default the session is committed after the method returns.
    Pass ``_commit=False`` to flush instead — useful when the method is
    called as an intermediate step inside a larger transaction.
    """

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # _commit is an out-of-band control kwarg, not part of the wrapped signature
        commit = kwargs.pop("_commit", True)
        result = await fn(*args, **kwargs)

        self = args[0]
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

        return result

    return wrapper  # type: ignore[return-value]
