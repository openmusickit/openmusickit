"""The graph relates objects (see `objects`) to each other with typed edges (see `graph.edge`).

Time in the graph is relative, and there is no score origin. The pieces:

- A **line** is a chain of `SequentialEvent`s joined by NEXT edges: one thing
  being done, usually by one performer. NEXT asserts sequence and nothing
  else; an event has at most one NEXT in and one out. A line is not a node;
  it is identified by its head.

- A **branch** (BRANCHES, `OmkGraph.add_branch`) hangs a second line off an
  event of the first, for the *same* performer: the pianist's left hand, a
  one-measure second voice, the drummer's feet. It carries where the child
  starts (the parent event's onset or offset, plus a signed displacement).
  A branch asserts ownership, so a walk over a span (`walk_span`,
  `transform_tones`) includes everything branched from it.

- A **pin** (SIMULTANEOUS, `OmkGraph.add_simultaneous`) says that an event of
  one line happens when an event of another does, with the same timing
  payload, and says nothing about who performs either. This is how
  incomplete music is joined: a melody, three bars of chords, a countermelody
  for bars 12-16. Span walks never cross a pin. Pins can disagree with the
  lines' own durations; `check_alignment` reports that as a musical fact.

- A **Part** is a performer; a **Stint** (PERFORMS, STARTS_AT, ENDS_AT;
  `OmkGraph.add_stint`) is its run on a line. Two Parts with stints over the
  same events are doubling, possibly through a transposition that the
  reader applies (`Stint.transposition`); `materialize` forks the line when
  the parts diverge.

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
