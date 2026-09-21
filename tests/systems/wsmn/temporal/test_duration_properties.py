"""Properties of the infinite duration domains: any positive rational length,
any positive rational scalar, any run of note values.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 examples per
property; `uv run pytest -m slow` adds the large-denominator run.
"""

from fractions import Fraction

import pytest
from hypothesis import example, given, settings
from hypothesis import strategies as st

from openmusickit.errors import ScalingError
from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.symbols import dotted_eighth, half
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.values.time.duration import TemporalUnit, ZeroDuration
from tests.domains import distinct, symbols_of
from tests.strategies import metrical_durations, positive_fractions

TIME_SIGNATURES = list(distinct(symbols_of(temporal_symbols, TimeSignature)).values())
ODD_SCALARS = st.sampled_from(
    [Fraction(3, 2), Fraction(2, 3), Fraction(3), Fraction(5), Fraction(1, 3), Fraction(5, 4)]
)
POWERS_OF_TWO = st.sampled_from([Fraction(1, 8), Fraction(1, 2), Fraction(2), Fraction(8)])


@given(positive_fractions(max_denominator=64))
def test_from_length_is_exact(length):
    """Whatever notation from_length picks, its real length is the input."""
    resolved = MetricalDuration.from_length(length)
    assert resolved.rational_length == length
    assert isinstance(resolved, MetricalDuration | TiedDuration)


@pytest.mark.slow
@settings(max_examples=2000)
@given(positive_fractions(max_denominator=4096))
def test_from_length_is_exact_for_large_denominators(length):
    assert MetricalDuration.from_length(length).rational_length == length


@given(metrical_durations())
def test_a_symbol_round_trips_through_its_length(d):
    """Resolving a symbol's own length gives back the same spelling."""
    resolved = MetricalDuration.from_length(d.rational_length)
    assert resolved == d
    assert repr(resolved) == repr(d)


@given(positive_fractions(), positive_fractions())
def test_lengths_add_and_subtract(x, y):
    """Sums and differences of any two lengths are exact, addition commutes,
    subtraction undoes it, and a length cancels itself, whether the operands
    are single symbols or ties."""
    a, b = MetricalDuration.from_length(x), MetricalDuration.from_length(y)
    total = a + b
    assert total.rational_length == x + y
    assert total == b + a
    assert (total - b) == a
    assert (a - b).rational_length == x - y
    negated = -a
    assert a - a == ZeroDuration()
    assert a + negated == ZeroDuration()
    assert -negated == a
    assert negated.rational_length == -x


@given(metrical_durations(), ODD_SCALARS)
def test_scaling_a_single_symbol_by_any_positive_rational_is_exact(d, k):
    scaled = d.scale(k)
    assert scaled.rational_length == d.rational_length * k
    assert scaled.scale(1 / k) == d


@given(metrical_durations(), POWERS_OF_TWO)
def test_scaling_by_a_power_of_two_keeps_the_spelling(d, k):
    scaled = d.scale(k)
    assert isinstance(scaled, MetricalDuration)
    assert scaled.dots == d.dots and scaled.ratio == d.ratio
    assert repr(scaled.scale(1 / k)) == repr(d)


@given(positive_fractions(), st.sampled_from([0, -1, Fraction(-1, 2)]))
def test_scaling_by_a_non_positive_scalar_raises(length, k):
    with pytest.raises(ScalingError):
        MetricalDuration.from_length(length).scale(k)


@given(st.lists(metrical_durations(), min_size=2, max_size=6))
def test_a_tie_measures_as_the_sum_of_its_members(members):
    tied = TiedDuration(members)
    total = sum(m.rational_length for m in members)
    assert tied.rational_length == total
    assert MetricalDuration.from_length(total) == tied
    assert sum(members) == tied
    assert (-tied).rational_length == -total
    assert list(-tied) == [-m for m in members]
    assert tied - tied == ZeroDuration()


@given(positive_fractions(), st.integers(1, 12))
def test_a_bar_divided_into_equal_parts_fills_the_bar(length, n):
    part = MetricalDuration.from_length(length / n)
    assert TemporalUnit(n, part).rational_length == length
    assert sum([part] * n) == MetricalDuration.from_length(length)


@given(st.sampled_from(TIME_SIGNATURES), st.lists(metrical_durations(), max_size=8))
def test_remainder_and_first_out_of_bounds_over_any_run(signature, run):
    """The remainder is the bar less the run; the first item to overflow is
    the first whose cumulative length passes the bar, or none."""
    lengths = [d.rational_length for d in run]
    assert signature.remainder(run) == signature.rational_length - sum(lengths)
    cumulative, expected = Fraction(0), None
    for i, length in enumerate(lengths):
        cumulative += length
        if cumulative > signature.rational_length:
            expected = i
            break
    assert signature.first_out_of_bounds(run) == expected


@given(st.sampled_from(TIME_SIGNATURES), ODD_SCALARS)
def test_scaling_a_time_signature_by_any_positive_rational_is_exact(signature, k):
    scaled = signature.scale(k)
    assert scaled.rational_length == signature.rational_length * k
    assert scaled.scale(1 / k) == signature


# --- ties under scaling and addition ----------------------------------------------


def test_scaling_a_tie_by_any_positive_rational_is_exact():
    """Scaling a tie scales its length, even when a member itself scales to a tie."""
    tied = TiedDuration([half, dotted_eighth])  # 11/16, a genuine tie
    assert tied.scale(3).rational_length == tied.rational_length * 3


@example(Fraction(1, 4), Fraction(5, 8))
@given(positive_fractions(), positive_fractions())
def test_any_two_lengths_add_in_either_order(x, y):
    a, b = MetricalDuration.from_length(x), MetricalDuration.from_length(y)
    assert (a + b).rational_length == x + y
    assert (b + a).rational_length == x + y
