from dataclasses import dataclass, field
from typing import Any, Callable

from openmusickit.values.time.duration import Duration

from openmusickit.utils.id import OmkId

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


@dataclass(kw_only=True)
class SequentialObject(OmkObject):
    duration: Duration | None = None


    def alter_duration(self, operation: Callable[[Duration, Any], Duration], operand: Any):
        new_duration = operation(self.duration, operand)
        self.duration = new_duration