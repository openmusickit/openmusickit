from dataclasses import dataclass, field

from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.values.scoring.division_shape import DivisionShape
from openmusickit.values.time.duration import Duration, ZeroDuration


@dataclass(kw_only=True, slots=True)
class DivisionEvent(SequentialEvent):
    """A division between one stretch of a line and the next:
    in WSMN, a bar line.
    It sits in the NEXT chain like any event and has zero duration;
    it cannot be given one.

    Divisions are optional and belong to the line they are in.
    An author may place all of them, some, or none,
    and different lines may divide differently (polymetric voices, early music).
    Nothing is measure-based:
    a pickup is simply a division that arrives early.
    A renderer that derives bar lines from a time signature fills the gaps
    and warns where an explicit division disagrees.

    `shape` is how the division is drawn,
    in the notation system's own vocabulary (`BarLineShape` for WSMN);
    `None` means a division whose drawing is unspecified.
    Repeat dots in a shape are visual only:
    whether anything repeats is the business of control flow,
    which follows the same rule (explicit wins, derived fills gaps, mismatch warns).

    >>> from openmusickit.systems.wsmn.scoring.symbols import end_repeat
    >>> DivisionEvent(shape=end_repeat)
    DivisionEvent(shape=BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK))
    >>> DivisionEvent().shape is None
    True
    >>> isinstance(DivisionEvent().duration, ZeroDuration)
    True
    >>> DivisionEvent(duration=None)
    Traceback (most recent call last):
    ...
    TypeError: ...

    Marks attach to a division as to any node;
    a segno or a fermata on a bar line is a `Marking` with a MARKS edge to it:

    >>> from openmusickit.graph.edge import EdgeType
    >>> from openmusickit.graph.graph import GraphMeta, OmkGraph
    >>> from openmusickit.objects.marking import Marking
    >>> from openmusickit.systems.wsmn.scoring.symbols import segno
    >>> graph = OmkGraph(GraphMeta())
    >>> division, sign = DivisionEvent(), Marking(mark=segno)
    >>> graph.add_node(division)
    >>> graph.add_node(sign)
    >>> graph.add_edge(sign, division, EdgeType.MARKS)
    >>> graph.get_edge(sign, division, EdgeType.MARKS).type
    <EdgeType.MARKS: 'marks'>
    """

    shape: DivisionShape | None = None
    duration: Duration = field(default_factory=ZeroDuration, init=False, repr=False)
