from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import config
from app.exceptions.http import HTTP403


# auto_error=False suppresses FastAPI's default 403 so we can raise our own HTTP403
api_key_header = APIKeyHeader(name="access_token", auto_error=False)


async def get_api_key(api_key: str | None = Security(api_key_header)) -> str:
    """FastAPI dependency that validates the ``access_token`` request header.

    Raises HTTP 403 if the header is absent or does not match the configured key.
    Returns the key string on success so it can be injected into route handlers.
    """
    if api_key == config.security.api_key:
        return api_key  # type: ignore[return-value]
    raise HTTP403(detail="Access is forbidden!")
