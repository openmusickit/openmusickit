import pytest

from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.context_event import ContextEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.marking import Marking
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineComponent, BarLineShape
from openmusickit.systems.wsmn.scoring.symbols import end_repeat, segno, single_bar
from openmusickit.systems.wsmn.temporal.symbols import quarter
from openmusickit.values.time.duration import ZeroDuration


def test_a_division_is_a_sequential_event_of_zero_duration():
    division = DivisionEvent()
    assert isinstance(division, SequentialEvent)
    assert not isinstance(division, ContextEvent)
    assert isinstance(division.duration, ZeroDuration)


def test_duration_cannot_be_given_at_construction():
    with pytest.raises(TypeError):
        DivisionEvent(duration=quarter)
    with pytest.raises(TypeError):
        DivisionEvent(duration=None)


def test_shape_defaults_to_unspecified():
    assert DivisionEvent().shape is None
    assert DivisionEvent(shape=end_repeat).shape is end_repeat


def test_equality_ignores_id_and_compares_the_shape():
    assert DivisionEvent(shape=single_bar) == DivisionEvent(shape=single_bar)
    assert DivisionEvent(shape=single_bar) != DivisionEvent(shape=end_repeat)
    assert DivisionEvent() == DivisionEvent()


def test_repr_round_trips():
    namespace = {
        "DivisionEvent": DivisionEvent,
        "BarLineShape": BarLineShape,
        "BarLineComponent": BarLineComponent,
    }
    for division in (DivisionEvent(), DivisionEvent(shape=end_repeat)):
        assert eval(repr(division), namespace) == division


def test_a_mark_attaches_to_a_division():
    graph = OmkGraph(GraphMeta())
    division, sign = DivisionEvent(shape=end_repeat), Marking(mark=segno)
    graph.add_node(division)
    graph.add_node(sign)
    graph.add_edge(sign, division, EdgeType.MARKS)
    assert graph.get_edge(sign, division, EdgeType.MARKS).type is EdgeType.MARKS
