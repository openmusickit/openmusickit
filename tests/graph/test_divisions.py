"""`OmkGraph.remove_derivable_divisions`: taking away the bar lines the meter
implies, and only those. The DivisionEvent itself is tested in
tests/objects/test_division_event.py."""

from fractions import Fraction

from hypothesis import given
from hypothesis import strategies as st

from openmusickit.graph.edge import EdgeType, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.context_event import MeterEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.marking import Marking
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import double_bar, end_repeat, fermata, final_bar
from openmusickit.systems.wsmn.temporal.symbols import (
    eighth,
    four_four,
    half,
    quarter,
    three_four,
)
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.symbols import C, D
from openmusickit.values.time.duration import Measurable, TemporalUnit
from tests.graph.helpers import fork_graph
from tests.strategies import metrical_durations


def quarters(n: int) -> list[NoteEvent]:
    return [NoteEvent(tones={C}, duration=quarter) for _ in range(n)]


def divisions_of(graph: OmkGraph, head) -> list[DivisionEvent]:
    return [event for event in graph.walk_line(head) if isinstance(event, DivisionEvent)]


def build(graph: OmkGraph, *segments) -> MeterEvent:
    """A 4/4 line: `segments` are lists of notes and the divisions between them."""
    meter = MeterEvent(meter=four_four)
    events = [meter]
    for segment in segments:
        events.extend(segment if isinstance(segment, list) else [segment])
    graph.add_line(events)
    return meter


def test_every_on_grid_division_goes():
    graph = OmkGraph(GraphMeta())
    first, second = DivisionEvent(), DivisionEvent()
    meter = build(graph, quarters(4), first, quarters(4), second, quarters(4))
    removed = graph.remove_derivable_divisions(meter)
    assert removed[0] is first and removed[1] is second and len(removed) == 2
    assert divisions_of(graph, meter) == []
    assert len(list(graph.walk_line(meter))) == 13


def test_a_pickup_stays_and_restarts_the_count():
    graph = OmkGraph(GraphMeta())
    pickup, bar = DivisionEvent(), DivisionEvent()
    meter = build(graph, quarters(1), pickup, quarters(4), bar, quarters(4))
    removed = graph.remove_derivable_divisions(meter)
    assert [d is bar for d in removed] == [True]
    assert [d is pickup for d in divisions_of(graph, meter)] == [True]


def test_a_split_bar_keeps_its_extra_division():
    graph = OmkGraph(GraphMeta())
    split, after_split, next_bar = DivisionEvent(), DivisionEvent(), DivisionEvent()
    meter = build(
        graph, quarters(3), split, quarters(1), after_split, quarters(4), next_bar, quarters(4)
    )
    removed = graph.remove_derivable_divisions(meter)
    assert [d is next_bar for d in removed] == [True]
    assert [d is split or d is after_split for d in divisions_of(graph, meter)] == [True, True]


def test_shaped_divisions_stay():
    graph = OmkGraph(GraphMeta())
    shaped = [DivisionEvent(shape=s) for s in (end_repeat, double_bar, final_bar)]
    meter = build(graph, quarters(4), shaped[0], quarters(4), shaped[1], quarters(4), shaped[2])
    assert graph.remove_derivable_divisions(meter) == []
    assert divisions_of(graph, meter) == shaped


def test_the_last_division_stays_even_if_on_the_grid():
    graph = OmkGraph(GraphMeta())
    last = DivisionEvent()
    meter = build(graph, quarters(4), last)
    assert graph.remove_derivable_divisions(meter) == []
    assert [d is last for d in divisions_of(graph, meter)] == [True]


def test_a_meter_change_changes_the_grid():
    graph = OmkGraph(GraphMeta())
    common, waltz, off = DivisionEvent(), DivisionEvent(), DivisionEvent()
    meter = MeterEvent(meter=four_four)
    graph.add_line(
        [
            meter,
            *quarters(4),
            common,
            MeterEvent(meter=three_four),
            *quarters(3),
            waltz,
            *quarters(4),
            off,
            *quarters(1),
        ]
    )
    removed = graph.remove_derivable_divisions(meter)
    assert [d is common or d is waltz for d in removed] == [True, True]
    assert [d is off for d in divisions_of(graph, meter)] == [True]


def test_a_line_with_no_meter_keeps_every_division():
    graph = OmkGraph(GraphMeta())
    bar = DivisionEvent()
    head = NoteEvent(tones={C}, duration=quarter)
    graph.add_line([head, *quarters(3), bar, *quarters(4)])
    assert graph.remove_derivable_divisions(head) == []
    assert [d is bar for d in divisions_of(graph, head)] == [True]


def test_a_division_with_a_mark_on_it_stays():
    graph = OmkGraph(GraphMeta())
    held, plain = DivisionEvent(), DivisionEvent()
    meter = build(graph, quarters(4), held, quarters(4), plain, quarters(4))
    graph.add_articulation(Marking(mark=fermata), held)
    removed = graph.remove_derivable_divisions(meter)
    assert [d is plain for d in removed] == [True]
    assert [d is held for d in divisions_of(graph, meter)] == [True]


def test_pins_move_to_the_event_after_a_removed_division():
    graph = OmkGraph(GraphMeta())
    bar = DivisionEvent()
    meter = build(graph, quarters(4), bar, quarters(4))
    other = [NoteEvent(tones={D}, duration=half) for _ in range(3)]
    graph.add_line(other)
    graph.add_simultaneous(bar, other[0], displacement=eighth)  # pin out of the division
    graph.add_simultaneous(other[2], bar, anchor=TimingAnchor.OFFSET)  # and one into it
    grid = SyncLine(temporal_system=WSMN_TEMPORAL)
    point = graph.sync_event(bar, grid, TemporalUnit(1, four_four))
    downbeat = graph.get_next(bar)

    graph.remove_derivable_divisions(meter)

    pins = list(graph.edges(EdgeType.SIMULTANEOUS))
    assert len(pins) == 3
    assert graph.get_edge(downbeat, other[0], EdgeType.SIMULTANEOUS).displacement == eighth
    into = graph.get_edge(other[2], downbeat, EdgeType.SIMULTANEOUS)
    assert into.anchor is TimingAnchor.OFFSET
    assert list(graph.synced_events(point)) == [downbeat]
    assert graph.relative_onset(meter, other[0]).rational_length == Fraction(9, 8)


def test_an_unknown_duration_stops_the_judging():
    graph = OmkGraph(GraphMeta())
    before, after = DivisionEvent(), DivisionEvent()
    opaque = NoteEvent(tones={C}, duration=None)
    meter = build(graph, quarters(4), before, [opaque, *quarters(3)], after, quarters(4))
    removed = graph.remove_derivable_divisions(meter)
    assert [d is before for d in removed] == [True]
    assert [d is after for d in divisions_of(graph, meter)] == [True]


def test_removed_divisions_go_back_where_they_were():
    graph = OmkGraph(GraphMeta())
    pickup, bar1, bar2 = DivisionEvent(), DivisionEvent(), DivisionEvent()
    meter = build(graph, quarters(1), pickup, quarters(4), bar1, quarters(4), bar2, quarters(2))
    original = fork_graph(graph)
    positions = {id(d): (graph.get_previous(d), graph.get_next(d)) for d in (bar1, bar2)}
    removed = graph.remove_derivable_divisions(meter)
    assert not graph.is_equivalent(original)
    for division in removed:
        previous, following = positions[id(division)]
        graph.insert_event(division, previous, following)
    assert graph.is_equivalent(original), graph.diff(original)


@given(
    durations=st.lists(metrical_durations(), min_size=1, max_size=12),
    beats=st.integers(1, 4),
    extra=st.data(),
)
def test_only_the_divisions_one_meter_after_a_boundary_are_removed(durations, beats, extra):
    """Divisions placed at every gap between notes, some on the grid and
    some off it: afterwards, exactly those the rule names are gone, and the
    notes are untouched."""
    graph = OmkGraph(GraphMeta())
    meter_length = Fraction(beats, 4)
    meter = MeterEvent(meter=TemporalUnit(beats, quarter))
    notes = [NoteEvent(tones={C}, duration=d) for d in durations]
    events: list = [meter]
    divisions: list[DivisionEvent] = []
    for note in notes:
        events.append(note)
        if extra.draw(st.booleans()):
            division = DivisionEvent()
            events.append(division)
            divisions.append(division)
    graph.add_line(events)

    expected: list[DivisionEvent] = []
    position = boundary = Fraction(0)
    for index, event in enumerate(events):
        if isinstance(event, DivisionEvent):
            if position - boundary == meter_length and index + 1 < len(events):
                expected.append(event)
            boundary = position
        if isinstance(event.duration, Measurable):
            position += event.duration.rational_length

    removed = graph.remove_derivable_divisions(meter)
    assert [id(d) for d in removed] == [id(d) for d in expected]
    assert [n for n in graph.walk_line(meter) if isinstance(n, NoteEvent)] == notes
    removed_ids = {
        id(d) for d in removed
    }  # `in` would use ==, and shapeless divisions are all equal
    kept = [d for d in divisions if id(d) not in removed_ids]
    assert [id(d) for d in divisions_of(graph, meter)] == [id(d) for d in kept]
