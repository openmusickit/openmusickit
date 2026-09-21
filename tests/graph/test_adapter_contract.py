"""The `GraphAdapter` contract, executed against every adapter implementation.

Each test builds a small graph through the adapter alone (no `OmkGraph`),
with plain `OmkObject`s, `NoteEvent`s and `Part`s as nodes and `OmkEdge`s
as edges, and asserts the behaviour the ABC docstrings promise. Step 6 of
the testing plan adds a dict-backed reference adapter to `ADAPTERS`, which
turns these into a differential test as well.

The two tests at the end pin Part 5, item 2 of the plan: they pass against
the reference adapter, which defines the intended behaviour, and are strict
xfails against `RustworkxAdapter` until it stops letting backend exceptions
out.
"""

from uuid import uuid4

import pytest

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, Next, OmkEdge
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.graph.rx_adapter import RustworkxAdapter
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import Part
from openmusickit.systems.wsmn.tonal.symbols import C, D, E
from tests.graph.dict_adapter import DictAdapter

ADAPTERS = [RustworkxAdapter, DictAdapter]

MARKS, ANNOTATES, LYRIC = EdgeType.MARKS, EdgeType.ANNOTATES, EdgeType.LYRIC


@pytest.fixture(params=ADAPTERS, ids=lambda cls: cls.__name__)
def adapter(request) -> GraphAdapter:
    return request.param()


def note(tone) -> NoteEvent:
    return NoteEvent(tones={tone})


def edge(edge_type: EdgeType) -> OmkEdge:
    return OmkEdge(type=edge_type)


def ids(items) -> set:
    """Objects and edges are unhashable by design; compare collections by id."""
    return {item.id for item in items}


@pytest.fixture
def small(adapter):
    """c -NEXT-> d -NEXT-> e, a Part marking c and annotating d, and an edge
    of a third type back from d to the part."""
    c, d, e, part = note(C), note(D), note(E), Part(name="Flute")
    for node in (c, d, e, part):
        adapter.add_node(node)
    adapter.add_edge(c, d, Next())
    adapter.add_edge(d, e, Next())
    adapter.add_edge(part, c, edge(MARKS))
    adapter.add_edge(part, d, edge(ANNOTATES))
    adapter.add_edge(d, part, edge(LYRIC))
    return adapter, c, d, e, part


def test_the_abstract_contract_is_fully_implemented(adapter):
    assert isinstance(adapter, GraphAdapter)
    assert not GraphAdapter.__abstractmethods__ - set(dir(adapter))
    assert len(GraphAdapter.__abstractmethods__) == 29


def test_add_node_is_idempotent(adapter):
    c = note(C)
    assert not adapter.has_node(c)
    adapter.add_node(c)
    adapter.add_node(c)
    assert adapter.has_node(c)
    assert adapter.num_nodes() == 1
    assert list(adapter.nodes()) == [c]
    assert adapter.get_node(c.id) is c
    assert adapter.get_node(str(c.id)) is c
    assert adapter.degree(c) == 0


def test_one_edge_per_type_between_two_nodes(adapter):
    c, d = note(C), note(D)
    adapter.add_node(c)
    adapter.add_node(d)
    marks, annotates = edge(MARKS), edge(ANNOTATES)
    adapter.add_edge(c, d, marks)
    adapter.add_edge(c, d, annotates)
    assert adapter.num_edges() == 2
    with pytest.raises(GraphError):
        adapter.add_edge(c, d, edge(MARKS))
    assert adapter.num_edges() == 2
    assert adapter.has_edge(c, d)
    assert adapter.has_edge(c, d, MARKS) and adapter.has_edge(c, d, ANNOTATES)
    assert not adapter.has_edge(c, d, LYRIC)
    assert not adapter.has_edge(d, c)  # edges are directed
    assert not adapter.has_edge(d, c, MARKS)
    assert adapter.get_edge(c, d, MARKS) is marks
    assert adapter.get_edge(c, d, ANNOTATES) is annotates
    with pytest.raises(GraphError):
        adapter.get_edge(c, d, LYRIC)
    assert ids(adapter.edges_between(c, d)) == ids([marks, annotates])
    assert list(adapter.edges_between(c, d, MARKS)) == [marks]
    assert list(adapter.edges_between(d, c)) == []
    # the same type the other way round is a different edge
    adapter.add_edge(d, c, edge(MARKS))
    assert adapter.num_edges() == 3 and adapter.has_edge(d, c, MARKS)


def test_next_is_one_out_and_one_in(adapter):
    c, d, e = note(C), note(D), note(E)
    for node in (c, d, e):
        adapter.add_node(node)
    adapter.add_edge(c, d, Next())
    with pytest.raises(GraphError):
        adapter.add_edge(c, e, Next())  # c already has a NEXT out
    with pytest.raises(GraphError):
        adapter.add_edge(e, d, Next())  # d already has a NEXT in
    # a NEXT back from d to c would make a two-event cycle, which the
    # one-in/one-out rule does not forbid (testing plan, Part 5 item 1)
    assert adapter.num_edges() == 1
    adapter.add_edge(d, e, Next())
    assert adapter.get_next(c) is d and adapter.get_next(d) is e and adapter.get_next(e) is None
    assert adapter.get_previous(e) is d and adapter.get_previous(c) is None
    # a non-NEXT edge alongside a NEXT is fine
    adapter.add_edge(c, d, edge(MARKS))
    assert adapter.get_next(c) is d


def test_remove_node_removes_its_edges_and_counts_follow(small):
    adapter, c, d, e, part = small
    assert adapter.num_nodes() == 4 and adapter.num_edges() == 5
    adapter.remove_node(d)
    assert not adapter.has_node(d)
    assert adapter.num_nodes() == 3
    assert adapter.num_edges() == 1  # only part -MARKS-> c survives
    assert list(adapter.out_edges(c)) == [] and list(adapter.in_edges(e)) == []
    assert adapter.get_next(c) is None and adapter.get_previous(e) is None
    assert adapter.degree(part) == 1 and adapter.degree(e) == 0
    assert adapter.get_node(c.id) is c
    # d can come back, as a new node with no edges
    adapter.add_node(d)
    assert adapter.has_node(d) and adapter.degree(d) == 0


def test_remove_edge_leaves_the_rest(small):
    adapter, c, d, e, part = small
    marks = adapter.get_edge(part, c, MARKS)
    adapter.remove_edge(marks)
    assert adapter.num_edges() == 4
    assert not adapter.has_edge(part, c)
    assert adapter.has_edge(part, d, ANNOTATES) and adapter.has_edge(d, part, LYRIC)
    assert adapter.get_next(c) is d
    assert adapter.degree(c) == 1 and adapter.degree(part) == 2
    # removing a NEXT frees both ends for a new NEXT
    adapter.remove_edge(adapter.get_edge(c, d, EdgeType.NEXT))
    adapter.add_edge(c, d, Next())
    assert adapter.get_next(c) is d


def test_endpoints(small):
    adapter, c, d, e, part = small
    marks = adapter.get_edge(part, c, MARKS)
    assert adapter.get_edge_endpoints(marks) == (part, c)
    assert adapter.get_source_of_edge(marks) is part
    assert adapter.get_target_of_edge(marks) is c
    following = adapter.get_edge(c, d, EdgeType.NEXT)
    assert adapter.get_edge_endpoints(following) == (c, d)


def test_node_and_edge_iteration_with_filters(small):
    adapter, c, d, e, part = small
    assert ids(adapter.nodes()) == ids([c, d, e, part])
    assert ids(adapter.nodes(NoteEvent)) == ids([c, d, e])
    assert list(adapter.nodes(Part)) == [part]
    assert list(adapter.nodes(predicate=lambda n: isinstance(n, NoteEvent) and D in n.tones)) == [d]
    assert list(adapter.nodes(NoteEvent, lambda n: E in n.tones)) == [e]
    assert list(adapter.nodes(Part, lambda n: n.name == "Oboe")) == []
    assert adapter.filter_nodes(lambda n: isinstance(n, Part)) == [part]
    assert ids(adapter.filter_nodes(lambda n: True)) == ids([c, d, e, part])

    assert len(list(adapter.edges())) == 5
    assert [x.type for x in adapter.edges(EdgeType.NEXT)] == [EdgeType.NEXT, EdgeType.NEXT]
    assert [x.type for x in adapter.edges(predicate=lambda x: x.type is LYRIC)] == [LYRIC]
    assert list(adapter.edges(MARKS, lambda x: x.type is LYRIC)) == []
    assert [x.type for x in adapter.filter_edges(lambda x: x.type is ANNOTATES)] == [ANNOTATES]
    assert ids(adapter.filter_edges(lambda x: True)) == ids(adapter.edges())


def test_neighbourhood_with_filters(small):
    adapter, c, d, e, part = small
    assert ids(adapter.successors(part)) == ids([c, d])
    assert list(adapter.successors(part, edge_type=MARKS)) == [c]
    assert list(adapter.successors(part, NoteEvent, predicate=lambda n: D in n.tones)) == [d]
    assert list(adapter.successors(part, Part)) == []
    assert ids(adapter.successors(d)) == ids([e, part])
    assert list(adapter.successors(d, NoteEvent)) == [e]
    assert list(adapter.successors(d, edge_type=EdgeType.NEXT)) == [e]

    assert ids(adapter.predecessors(d)) == ids([c, part])
    assert list(adapter.predecessors(d, Part)) == [part]
    assert list(adapter.predecessors(d, edge_type=EdgeType.NEXT)) == [c]
    assert list(adapter.predecessors(d, NoteEvent, EdgeType.NEXT, lambda n: E in n.tones)) == []
    assert list(adapter.predecessors(c, NoteEvent)) == []

    # neighbours are predecessors and successors, each node once, in no promised order
    assert ids(adapter.neighbors(d)) == ids([c, part, e])
    assert len(list(adapter.neighbors(d))) == 3
    assert ids(adapter.neighbors(d, NoteEvent)) == ids([c, e])
    assert ids(adapter.neighbors(d, edge_type=EdgeType.NEXT)) == ids([c, e])
    assert ids(adapter.neighbors(part)) == ids([d, c])
    assert len(list(adapter.neighbors(part))) == 2  # d is both a predecessor and a successor
    assert list(adapter.neighbors(part, edge_type=LYRIC)) == [d]

    assert [x.type for x in adapter.out_edges(d)] == [EdgeType.NEXT, LYRIC] or [
        x.type for x in adapter.out_edges(d)
    ] == [LYRIC, EdgeType.NEXT]
    assert [x.type for x in adapter.out_edges(d, LYRIC)] == [LYRIC]
    assert [x.type for x in adapter.in_edges(d, ANNOTATES)] == [ANNOTATES]
    assert {x.type for x in adapter.incident_edges(d)} == {EdgeType.NEXT, ANNOTATES, LYRIC}
    assert len(list(adapter.incident_edges(d))) == 4
    assert [x.type for x in adapter.incident_edges(d, ANNOTATES)] == [ANNOTATES]
    assert list(adapter.incident_edges(e, MARKS)) == []

    assert (adapter.in_degree(d), adapter.out_degree(d), adapter.degree(d)) == (2, 2, 4)
    assert (adapter.in_degree(part), adapter.out_degree(part), adapter.degree(part)) == (1, 2, 3)
    assert (adapter.in_degree(e), adapter.out_degree(e), adapter.degree(e)) == (1, 0, 1)


def test_two_different_objects_with_equal_content_are_two_nodes(adapter):
    c1, c2 = note(C), note(C)
    assert c1 == c2 and c1 is not c2
    adapter.add_node(c1)
    adapter.add_node(c2)
    assert adapter.num_nodes() == 2
    assert adapter.get_node(c1.id) is c1 and adapter.get_node(c2.id) is c2
    adapter.add_edge(c1, c2, Next())
    assert adapter.get_next(c1) is c2 and adapter.get_next(c2) is None


def test_has_node_is_false_for_an_unknown_node(adapter):
    assert not adapter.has_node(OmkObject())
    adapter.add_node(c := note(C))
    adapter.remove_node(c)
    assert not adapter.has_node(c)
    assert adapter.num_nodes() == 0


# --- Part 5, item 2: backend exceptions must not cross the adapter boundary ---


LEAKS_KEY_ERROR = pytest.mark.xfail(
    strict=True,
    reason="revisit: a missing node or edge raises a raw KeyError from _rxid "
    "instead of GraphError (or None from get_node)",
)
LEAKS_NO_EDGE = pytest.mark.xfail(
    strict=True,
    reason="revisit: get_edge between two nodes with no edge at all lets "
    "rustworkx.NoEdgeBetweenNodes escape; with an edge of another type it is a GraphError",
)


@pytest.mark.parametrize(
    "adapter_class",
    [pytest.param(RustworkxAdapter, marks=LEAKS_KEY_ERROR), DictAdapter],
    ids=lambda cls: cls.__name__,
)
def test_a_missing_node_or_edge_is_a_graph_error_not_a_backend_exception(adapter_class):
    adapter = adapter_class()
    c, stranger = note(C), note(D)
    adapter.add_node(c)
    assert adapter.get_node(uuid4()) is None
    for operation in (
        lambda: adapter.remove_node(stranger),
        lambda: adapter.add_edge(c, stranger, Next()),
        lambda: adapter.add_edge(stranger, c, Next()),
        lambda: adapter.get_edge(c, stranger, MARKS),
        lambda: adapter.has_edge(c, stranger),
        lambda: list(adapter.edges_between(c, stranger)),
        lambda: list(adapter.successors(stranger)),
        lambda: list(adapter.predecessors(stranger)),
        lambda: adapter.get_next(stranger),
        lambda: adapter.degree(stranger),
        lambda: adapter.remove_edge(edge(MARKS)),
        lambda: adapter.get_edge_endpoints(edge(MARKS)),
    ):
        with pytest.raises(GraphError):
            operation()


@pytest.mark.parametrize(
    "adapter_class",
    [pytest.param(RustworkxAdapter, marks=LEAKS_NO_EDGE), DictAdapter],
    ids=lambda cls: cls.__name__,
)
def test_get_edge_between_unconnected_nodes_is_a_graph_error(adapter_class):
    adapter = adapter_class()
    c, d = note(C), note(D)
    adapter.add_node(c)
    adapter.add_node(d)
    with pytest.raises(GraphError):
        adapter.get_edge(c, d, MARKS)
