import pytest

from test_fixtures import tonal_tuples, tonal_oct_tuples
from openmusickit.tones import tonal_arithmetic as ta

def test_test(tonal_tuples):
    assert len(tonal_tuples) == 35

def test_tonal_sum_diff(tonal_tuples, tonal_oct_tuples):
    """Addition and subtraction are opposite operations,
    therefore (x + y) - y should equal x.
    """

    for x in tonal_tuples:
        for y in tonal_tuples:
            assert x == ta.tonal_diff(ta.tonal_sum(x, y), y)
            assert y == ta.tonal_sum(ta.tonal_diff(y, x), x)

    for x in tonal_oct_tuples:
        for y in tonal_oct_tuples:
            assert x == ta.tonal_diff(ta.tonal_sum(x, y), y)
            assert y == ta.tonal_sum(ta.tonal_diff(y, x), x)

def test_tonal_invert(tonal_tuples, tonal_oct_tuples):
    """An inversion is self-reversing,
    therefore tonal_invert(tonal_invert(x)) should equal x.
    """

    for x in tonal_tuples:
        assert ta.tonal_invert(ta.tonal_invert(x)) == x

        for y in tonal_tuples:
            assert ta.tonal_invert(ta.tonal_invert(x, y), y) == x

    for x in tonal_oct_tuples:
        assert ta.tonal_invert(ta.tonal_invert(x)) == x

        for y in tonal_oct_tuples:
            assert ta.tonal_invert(ta.tonal_invert(x, y), y) == x


def test_tonal_abs_diff(tonal_tuples, tonal_oct_tuples):
    """Tonal abs diff should always be less than 7 half-steps."""
    for x in tonal_tuples:
        for y in tonal_tuples:
            assert ta.tonal_int(ta.tonal_abs_diff(x, y)) < 7

    for x in tonal_tuples:
        for y in tonal_tuples:
            z = ta.tonal_sum(x, y)
            a = ta.tonal_abs_diff(x, z)
            assert a == y or a == ta.tonal_invert(y)
            assert ta.tonal_int(a) < 7

    for x in tonal_oct_tuples:
        for y in tonal_oct_tuples:
            z = ta.tonal_sum(x, y)
            a = ta.tonal_abs_diff(x, z)
            assert a == y or a == ta.tonal_invert(y)

def test_nearest_instance(tonal_tuples, tonal_oct_tuples):
    """The nearest instance should always be
    less than 7 half-steps away."""

    for x in tonal_tuples:
        for y in tonal_tuples:
            z = ta.tonal_nearest_instance(x, y)

            assert ta.abs_int_diff(x, z) < 7

    for x in tonal_oct_tuples:
        for y in tonal_oct_tuples:
            z = ta.tonal_nearest_instance(x, y)

            assert ta.abs_int_diff(x, z) < 7

def test_abs_int_diff(tonal_tuples):
    """Tonal abs int diff should always be less than 7 half-steps."""
    for x in tonal_tuples:
        for y in tonal_tuples:
            z = ta.abs_int_diff(x,y)
            assert z < 7


#### Testing internal functions ####

from openmusickit.tones.tonal_arithmetic import _tonal_modulo, _negative_tuple

def test_tonal_modulo(tonal_tuples):
    for x in tonal_tuples:
        for y in tonal_tuples:
            a = _tonal_modulo((x[0]+y[0], x[1]+y[1]))
            b = ta.tonal_sum(x, y)
            assert a == b

def test_negative_tuple(tonal_tuples, tonal_oct_tuples):
    """A tuple and its negative tuple should sum to to (0, 0) or (0, 0, 0)"""

    for x in tonal_tuples:
        neg_x = _negative_tuple(x)
        assert ta.tonal_sum(x, neg_x) == (0,0)

    for x in tonal_oct_tuples:
        neg_x = _negative_tuple(x)
        assert ta.tonal_sum(x, neg_x) == (0,0,0)