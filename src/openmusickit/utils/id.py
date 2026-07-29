from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class OmkId:
    value: UUID

    @classmethod
    def new(cls) -> OmkId:
        return cls(uuid4())

    @classmethod
    def parse(cls, value: str) -> OmkId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)
    
    def __eq__(self, other: OmkId) -> bool:
        return str(self) == str(other)