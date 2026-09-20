from dataclasses import dataclass

from openmusickit.objects.omk_object import OmkObject, Spanner
from openmusickit.values.tone.interval import Interval


@dataclass(kw_only=True, slots=True)
class Part(OmkObject):
    """A performer: whoever does a line.

    A Part is connected to what it performs through `Stint`s (a PERFORMS edge
    to each). It has no lines of its own; a line is a chain of events, and a
    Part is the one doing it. The instrument is deferred; for now a Part is a
    name.

    >>> Part(name="Flute")
    Part(name='Flute')
    """

    name: str


@dataclass(kw_only=True, slots=True)
class Stint(Spanner):
    """A Part's run on a line: from one event (STARTS_AT) to another (ENDS_AT),
    or to the end of the line, however long it grows, if the stint has no end.

    Two Parts with stints over the same events are doubling. `transposition`,
    if given, is how this Part reads the shared events: a piccolo doubling the
    flute an octave up, a clarinet in A reading a concert-pitch line. Reading
    through a Stint never changes the events; the consumer applies the
    transposition to what the walk yields.

    >>> from openmusickit.systems.wsmn.tonal.symbols import P5
    >>> Stint(transposition=P5)
    Stint(transposition=TonalVector((4, 7)))
    """

    transposition: Interval | None = None
