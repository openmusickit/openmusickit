"""Laws that hold for any line, checked over random lines of random note
events (durations may be unknown): timing is antisymmetric and follows
durations; span walks are line walks plus branches and never cross a pin;
composite operations equal their primitive expansion; transposition undoes
itself; `materialize` copies exactly and leaves the original alone.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 examples per
property.
"""

import itertools
import warnings

import pytest
from hypothesis import given
from hypothesis import strategies as st

from openmusickit.errors import GraphError, OmkWarning
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import Part, Stint
from openmusickit.systems.wsmn.temporal.symbols import eighth, quarter
from openmusickit.systems.wsmn.tonal.symbols import M2, A, C, D, E, F
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from openmusickit.values.time.duration import ZeroDuration
from tests.graph.helpers import names, notes, snapshot
from tests.strategies import lines, note_events, tonal_vectors


def fresh(line: list[NoteEvent]) -> OmkGraph:
    graph = OmkGraph(GraphMeta())
    graph.add_line(line)
    return graph


@given(lines())
def test_relative_onset_of_an_event_to_itself_is_zero(line):
    graph = fresh(line)
    for event in line:
        assert graph.relative_onset(event, event) == ZeroDuration()


@given(lines(min_size=2))
def test_relative_onset_is_antisymmetric_and_follows_the_durations_between(line):
    """From i to a later j, the onset is the sum of the durations of the
    events in between (i included, j excluded) if all are known; then the
    reverse onset is its negation; otherwise both directions raise."""
    graph = fresh(line)
    for i, j in itertools.combinations(range(len(line)), 2):
        between = [event.duration for event in line[i:j]]
        if all(d is not None for d in between):
            forward = graph.relative_onset(line[i], line[j])
            assert forward == sum(between)
            assert graph.relative_onset(line[j], line[i]) == -forward
        else:
            with pytest.raises(GraphError):
                graph.relative_onset(line[i], line[j])
            with pytest.raises(GraphError):
                graph.relative_onset(line[j], line[i])


@given(lines())
def test_next_degree_is_at_most_one_each_way(line):
    graph = fresh(line)
    for event in line:
        assert len(list(graph._graph.out_edges(event, EdgeType.NEXT))) <= 1
        assert len(list(graph._graph.in_edges(event, EdgeType.NEXT))) <= 1
    assert [graph.get_next(e) for e in line] == line[1:] + [None]
    assert [graph.get_previous(e) for e in line] == [None, *line[:-1]]


@given(lines(min_size=2), lines(max_size=3), lines(max_size=3), st.data())
def test_walk_span_is_walk_line_plus_branches_and_never_crosses_a_pin(line, branch, pinned, data):
    at = data.draw(st.integers(0, len(line) - 1))
    pin_at = data.draw(st.integers(0, len(line) - 1))
    graph = fresh(line)
    graph.add_line(branch)
    graph.add_line(pinned)
    graph.add_branch(line[at], branch[0])
    graph.add_simultaneous(line[pin_at], pinned[0])
    assert list(graph.walk_line(line[0])) == line
    assert list(graph.walk_span(line[0])) == line[: at + 1] + branch + line[at + 1 :]
    assert list(graph.walk_span(pinned[0])) == pinned
    assert list(graph.walk_span(branch[0])) == branch
    assert list(graph.branches_from(line[at])) == [branch[0]]
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_alignment() == []  # one pin, no other path: nothing to disagree


@given(lines(), tonal_vectors(qualified=False))
def test_transposing_a_line_up_then_down_restores_it(line, interval):
    graph = fresh(line)
    before = snapshot(graph)
    originals = [set(event.tones) for event in line]
    graph.transform_tones(line[0], None, TonalVector.transpose, interval)
    for event, tones in zip(line, originals, strict=True):
        assert event.tones == {t + interval for t in tones}
    graph.transform_tones(line[0], None, TonalVector.transpose, interval, TonalDirection.DOWN)
    assert snapshot(graph) == before


@given(lines())
def test_add_line_equals_repeated_add_next(line):
    by_primitives = OmkGraph(GraphMeta())
    by_primitives.add_node(line[0])
    for a, b in zip(line, line[1:], strict=False):
        by_primitives.add_next(a, b)
    assert snapshot(fresh(line)) == snapshot(by_primitives)


@given(lines(min_size=2), note_events(), st.data())
def test_insert_event_equals_its_primitive_expansion(line, event, data):
    k = data.draw(st.integers(1, len(line) - 1))
    graph = fresh(line)
    graph.insert_event(event, line[k - 1], line[k])
    assert list(graph.walk_line(line[0])) == line[:k] + [event] + line[k:]

    by_primitives = fresh(line)
    by_primitives.remove_edge(by_primitives.get_edge(line[k - 1], line[k], EdgeType.NEXT))
    by_primitives.add_next(line[k - 1], event)
    by_primitives.add_next(event, line[k])
    assert snapshot(graph) == snapshot(by_primitives)


@given(lines(), st.data())
def test_materialize_copies_the_span_exactly_and_leaves_the_original(line, data):
    start = data.draw(st.integers(0, len(line) - 1))
    end = data.draw(st.integers(start, len(line) - 1))
    graph = fresh(line)
    before = snapshot(graph)
    stint = Stint()
    graph.add_stint(Part(name="Oboe"), stint, line[start], line[end])

    head = graph.materialize(stint)

    forked = list(graph.walk_stint(stint))
    assert forked[0] is head
    assert forked == line[start : end + 1]  # equal content ...
    assert not any(copy is original for copy in forked for original in line)  # ... new objects
    assert {copy.id for copy in forked}.isdisjoint({original.id for original in line})
    assert graph.get_previous(head) is None and graph.get_next(forked[-1]) is None
    after = snapshot(graph)
    assert set(before[0]) <= set(after[0]) and set(before[1]) <= set(after[1])
    assert list(graph.walk_line(line[0])) == line
    assert list(graph._graph.successors(stint, edge_type=EdgeType.STARTS_AT)) == [head]


# --- cyclic lines: valid music, and walkers go round once ---------------------------


def test_walk_line_terminates_on_a_cyclic_line():
    """A NEXT cycle (a gamelan cycle) is accepted, and `walk_line` yields
    each event once, from wherever it starts; an `end` past the cycle is a
    ValueError, not a hang."""
    graph = OmkGraph(GraphMeta())
    cycle = notes(C, D, E)
    graph.add_line(cycle)
    graph.add_next(cycle[-1], cycle[0])  # closes the cycle: both guards pass
    assert graph.get_next(cycle[-1]) is cycle[0]
    events = list(itertools.islice(graph.walk_line(cycle[0]), len(cycle) + 1))
    assert events == cycle
    assert list(graph.walk_line(cycle[1])) == cycle[1:] + cycle[:1]
    assert list(graph.walk_line(cycle[1], cycle[0])) == cycle[1:] + cycle[:1]
    stranger = notes(A)[0]
    graph.add_node(stranger)
    with pytest.raises(ValueError):
        list(graph.walk_line(cycle[0], stranger))


def test_walk_span_terminates_when_lines_branch_into_each_other():
    """Two heads each branched from the other's line are walked once each;
    `transform_tones` over the span touches every event exactly once."""
    graph = OmkGraph(GraphMeta())
    first, second = notes(C, D), notes(E, F)
    graph.add_line(first)
    graph.add_line(second)
    graph.add_branch(first[0], second[0])
    graph.add_branch(second[0], first[0])
    events = list(itertools.islice(graph.walk_span(first[0]), 5))
    assert sorted(names(events)) == sorted(names(first + second))
    assert len(events) == 4
    graph.transform_tones(first[0], None, TonalVector.transpose, M2)
    assert names(first + second) == ["D", "E", "F#", "G"]


def test_a_nudged_branch_keeps_onsets_consistent():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    a, b = notes(E, C, duration=eighth)
    graph.add_line([c, d])
    graph.add_line([a, b])
    graph.add_branch(c, a, displacement=eighth)
    assert graph.relative_onset(c, b) == quarter
    assert graph.relative_onset(b, d) == ZeroDuration()
