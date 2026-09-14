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

@dataclass(kw_only=True)
class Spanner(OmkObject):
    """Used with OmkEdges of type STARTS_AT and ENDS_AT
    to group a sequence of SequentialObjects together.
    
    Articulations (such as slurs and crescendos) and other objects
    which normally attach to a single OmkObject can attach to a Spanner
    to indicate that they apply to the entire sequence of objects."""
    pass