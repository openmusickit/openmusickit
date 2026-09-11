from enum import StrEnum, auto
from dataclasses import dataclass, field

from openmusickit.utils.id import OmkId
from openmusickit.values.time.duration import Duration, ZeroDuration

class EdgeType(StrEnum):
    NEXT = auto()
    IMPLEMENTS = auto()
    REALIZES = auto()
    ANNOTATES = auto()
    ARTICULATION = auto()
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

@dataclass(slots=True, frozen=True)
class OmkEdge:
    _type: EdgeType
    origin: EdgeOrigin = EdgeOrigin.ASSERTED
    _meta: dict = field(default_factory=dict)
    _id: OmkId = field(default_factory=OmkId.new)

    @property
    def type(self) -> EdgeType:
        return self._type

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type}, origin={self.origin})"

class TimingAnchor(StrEnum):
    ONSET = auto()
    OFFSET = auto()

class NudgeDirection(StrEnum):
    FORWARD = auto()
    BACKWARD = auto()

    
@dataclass(slots=True, kw_only=True)
class Next(OmkEdge):
    _type: EdgeType = field(
        default=EdgeType.NEXT,
        init=False,
    )
    anchor: TimingAnchor = TimingAnchor.OFFSET
    displacement: Duration | None = None

    @property
    def type(self) -> EdgeType:
        return EdgeType.NEXT

    def nudge(self, direction: NudgeDirection, amount: Duration) -> None:
        """Nudges the displacement of this Next edge in the specified direction by the specified amount."""
        if type(amount) != type(self.displacement) and self.displacement is not None:
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
        return f"Next(anchor={self.anchor}, displacement={self.displacement})"