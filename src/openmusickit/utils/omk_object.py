from dataclasses import dataclass, field
from typing import Any

from .id import OmkId

@dataclass(kw_only=True)
class OmkObject:
    _id: OmkId = field(
        default_factory=OmkId.new,
        repr=False,
    )
    _meta: dict[str, Any] = field(
        default_factory=dict,
        repr=False,
    )

    @property
    def id(self) -> OmkId:
        return self._id

    @property
    def meta(self) -> dict[str, Any]:
        return self._meta