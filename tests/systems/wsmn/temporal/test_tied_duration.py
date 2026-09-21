"""`TiedDuration`: one sounding length written as two or more tied symbols.

Construction, the sequence protocol, `from_length`'s greedy split, the merge
rules of `+`, negation, scaling, and comparison, each on small hand-picked
values; the lengths themselves are checked by law in `test_duration_algebra`.
"""

from fractions import Fraction as F

import pytest

from openmusickit.errors import ScalingError
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration, TiedDuration
from openmusickit.systems.wsmn.temporal.symbols import (
    dotted_eighth,
    dotted_half,
    eighth,
    grace_eighth,
    half,
    quarter,
    quarter_in_triplet,
    sixteenth,
    whole,
)
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.values.time.duration import ZeroDuration

half_tied_to_eighth = TiedDuration([half, eighth])  # 5/8


def test_a_tie_needs_at_least_two_members():
    with pytest.raises(ValueError):
        TiedDuration([quarter])
    with pytest.raises(ValueError):
        TiedDuration([])
    assert len(TiedDuration([quarter, sixteenth])) == 2


def test_a_tie_is_a_sequence_of_its_members():
    tied = half_tied_to_eighth
    assert list(tied) == [half, eighth]
    assert tied[0] is half and tied[-1] is eighth
    assert len(tied) == 2
    assert tied.members == (half, eighth)
    assert tied.temporal_system is WSMN_TEMPORAL
    assert repr(tied) == "TiedDuration([MetricalDuration(1, 2), MetricalDuration(1, 8)])"


def test_length_is_the_sum_of_the_members():
    assert half_tied_to_eighth.rational_length == F(5, 8)
    assert TiedDuration([quarter, sixteenth]).rational_length == F(5, 16)
    assert TiedDuration([whole, half, eighth]).rational_length == F(13, 8)


def test_from_length_splits_greedily_largest_first():
    """A length with no single symbol comes back as a tie, dotted values
    included, and resolving a tie's own length reproduces it."""
    assert MetricalDuration.from_length(F(5, 8)) == half_tied_to_eighth
    assert repr(MetricalDuration.from_length(F(5, 8))) == repr(half_tied_to_eighth)
    assert list(MetricalDuration.from_length(F(13, 16))) == [dotted_half, sixteenth]
    for tied in [
        half_tied_to_eighth,
        TiedDuration([quarter, sixteenth]),
        TiedDuration([whole, half, eighth]),
        TiedDuration([quarter, quarter, quarter, quarter, quarter]),
    ]:
        assert MetricalDuration.from_length(tied.rational_length) == tied
        assert sum(tied) == tied
        assert sum(tied).rational_length == tied.rational_length


def test_adding_to_the_tail_merges_as_far_back_as_it_can():
    """half~eighth + eighth is a dotted half (one symbol); + sixteenth is
    half~dotted eighth; + quarter merges twice into a double-dotted half."""
    assert half_tied_to_eighth + eighth == dotted_half
    assert isinstance(half_tied_to_eighth + eighth, MetricalDuration)
    assert list(half_tied_to_eighth + sixteenth) == [half, dotted_eighth]
    assert half_tied_to_eighth + quarter == MetricalDuration(1, 2, dots=2)
    assert isinstance(half_tied_to_eighth + quarter, MetricalDuration)


def test_adding_a_tie_folds_its_members_one_by_one():
    tied = half_tied_to_eighth + half_tied_to_eighth
    assert list(tied) == [half, eighth, half, eighth]
    assert tied.rational_length == F(5, 4)
    assert half_tied_to_eighth + TiedDuration([eighth, quarter]) == whole


def test_members_in_different_tuplets_do_not_merge():
    mixed = TiedDuration([quarter_in_triplet, quarter])
    assert list(mixed + quarter_in_triplet) == [quarter_in_triplet, quarter, quarter_in_triplet]
    assert list(mixed + quarter) == [quarter_in_triplet, half]


def test_zero_and_grace_durations_leave_a_tie_alone():
    assert (half_tied_to_eighth + ZeroDuration()) is half_tied_to_eighth
    assert ZeroDuration() + half_tied_to_eighth == half_tied_to_eighth
    assert (half_tied_to_eighth + grace_eighth) is half_tied_to_eighth
    assert grace_eighth + half_tied_to_eighth == half_tied_to_eighth


def test_negation_negates_every_member():
    negated = -half_tied_to_eighth
    assert list(negated) == [-half, -eighth]
    assert negated.rational_length == F(-5, 8)
    assert -negated == half_tied_to_eighth
    assert half_tied_to_eighth + negated == ZeroDuration()
    assert half_tied_to_eighth - half_tied_to_eighth == ZeroDuration()


def test_subtraction_resolves_by_length():
    """Taking away part of a tie leaves the canonical spelling of the rest,
    and taking away more than the tie leaves a negative duration."""
    assert half_tied_to_eighth - eighth == half
    assert half_tied_to_eighth - quarter == MetricalDuration(1, 4, dots=1)
    assert half_tied_to_eighth - half == eighth
    assert half_tied_to_eighth - whole == MetricalDuration(-1, 4, dots=1)
    assert eighth - half_tied_to_eighth == -half


def test_scaling_scales_every_member_and_may_collapse():
    tied = half_tied_to_eighth
    assert list(tied.scale(2)) == [whole, quarter]
    assert list(tied.scale(F(1, 2))) == [quarter, sixteenth]
    assert tied.scale(3) == MetricalDuration(1, 1, dots=3)
    assert isinstance(tied.scale(3), MetricalDuration)
    for k in [F(2), F(3), F(1, 2), F(2, 3), F(3, 2), F(5)]:
        assert tied.scale(k).rational_length == tied.rational_length * k, k
        assert tied.scale(k).scale(1 / k) == tied, k
    with pytest.raises(ScalingError):
        tied.scale(0)


def test_comparison_is_by_length():
    assert half_tied_to_eighth == MetricalDuration.from_length(F(5, 8))
    assert half_tied_to_eighth == [half, eighth]
    assert half_tied_to_eighth == [quarter, quarter, eighth]
    assert hash(half_tied_to_eighth) == hash(F(5, 8))
    assert half < half_tied_to_eighth < whole
    assert half_tied_to_eighth != dotted_half


def test_a_symbol_plus_a_tie_is_the_tie_plus_the_symbol():
    """A tie adds on either side of a symbol, to the same length."""
    assert quarter + half_tied_to_eighth == half_tied_to_eighth + quarter
    assert eighth + half_tied_to_eighth == dotted_half
