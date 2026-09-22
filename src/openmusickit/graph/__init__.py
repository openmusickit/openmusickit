"""The graph relates objects (see `objects`) to each other with typed edges (see `graph.edge`).

Time in the graph is relative, and there is no score origin. The pieces:

- A **line** is a chain of `SequentialEvent`s joined by NEXT edges: one thing
  being done, usually by one performer. NEXT asserts sequence and nothing
  else; an event has at most one NEXT in and one out. A line is not a node;
  it is identified by its head.

- A **branch** (BRANCHES, `OmkGraph.add_branch`) hangs a second voice off an
  event of a line, within one instrument: a one-measure second voice, a
  voice that runs the whole piece. It carries where the child starts (the
  parent event's onset or offset, plus a signed displacement). A branch
  asserts ownership, so a walk over a span (`walk_span`, `transform_tones`)
  includes everything branched from it, and a branched line never has a
  Part of its own.

- A **pin** (SIMULTANEOUS, `OmkGraph.add_simultaneous`) says that an event of
  one line happens when an event of another does, with the same timing
  payload, and says nothing about who performs either. This is how
  incomplete music is joined: a melody, three bars of chords, a countermelody
  for bars 12-16. Span walks never cross a pin. Pins can disagree with the
  lines' own durations; `check_alignment` reports that as a musical fact.

- A **group** (`LineGroup`; CONTAINS, `OmkGraph.add_group`) holds lines that
  are their own things done together: the hands of a pianist, the drums of a
  kit, the three instruments of one percussionist. The group is a local
  timing origin for its lines (each CONTAINS edge carries the line's
  displacement from it, zero by default), so its lines need no pins.
  `walk_group` walks them all.

- A **Part** is an instrument, and by extension whoever plays it. It points
  at a line through a **Stint** (PERFORMS, STARTS_AT, ENDS_AT;
  `OmkGraph.add_stint`), its run on that line, or at a whole group
  (PERFORMS; `OmkGraph.add_performs`). A kit is one Part per drum on the
  lines of one group; a piano is one Part on the group. Two Parts with stints
  over the same events are doubling, possibly through a transposition that
  the reader applies (`Stint.transposition`); `materialize` forks the line
  when the parts diverge.

A score is a connected component. "Where is this event" only ever means
"how far from that one" (`relative_onset`), and an event of unknown duration
is opaque to the answer.
"""

from . import edge, graph, graph_adapter, rx_adapter

__all__ = [
    "edge",
    "graph",
    "graph_adapter",
    "rx_adapter",
]
