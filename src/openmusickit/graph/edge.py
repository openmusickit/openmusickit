from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any

from openmusickit.errors import TemporalCompatibilityError
from openmusickit.utils.id import OmkId
from openmusickit.values.time.duration import ANY_TEMPORAL_SYSTEM, Duration, ZeroDuration


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
        """Nudges the displacement of this Next edge in the specified direction by the specified amount.

        The displacement is a signed Duration: negative means the following
        event starts before the anchor.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, half
        >>> edge = Next()
        >>> edge.nudge(NudgeDirection.FORWARD, quarter)
        >>> edge.nudge(NudgeDirection.BACKWARD, half)
        >>> edge.displacement
        MetricalDuration(-1, 4)

        Raises
        ------
        TemporalCompatibilityError
            if ``amount`` belongs to a different temporal system than the current displacement.
        """
        if self.displacement is None:
            self.displacement = ZeroDuration()
        if self.displacement.temporal_system not in (ANY_TEMPORAL_SYSTEM, amount.temporal_system):
            raise TemporalCompatibilityError(
                f"Cannot nudge a displacement in {self.displacement.temporal_system.name} "
                f"by an amount in {amount.temporal_system.name}. "
                "Convert the amount first with a TemporalRatio."
            )
        if direction == NudgeDirection.BACKWARD:
            self.displacement -= amount
        else:
            self.displacement += amount

    def __repr__(self):
        return f"{type(self).__name__}(anchor={self.anchor}, displacement={self.displacement})"
