from fastapi import Security
from fastapi.security import APIKeyHeader

from app.config import config
from app.exceptions.http import HTTP403


api_key_header = APIKeyHeader(
    name="access_token",
    auto_error=False,
)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == config.security.api_key:
        return api_key
    else:
        raise HTTP403(detail="Access is forbidden!")
