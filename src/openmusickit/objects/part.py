from dataclasses import dataclass

from openmusickit.objects.omk_object import OmkObject, Spanner
from openmusickit.values.tone.interval import Interval
from openmusickit.values.tone.tone_collection import ToneCollection


@dataclass(kw_only=True, slots=True)
class Part(OmkObject):
    """An instrument (Violin, Flute, Congas), and by extension whoever plays it.

    A Part is connected to what it plays through `Stint`s
    (a PERFORMS edge to each: a run on one line)
    or directly to a `LineGroup`
    (a PERFORMS edge to the group: all of its lines, as a pianist plays both hands).
    A drum kit, or a percussionist covering snare, triangle and cymbals,
    is several Parts, one per instrument, on the lines of one group.
    For now a Part is a name.

    >>> Part(name="Flute")
    Part(name='Flute')
    """

    name: str


@dataclass(kw_only=True, slots=True)
class PercussionPart(Part):
    """An unpitched instrument, with the palette of tones it is expected to use,
    if one has been chosen.

    A palette is a `ToneCollection` of unpitched tones meaningful for a class
    of instrument (`systems.wsmn.percussion.symbols` has the ready-made ones).
    Core never checks a tone against it; an app may warn, an exporter may refuse.

    >>> PercussionPart(name="Snare")
    PercussionPart(name='Snare', palette=None)
    """

    palette: ToneCollection | None = None


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


@dataclass(kw_only=True, slots=True)
class LineGroup(OmkObject):
    """Lines that belong together as one unit:
    the drums of a kit, the hands of a pianist, the manuals and pedal of an organ.

    A group holds line heads (the first event of each NEXT chain)
    with CONTAINS edges (`OmkGraph.add_group`),
    and is a local timing origin for them:
    each member starts at the group's origin plus the edge's displacement,
    zero by default,
    so the lines of a kit or a piano need no pins to be aligned.
    A Part points at the group when one instrument plays all of its lines,
    or at a line head (through a Stint) when each line is its own instrument.

    >>> LineGroup(name="Drum kit")
    LineGroup(name='Drum kit')
    """

    name: str | None = None
