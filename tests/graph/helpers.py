"""Helpers shared by the graph tests: quick note lines, readable names, and
a canonical snapshot for do/inspect/undo laws.
"""

from openmusickit.graph.graph import OmkGraph
from openmusickit.objects.note_event import NoteEvent
from openmusickit.systems.wsmn.temporal.symbols import quarter


def notes(*tones, duration=quarter) -> list[NoteEvent]:
    """One NoteEvent per tone, all with the same duration (a quarter by default)."""
    return [NoteEvent(tones={t}, duration=duration) for t in tones]


def names(events) -> list[str]:
    """The ASCII pitch name of the single tone of each event."""
    return [format(next(iter(n.tones)), "ascii") for n in events]


def snapshot(graph: OmkGraph) -> tuple[list, list]:
    """A canonical, comparable picture of a graph: node ids with their
    repr, and edges as (source id, target id, type, repr).

    Edge ids are left out on purpose: an undo that re-adds a NEXT edge makes
    a new edge object, and the graph is "back where it was" all the same.
    """
    adapter = graph._graph
    nodes = sorted((str(n.id), repr(n)) for n in adapter.nodes())
    edges = sorted(
        (str(s.id), str(t.id), e.type.name, repr(e))
        for e in adapter.edges()
        for s, t in [adapter.get_edge_endpoints(e)]
    )
    return nodes, edges
