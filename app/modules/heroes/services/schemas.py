from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.types.heroes import RoleType
from app.utils.schemas import BaseInput, BaseOutput, BaseSearch


class HeroBase(BaseModel):
    """Common fields for serialisation and validation."""

    nickname: str = Field(max_length=255)
    role: RoleType


class HeroCreate(BaseInput, HeroBase):
    """Validation schema to create hero record."""


class HeroUpdate(HeroCreate):
    """Validation schema to create/update hero record."""


class HeroPatch(BaseInput):
    """Validation schema to patch hero record."""

    nickname: Optional[str] = Field(max_length=255)
    role: Optional[RoleType]


class HeroRetrieve(BaseOutput, HeroBase):
    """Serialisation schema to retrieve hero records."""

    uuid: UUID

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class HeroSearch(BaseSearch):
    """Schema to validate hero search parameters."""

    nickname: Optional[str] = Field(max_length=255)
    role: Optional[RoleType]


class HeroSearchResult(BaseModel):
    """Schema to serialise search results for heroes."""

    count: int
    items: list[HeroRetrieve]
