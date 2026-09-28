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

- A **sync line** (`objects.sync_line`; CONTAINS, `OmkGraph.sync_event`) is a
  named origin in its own temporal system, holding the instants (`SyncPoint`)
  that music pins to: a stopwatch, a film reel, a tape. It is a second kind of
  *local* origin, like a group, and no more a score origin than one: it relates
  its own points to each other, and relates an event to the point it is pinned
  to, but never joins two musical lines. A walk meets a sync line at a point
  and does not pass through, so a position in the music is still answered in
  the music's own units. `check_sync_alignment` reports a timeline whose points
  run counter to the music; the *distance* between points is never checked,
  because two stretches of metrical music at different tempos cover the same
  real time in different numbers of quarter notes, so only their order can be
  compared.

- A **Part** is an instrument, and by extension whoever plays it. It points
  at a line through a **Stint** (PERFORMS, STARTS_AT, ENDS_AT;
  `OmkGraph.add_stint`), its run on that line, or at a whole group
  (PERFORMS; `OmkGraph.add_performs`). A kit is one Part per drum on the
  lines of one group; a piano is one Part on the group. Two Parts with stints
  over the same events are doubling, possibly through a transposition that
  the reader applies (`Stint.transposition`); `materialize` forks the line
  when the parts diverge.

- A **Score** (`objects.score`; CONTAINS, `OmkGraph.add_line_to_score`,
  `add_part_to_score`) carries the work's metadata (title, composer, ...)
  and names one connected component: it points at the heads of the
  component's top-level lines and at its Parts. Its CONTAINS edges are
  plain, not timed (a group's are timed because a group is a timing origin;
  a score is not), so a Score says nothing about when anything happens.
  `walk_score` walks every line; `scores_of` finds a head's or a Part's
  score.

A connected component is a score, whether or not a `Score` names it; a graph
may hold several, or fragments that are none (`GraphMeta` describes the
graph, not a work). "Where is this event" only ever means "how far from that
one" (`relative_onset`), and an event of unknown duration is opaque to the
answer.
"""

from . import edge, graph, graph_adapter, rx_adapter
from .edge import (
    Branch,
    Contains,
    EdgeOrigin,
    EdgeType,
    Next,
    NudgeDirection,
    OmkEdge,
    Simultaneous,
    TimedEdge,
    TimingAnchor,
)
from .graph import GraphMeta, OmkGraph
from .graph_adapter import GraphAdapter
from .rx_adapter import RustworkxAdapter

__all__ = [
    "edge",
    "graph",
    "graph_adapter",
    "rx_adapter",
    "Branch",
    "Contains",
    "EdgeOrigin",
    "EdgeType",
    "GraphAdapter",
    "GraphMeta",
    "Next",
    "NudgeDirection",
    "OmkEdge",
    "OmkGraph",
    "RustworkxAdapter",
    "Simultaneous",
    "TimedEdge",
    "TimingAnchor",
]
