"""Temporal context events: a meter or a tempo placed in a line, holding
any Measurable or any TemporalRatio, taking no time, and printing a repr
that builds them back."""

import copy
import itertools
from fractions import Fraction

import pytest

from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.context_event import (
    ContextEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
    TemporalContextEvent,
)
from openmusickit.objects.omk_object import SequentialEvent, TonalObject
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.symbols import (
    dotted_quarter,
    eighth,
    four_four,
    half,
    quarter,
    six_eight,
    two_two,
)
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.tonal.symbols import C, D, E
from openmusickit.values.time.clock_time import ClockDuration, Tempo
from openmusickit.values.time.duration import (
    CompoundTemporalUnit,
    TemporalRatio,
    TemporalUnit,
    ZeroDuration,
)
from tests.graph.helpers import notes

NAMESPACE = {
    name: obj
    for name, obj in [
        ("ContextEvent", ContextEvent),
        ("ModalContextEvent", ModalContextEvent),
        ("MeterEvent", MeterEvent),
        ("TempoEvent", TempoEvent),
        ("TimeSignature", TimeSignature),
        ("TemporalUnit", TemporalUnit),
        ("CompoundTemporalUnit", CompoundTemporalUnit),
        ("TemporalRatio", TemporalRatio),
        ("MetricalDuration", MetricalDuration),
        ("ClockDuration", ClockDuration),
        ("Tempo", Tempo),
    ]
}


def test_temporal_contexts_are_context_events_of_zero_duration():
    for event in (MeterEvent(), TempoEvent()):
        assert isinstance(event, TemporalContextEvent)
        assert isinstance(event, ContextEvent) and isinstance(event, SequentialEvent)
        assert not isinstance(event, TonalObject)
        assert isinstance(event.duration, ZeroDuration)
    assert not isinstance(ModalContextEvent(), TemporalContextEvent)


def test_duration_cannot_be_given_at_construction():
    with pytest.raises(TypeError):
        MeterEvent(duration=quarter)
    with pytest.raises(TypeError):
        TempoEvent(duration=None)


def test_values_default_to_unspecified():
    assert MeterEvent().meter is None
    assert TempoEvent().tempo is None


def test_a_meter_is_any_measurable():
    """A time signature, a bare unit, an additive cycle, or a single note
    value: whatever the system measures its cycle in, held as given."""
    meters = [
        four_four,
        TemporalUnit(3, quarter),
        CompoundTemporalUnit([TemporalUnit(2, eighth), TemporalUnit(3, eighth)]),
        dotted_quarter,
    ]
    for meter in meters:
        assert MeterEvent(meter=meter).meter is meter


def test_a_tempo_is_any_temporal_ratio():
    """A metronome marking is a Tempo; a metric modulation is a plain ratio
    of the new note value to the old, which says nothing about clock time."""
    marking = Tempo(120, quarter)
    assert TempoEvent(tempo=marking).tempo is marking
    modulation = TemporalRatio(dotted_quarter, quarter)  # quarter = dotted quarter
    assert TempoEvent(tempo=modulation).tempo is modulation
    assert modulation.multiplier == Fraction(2, 3)
    assert dotted_quarter.rational_length * modulation.multiplier == quarter.rational_length


def test_equality_ignores_id_and_compares_the_value():
    assert MeterEvent(meter=four_four) == MeterEvent(meter=four_four)
    assert MeterEvent(meter=four_four) != MeterEvent(meter=six_eight)
    assert MeterEvent() == MeterEvent() and MeterEvent() != MeterEvent(meter=four_four)
    assert MeterEvent(meter=four_four).id != MeterEvent(meter=four_four).id
    assert TempoEvent(tempo=Tempo(120, quarter)) == TempoEvent(tempo=Tempo(120, quarter))
    assert TempoEvent(tempo=Tempo(120, quarter)) != TempoEvent(tempo=Tempo(60, quarter))
    assert TempoEvent() == TempoEvent()
    assert MeterEvent() != TempoEvent()


def test_equality_is_the_values_equality():
    """Measurables compare by length and ratios by multiplier, and the
    events inherit that: 4/4 equals 2/2, and 120 quarters equal 60 halves."""
    assert MeterEvent(meter=four_four) == MeterEvent(meter=two_two)
    assert MeterEvent(meter=four_four) == MeterEvent(meter=TemporalUnit(4, quarter))
    assert TempoEvent(tempo=Tempo(120, quarter)) == TempoEvent(tempo=Tempo(60, half))


def test_repr_round_trips(time_signature_symbols):
    events = [
        MeterEvent(),
        TempoEvent(),
        ContextEvent(),
        ModalContextEvent(),
        MeterEvent(meter=TemporalUnit(3, quarter)),
        MeterEvent(meter=CompoundTemporalUnit([TemporalUnit(2, eighth), TemporalUnit(3, eighth)])),
        MeterEvent(meter=dotted_quarter),
        TempoEvent(tempo=Tempo(120, quarter)),
        TempoEvent(tempo=Tempo(60, dotted_quarter, ClockDuration.from_seconds(30))),
        TempoEvent(tempo=TemporalRatio(dotted_quarter, quarter)),
    ]
    events += [MeterEvent(meter=ts) for ts in time_signature_symbols.values()]
    for event in events:
        assert eval(repr(event), NAMESPACE) == event, repr(event)


def test_relative_onset_passes_through_temporal_contexts():
    """A meter or a tempo takes no time: onsets across them are what they
    would be without them, in both directions."""
    plain, marked = notes(C, D, E), notes(C, D, E)
    without = OmkGraph(GraphMeta())
    without.add_line(plain)
    with_contexts = OmkGraph(GraphMeta())
    with_contexts.add_line(
        [
            MeterEvent(meter=four_four),
            TempoEvent(tempo=Tempo(120, quarter)),
            marked[0],
            MeterEvent(meter=six_eight),
            marked[1],
            TempoEvent(tempo=TemporalRatio(dotted_quarter, quarter)),
            marked[2],
        ]
    )
    for i, j in itertools.permutations(range(3), 2):
        assert with_contexts.relative_onset(marked[i], marked[j]) == without.relative_onset(
            plain[i], plain[j]
        )


def test_events_survive_deepcopy():
    """`materialize` copies events with deepcopy; a copy is a distinct,
    equal event holding an equal value."""
    for event in (
        MeterEvent(meter=four_four),
        TempoEvent(tempo=Tempo(120, quarter)),
        TempoEvent(tempo=TemporalRatio(dotted_quarter, quarter)),
    ):
        twin = copy.deepcopy(event)
        assert twin == event and twin is not event
