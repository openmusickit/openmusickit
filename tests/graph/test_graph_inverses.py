"""Do, inspect, undo: every OmkGraph mutator, performed and then reversed,
leaves the graph exactly as it was (`helpers.snapshot`).

Where no inverse method exists (a branch, a pin, a stint, a spanner), the
test spells out the primitive undo with `remove_edge` and `remove_node`.
"""

import pytest

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, NudgeDirection, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import Part, Stint
from openmusickit.systems.wsmn.scoring.symbols import slur, staccato
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter, whole
from openmusickit.systems.wsmn.tonal.symbols import A, B, C, D, E, F, G, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from openmusickit.values.time.duration import ZeroDuration
from tests.domains import ABSTRACT_VECTORS
from tests.graph.helpers import names, notes, snapshot

DOWN = TonalDirection.DOWN
NEXT = EdgeType.NEXT


def fresh() -> OmkGraph:
    return OmkGraph(GraphMeta())


def next_edges(graph: OmkGraph, line: list) -> list:
    return [graph.get_edge(a, b, NEXT) for a, b in zip(line, line[1:], strict=False)]


# --- nodes and NEXT ---------------------------------------------------------------


def test_add_node_can_be_undone():
    graph = fresh()
    before = snapshot(graph)
    (c,) = notes(C)
    graph.add_node(c)
    assert graph.get_node(c.id) is c
    assert graph.get_node(str(c.id)) is c
    assert graph._graph.num_nodes() == 1
    graph.add_node(c)  # a second add is a no-op
    assert graph._graph.num_nodes() == 1
    graph.remove_node(c)
    assert not graph._graph.has_node(c)
    assert snapshot(graph) == before == ([], [])


def test_add_next_can_be_undone():
    graph = fresh()
    c, d = notes(C, D)
    graph.add_node(c)
    graph.add_node(d)
    before = snapshot(graph)
    graph.add_next(c, d)
    assert graph.get_next(c) is d and graph.get_previous(d) is c
    assert list(graph.walk_line(c)) == [c, d]
    graph.remove_edge(graph.get_edge(c, d, NEXT))
    assert graph.get_next(c) is None and graph.get_previous(d) is None
    assert snapshot(graph) == before


def test_add_next_puts_the_following_event_on_the_graph():
    graph = fresh()
    c, d = notes(C, D)
    graph.add_node(c)
    before = snapshot(graph)
    graph.add_next(c, d)
    assert graph._graph.has_node(d)
    graph.remove_edge(graph.get_edge(c, d, NEXT))
    graph.remove_node(d)
    assert snapshot(graph) == before


def test_add_line_is_repeated_add_next_and_can_be_undone():
    graph = fresh()
    before = snapshot(graph)
    line = notes(C, D, E, F)
    graph.add_line(line)
    assert list(graph.walk_line(line[0])) == line
    assert [graph.get_previous(n) for n in line] == [None, *line[:-1]]

    by_primitives = fresh()
    by_primitives.add_node(line[0])
    for a, b in zip(line, line[1:], strict=False):
        by_primitives.add_next(a, b)
    assert snapshot(by_primitives) == snapshot(graph)

    for edge in next_edges(graph, line):
        graph.remove_edge(edge)
    assert all(graph.get_next(n) is None for n in line)
    assert list(graph.walk_line(line[0])) == [line[0]]
    for n in line:
        graph.remove_node(n)
    assert snapshot(graph) == before


def test_remove_node_takes_its_edges_and_can_be_undone():
    graph = fresh()
    c, d, e = notes(C, D, E)
    graph.add_line([c, d, e])
    before = snapshot(graph)
    graph.remove_node(d)
    assert graph.get_next(c) is None and graph.get_previous(e) is None
    assert graph._graph.num_edges() == 0
    assert list(graph.walk_line(c)) == [c]
    graph.add_node(d)
    graph.add_next(c, d)
    graph.add_next(d, e)
    assert snapshot(graph) == before


def test_insert_event_can_be_undone():
    graph = fresh()
    c, d, e = notes(C, D, E)
    graph.add_line([c, e])
    before = snapshot(graph)
    graph.insert_event(d, c, e)
    assert list(graph.walk_line(c)) == [c, d, e]

    by_primitives = fresh()
    by_primitives.add_line([c, e])
    by_primitives.remove_edge(by_primitives.get_edge(c, e, NEXT))
    by_primitives.add_next(c, d)
    by_primitives.add_next(d, e)
    assert snapshot(by_primitives) == snapshot(graph)

    graph.remove_edge(graph.get_edge(c, d, NEXT))
    graph.remove_edge(graph.get_edge(d, e, NEXT))
    graph.add_next(c, e)
    graph.remove_node(d)
    assert snapshot(graph) == before


def test_insert_line_from_list_can_be_undone():
    graph = fresh()
    c, f = notes(C, F)
    inserted = notes(D, E)
    graph.add_line([c, f])
    before = snapshot(graph)
    graph.insert_line_from_list(inserted, c, f)
    assert list(graph.walk_line(c)) == [c, *inserted, f]
    for edge in next_edges(graph, [c, *inserted, f]):
        graph.remove_edge(edge)
    graph.add_next(c, f)
    for n in inserted:
        graph.remove_node(n)
    assert snapshot(graph) == before


def test_inserting_an_empty_list_changes_nothing():
    graph = fresh()
    c, f = notes(C, F)
    graph.add_line([c, f])
    before = snapshot(graph)
    graph.insert_line_from_list([], c, f)
    assert list(graph.walk_line(c)) == [c, f]
    assert snapshot(graph) == before


# --- branches and pins ------------------------------------------------------------


def test_branch_can_be_undone():
    graph = fresh()
    parent, child = notes(C, D), notes(A, B)
    graph.add_line(parent)
    graph.add_line(child)
    before = snapshot(graph)
    graph.add_branch(parent[0], child[0])
    assert list(graph.branches_from(parent[0])) == [child[0]]
    assert graph.relative_onset(parent[0], child[1]) == quarter
    assert names(graph.walk_span(parent[0])) == ["C", "A", "B", "D"]
    graph.remove_edge(graph.get_edge(parent[0], child[0], EdgeType.BRANCHES))
    assert list(graph.branches_from(parent[0])) == []
    assert names(graph.walk_span(parent[0])) == ["C", "D"]
    with pytest.raises(GraphError):
        graph.relative_onset(parent[0], child[0])
    assert snapshot(graph) == before
    graph.add_branch(parent[1], child[0])  # the head is free to be branched again
    assert list(graph.branches_from(parent[1])) == [child[0]]


def test_branch_from_offset_with_displacement_can_be_undone():
    graph = fresh()
    c, d = notes(C, D, duration=half)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    before = snapshot(graph)
    graph.add_branch(c, a, anchor=TimingAnchor.OFFSET, displacement=-quarter)
    assert graph.relative_onset(c, a) == quarter
    assert graph.relative_onset(c, b) == half
    graph.remove_edge(graph.get_edge(c, a, EdgeType.BRANCHES))
    assert snapshot(graph) == before


def test_pin_can_be_undone():
    graph = fresh()
    melody = notes(C, D, E, duration=whole)
    chords = [ChordEvent(chord=C(maj), duration=whole), ChordEvent(chord=F(maj), duration=whole)]
    graph.add_line(melody)
    graph.add_line(chords)
    before = snapshot(graph)
    graph.add_simultaneous(melody[0], chords[0], displacement=quarter)
    assert graph.relative_onset(melody[0], chords[0]) == quarter
    assert graph.relative_onset(chords[1], melody[2]) == whole - quarter
    assert graph.relative_onset(chords[0], melody[0]) == -quarter
    graph.remove_edge(graph.get_edge(melody[0], chords[0], EdgeType.SIMULTANEOUS))
    with pytest.raises(GraphError):
        graph.relative_onset(melody[0], chords[0])
    with pytest.raises(GraphError):
        graph.relative_onset(chords[0], melody[0])
    assert snapshot(graph) == before


def test_nudging_a_timed_edge_forward_then_back_restores_the_timing():
    graph = fresh()
    c, d = notes(C, D)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    graph.add_branch(c, a)
    edge = graph.get_edge(c, a, EdgeType.BRANCHES)
    original = graph.relative_onset(c, b)
    assert edge.displacement is None and original == quarter

    edge.nudge(NudgeDirection.FORWARD, eighth)
    assert edge.displacement == eighth
    assert graph.relative_onset(c, a) == eighth
    assert graph.relative_onset(c, b) == original + eighth

    edge.nudge(NudgeDirection.BACKWARD, eighth)
    assert edge.displacement == ZeroDuration()
    assert graph.relative_onset(c, a) == ZeroDuration()
    assert graph.relative_onset(c, b) == original
    assert graph.relative_onset(b, c) == -original


# --- transformation ---------------------------------------------------------------


def test_transposing_a_span_up_then_down_restores_it():
    """For every interval: the line and its branch move together, the pinned
    line stays put, and transposing back restores the snapshot."""
    graph = fresh()
    rh = notes(C, D, E, F)
    voice2 = notes(A, B, duration=eighth)
    chords = [ChordEvent(chord=C(maj), duration=whole)]
    graph.add_line(rh)
    graph.add_line(voice2)
    graph.add_line(chords)
    graph.add_branch(rh[1], voice2[0])
    graph.add_simultaneous(rh[0], chords[0])
    before = snapshot(graph)
    for i in ABSTRACT_VECTORS:
        graph.transform_tones(rh[0], None, TonalVector.transpose, i)
        assert [next(iter(n.tones)) for n in rh] == [t + i for t in (C, D, E, F)], i
        assert [next(iter(n.tones)) for n in voice2] == [A + i, B + i], i
        assert str(chords[0].chord) == "C", i
        graph.transform_tones(rh[0], None, TonalVector.transpose, i, DOWN)
        assert names(rh) == ["C", "D", "E", "F"], i
        assert names(voice2) == ["A", "B"], i
        assert snapshot(graph) == before, i


def test_transposing_part_of_a_line_leaves_the_rest_alone():
    graph = fresh()
    line = notes(C, D, E, F)
    graph.add_line(line)
    before = snapshot(graph)
    graph.transform_tones(line[1], line[2], TonalVector.transpose, TonalVector((1, 2)))
    assert names(line) == ["C", "E", "F#", "F"]
    graph.transform_tones(line[1], line[2], TonalVector.transpose, TonalVector((1, 2)), DOWN)
    assert snapshot(graph) == before


# --- parts and stints ---------------------------------------------------------------


def test_stint_can_be_undone_edge_by_edge():
    graph = fresh()
    line = notes(C, D, E, F)
    graph.add_line(line)
    before = snapshot(graph)
    flute, stint = Part(name="Flute"), Stint()
    graph.add_stint(flute, stint, line[0], line[1])
    assert list(graph.stints(flute)) == [stint]
    assert list(graph.walk_stint(stint)) == line[:2]
    graph.remove_edge(graph.get_edge(stint, line[0], EdgeType.STARTS_AT))
    graph.remove_edge(graph.get_edge(stint, line[1], EdgeType.ENDS_AT))
    graph.remove_edge(graph.get_edge(flute, stint, EdgeType.PERFORMS))
    assert list(graph.stints(flute)) == []
    graph.remove_node(stint)
    graph.remove_node(flute)
    assert snapshot(graph) == before


def test_open_ended_stint_can_be_undone_by_removing_its_nodes():
    graph = fresh()
    line = notes(C, D, E, F)
    graph.add_line(line)
    before = snapshot(graph)
    flute, stint = Part(name="Flute"), Stint()
    graph.add_stint(flute, stint, line[1])
    assert list(graph.walk_stint(stint)) == line[1:]
    graph.remove_node(stint)  # takes PERFORMS, STARTS_AT with it
    graph.remove_node(flute)
    assert snapshot(graph) == before


# --- attachments -----------------------------------------------------------------------


def test_spanner_articulation_and_annotation_can_be_undone():
    graph = fresh()
    c, d = notes(C, D)
    graph.add_line([c, d])
    before = snapshot(graph)
    arc, dot, memo = MarkSpanner(mark=slur), Marking(mark=staccato), OmkObject()
    graph.add_spanner(arc, c, d)
    graph.add_articulation(dot, c)
    graph.add_annotation(memo, d)
    assert graph.get_edge(arc, c, EdgeType.STARTS_AT).type is EdgeType.STARTS_AT
    assert graph.get_edge(arc, d, EdgeType.ENDS_AT).type is EdgeType.ENDS_AT
    assert graph.get_edge(dot, c, EdgeType.MARKS).type is EdgeType.MARKS
    assert graph.get_edge(memo, d, EdgeType.ANNOTATES).type is EdgeType.ANNOTATES
    assert graph._graph.num_edges() == len(before[1]) + 4
    assert sorted(e.type.name for e in graph.edges()) == sorted(
        ["NEXT", "STARTS_AT", "ENDS_AT", "MARKS", "ANNOTATES"]
    )
    assert [e.type for e in graph.edges(EdgeType.MARKS)] == [EdgeType.MARKS]

    graph.remove_edge(graph.get_edge(arc, c, EdgeType.STARTS_AT))
    graph.remove_edge(graph.get_edge(arc, d, EdgeType.ENDS_AT))
    graph.remove_edge(graph.get_edge(dot, c, EdgeType.MARKS))
    graph.remove_edge(graph.get_edge(memo, d, EdgeType.ANNOTATES))
    for node in (arc, dot, memo):
        graph.remove_node(node)
    assert snapshot(graph) == before


def test_articulation_is_a_plain_edge_and_can_be_undone_with_add_edge_primitives():
    graph = fresh()
    (c,) = notes(C)
    graph.add_node(c)
    dot = Marking(mark=staccato)
    graph.add_node(dot)
    before = snapshot(graph)
    graph.add_edge(dot, c, EdgeType.MARKS)
    with pytest.raises(GraphError):
        graph.add_edge(dot, c, EdgeType.MARKS)  # one edge of a type between two nodes
    assert list(graph.edges_between(dot, c, EdgeType.MARKS))
    graph.remove_edge(graph.get_edge(dot, c, EdgeType.MARKS))
    assert list(graph.edges_between(dot, c)) == []
    assert snapshot(graph) == before


# --- remove_edge hands back what it removed -------------------------------------------


def test_remove_edge_returns_the_removed_edge():
    """The removed edge comes back from `remove_edge`, so an undo can re-add it."""
    graph = fresh()
    c, d = notes(C, D)
    graph.add_line([c, d])
    before = snapshot(graph)
    edge = graph.get_edge(c, d, NEXT)
    assert graph.remove_edge(edge) is edge
    assert graph.get_next(c) is None
    graph._graph.add_edge(c, d, edge)  # the same edge object goes back through the adapter
    assert snapshot(graph) == before


# --- the pieces used above are themselves on the graph as expected -------------------


def test_notes_helper_and_names_helper():
    line = notes(C, G, duration=half)
    assert names(line) == ["C", "G"]
    assert all(n.duration == half for n in line)
    assert names(notes(E)) == ["E"] and notes(E)[0].duration == quarter
