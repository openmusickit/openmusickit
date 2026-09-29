"""MusicXML in and out: `read` a file into an `OmkGraph` holding one `Score`.

The reader records what the file asserts and nothing more
(no derived chord durations, no bar lines the file does not have),
tolerates what notation programs actually export
(a pickup numbered 0, voices reused for unrelated fragments,
held notes re-voiced across a bar line, wrong `<syllabic>` flags),
and warns with an `OmkWarning` for every musical fact it cannot place.
Presentation (layout, stems, beams, positions, fonts) is dropped silently.
What the writer will need back and the model cannot hold
goes in `node.meta["musicxml"]`, which OMK itself never reads;
`reader` documents the keys.

    from openmusickit.io.musicxml import read
    graph = read("score.mxl")

`read`'s docstring shows a whole small document going in.
The design, the mapping rule by rule, and what is deliberately left out
are in `_plans/musicxml.md`.
"""

from openmusickit.io.musicxml import container, reader, tables
from openmusickit.io.musicxml.reader import read

__all__ = ["container", "read", "reader", "tables"]
