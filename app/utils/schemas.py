from datetime import date, datetime

from pydantic import BaseModel


class BaseInput(BaseModel):
    """Customised pydantic model for input operations."""

    class Config:
        use_enum_values = True

    def dict(self, *args, **kwargs):
        values = super().dict(*args, **kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.replace(tzinfo=None)  # type: ignore

        return values


class BaseOutput(BaseModel):
    """Customised pydantic model for output operations."""

    class Config:
        orm_mode = True

    def dict(self, *args, **kwargs):
        values = super().dict(*args, **kwargs)
        for k, v in values.items():
            if isinstance(v, (datetime, date)):
                values[k] = v.isoformat()

        return values


class OrderByField(BaseModel):
    """Base fields for order by queries."""

    field: str = "updated_at"
    desc: bool = True


class BaseSearch(BaseModel):
    """Base fields for search queries."""

    offset: int = 0
    limit: int = 10

    order_by: list[OrderByField]


class StatusMessage(BaseModel):
    """Schema for status & message responses."""

    status: bool
    message: str
