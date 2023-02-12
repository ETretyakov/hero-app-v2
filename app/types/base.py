from enum import Enum

from sqlalchemy.dialects.postgresql import ENUM


class BaseEnum(Enum):
    """Base class for enums."""

    @classmethod
    def values(cls) -> list[str]:
        return [i.value for i in cls.__members__.values()]

    @classmethod
    def as_pg_enum(cls, name: str):
        return ENUM(*cls.values(), name=name)
