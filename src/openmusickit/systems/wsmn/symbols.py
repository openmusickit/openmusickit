"""WSMN's ready-made vocabulary in one namespace:
pitches and intervals, chord types and modes (`tonal.symbols`),
durations, tuplets and time signatures (`temporal.symbols`),
and marks, tempo terms, bar lines and clefs (`scoring.symbols`).

```
from openmusickit.systems.wsmn.symbols import *
```

The three share no names.
Percussion tones are not included:
several of them (`heel`, `toe`, `shake`, `half_open`) are also the names of marks,
so they stay in `percussion.symbols`.

Examples
--------

>>> C, quarter, staccato.kind
(TonalVector((0, 0)), MetricalDuration(1, 4), <MarkType.ARTICULATION: 'articulation'>)
"""

from openmusickit.systems.wsmn.scoring.symbols import *  # noqa: F403
from openmusickit.systems.wsmn.temporal.symbols import *  # noqa: F403
from openmusickit.systems.wsmn.tonal.symbols import *  # noqa: F403
