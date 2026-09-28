"""Western Standard Music Notation (WSMN): one musical system among many.

Nothing here is imported by the top-level `openmusickit` namespace;
a program that writes Western music opts in:

```
from openmusickit.systems import wsmn
from openmusickit.systems.wsmn.symbols import *
```

This package holds the system's types (`wsmn.TonalVector`, `wsmn.MetricalDuration`, ...);
`symbols` holds its ready-made vocabulary (`C`, `P5`, `quarter`, `staccato`, ...).
Percussion is its own namespace, `wsmn.percussion`,
because several of its tone names (`heel`, `toe`, `shake`, `half_open`)
are also the names of marks.

Examples
--------

>>> from openmusickit.systems import wsmn
>>> wsmn.MetricalDuration(1, 4) == wsmn.symbols.quarter
True
"""

from . import percussion, scoring, symbols, temporal, tonal
from .scoring import BarLineComponent, BarLineShape, ClefSign, StaffClef
from .temporal import WSMN_TEMPORAL, MetricalDuration, TiedDuration, TimeSignature
from .tonal import (
    WSMN,
    Chord,
    ChordQuality,
    ChordType,
    IntervalQuality,
    Key,
    KeySignature,
    ModePattern,
    TonalDirection,
    TonalVector,
)

__all__ = [
    "percussion",
    "scoring",
    "symbols",
    "temporal",
    "tonal",
    "WSMN",
    "WSMN_TEMPORAL",
    "BarLineComponent",
    "BarLineShape",
    "Chord",
    "ChordQuality",
    "ChordType",
    "ClefSign",
    "IntervalQuality",
    "Key",
    "KeySignature",
    "MetricalDuration",
    "ModePattern",
    "StaffClef",
    "TiedDuration",
    "TimeSignature",
    "TonalDirection",
    "TonalVector",
]
