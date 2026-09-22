from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineComponent, BarLineShape
from openmusickit.systems.wsmn.scoring.symbols import (
    double_repeat,
    end_repeat,
    final_bar,
    invisible_bar,
    single_bar,
    start_repeat,
)
from openmusickit.values.scoring.division_shape import DivisionShape

THIN, THICK, DOTS = BarLineComponent.THIN, BarLineComponent.THICK, BarLineComponent.DOTS


def test_components_are_taken_positionally_in_time_order():
    assert BarLineShape(THIN).components == (THIN,)
    assert BarLineShape(DOTS, THIN, THICK).components == (DOTS, THIN, THICK)


def test_no_components_is_the_invisible_bar_line():
    assert BarLineShape().components == ()
    assert BarLineShape() == invisible_bar
    assert hash(BarLineShape()) == hash(invisible_bar)


def test_equality_and_hash_follow_the_components():
    assert BarLineShape(THIN, THICK) == BarLineShape(THIN, THICK) == final_bar
    assert BarLineShape(THIN, THICK) != BarLineShape(THICK, THIN)
    assert len({BarLineShape(THIN), BarLineShape(THIN), single_bar}) == 1


def test_a_shape_is_a_division_shape_and_is_frozen():
    import pytest

    assert isinstance(single_bar, DivisionShape)
    with pytest.raises(AttributeError):
        single_bar.components = ()


def test_repr_round_trips(bar_line_symbols):
    for name, shape in bar_line_symbols.items():
        assert eval(repr(shape)) == shape, name
    assert repr(end_repeat) == (
        "BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK)"
    )
    assert repr(BarLineShape()) == "BarLineShape()"


def test_every_symbol_is_a_distinct_hashable_bar_line_shape(bar_line_symbols):
    assert all(type(shape) is BarLineShape for shape in bar_line_symbols.values())
    assert len(set(bar_line_symbols.values())) == len(bar_line_symbols)


def test_repeats_mirror_each_other():
    assert start_repeat.components == tuple(reversed(end_repeat.components))
    assert double_repeat.components == end_repeat.components + start_repeat.components[1:]
    assert double_repeat.components[0] is DOTS and double_repeat.components[-1] is DOTS
