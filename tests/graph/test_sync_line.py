"""Sync lines: a named timing origin, in its own temporal system, that music
pins to without the two ever becoming one clock. See _plans/sync-line.md."""

import warnings

import pytest

from openmusickit.errors import GraphError, OmkWarning, TemporalCompatibilityError
from openmusickit.graph.edge import EdgeType, TimedEdge, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.objects.part import LineGroup
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.systems.wsmn.temporal.symbols import half, quarter, whole
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.symbols import A, C, D, E, F, G
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration
from openmusickit.values.time.duration import (
    Duration,
    Measurable,
    TemporalSystem,
    ZeroDuration,
)
from tests.graph.helpers import notes


def seconds(n) -> ClockDuration:
    return ClockDuration.from_seconds(n)


@pytest.fixture
def cue():
    """A stopwatch score: four whole notes, the first pinned five seconds into
    the reel and the last nine seconds in."""
    graph = OmkGraph(GraphMeta())
    line = notes(C, D, E, F, duration=whole)
    graph.add_line(line)
    film = SyncLine(temporal_system=CLOCK_TIME, name="Reel 1")
    start = graph.sync_event(line[0], film, seconds(5))
    end = graph.sync_event(line[3], film, seconds(9))
    return graph, line, film, start, end


# The shape of a sync line


def test_a_sync_line_holds_its_points_in_offset_order(cue):
    graph, _, film, start, end = cue
    middle = graph.create_sync_point(film, seconds(7))
    assert graph.sync_points(film) == [start, middle, end]
    assert [p.offset for p in graph.sync_points(film)] == [seconds(5), seconds(7), seconds(9)]


def test_a_point_knows_its_line_and_its_events(cue):
    graph, line, film, start, _ = cue
    assert graph.sync_line_of(start) is film
    assert list(graph.synced_events(start)) == [line[0]]


def test_the_containment_edge_is_plain_not_timed(cue):
    """The offset lives on the point, so the edge carries nothing: a sync
    line's CONTAINS is plain, as a Score's is, not timed as a group's is."""
    graph, _, film, start, _ = cue
    edge = graph.get_edge(film, start, EdgeType.CONTAINS)
    assert not isinstance(edge, TimedEdge)


def test_points_are_not_sequential_events(cue):
    """A point is an instant, so it cannot be chained, branched or scored as a
    line head."""
    _, _, _, start, _ = cue
    assert not isinstance(start, SequentialEvent)
    assert not hasattr(start, "duration")


def test_a_point_may_fall_before_the_origin():
    graph = OmkGraph(GraphMeta())
    film = SyncLine(temporal_system=CLOCK_TIME)
    count_in = graph.create_sync_point(film, -seconds(2))
    origin = graph.create_sync_point(film, ZeroDuration())
    assert graph.sync_points(film) == [count_in, origin]
    assert graph.relative_onset(count_in, origin) == seconds(2)


# Timing: the line and the music meet without composing


def test_the_timeline_measures_its_own_points(cue):
    graph, _, _, start, end = cue
    assert graph.relative_onset(start, end) == seconds(4)
    assert graph.relative_onset(end, start) == -seconds(4)


def test_an_event_sits_on_its_own_point(cue):
    graph, line, _, start, _ = cue
    assert graph.relative_onset(line[0], start) == ZeroDuration()
    assert graph.relative_onset(start, line[0]) == ZeroDuration()


def test_the_music_keeps_its_own_units_across_a_sync_line(cue):
    """The regression test: a breadth-first walk reaches the far event in two
    hops through the timeline and in three along the line, so without the gate
    this answers in seconds."""
    graph, line, _, _, _ = cue
    assert graph.relative_onset(line[0], line[3]) == whole + whole + whole
    assert graph.relative_onset(line[0], line[3]).temporal_system is WSMN_TEMPORAL


def test_a_sync_line_does_not_join_two_lines():
    """Two lines pinned to one timeline stay unrelated: the walk meets the
    timeline at a point and does not pass through it."""
    graph = OmkGraph(GraphMeta())
    first, second = notes(C, D), notes(E, F, duration=half)
    graph.add_line(first)
    graph.add_line(second)
    film = SyncLine(temporal_system=CLOCK_TIME)
    graph.sync_event(first[0], film, ZeroDuration())
    graph.sync_event(second[0], film, seconds(5))
    for u, v in ((first[0], second[0]), (second[0], first[0])):
        with pytest.raises(GraphError, match="No timing path"):
            graph.relative_onset(u, v)


@pytest.mark.parametrize("reverse", [False, True])
def test_reaching_past_a_point_fails_the_same_way_in_both_directions(reverse):
    """The gate is two-sided, so the relation stays antisymmetric: a one-sided
    gate answered in seconds one way and raised the other."""
    graph = OmkGraph(GraphMeta())
    first, second = notes(C, D), notes(E, F, duration=half)
    graph.add_line(first)
    graph.add_line(second)
    film = SyncLine(temporal_system=CLOCK_TIME)
    point = graph.sync_event(first[0], film, ZeroDuration())
    graph.sync_event(second[0], film, seconds(5))
    u, v = (second[1], point) if reverse else (point, second[1])
    with pytest.raises(GraphError, match="No timing path"):
        graph.relative_onset(u, v)


def test_two_events_on_one_point_are_simultaneous():
    """A pin through a point is not a pin through the line: two events sharing
    a point relate to each other, which is the whole meaning of sharing it."""
    graph = OmkGraph(GraphMeta())
    flute, violin = notes(C, D), notes(E, F)
    graph.add_line(flute)
    graph.add_line(violin)
    film = SyncLine(temporal_system=CLOCK_TIME)
    point = graph.sync_event(flute[0], film, seconds(3))
    graph.sync_event(violin[0], film, seconds(3))
    assert graph.relative_onset(flute[0], violin[0]) == ZeroDuration()
    assert graph.relative_onset(flute[1], violin[1]) == ZeroDuration()
    assert sorted(id(e) for e in graph.synced_events(point)) == sorted(
        [id(flute[0]), id(violin[0])]
    )


def test_a_group_contains_edge_still_carries_timing(cue):
    """The gate keys on sync nodes, not on CONTAINS: a group is still a timing
    origin and a pin off one of its lines still works."""
    graph = OmkGraph(GraphMeta())
    rh, lh, other = notes(C, D), notes(E, F), notes(G, A)
    for line in (rh, lh, other):
        graph.add_line(line)
    piano = LineGroup(name="Piano")
    graph.add_group(piano, [rh[0], lh[0]])
    graph.add_simultaneous(rh[1], other[0])
    assert graph.relative_onset(piano, lh[0]) == ZeroDuration()
    assert graph.relative_onset(rh[0], other[0]) == quarter
    assert graph.relative_onset(other[0], rh[0]) == -quarter


def test_anchoring_to_the_release_puts_the_point_at_the_end():
    graph = OmkGraph(GraphMeta())
    line = notes(C, D, duration=whole)
    graph.add_line(line)
    film = SyncLine(temporal_system=CLOCK_TIME)
    release = graph.sync_event(line[0], film, seconds(9), anchor=TimingAnchor.OFFSET)
    assert graph.relative_onset(line[0], release) == whole


def test_a_release_anchor_says_nothing_while_the_duration_is_unknown():
    graph = OmkGraph(GraphMeta())
    event = NoteEvent(tones={C})
    graph.add_node(event)
    film = SyncLine(temporal_system=CLOCK_TIME)
    release = graph.sync_event(event, film, seconds(9), anchor=TimingAnchor.OFFSET)
    with pytest.raises(GraphError, match="No timing path"):
        graph.relative_onset(event, release)


# Find or create


def test_a_point_is_reused_for_an_equal_offset(cue):
    graph, _, film, start, _ = cue
    assert graph.create_sync_point(film, ClockDuration.from_milliseconds(5000)) is start
    assert len(graph.sync_points(film)) == 2


def test_offsets_are_matched_by_length_not_by_spelling():
    """Durations compare by length, so a half finds a point written as two
    quarters' worth."""
    graph = OmkGraph(GraphMeta())
    bars = SyncLine(temporal_system=WSMN_TEMPORAL, name="Rehearsal ruler")
    written = graph.create_sync_point(bars, quarter + quarter)
    assert graph.create_sync_point(bars, half) is written
    assert len(graph.sync_points(bars)) == 1


def test_an_empty_sync_line_can_be_put_on_the_graph():
    graph = OmkGraph(GraphMeta())
    film = SyncLine(temporal_system=CLOCK_TIME)
    graph.add_sync_line(film)
    assert graph.sync_points(film) == []
    assert graph.get_node(film.id) is film


# Guards


def test_an_offset_must_belong_to_the_lines_temporal_system():
    graph = OmkGraph(GraphMeta())
    film = SyncLine(temporal_system=CLOCK_TIME)
    with pytest.raises(TemporalCompatibilityError, match="Western Standard"):
        graph.create_sync_point(film, quarter)


def test_a_zero_offset_belongs_to_every_system():
    graph = OmkGraph(GraphMeta())
    film = SyncLine(temporal_system=CLOCK_TIME)
    origin = graph.create_sync_point(film, ZeroDuration())
    assert graph.sync_points(film) == [origin]


class Unmeasured(Duration):
    """A duration in a system whose elements do not reduce to one number, which
    `Duration` explicitly allows (a chant notation, say)."""

    __slots__ = ()

    @property
    def temporal_system(self) -> TemporalSystem:
        return CLOCK_TIME

    def __neg__(self):
        return self


def test_an_offset_must_be_measurable():
    """A sync line orders its points, so an offset that reduces to no number
    cannot go on one."""
    graph = OmkGraph(GraphMeta())
    film = SyncLine(temporal_system=CLOCK_TIME)
    with pytest.raises(TypeError, match="must be a Measurable"):
        graph.add_sync_point(film, SyncPoint(offset=Unmeasured()))


def test_two_points_on_one_line_cannot_share_an_offset(cue):
    graph, _, film, _, _ = cue
    with pytest.raises(GraphError, match="already has a point at"):
        graph.add_sync_point(film, SyncPoint(offset=seconds(5), name="a second five"))


def test_a_point_belongs_to_one_sync_line_only(cue):
    graph, _, _, start, _ = cue
    other = SyncLine(temporal_system=CLOCK_TIME, name="Reel 2")
    with pytest.raises(GraphError, match="already on another sync line"):
        graph.add_sync_point(other, start)


def test_adding_the_same_point_to_the_same_line_twice_is_refused(cue):
    graph, _, film, start, _ = cue
    with pytest.raises(GraphError, match="already exists"):
        graph.add_sync_point(film, start)


# Order agreement


def test_points_pinned_out_of_order_are_reported(cue):
    """Across temporal systems: the offsets are clock time, the music is
    metrical, and only their order is compared."""
    graph, line, film, _, _ = cue
    earlier = graph.create_sync_point(film, seconds(1))
    graph.add_simultaneous(line[2], earlier)  # but line[2] comes after line[0]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        conflicts = graph.check_sync_alignment(film)
    assert len(conflicts) == 1
    assert "runs the other way" in str(caught[0].message)
    assert conflicts[0] == (earlier, graph.sync_points(film)[1])


def test_simultaneous_events_pinned_to_two_points_are_reported():
    """The zero case: the music makes them one instant, the timeline makes
    them two."""
    graph = OmkGraph(GraphMeta())
    flute, violin = notes(C, D), notes(E, F)
    graph.add_line(flute)
    graph.add_line(violin)
    graph.add_simultaneous(flute[0], violin[0])
    film = SyncLine(temporal_system=CLOCK_TIME)
    graph.sync_event(flute[0], film, seconds(3))
    graph.sync_event(violin[0], film, seconds(8))
    with pytest.warns(OmkWarning, match="runs the other way"):
        assert len(graph.check_sync_alignment(film)) == 1


def test_a_same_system_line_is_checked_for_order_too():
    graph = OmkGraph(GraphMeta())
    line = notes(C, D, E, duration=whole)
    graph.add_line(line)
    bars = SyncLine(temporal_system=WSMN_TEMPORAL)
    graph.sync_event(line[0], bars, whole)
    graph.sync_event(line[2], bars, ZeroDuration())
    with pytest.warns(OmkWarning, match="runs the other way"):
        assert len(graph.check_sync_alignment(bars)) == 1


def test_distance_is_not_checked_only_order():
    """Deliberate: comparing the gap between offsets with the elapsed music
    would need both to be paced alike, which a temporal system does not say.
    Four whole notes against four seconds is in order, so it is silent."""
    graph = OmkGraph(GraphMeta())
    line = notes(C, D, E, F, duration=whole)
    graph.add_line(line)
    bars = SyncLine(temporal_system=WSMN_TEMPORAL)
    graph.sync_event(line[0], bars, ZeroDuration())
    graph.sync_event(line[3], bars, quarter)  # the music covers three wholes, not a quarter
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_sync_alignment(bars) == []


def test_a_timeline_in_order_is_silent(cue):
    graph, _, film, _, _ = cue
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_sync_alignment(film) == []


def test_unrelated_music_cannot_be_checked(cue):
    """Two events on different points with no other path between them have no
    relative onset, so there is nothing to disagree with."""
    graph, _, film, _, _ = cue
    loose = notes(G, A)
    graph.add_line(loose)
    graph.sync_event(loose[0], film, seconds(7))
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_sync_alignment(film) == []


def test_every_sync_line_is_checked_when_none_is_named(cue):
    graph, line, film, _, _ = cue
    earlier = graph.create_sync_point(film, seconds(1))
    graph.add_simultaneous(line[2], earlier)
    with pytest.warns(OmkWarning):
        assert len(graph.check_sync_alignment()) == 1


def test_music_of_unmeasurable_length_cannot_be_checked_for_order():
    """An offset must be measurable, but a *distance through the music* need
    not be: a system whose durations reduce to no number gives the walk nothing
    to take a sign of, so there is nothing to agree or disagree with."""
    graph = OmkGraph(GraphMeta())
    line = [NoteEvent(tones={C}, duration=Unmeasured()), NoteEvent(tones={D})]
    graph.add_line(line)
    film = SyncLine(temporal_system=CLOCK_TIME)
    graph.sync_event(line[0], film, seconds(9))
    graph.sync_event(line[1], film, seconds(1))  # backwards, but unprovably so
    assert not isinstance(graph.relative_onset(line[0], line[1]), Measurable)
    with warnings.catch_warnings():
        warnings.simplefilter("error", OmkWarning)
        assert graph.check_sync_alignment(film) == []
