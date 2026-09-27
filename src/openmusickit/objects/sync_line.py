"""A timing origin with no musical content, and the instants on it.

Music in OMK has no origin:
a position only ever means "how far from that other event"
(`graph.OmkGraph.relative_onset`, `paper/mathy.md` §5.4).
That is the right default for notated music,
but some scores take their timing from somewhere outside the notation:
a stopwatch, a film, a tape, a recorded performance being transcribed.

A `SyncLine` is that somewhere.
It is a named origin in a declared temporal system,
holding `SyncPoint`s -- single instants at a signed distance from it --
that musical events pin to with ordinary SIMULTANEOUS edges
(`graph.OmkGraph.sync_event`).
Asserting "measure 10 beat 1 lands five seconds in"
is then two facts the graph can hold and check,
and fitting a tempo curve through them is a consumer's job, not core's:
a `SyncLine` converts nothing and assumes no tempo.

What a sync line is not:

- It is **not a line** in the graph's sense.
  Elsewhere a line is a chain of NEXT edges identified by its head
  (see `graph`); a `SyncLine` is a single node,
  and its points are never joined to each other.
  "Line" is how the thing is pictured, not how it is built.
- It is **not musical content**.
  A `SyncPoint` has no tones, no duration and no notation.
  A reference line that does have content -- a bell pattern,
  a colotomic structure, a drum loop -- is an ordinary line
  that other lines pin to, and needs nothing from this module.
- It is **not a temporal conversion**.
  A sync line in clock time and music in metrical time
  stay in their own systems; see `graph.OmkGraph.relative_onset`
  for what that means for the timing walk.

Subclasses are expected to be media timelines
(an audio file, a video reel, a MIDI file),
which differ from the base only in which temporal system they declare
and in what resource they point at.
Nothing here is specific to clock time.
"""

from dataclasses import dataclass

from openmusickit.objects.omk_object import OmkObject
from openmusickit.values.time.duration import Duration, TemporalSystem


@dataclass(kw_only=True, slots=True)
class SyncLine(OmkObject):
    """A timing origin that music can be measured against, with no content of its own.

    The node *is* the origin, as a `LineGroup` is for its lines;
    `temporal_system` is required because it is what the offsets of the line's
    points are measured in, and nothing else in the graph could say so
    (a `ZeroDuration` offset belongs to every system, so the points cannot
    report it).

    >>> from openmusickit.values.time.clock_time import CLOCK_TIME
    >>> SyncLine(temporal_system=CLOCK_TIME, name="Reel 1").name
    'Reel 1'
    >>> SyncLine(temporal_system=CLOCK_TIME).description is None
    True
    """

    temporal_system: TemporalSystem
    name: str | None = None
    description: str | None = None


@dataclass(kw_only=True, slots=True)
class SyncPoint(OmkObject):
    """One instant on a `SyncLine`, at a signed distance from that line's origin.

    A point has no content and no duration: it is a moment, not a span,
    which is why it is not a `SequentialEvent`.
    The `offset` is signed, so a point may fall *before* the origin
    (a count-in ahead of the first frame).
    It must be a `Measurable`, since the graph orders points by it.

    `offset` is checked against its line's temporal system when the point is put
    on a line (`graph.OmkGraph.add_sync_point`), not on assignment:
    like every other guard in the graph, it is an insertion-time check.

    >>> from openmusickit.values.time.clock_time import ClockDuration
    >>> SyncPoint(offset=ClockDuration.from_seconds(5), name="door slams")
    SyncPoint(offset=ClockDuration(microseconds=5000000), name='door slams', description=None)
    >>> SyncPoint(offset=-ClockDuration.from_seconds(2)).offset
    ClockDuration(microseconds=-2000000)
    """

    offset: Duration
    name: str | None = None
    description: str | None = None
