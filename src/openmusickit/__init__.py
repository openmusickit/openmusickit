"""Open Music Kit: Music encoding/decoding tools for computational analysis and machine learning.

The top level holds what any score is built from,
whatever its musical system:
the graph, the objects placed in it, the values that belong to no one system,
and the base error types.

```
import openmusickit as omk
```

Musical systems are opt-in, under `systems`;
nothing here assumes one.
Western Standard Music Notation is `openmusickit.systems.wsmn`.
Abstract bases for implementing a system are in `values` and `objects`,
graph internals in `graph`, and every error type in `errors`.

Examples
--------

>>> import openmusickit as omk
>>> g = omk.OmkGraph(omk.GraphMeta(name="Sketch"))
>>> g.meta
GraphMeta(name='Sketch', description=None, info={})
"""

from . import errors, graph, objects, systems, utils, values
from .errors import OmkError, OmkWarning
from .graph import EdgeType, GraphMeta, OmkGraph
from .objects import (
    ChordEvent,
    ClefEvent,
    DivisionEvent,
    LineGroup,
    LyricSection,
    LyricSyllable,
    Marking,
    MarkSpanner,
    MeterEvent,
    ModalContextEvent,
    NoteEvent,
    Part,
    PercussionPart,
    Rest,
    Score,
    Stint,
    SyncLine,
    SyncPoint,
    TempoEvent,
    parse_lyrics,
)
from .values import (
    AttachmentMode,
    ClockDuration,
    Mark,
    MarkType,
    SilentTone,
    Tempo,
    TempoTerm,
    ToneCollection,
    Word,
)

__all__ = [
    "errors",
    "graph",
    "objects",
    "systems",
    "utils",
    "values",
    "AttachmentMode",
    "ChordEvent",
    "ClefEvent",
    "ClockDuration",
    "DivisionEvent",
    "EdgeType",
    "GraphMeta",
    "LineGroup",
    "LyricSection",
    "LyricSyllable",
    "Mark",
    "MarkSpanner",
    "MarkType",
    "Marking",
    "MeterEvent",
    "ModalContextEvent",
    "NoteEvent",
    "OmkError",
    "OmkGraph",
    "OmkWarning",
    "Part",
    "PercussionPart",
    "Rest",
    "Score",
    "SilentTone",
    "Stint",
    "SyncLine",
    "SyncPoint",
    "Tempo",
    "TempoEvent",
    "TempoTerm",
    "ToneCollection",
    "Word",
    "parse_lyrics",
]
