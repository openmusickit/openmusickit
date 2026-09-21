"""Laws of tonal tuple arithmetic, checked over every pitch class and every
octave-qualified pitch in the test domain (`tests.domains`).

A law about the *size* of a derived interval (`tonal_int`, `abs_int_diff`)
is asserted where that interval is itself in the domain, at most doubly
altered. The pairs whose difference falls outside it (a doubly diminished
second, a quadruply flattened third) are covered by the strict-xfail tests
at the end, one per defect, each pointing at `_plans/revisit.md`.
"""

import pytest

from openmusickit.systems.wsmn.tonal import tonal_arithmetic as ta
from openmusickit.systems.wsmn.tonal.tonal_arithmetic import _negative_tuple, _tonal_modulo
from tests.domains import TONAL_OCT_TUPLES, TONAL_TUPLES, in_domain

ORIGIN = (0, 0, 0)


def _pairs(domain):
    """Every ordered pair (x, y) from the domain, x == y included."""
    return [(x, y) for x in domain for y in domain]


def _difference_in_domain(x, y) -> bool:
    """Both x - y and y - x are spellable with at most a double alteration."""
    return in_domain(ta.tonal_diff(x, y)) and in_domain(ta.tonal_diff(y, x))


def _is_tie(x, y) -> bool:
    """x and y are enharmonically the same pitch (or interval size)."""
    return ta.tonal_int(x) == ta.tonal_int(y)


def _smaller_side(halfsteps: int) -> int:
    """A signed distance in half-steps reduced to the nearer way round the octave."""
    k = halfsteps % 12
    return min(k, 12 - k)


def test_fixture_covers_all_35_pitch_classes(tonal_tuples):
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


def test_tonal_int_of_inversion():
    """Inverting an octave-qualified interval negates its size in half-steps;
    an abstract interval and its inversion add up to an octave (or to zero,
    for a unison), so their sizes cancel modulo 12."""
    for x in TONAL_OCT_TUPLES:
        inv = ta.tonal_invert(x)
        assert ta.tonal_int(inv) == -ta.tonal_int(x), (x, inv)
        assert ta.tonal_abs(inv) == ta.tonal_abs(x), (x, inv)

    for x in TONAL_TUPLES:
        inv = ta.tonal_invert(x)
        assert (ta.tonal_int(x) + ta.tonal_int(inv)) % 12 == 0, (x, inv)


def test_tonal_abs_diff(tonal_tuples, tonal_oct_tuples):
    """The absolute difference between two pitches is symmetric, is one of
    the two directed differences, and is never larger than a tritone; between
    x and x + y it is y or the inversion of y."""
    for x, y in _pairs(tonal_tuples):
        a = ta.tonal_abs_diff(x, y)
        assert a == ta.tonal_abs_diff(y, x), (x, y, a)
        assert a in (ta.tonal_diff(x, y), ta.tonal_diff(y, x)), (x, y, a)
        assert ta.tonal_abs(a) < 7, (x, y, a)
        if _difference_in_domain(x, y):
            assert ta.tonal_int(a) == ta.abs_int_diff(x, y), (x, y, a)

        z = ta.tonal_sum(x, y)
        a = ta.tonal_abs_diff(x, z)
        assert a == y or a == ta.tonal_invert(y), (x, y, z, a)

    for x, y in _pairs(tonal_oct_tuples):
        a = ta.tonal_abs_diff(x, y)
        assert a == ta.tonal_abs_diff(y, x), (x, y, a)
        assert a in (ta.tonal_diff(x, y), ta.tonal_diff(y, x)), (x, y, a)
        if _difference_in_domain(x, y):
            assert ta.tonal_int(a) == ta.abs_int_diff(x, y), (x, y, a)

        z = ta.tonal_sum(x, y)
        a = ta.tonal_abs_diff(x, z)
        assert a == y or a == ta.tonal_invert(y), (x, y, z, a)


def test_nearest_instance(tonal_tuples, tonal_oct_tuples):
    """The nearest instance of y to x has the pitch class of y and lies
    within a tritone of x; an abstract x gets y back with no octave."""
    for x, y in _pairs(tonal_tuples):
        z = ta.tonal_nearest_instance(x, y)
        assert z == y, (x, y, z)

    for x in tonal_tuples:
        for y in tonal_oct_tuples:
            z = ta.tonal_nearest_instance(x, y)
            assert z == y[:2], (x, y, z)

    for x, y in _pairs(tonal_oct_tuples):
        z = ta.tonal_nearest_instance(x, y)
        assert z[:2] == y[:2], (x, y, z)
        assert len(z) == 3, (x, y, z)
        assert ta.abs_int_diff(x, z) < 7, (x, y, z)

    for x in tonal_oct_tuples:
        for y in tonal_tuples:
            z = ta.tonal_nearest_instance(x, y)
            assert z[:2] == y, (x, y, z)
            assert len(z) == 3, (x, y, z)
            assert ta.abs_int_diff(x, z) < 7, (x, y, z)


def test_abs_int_diff(tonal_tuples, tonal_oct_tuples):
    """Between two pitch classes, the smallest number of half-steps is the
    signed distance reduced to the nearer way round the octave; between
    two octave-qualified pitches it is the plain absolute distance."""
    for x, y in _pairs(tonal_tuples):
        if _difference_in_domain(x, y):
            expected = _smaller_side(ta.tonal_int(x) - ta.tonal_int(y))
            assert ta.abs_int_diff(x, y) == expected, (x, y)

    for x, y in _pairs(tonal_oct_tuples):
        assert ta.abs_int_diff(x, y) == abs(ta.tonal_int(x) - ta.tonal_int(y)), (x, y)


def test_higher_of_and_lower_of(tonal_tuples, tonal_oct_tuples):
    """Of two pitches that are not enharmonically the same, one is the higher
    and the other the lower, whichever order they are given in."""
    for domain in (tonal_tuples, tonal_oct_tuples):
        for x, y in _pairs(domain):
            if _is_tie(x, y):
                continue
            higher = ta.tonal_higher_of(x, y)
            lower = ta.tonal_lower_of(x, y)
            assert {higher, lower} == {x, y}, (x, y, higher, lower)
            assert higher == ta.tonal_higher_of(y, x), (x, y)
            assert lower == ta.tonal_lower_of(y, x), (x, y)
            assert ta.tonal_int(higher) > ta.tonal_int(lower), (x, y)


def test_higher_of_enharmonic_tie_goes_to_the_higher_letter(tonal_tuples):
    """An augmented fourth and a diminished fifth are the same size; the
    diminished fifth is the higher (it is spelled on the higher letter)."""
    for x, y in _pairs(tonal_tuples):
        if x == y or not _is_tie(x, y):
            continue
        higher = ta.tonal_higher_of(x, y)
        lower = ta.tonal_lower_of(x, y)
        assert {higher, lower} == {x, y}, (x, y, higher, lower)
        assert higher[0] > lower[0], (x, y, higher, lower)


def test_larger_of_and_smaller_of(tonal_tuples, tonal_oct_tuples):
    """Of two intervals, the larger spans at least as many half-steps as the
    smaller, and together they are the two intervals given."""
    for domain in (tonal_tuples, tonal_oct_tuples):
        for x, y in _pairs(domain):
            larger = ta.tonal_larger_of(x, y)
            smaller = ta.tonal_smaller_of(x, y)
            assert larger in (x, y) and smaller in (x, y), (x, y, larger, smaller)
            if x != y:
                assert {larger, smaller} == {x, y}, (x, y, larger, smaller)
            assert ta.tonal_abs(larger) >= ta.tonal_abs(smaller), (x, y, larger, smaller)
            if ta.tonal_abs(x) != ta.tonal_abs(y):
                assert larger == ta.tonal_larger_of(y, x), (x, y)
                assert smaller == ta.tonal_smaller_of(y, x), (x, y)


def test_abs_interval(tonal_tuples, tonal_oct_tuples):
    """The absolute form of an interval is the interval or its inversion,
    taking it again changes nothing, and for an abstract interval it is at
    most a tritone."""
    for domain in (tonal_tuples, tonal_oct_tuples):
        for x in domain:
            a = ta.abs_interval(x)
            assert a in (x, ta.tonal_invert(x)), (x, a)
            assert ta.abs_interval(a) == a, (x, a)

    for x in tonal_tuples:
        assert ta.tonal_abs(ta.abs_interval(x)) <= 6, x

    for x in tonal_oct_tuples:
        if in_domain(ta.tonal_invert(x)):
            assert ta.tonal_int(ta.abs_interval(x)) == ta.tonal_abs(x), x


def test_tonal_int_is_additive_on_qualified_tuples(tonal_oct_tuples):
    """The size of a difference of two pitches is the difference of their
    sizes, as long as the difference is a spellable interval."""
    for x, y in _pairs(tonal_oct_tuples):
        if _difference_in_domain(x, y):
            d = ta.tonal_diff(x, y)
            assert ta.tonal_int(d) == ta.tonal_int(x) - ta.tonal_int(y), (x, y, d)


# --- Testing internal functions ---


def test_tonal_modulo(tonal_tuples):
    for x in tonal_tuples:
        for y in tonal_tuples:
            a = _tonal_modulo((x[0] + y[0], x[1] + y[1]))
            b = ta.tonal_sum(x, y)
            assert a == b


def test_negative_tuple(tonal_tuples, tonal_oct_tuples):
    """A tuple and its negative tuple should sum to to (0, 0) or (0, 0, 0)"""

    for x in tonal_tuples:
        neg_x = _negative_tuple(x)
        assert ta.tonal_sum(x, neg_x) == (0, 0)

    for x in tonal_oct_tuples:
        neg_x = _negative_tuple(x)
        assert ta.tonal_sum(x, neg_x) == (0, 0, 0)


# --- Defects pinned as strict xfails; each is an entry in _plans/revisit.md ---


def test_abs_int_diff_is_never_negative(tonal_tuples):
    """The count of half-steps is a magnitude, even where the nearest spelling
    of the difference is a negative interval (C to B double-sharp)."""
    for x, y in _pairs(tonal_tuples):
        assert ta.abs_int_diff(x, y) >= 0, (x, y, ta.abs_int_diff(x, y))


@pytest.mark.xfail(
    strict=True,
    reason="revisit: tonal_int assumes at most a triple alteration; the difference of "
    "two doubly altered pitches (D-sharp and F-double-flat) can exceed that and is misread",
)
def test_tonal_int_is_additive_beyond_the_domain(tonal_oct_tuples):
    for x, y in _pairs(tonal_oct_tuples):
        if not _difference_in_domain(x, y):
            d = ta.tonal_diff(x, y)
            assert ta.tonal_int(d) == ta.tonal_int(x) - ta.tonal_int(y), (x, y, d)


@pytest.mark.xfail(
    strict=True,
    reason="revisit: tonal_lower_of returns an un-normalized tuple, (6, 12) or (0, -1, 1), "
    "on an enharmonic tie",
)
def test_lower_of_returns_a_normalized_tuple_on_a_tie(tonal_tuples, tonal_oct_tuples):
    for domain in (tonal_tuples, tonal_oct_tuples):
        for x, y in _pairs(domain):
            if _is_tie(x, y):
                assert ta.tonal_lower_of(x, y) in (x, y), (x, y, ta.tonal_lower_of(x, y))


@pytest.mark.xfail(
    strict=True,
    reason="revisit: the higher_of/lower_of tie-break compares letters without the octave, "
    "so B-sharp 3 is called higher than C4",
)
def test_higher_of_enharmonic_tie_across_an_octave_goes_to_the_higher_letter(tonal_oct_tuples):
    def diatonic_position(t):
        return t[0] + 7 * t[2]

    for x, y in _pairs(tonal_oct_tuples):
        if x == y or not _is_tie(x, y):
            continue
        higher = ta.tonal_higher_of(x, y)
        lower = ta.tonal_lower_of(x, y)
        assert {higher, lower} == {x, y}, (x, y, higher, lower)
        assert diatonic_position(higher) > diatonic_position(lower), (x, y, higher, lower)
