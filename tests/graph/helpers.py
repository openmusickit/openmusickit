"""Helpers shared by the graph tests: quick note lines, readable names,
a canonical snapshot for do/inspect/undo laws,
and a fork with fresh ids for equivalence.
"""

import copy
from uuid import uuid4

from openmusickit.graph.graph import OmkGraph
from openmusickit.graph.graph_adapter import GraphAdapter
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


def fork_graph(graph: OmkGraph, engine: GraphAdapter | None = None) -> OmkGraph:
    """A copy of `graph`, on `engine` if given, in which every node and edge
    is a new object with an id of its own: the same music, nothing shared by
    identity. One deepcopy memo spans the copy, as in `OmkGraph.materialize`.
    """
    memo: dict[int, object] = {}
    forked = OmkGraph(copy.deepcopy(graph.meta, memo), graph_engine=engine)
    copies = {}
    for node in graph.nodes():
        copies[node.id] = _fresh(node, memo)
        forked.add_node(copies[node.id])
    for edge in graph.edges():
        source, target = graph.edge_endpoints(edge)
        forked._graph.add_edge(copies[source.id], copies[target.id], _fresh(edge, memo))
    return forked


def _fresh(item, memo):
    """A deepcopy of a node or an edge, with a new id."""
    copied = copy.deepcopy(item, memo)
    copied._id = uuid4()
    return copied
