from typing import Any

from fastapi import HTTPException, status


class HTTP403(HTTPException):
    """Raised when the caller is authenticated but lacks permission (403 Forbidden)."""

    def __init__(self, detail: Any = None, headers: dict[str, Any] | None = None) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, headers=headers)


class HTTP404(HTTPException):
    """Raised when a requested resource does not exist (404 Not Found)."""

    def __init__(self, detail: Any = None, headers: dict[str, Any] | None = None) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers)


class HTTP409(HTTPException):
    """Raised on a uniqueness or state conflict, e.g. duplicate record (409 Conflict)."""

    def __init__(self, detail: Any = None, headers: dict[str, Any] | None = None) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, headers=headers)
