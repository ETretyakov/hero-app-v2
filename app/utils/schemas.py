from datetime import date, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseInput(BaseModel):
    """Customised pydantic model for input operations."""

    model_config = ConfigDict(use_enum_values=True)

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.replace(tzinfo=None)  # type: ignore

        return values


class BaseOutput(BaseModel):
    """Customised pydantic model for output operations."""

    model_config = ConfigDict(from_attributes=True)

    def model_dump(self, **kwargs):
        values = super().model_dump(**kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.isoformat()

        return values


class OrderByField(BaseModel):
    """Base fields for order by queries.

    Subclasses may define ``allowed_fields`` to restrict which column names
    are accepted, preventing ORDER BY injection via user-supplied input.
    """

    # Override in subclasses with a non-empty frozenset to enable allowlist validation.
    allowed_fields: ClassVar[frozenset[str]] = frozenset()

    field: str = "updated_at"
    desc: bool = True

    @field_validator("field")
    @classmethod
    def validate_allowed_field(cls, v: str) -> str:
        if cls.allowed_fields and v not in cls.allowed_fields:
            allowed = ", ".join(sorted(cls.allowed_fields))
            raise ValueError(f"'{v}' is not a sortable field. Allowed: {allowed}")
        return v


class BaseSearch(BaseModel):
    """Base fields for search queries."""

    offset: int = 0
    limit: int = 10

    order_by: list[OrderByField] = Field(default_factory=list)


class StatusMessage(BaseModel):
    """Schema for status & message responses."""

    status: bool
    message: str
