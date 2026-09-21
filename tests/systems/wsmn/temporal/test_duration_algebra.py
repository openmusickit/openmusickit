"""Laws of WSMN duration arithmetic over the whole symbol table: every note
value in `temporal.symbols` (39 distinct `MetricalDuration`s, from the
maxima to the 128th, dotted, double dotted, and inside triplets), the five
grace durations, the tuplet ratios, and the 29 time signatures.

The fixtures are deduplicated with `tests.domains.distinct` so a law is
checked once per value, not once per spelling (`quarter is crotchet`).
"""

import itertools
from fractions import Fraction as F

import pytest

from openmusickit.errors import ScalingError
from openmusickit.systems.wsmn.temporal import symbols as sym
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.values.time.duration import ZeroDuration
from tests.domains import distinct

SCALARS = [F(2), F(3), F(1, 2), F(2, 3), F(3, 2), F(5), F(1, 3), F(7, 4)]
BAD_SCALARS = [0, -1, F(-1, 2)]


# --- negation, zero, subtraction ---------------------------------------------------


def test_a_duration_and_its_negation_cancel(duration_symbols):
    """d + (-d) is the zero duration, and negation is an involution,
    for every note value in the symbol table."""
    for name, d in distinct(duration_symbols).items():
        assert d - d == ZeroDuration(), name
        assert isinstance(d - d, ZeroDuration), name
        negated = -d
        assert d + negated == ZeroDuration(), name
        assert -negated == d, name
        assert repr(-negated) == repr(d), name
        assert negated.rational_length == -d.rational_length, name


def test_zero_is_the_additive_identity(duration_symbols):
    """Adding nothing changes nothing, on either side; the zero duration
    subtracted from a value is the value's negation."""
    zero = ZeroDuration()
    for name, d in distinct(duration_symbols).items():
        assert d + zero == d, name
        assert zero + d == d, name
        assert (d + zero) is d, name
        assert zero - d == -d, name


# --- addition ------------------------------------------------------------------


def test_addition_is_commutative_and_subtraction_undoes_it(duration_symbols):
    """a + b == b + a, and (a + b) - b == a, for every pair of note values,
    whether the sum is one symbol or a tie."""
    for (na, a), (nb, b) in itertools.product(distinct(duration_symbols).items(), repeat=2):
        assert a + b == b + a, (na, nb)
        assert (a + b) - b == a, (na, nb)
        assert (a + b).rational_length == a.rational_length + b.rational_length, (na, nb)


def test_a_sum_is_notation_for_its_length(duration_symbols):
    """The sum of two note values is what `from_length` gives for the summed
    length, and `sum` over a list of symbols folds the same way."""
    for (na, a), (nb, b) in itertools.product(distinct(duration_symbols).items(), repeat=2):
        total = a + b
        assert MetricalDuration.from_length(total.rational_length) == total, (na, nb)
        assert sum([a, b]) == total, (na, nb)


def test_sum_of_the_whole_table(duration_symbols):
    """`sum` over every symbol has the summed length, whatever tie it takes."""
    values = list(distinct(duration_symbols).values())
    total = sum(values)
    assert total.rational_length == sum(d.rational_length for d in values)
    assert MetricalDuration.from_length(total.rational_length) == total


@pytest.mark.xfail(
    strict=True,
    reason="revisit: MetricalDuration + TiedDuration raises ValueError "
    "(it builds a one-member TiedDuration), so addition is not associative",
)
def test_addition_is_associative(duration_symbols):
    for (na, a), (nb, b), (nc, c) in itertools.product(
        distinct(duration_symbols).items(), repeat=3
    ):
        assert (a + b) + c == a + (b + c), (na, nb, nc)


# --- order, equality, hashing --------------------------------------------------------------


def test_order_and_equality_follow_rational_length(duration_symbols):
    """`<` and `==` are by real length, so a dotted quarter equals a quarter
    plus an eighth, and equal values hash alike."""
    symbols = distinct(duration_symbols)
    for (na, a), (nb, b) in itertools.product(symbols.items(), repeat=2):
        assert (a < b) == (a.rational_length < b.rational_length), (na, nb)
        assert (a == b) == (a.rational_length == b.rational_length), (na, nb)
        if a == b:
            assert hash(a) == hash(b), (na, nb)
    assert sym.dotted_quarter == sym.quarter + sym.eighth
    assert hash(sym.dotted_quarter) == hash(sym.quarter + sym.eighth)
    assert sorted(symbols.values()) == sorted(symbols.values(), key=lambda d: d.rational_length)


# --- from_length and scaling --------------------------------------------------------------


def test_from_length_reproduces_every_symbol_exactly(duration_symbols):
    """Resolving a symbol's length gives back that symbol with the same
    spelling: the same nominal value, dots, and tuplet ratio."""
    for name, d in distinct(duration_symbols).items():
        resolved = MetricalDuration.from_length(d.rational_length)
        assert resolved == d, name
        assert repr(resolved) == repr(d), name


def test_scaling_multiplies_the_length_and_undoes_itself(duration_symbols):
    """Scaling by k gives k times the length, whatever notation that needs,
    and scaling back by 1/k restores the value."""
    for name, d in distinct(duration_symbols).items():
        for k in SCALARS:
            scaled = d.scale(k)
            assert scaled.rational_length == d.rational_length * k, (name, k)
            assert scaled.scale(1 / k) == d, (name, k)
        for k in [2, 4, F(1, 2), F(1, 4)]:
            assert isinstance(d.scale(k), MetricalDuration), (name, k)
            assert d.scale(k).dots == d.dots, (name, k)


def test_scaling_by_a_non_positive_scalar_raises_scaling_error(duration_symbols):
    for d in distinct(duration_symbols).values():
        for k in BAD_SCALARS:
            with pytest.raises(ScalingError):
                d.scale(k)


# --- grace durations ----------------------------------------------------------------


def test_grace_durations_take_no_time(duration_symbols, grace_duration_symbols):
    """A grace is absorbed by any duration on either side, is its own
    negation, equals the zero duration, and a run of graces sums to zero."""
    graces = distinct(grace_duration_symbols)
    for gname, g in graces.items():
        assert g == ZeroDuration(), gname
        assert -g == g, gname
        assert g.rational_length == 0, gname
        for k in SCALARS:
            assert g.scale(k).nominal == g.nominal.scale(k), (gname, k)
            assert g.scale(k).on_beat == g.on_beat, (gname, k)
        for name, d in distinct(duration_symbols).items():
            assert d + g == d, (name, gname)
            assert g + d == d, (name, gname)
            assert (d + g) is d, (name, gname)
    assert sum(graces.values()) == ZeroDuration()


# --- tuplet ratios --------------------------------------------------------------------


def test_ratio_equality_is_by_multiplier(tuplet_ratio_symbols):
    """A sextuplet (6:4) is the same ratio as a triplet (3:2), on any base,
    and hashes alike; 7:6 is not 7:4."""
    assert sym.sextuplet(sym.quarter) == sym.triplet(sym.quarter)
    assert hash(sym.sextuplet(sym.quarter)) == hash(sym.triplet(sym.quarter))
    assert sym.triplet(sym.quarter) == sym.triplet(sym.eighth)
    assert sym.tuplet(7, 6, sym.quarter) != sym.septuplet(sym.quarter)
    for name, ratio in tuplet_ratio_symbols.items():
        expected = ratio.contextual.rational_length / ratio.nominal.rational_length
        assert ratio.multiplier == expected, name
        inside = MetricalDuration(1, 4, ratio=ratio)
        assert inside.rational_length == F(1, 4) * ratio.multiplier, name
        assert inside.nominal_length == F(1, 4), name


def test_triplet_symbols_are_a_third_of_the_next_value_up(duration_symbols):
    """A quarter in a triplet is a third of a half; every `*_in_triplet`
    symbol is a third of the value twice its nominal size."""
    for name, d in distinct(duration_symbols).items():
        if d.ratio is None:
            continue
        plain = MetricalDuration(d.numerator, d.denominator, d.dots)
        assert d.rational_length == plain.rational_length * F(2, 3), name
        assert d.rational_length * 3 == plain.scale(2).rational_length, name


# --- time signatures ------------------------------------------------------------------


def test_time_signatures_are_equal_by_total_length(time_signature_symbols):
    """4/4 is 2/2 is 8/8; 6/8 is two dotted quarters. Equality and hashing
    follow the bar length alone."""
    assert sym.four_four == sym.two_two
    assert sym.six_eight == sym.two_dotted_quarters
    assert sym.seven_eight == sym.seven_eight_2_2_3 == sym.seven_eight_3_2_2
    signatures = distinct(time_signature_symbols)
    for (na, a), (nb, b) in itertools.product(signatures.items(), repeat=2):
        assert (a == b) == (a.rational_length == b.rational_length), (na, nb)
        if a == b:
            assert hash(a) == hash(b), (na, nb)


def test_scaling_a_time_signature_scales_the_bar(time_signature_symbols):
    """Scaling by k gives a time signature k times as long; a non-positive
    scalar is a ScalingError."""
    for name, signature in distinct(time_signature_symbols).items():
        for k in [F(2), F(1, 2), F(3), F(1, 3), F(3, 2), F(2, 3)]:
            scaled = signature.scale(k)
            assert type(scaled) is TimeSignature, (name, k)
            assert scaled.rational_length == signature.rational_length * k, (name, k)
        for k in BAD_SCALARS:
            with pytest.raises(ScalingError):
                signature.scale(k)


def test_remainder_and_first_out_of_bounds_against_every_note_value(
    time_signature_symbols, duration_symbols
):
    """The remainder after one note is the bar length less the note; as many
    copies of a note as fit stay in bounds and one more overflows at exactly
    that index."""
    for sname, signature in distinct(time_signature_symbols).items():
        assert signature.remainder([]) == signature.rational_length, sname
        assert signature.first_out_of_bounds([]) is None, sname
        for dname, d in distinct(duration_symbols).items():
            assert signature.remainder([d]) == signature.rational_length - d.rational_length, (
                sname,
                dname,
            )
            fits = signature.rational_length // d.rational_length
            assert signature.first_out_of_bounds([d] * fits) is None, (sname, dname)
            assert signature.first_out_of_bounds([d] * (fits + 1)) == fits, (sname, dname)
            assert signature.remainder([d] * fits) >= 0, (sname, dname)
            assert signature.remainder([d] * (fits + 1)) < 0, (sname, dname)


def test_a_tie_of_symbols_measures_as_their_sum(time_signature_symbols):
    """A TimeSignature compares against any iterable of Measurables, measured
    as the sum: a bar of 4/4 is a whole, or a half tied to two quarters."""
    assert sym.four_four == [sym.whole]
    assert sym.four_four == [sym.half, sym.quarter, sym.quarter]
    assert sym.four_four == TiedDuration([sym.half, sym.quarter, sym.quarter])
    for name, signature in distinct(time_signature_symbols).items():
        assert signature == list(signature), name
        assert signature == MetricalDuration.from_length(signature.rational_length), name
