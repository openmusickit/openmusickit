"""Objects are the basic building blocks of the music graph, serving as nodes in the graph.

Objects are (usually) mutable, and represent items found in a score, sketch, or other piece of music,
such as notes, chords, sections, lyrics, articulations, markings, analysis figures, etc.
Each instantiated object represents a single thing: this note, that syllable, this staccato mark.
They are generally composed of immutable values.

So a C-sharp in the tenor line of a chorale is represented by a single OmkObject instance
(in this case, a NoteEvent, which is a SequentialEvent),
and has a `tones` attribute (containing the value C-sharp, `TonalVector((0, 1, 0))`),
and a duration (for example, the value of a quarter note, `MetricalDuration(1, 4)`).

To transpose the note, a new NoteEvent object is not needed:
the tones can simply be replaced with new values.

OmkObjects are connected to each other in the graph by edges (see `graph.edge`).
In the case of our C-sharp above, the lyric syllable sung on that C-sharp
is a LyricSyllable object (which contains the syllable text),
and is connected to the NoteEvent by an edge of type LYRIC.
"""

from . import (
    chord_event,
    context_event,
    division_event,
    lyrics,
    marking,
    note_event,
    omk_object,
    part,
    score,
    sync_line,
)
from .chord_event import ChordEvent
from .context_event import (
    ClefEvent,
    ContextEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
    TemporalContextEvent,
)
from .division_event import DivisionEvent
from .lyrics import LyricSection, LyricSyllable, SyllablePlacement, parse_lyrics
from .marking import Marked, Marking, MarkSpanner
from .note_event import NoteEvent, Rest
from .omk_object import OmkObject, SequentialEvent, Spanner, TonalObject
from .part import LineGroup, Part, PercussionPart, Stint
from .score import Score
from .sync_line import SyncLine, SyncPoint

__all__ = [
    "chord_event",
    "context_event",
    "division_event",
    "lyrics",
    "marking",
    "note_event",
    "omk_object",
    "part",
    "score",
    "sync_line",
    "ChordEvent",
    "ClefEvent",
    "ContextEvent",
    "DivisionEvent",
    "LineGroup",
    "LyricSection",
    "LyricSyllable",
    "MarkSpanner",
    "Marked",
    "Marking",
    "MeterEvent",
    "ModalContextEvent",
    "NoteEvent",
    "OmkObject",
    "Part",
    "PercussionPart",
    "Rest",
    "Score",
    "SequentialEvent",
    "Spanner",
    "Stint",
    "SyllablePlacement",
    "SyncLine",
    "SyncPoint",
    "TempoEvent",
    "TemporalContextEvent",
    "TonalObject",
    "parse_lyrics",
]
