"""MusicXML in and out: `read` a file into an `OmkGraph` holding one `Score`,
and `write` a Score of a graph back out.

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

    from openmusickit.io.musicxml import read, write
    graph = read("score.mxl")
    write(graph, "copy.musicxml")

The writer is the reader's inverse, rule by rule:
`read(write(read(f)))` is equivalent (`OmkGraph.is_equivalent`) to `read(f)`,
and a graph stripped of its bar grid and of the bar lines its meters imply
writes the same document.
It refuses only when there is no score to write,
and warns for what it leaves out.
`read`'s docstring shows a whole small document going in,
`write`'s a small graph going out.
Whether an export kept the music is `compare(canonicalize(a), canonicalize(b))`:
`canonical` reduces two documents to what they say musically and lists the differences.
The design, the mapping rule by rule, and what is deliberately left out
are in `_plans/musicxml.md`.
"""

from openmusickit.io.musicxml import canonical, container, reader, tables, writer
from openmusickit.io.musicxml.canonical import Difference, canonicalize, compare
from openmusickit.io.musicxml.reader import read
from openmusickit.io.musicxml.writer import write

__all__ = [
    "Difference",
    "canonical",
    "canonicalize",
    "compare",
    "container",
    "read",
    "reader",
    "tables",
    "write",
    "writer",
]
