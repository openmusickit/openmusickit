"""Graph equivalence: the same music held by different objects
(`OmkGraph.is_equivalent`, `correspondence`, `diff`).
See _plans/graph-equivalence.md.
"""

import copy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openmusickit.graph.edge import EdgeOrigin, EdgeType, Next, OmkEdge, Simultaneous, TimingAnchor
from openmusickit.graph.equivalence import GraphDiff
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.lyrics import LyricSection
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import accent, slur, staccato
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter
from openmusickit.systems.wsmn.tonal.symbols import P5, A, B, C, D, E, F, G, dom7, maj
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration
from tests.graph.dict_adapter import DictAdapter
from tests.graph.helpers import fork_graph, notes
from tests.strategies import lines


def everything() -> OmkGraph:
    """A graph with one of every structure: lines, a branch, a pin, a mark,
    a spanner, lyrics in a section, a group with a Part, a stint, a score,
    a sync line and an annotation."""
    graph = OmkGraph(GraphMeta(name="everything"))
    melody = notes(C, D, E, F)
    voice = notes(A, B, duration=eighth)
    chords = [ChordEvent(chord=C(maj), duration=half), ChordEvent(chord=G(dom7), duration=half)]
    left = notes(C, G, duration=half)
    for line in (melody, voice, chords, left):
        graph.add_line(line)
    graph.add_branch(melody[1], voice[0], anchor=TimingAnchor.OFFSET)
    graph.add_simultaneous(melody[0], chords[0], displacement=-quarter)
    graph.add_articulation(Marking(mark=staccato), melody[2])
    graph.add_spanner(MarkSpanner(mark=slur), melody[0], melody[1])
    verse = LyricSection(section_type="verse", section_number=1)
    syllables = graph.add_lyrics("Al-le-lu-ia", section=verse)
    graph.zip_lyrics_to_objects(syllables[0], melody[0])
    piano_lines = LineGroup(name="Piano")
    graph.add_group(piano_lines, [left[0]])
    graph.add_performs(Part(name="Piano"), piano_lines)
    singer = Part(name="Voice")
    graph.add_stint(singer, Stint(transposition=P5), melody[0], melody[2])
    score = Score(title="Everything")
    graph.add_line_to_score(score, melody[0])
    graph.add_line_to_score(score, chords[0])
    graph.add_part_to_score(score, singer)
    film = SyncLine(temporal_system=CLOCK_TIME, name="Reel 1")
    graph.sync_event(chords[1], film, ClockDuration.from_seconds(5))
    graph.add_annotation(OmkObject(), melody[3])
    return graph


def assert_isomorphism(first: OmkGraph, second: OmkGraph, mapping: dict) -> None:
    """`mapping` pairs every node of `first` with an equal node of
    `second`, one to one, and carries every edge onto an equal edge."""
    assert set(mapping) == {node.id for node in first.nodes()}
    assert set(mapping.values()) == {node.id for node in second.nodes()}
    for node in first.nodes():
        assert second.get_node(mapping[node.id]) == node
    for edge in first.edges():
        source, target = first.edge_endpoints(edge)
        mapped_source = second.get_node(mapping[source.id])
        mapped_target = second.get_node(mapping[target.id])
        assert second.get_edge(mapped_source, mapped_target, edge.type) == edge
    assert len(list(first.edges())) == len(list(second.edges()))


def mirrored(diff: GraphDiff) -> GraphDiff:
    return GraphDiff(
        removed_nodes=diff.added_nodes,
        added_nodes=diff.removed_nodes,
        removed_edges=diff.added_edges,
        added_edges=diff.removed_edges,
        rearranged=diff.rearranged,
    )


# --- equivalent graphs ----------------------------------------------------------------


def test_a_fork_is_equivalent_and_shares_no_ids():
    graph = everything()
    forked = fork_graph(graph)
    assert {n.id for n in graph.nodes()}.isdisjoint(n.id for n in forked.nodes())
    assert graph.is_equivalent(forked) and forked.is_equivalent(graph)
    assert_isomorphism(graph, forked, graph.correspondence(forked))
    assert graph.diff(forked) == GraphDiff()


def test_a_fork_on_another_adapter_is_equivalent():
    graph = everything()
    forked = fork_graph(graph, DictAdapter())
    assert graph.is_equivalent(forked) and forked.is_equivalent(graph)
    assert_isomorphism(forked, graph, forked.correspondence(graph))


def test_graphs_built_separately_are_equivalent():
    assert everything().is_equivalent(everything())


def test_meta_is_not_compared():
    graph = everything()
    forked = fork_graph(graph)
    forked.meta.name = "renamed"
    forked.meta.info["app"] = "demo"
    next(forked.nodes()).meta["x"] = 1
    next(forked.edges()).meta["y"] = 2
    assert graph.is_equivalent(forked)
    assert graph.diff(forked) == GraphDiff()


def test_empty_graphs_are_equivalent():
    empty, other = OmkGraph(GraphMeta()), OmkGraph(GraphMeta())
    assert empty.correspondence(other) == {}
    assert empty.diff(other) == GraphDiff()


# --- one change, and the diff that names it ---------------------------------------------


def _line(*events):
    graph = OmkGraph(GraphMeta())
    graph.add_line(list(events))
    return graph


def tone_changed():
    c, d, e, f = notes(C, D, E, F)
    first, second = _line(c, d, e), _line(*notes(C, D), f)
    return (
        first,
        second,
        GraphDiff(
            removed_nodes=(e,),
            added_nodes=(f,),
            removed_edges=((d, Next(), e),),
            added_edges=((d, Next(), f),),
        ),
    )


def duration_changed():
    [short], [long] = notes(C), notes(C, duration=half)
    return _line(short), _line(long), GraphDiff(removed_nodes=(short,), added_nodes=(long,))


def marking_dropped():
    c, d = notes(C, D)
    first, second = _line(c, d), _line(*notes(C, D))
    dot = Marking(mark=staccato)
    first.add_articulation(dot, d)
    return (
        first,
        second,
        GraphDiff(removed_nodes=(dot,), removed_edges=((dot, OmkEdge(type=EdgeType.MARKS), d),)),
    )


def pin_added():
    c, a = notes(C, A)
    first, second = OmkGraph(GraphMeta()), OmkGraph(GraphMeta())
    first.add_node(c)
    first.add_node(a)
    second.add_node(c2 := notes(C)[0])
    second.add_simultaneous(c2, a2 := notes(A)[0])
    return first, second, GraphDiff(added_edges=((c2, Simultaneous(), a2),))


def contains_is_not_a_plain_edge():
    group, head = LineGroup(), notes(C)[0]
    first = OmkGraph(GraphMeta())
    first.add_group(group, [head])
    second = OmkGraph(GraphMeta())
    second.add_node(LineGroup())
    second.add_node(head2 := notes(C)[0])
    second.add_edge(next(second.nodes(LineGroup)), head2, EdgeType.CONTAINS)
    removed = next(first.edges())
    return (
        first,
        second,
        GraphDiff(
            removed_edges=((group, removed, head),),
            added_edges=((LineGroup(), OmkEdge(type=EdgeType.CONTAINS), head),),
        ),
    )


def _branched(**branch):
    c, a = notes(C, A)
    graph = OmkGraph(GraphMeta())
    graph.add_node(c)
    graph.add_branch(c, a, **branch)
    return graph, c, a, next(graph.edges())


def _branch_differs(first_branch, second_branch):
    first, c, a, removed = _branched(**first_branch)
    second, _, _, added = _branched(**second_branch)
    return first, second, GraphDiff(removed_edges=((c, removed, a),), added_edges=((c, added, a),))


def displacement_differs():
    return _branch_differs({"displacement": quarter}, {"displacement": eighth})


def anchor_differs():
    return _branch_differs({"anchor": TimingAnchor.ONSET}, {"anchor": TimingAnchor.OFFSET})


def origin_differs():
    graphs = []
    for origin in (EdgeOrigin.ASSERTED, EdgeOrigin.DERIVED):
        graph = OmkGraph(GraphMeta())
        memo, c = OmkObject(), notes(C)[0]
        graph.add_node(memo)
        graph.add_node(c)
        graph._graph.add_edge(memo, c, OmkEdge(type=EdgeType.ANNOTATES, origin=origin))
        graphs.append(graph)
    memo, c = OmkObject(), notes(C)[0]
    return (
        graphs[0],
        graphs[1],
        GraphDiff(
            removed_edges=((memo, OmkEdge(type=EdgeType.ANNOTATES), c),),
            added_edges=((memo, OmkEdge(type=EdgeType.ANNOTATES, origin=EdgeOrigin.DERIVED), c),),
        ),
    )


def pin_reversed():
    c, a = notes(C, A)
    first, second = OmkGraph(GraphMeta()), OmkGraph(GraphMeta())
    first.add_node(c)
    first.add_simultaneous(c, a)
    second.add_node(a2 := notes(A)[0])
    second.add_simultaneous(a2, notes(C)[0])
    return (
        first,
        second,
        GraphDiff(removed_edges=((c, Simultaneous(), a),), added_edges=((a, Simultaneous(), c),)),
    )


def staccato_moved_to_another_note():
    first, second = _line(*notes(C, D)), _line(*notes(C, D))
    c, d = notes(C, D)
    first.add_articulation(Marking(mark=staccato), next(first.nodes(predicate=lambda n: n == c)))
    second.add_articulation(Marking(mark=staccato), next(second.nodes(predicate=lambda n: n == d)))
    dot, marks = Marking(mark=staccato), OmkEdge(type=EdgeType.MARKS)
    return (
        first,
        second,
        GraphDiff(removed_edges=((dot, marks, c),), added_edges=((dot, marks, d),)),
    )


@pytest.mark.parametrize(
    "case",
    [
        tone_changed,
        duration_changed,
        marking_dropped,
        pin_added,
        contains_is_not_a_plain_edge,
        displacement_differs,
        anchor_differs,
        origin_differs,
        pin_reversed,
        staccato_moved_to_another_note,
    ],
)
def test_one_change_is_not_equivalent_and_the_diff_names_it(case):
    first, second, expected = case()
    assert not first.is_equivalent(second) and not second.is_equivalent(first)
    assert first.correspondence(second) is None
    assert first.diff(second) == expected
    assert second.diff(first) == mirrored(expected)


# --- the same things, arranged differently --------------------------------------------


def test_parallel_edges_are_compared_together():
    """A slur over one note has its STARTS_AT and ENDS_AT on the same node;
    over two equal notes it has them on different nodes. Counted by content,
    the two are the same."""
    one = _line(*notes(C, C))
    one.add_spanner(MarkSpanner(mark=slur), _head(one), _head(one))
    two = _line(first := notes(C)[0], last := notes(C)[0])
    two.add_spanner(MarkSpanner(mark=slur), first, last)
    assert one.is_equivalent(fork_graph(one))
    assert not one.is_equivalent(two)
    assert one.diff(two) == GraphDiff(rearranged=True)


def test_a_self_loop_is_compared():
    looped = OmkGraph(GraphMeta())
    x, y = notes(C, C)
    looped.add_node(x)
    looped.add_node(y)
    looped.add_next(x, x)  # a cyclic line of one note
    joined = _line(*notes(C, C))
    assert looped.is_equivalent(fork_graph(looped))
    assert not looped.is_equivalent(joined)
    assert looped.diff(joined) == GraphDiff(rearranged=True)


def test_a_mark_moved_between_equal_notes_is_rearranged():
    first, second = _line(*notes(C, C, C, D)), _line(*notes(C, C, C, D))
    first_line, second_line = (list(g.walk_line(_head(g))) for g in (first, second))
    first.add_articulation(Marking(mark=accent), first_line[0])
    second.add_articulation(Marking(mark=accent), second_line[1])
    assert not first.is_equivalent(second)
    diff = first.diff(second)
    assert diff == GraphDiff(rearranged=True)
    assert str(diff) == "the same nodes and edges, arranged differently"


def test_cycles_refinement_cannot_split_are_still_told_apart():
    """Two cycles of three identical notes against one of six: every note is
    surrounded alike, so only the search can say no."""
    two_cycles = OmkGraph(GraphMeta())
    for _ in range(2):
        cycle = notes(C, C, C)
        two_cycles.add_line(cycle)
        two_cycles.add_next(cycle[-1], cycle[0])
    one_cycle = OmkGraph(GraphMeta())
    cycle = notes(*[C] * 6)
    one_cycle.add_line(cycle)
    one_cycle.add_next(cycle[-1], cycle[0])
    assert not two_cycles.is_equivalent(one_cycle)
    assert two_cycles.is_equivalent(fork_graph(two_cycles))


def _head(graph: OmkGraph):
    return next(graph.nodes(predicate=lambda n: graph.get_previous(n) is None))


# --- symmetric material that a search alone cannot refute in reasonable time ---------------


def test_identical_fragments_with_one_odd_one_out():
    first, second = OmkGraph(GraphMeta()), OmkGraph(GraphMeta())
    for graph, odd in ((first, A), (second, B)):
        for note in notes(*[C] * 13, odd):
            graph.add_node(note)
    assert not first.is_equivalent(second)


def _identical_lines(marked_at: list[int]) -> OmkGraph:
    """Twenty lines of twenty identical notes, line i with an accent on its
    note marked_at[i]."""
    graph = OmkGraph(GraphMeta())
    for position in marked_at:
        line = notes(*[C] * 20)
        graph.add_line(line)
        graph.add_articulation(Marking(mark=accent), line[position])
    return graph


def test_identical_lines_with_one_mark_moved():
    first = _identical_lines([5] * 20)
    second = _identical_lines([5] * 19 + [6])
    assert not first.is_equivalent(second)
    assert first.diff(second) == GraphDiff(rearranged=True)
    assert first.is_equivalent(_identical_lines([5] * 20))


@pytest.mark.slow
def test_a_long_line_of_identical_notes():
    def marked_line(position):
        graph = _line(*(line := notes(*[C] * 2000)))
        for note in line:
            graph.add_articulation(Marking(mark=staccato), note)
        graph.add_articulation(Marking(mark=accent), line[position])
        return graph

    assert marked_line(700).is_equivalent(fork_graph(marked_line(700)))
    assert not marked_line(700).is_equivalent(marked_line(1000))


# --- the diff's text --------------------------------------------------------------------


def test_the_diff_reads_as_removals_and_additions():
    first, second, expected = marking_dropped()
    [dot] = expected.removed_nodes
    [(source, edge, target)] = expected.removed_edges
    assert str(first.diff(second)) == f"- {dot!r}\n- {source!r} --{edge!r}--> {target!r}"
    assert str(second.diff(first)) == f"+ {dot!r}\n+ {source!r} --{edge!r}--> {target!r}"
    assert str(first.diff(first)) == "no differences"


# --- properties -------------------------------------------------------------------------


@st.composite
def graphs(draw) -> OmkGraph:
    """Up to four lines of notes, with some pins (a note may be pinned to
    itself) and some marks."""
    graph = OmkGraph(GraphMeta())
    events = []
    for line in draw(st.lists(lines(), min_size=1, max_size=4)):
        graph.add_line(line)
        events += line
    index = st.integers(0, len(events) - 1)
    for i, j in draw(st.lists(st.tuples(index, index), max_size=4)):
        if not graph._graph.has_edge(events[i], events[j], EdgeType.SIMULTANEOUS):
            graph.add_simultaneous(events[i], events[j])
    for i, mark in draw(
        st.lists(st.tuples(index, st.sampled_from([staccato, accent])), max_size=4)
    ):
        graph.add_articulation(Marking(mark=mark), events[i])
    return graph


@given(graphs(), st.booleans())
def test_a_fork_is_equivalent_through_a_genuine_correspondence(graph, on_dict_adapter):
    forked = fork_graph(graph, DictAdapter() if on_dict_adapter else None)
    assert graph.is_equivalent(forked)
    assert_isomorphism(graph, forked, graph.correspondence(forked))
    assert graph.diff(forked) == GraphDiff()


@given(graphs(), graphs())
def test_equivalence_and_diff_are_symmetric(first, second):
    assert first.is_equivalent(second) == second.is_equivalent(first)
    assert second.diff(first) == mirrored(first.diff(second))


@given(graphs(), st.data())
def test_changing_one_node_is_seen(graph, data):
    forked = fork_graph(graph)
    changed = data.draw(st.sampled_from(sorted(forked.nodes(NoteEvent), key=repr)))
    was = copy.deepcopy(changed)
    changed.duration = ClockDuration.from_seconds(1)  # no drawn note has a clock duration
    assert not graph.is_equivalent(forked)
    diff = graph.diff(forked)
    assert diff.added_nodes == (changed,)
    assert diff.removed_nodes == (was,)
