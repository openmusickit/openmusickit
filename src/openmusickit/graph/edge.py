from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any
from uuid import UUID, uuid4

from openmusickit.errors import TemporalCompatibilityError
from openmusickit.values.time.duration import Duration, ZeroDuration


class EdgeType(StrEnum):
    NEXT = auto()
    BRANCHES = auto()
    SIMULTANEOUS = auto()
    PERFORMS = auto()
    IMPLEMENTS = auto()
    REALIZES = auto()
    ANNOTATES = auto()
    MARKS = auto()
    LYRIC = auto()
    ACCOMPANIES = auto()
    HARMONIZES = auto()
    VARIATION_OF = auto()
    DERIVATIVE_OF = auto()
    CONTAINS = auto()
    REFERENCES = auto()
    USER_DEFINED = auto()
    STARTS_AT = auto()
    ENDS_AT = auto()


class EdgeOrigin(StrEnum):
    ASSERTED = auto()
    DERIVED = auto()
    INFERRED = auto()


@dataclass(kw_only=True, slots=True)
class OmkEdge:
    type: EdgeType
    origin: EdgeOrigin = EdgeOrigin.ASSERTED
    _id: UUID = field(default_factory=uuid4, init=False, repr=False, compare=False)
    meta: dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def id(self) -> UUID:
        return self._id

    def __repr__(self):
        return f"{type(self).__name__}({self.type}, origin={self.origin})"


class TimingAnchor(StrEnum):
    ONSET = auto()
    OFFSET = auto()


class NudgeDirection(StrEnum):
    FORWARD = auto()
    BACKWARD = auto()


@dataclass(kw_only=True, slots=True, repr=False)
class Next(OmkEdge):
    """Sequence within a line: the target follows the source, and nothing else.

    A line is a maximal chain of NEXT edges; an event has at most one incoming
    and one outgoing NEXT (`OmkGraph.add_next` enforces this). Relative timing
    between lines is carried by `TimedEdge`s, never by NEXT.

    >>> Next()
    Next(next, origin=asserted)
    """

    type: EdgeType = field(default=EdgeType.NEXT, init=False)


@dataclass(kw_only=True, slots=True)
class TimedEdge(OmkEdge):
    """An edge that places its target in time relative to its source.

    The target starts at the `anchor` of the source (its onset or its offset)
    plus a signed `displacement`; `None` means no displacement, so the target
    coincides with the anchor.
    """

    anchor: TimingAnchor = TimingAnchor.ONSET
    displacement: Duration | None = None

    def nudge(self, direction: NudgeDirection, amount: Duration) -> None:
        """Nudges the displacement of this edge in the specified direction by the specified amount.

        The displacement is a signed Duration: negative means the target
        starts before the anchor.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, half
        >>> edge = Branch()
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
        if not self.displacement.temporal_system.compatible_with(amount.temporal_system):
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


@dataclass(kw_only=True, slots=True, repr=False)
class Branch(TimedEdge):
    """From an event of a parent line to the head of a child line that the
    same performer does at the same time: a second voice, the other hand.

    A branch asserts ownership: span walks over the parent include the child.
    A head has at most one incoming Branch and no incoming NEXT.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> late = Branch(anchor=TimingAnchor.OFFSET, displacement=quarter)
    >>> late.type, late.anchor, late.displacement
    (<EdgeType.BRANCHES: 'branches'>, <TimingAnchor.OFFSET: 'offset'>, MetricalDuration(1, 4))
    >>> Branch().anchor, Branch().displacement is None
    (<TimingAnchor.ONSET: 'onset'>, True)
    >>> late
    Branch(anchor=offset, displacement=MetricalDuration(1, 4))
    """

    type: EdgeType = field(default=EdgeType.BRANCHES, init=False)


@dataclass(kw_only=True, slots=True, repr=False)
class Simultaneous(TimedEdge):
    """A pin between events of two independent lines: this happens when that
    does (give or take the displacement). Symmetric in meaning, stored directed.

    A pin asserts nothing about who performs either line; span walks never
    cross one.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> early = Simultaneous(displacement=-quarter)
    >>> early.type, early.anchor, early.displacement
    (<EdgeType.SIMULTANEOUS: 'simultaneous'>, <TimingAnchor.ONSET: 'onset'>, MetricalDuration(-1, 4))
    >>> early
    Simultaneous(anchor=onset, displacement=MetricalDuration(-1, 4))
    """

    type: EdgeType = field(default=EdgeType.SIMULTANEOUS, init=False)


@dataclass(kw_only=True, slots=True, repr=False)
class Contains(TimedEdge):
    """From a `LineGroup` to the head of one of its lines: the line starts at
    the group's origin plus the displacement. A group has no offset, so the
    anchor is always the origin and only `displacement` can be set.
    A `Score`'s CONTAINS edges are plain `OmkEdge`s, not this class:
    a score is not a timing origin.

    >>> from openmusickit.systems.wsmn.temporal.symbols import whole
    >>> Contains(displacement=whole)
    Contains(displacement=MetricalDuration(1, 1))
    >>> Contains().displacement is None, Contains().type
    (True, <EdgeType.CONTAINS: 'contains'>)
    """

    type: EdgeType = field(default=EdgeType.CONTAINS, init=False)
    anchor: TimingAnchor = field(default=TimingAnchor.ONSET, init=False)

    def __repr__(self):
        return f"{type(self).__name__}(displacement={self.displacement})"
