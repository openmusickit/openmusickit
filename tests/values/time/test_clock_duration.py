"""`ClockDuration`: real time in microseconds, as a ring under `+ - neg * /`,
with its `from_*`/accessor pairs, `timedelta` round trip, `str` format, and
its refusal to mix with metrical time.
"""

import itertools
import operator
from datetime import timedelta
from fractions import Fraction as F

import pytest

from openmusickit.errors import ScalingError, TemporalCompatibilityError
from openmusickit.systems.wsmn.temporal.symbols import quarter, triplet
from openmusickit.values.time.clock_time import CLOCK_TIME, ONE_MINUTE, ClockDuration, Tempo
from openmusickit.values.time.duration import ZeroDuration
from tests.domains import distinct

MICROSECONDS = [0, 1, 7, 1_000, 1_000_000, 60_000_000, F(1, 3), F(5, 2)]
CLOCKS = [ClockDuration(m) for m in MICROSECONDS]
SCALARS = [2, 3, F(1, 2), F(2, 3), F(3, 2)]


def test_addition_and_subtraction_form_a_ring():
    """Sums and differences are exact on the microsecond count, addition
    commutes and associates, and subtraction is addition of the negation."""
    zero = ClockDuration(0)
    for a, b in itertools.product(CLOCKS, repeat=2):
        assert a + b == ClockDuration(a.microseconds + b.microseconds), (a, b)
        assert a + b == b + a, (a, b)
        assert a - b == ClockDuration(a.microseconds - b.microseconds), (a, b)
        assert a - b == a + (-b), (a, b)
        assert (a + b) - b == a, (a, b)
    for a, b, c in itertools.product(CLOCKS, repeat=3):
        assert (a + b) + c == a + (b + c), (a, b, c)
    for a in CLOCKS:
        negated = -a
        assert a - a == zero, a
        assert a + negated == zero, a
        assert -negated == a, a
        assert a + zero == a, a
        assert negated.microseconds == -a.microseconds, a


def test_multiplication_and_scaling_agree():
    """`* k` and `scale(k)` are the same operation, doubling is adding to
    itself, and a Fraction scalar divides back exactly."""
    for a in CLOCKS:
        assert a * 2 == a + a, a
        for k in SCALARS:
            assert a * k == a.scale(k), (a, k)
            assert (a * k).microseconds == a.microseconds * k, (a, k)
            assert (a * k) / F(k) == a, (a, k)
            assert a / F(k) == a * (1 / F(k)), (a, k)
        assert a / 1 == a, a


def test_sum_of_a_list():
    assert sum(CLOCKS) == ClockDuration(sum(MICROSECONDS))
    assert sum([]) == 0


def test_from_and_accessor_pairs_round_trip():
    """`from_seconds(n).seconds` is n, and likewise for minutes and
    milliseconds, for whole and fractional n."""
    for n in [0, 1, 90, F(1, 3), F(7, 2)]:
        assert ClockDuration.from_seconds(n).seconds == n, n
        assert ClockDuration.from_minutes(n).minutes == n, n
        assert ClockDuration.from_milliseconds(n).milliseconds == n, n
        assert ClockDuration.from_minutes(n) == ClockDuration.from_seconds(60 * n), n
        assert ClockDuration.from_seconds(n) == ClockDuration.from_milliseconds(1000 * n), n
        assert ClockDuration.from_minutes(n).hours == n / 60, n
    for n in [0, 1, 123_456_789]:
        assert ClockDuration(n).whole_microseconds == n, n
    assert ClockDuration(F(1, 3)).whole_microseconds == 0
    assert ClockDuration(F(5, 3)).whole_microseconds == 2
    assert ONE_MINUTE == ClockDuration.from_seconds(60)


def test_timedelta_round_trip():
    for td in [
        timedelta(0),
        timedelta(microseconds=1),
        timedelta(days=1, seconds=3, microseconds=7),
    ]:
        assert ClockDuration.from_timedelta(td).timedelta == td, td
    for n in [0, 1, 123_456_789]:
        assert ClockDuration.from_timedelta(ClockDuration(n).timedelta) == ClockDuration(n), n
    assert ClockDuration.from_timedelta(timedelta(days=1)) == ClockDuration.from_minutes(24 * 60)


def test_str_is_hours_minutes_seconds_microseconds():
    assert str(ClockDuration(0)) == "00:00:00.000000"
    assert str(ClockDuration(1)) == "00:00:00.000001"
    assert str(ClockDuration.from_seconds(90)) == "00:01:30.000000"
    assert str(ClockDuration.from_minutes(61)) == "01:01:00.000000"
    assert str(ClockDuration.from_milliseconds(1500)) == "00:00:01.500000"
    assert str(ClockDuration(F(1, 3))) == "00:00:00.000000"  # rounded to whole microseconds


def test_equality_hashing_and_order_are_by_microseconds():
    """An int and a Fraction count of the same microseconds are the same
    duration; ordering is numeric."""
    assert ClockDuration(1000) == ClockDuration(F(1000))
    assert hash(ClockDuration(1000)) == hash(ClockDuration(F(1000)))
    assert ClockDuration(1000) == [ClockDuration(400), ClockDuration(600)]
    assert sorted(reversed(CLOCKS)) == sorted(CLOCKS, key=lambda c: c.microseconds)
    assert ClockDuration(1) < ClockDuration(2) <= ClockDuration(2)
    assert ClockDuration(3).temporal_system is CLOCK_TIME


def test_clock_time_does_not_mix_with_metrical_time():
    """A quarter note is not a quarter second, and neither can be ordered
    against or added to the other."""
    assert quarter != ClockDuration(250_000)
    assert ClockDuration(250_000) != quarter
    with pytest.raises(TypeError):
        operator.lt(ClockDuration(250_000), quarter)
    with pytest.raises(TypeError):
        operator.lt(quarter, ClockDuration(250_000))
    with pytest.raises(TypeError):
        ClockDuration(250_000) + quarter


def test_from_duration_needs_a_clock_time_ratio(duration_symbols):
    """A tempo converts any note value to seconds exactly; a tuplet ratio,
    whose contextual side is metrical, is refused."""
    tempo = Tempo(60, quarter)
    assert tempo.multiplier == 4_000_000
    assert ClockDuration.from_duration(quarter, tempo) == ClockDuration.from_seconds(1)
    for name, d in distinct(duration_symbols).items():
        assert ClockDuration.from_duration(d, tempo).seconds == d.rational_length * 4, name
    with pytest.raises(TemporalCompatibilityError):
        ClockDuration.from_duration(quarter, triplet(quarter))


# --- Defects pinned as strict xfails; each is an entry in _plans/revisit.md ---


@pytest.mark.xfail(
    strict=True,
    reason="revisit: MetricalDuration + ClockDuration builds a cross-system TiedDuration "
    "instead of raising",
)
def test_metrical_time_plus_clock_time_is_refused():
    with pytest.raises((TypeError, TemporalCompatibilityError)):
        quarter + ClockDuration(250_000)


@pytest.mark.xfail(
    strict=True,
    reason="revisit: ClockDuration + ZeroDuration raises TypeError "
    "(ZeroDuration has no __radd__, unlike GraceDuration)",
)
def test_zero_is_the_additive_identity_on_either_side():
    for a in CLOCKS:
        assert ZeroDuration() + a == a, a
        assert a + ZeroDuration() == a, a


@pytest.mark.xfail(
    strict=True,
    reason="revisit: ClockDuration.__truediv__ divides through float, so an int divisor "
    "loses the exactness the class promises",
)
def test_division_by_an_int_is_exact():
    assert ClockDuration(7) / 3 == ClockDuration(F(7, 3))
    for a in CLOCKS:
        for k in [3, 7]:
            assert (a / k) * k == a, (a, k)


@pytest.mark.xfail(
    strict=True,
    reason="revisit: ClockDuration.scale accepts zero and negative scalars against the "
    "Measurable.scale contract",
)
def test_scaling_by_a_non_positive_scalar_raises_scaling_error():
    for k in [0, -1, F(-1, 2)]:
        with pytest.raises(ScalingError):
            ClockDuration(7).scale(k)
