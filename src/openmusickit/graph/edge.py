from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any

from openmusickit.utils.id import OmkId
from openmusickit.values.time.duration import Duration, ZeroDuration


class EdgeType(StrEnum):
    NEXT = auto()
    IMPLEMENTS = auto()
    REALIZES = auto()
    ANNOTATES = auto()
    MARKS = auto()
    LYRIC = auto()
    ACCOMPANIES = auto()
    HARMONIZES = auto()
    VARIATION_OF = auto()
    DERIVATIVE_OF = auto()
    SIMULTANEOUS = auto()
    CONTAINS = auto()
    REFERENCES = auto()
    USER_DEFINED = auto()
    STARTS_AT = auto()
    ENDS_AT = auto()


class EdgeOrigin(StrEnum):
    ASSERTED = auto()
    DERIVED = auto()
    INFERRED = auto()


@dataclass(kw_only=True)
class OmkEdge:
    type: EdgeType
    origin: EdgeOrigin = EdgeOrigin.ASSERTED
    _id: OmkId = field(default_factory=OmkId.new, init=False, repr=False, compare=False)
    _meta: dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def id(self) -> OmkId:
        return self._id

    @property
    def meta(self) -> dict[str, Any]:
        return self._meta

    def __repr__(self):
        return f"{type(self).__name__}({self.type}, origin={self.origin})"


class TimingAnchor(StrEnum):
    ONSET = auto()
    OFFSET = auto()


class NudgeDirection(StrEnum):
    FORWARD = auto()
    BACKWARD = auto()


@dataclass(kw_only=True)
class Next(OmkEdge):
    type: EdgeType = field(default=EdgeType.NEXT, init=False)
    anchor: TimingAnchor = TimingAnchor.OFFSET
    displacement: Duration | None = None

    def nudge(self, direction: NudgeDirection, amount: Duration) -> None:
        """Nudges the displacement of this Next edge in the specified direction by the specified amount."""
        if self.displacement is not None and type(amount) is not type(self.displacement):
            raise TypeError(
                f"""Current displacement type ({type(self.displacement)}) does not match nudge amount type ({type(amount)}).
                Try reconciling duration types with a TemporalRatio."""
            )

        if self.displacement is None:
            self.displacement = ZeroDuration()
        if direction == NudgeDirection.FORWARD:
            self.displacement += amount
        elif direction == NudgeDirection.BACKWARD:
            self.displacement -= amount
        else:
            raise ValueError(f"Invalid nudge direction: {direction}")

    def __repr__(self):
        return f"{type(self).__name__}(anchor={self.anchor}, displacement={self.displacement})"
