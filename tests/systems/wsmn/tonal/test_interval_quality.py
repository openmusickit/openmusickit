"""`IntervalQuality`: the nineteen-entry table in `QUALITIES`, keyed by
relative number, and the arithmetic that walks it.
"""

import math

import pytest

from openmusickit.systems.wsmn.tonal.interval_quality import (
    QUALITIES,
    IntervalQuality,
    _get_quality,
)
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from tests.domains import ABSTRACT_VECTORS


def _is_perfect_type(quality: IntervalQuality) -> bool:
    """Perfect-type qualities sit on whole numbers; major/minor-type on halves."""
    return quality.rel_number == int(quality.rel_number)


def test_the_table_is_nineteen_qualities_half_a_step_apart(interval_qualities):
    assert len(interval_qualities) == 19
    numbers = [q.rel_number for q in interval_qualities]
    assert numbers == sorted(numbers)
    assert numbers == [n / 2 for n in range(-9, 10)]
    assert len({q.name for q in interval_qualities}) == 19
    for q in interval_qualities:
        assert QUALITIES[q.rel_number] is q, q
        assert _get_quality(q.rel_number) is q, q


def test_chromatic_modifier_is_the_floor_of_the_relative_number(interval_qualities):
    """Perfect and major add nothing to the diatonic base; minor takes one
    half-step; each diminution takes one more, each augmentation adds one."""
    for q in interval_qualities:
        assert q.chromatic_modifier == math.floor(q.rel_number), q
    assert QUALITIES[0].chromatic_modifier == QUALITIES[0.5].chromatic_modifier == 0
    assert QUALITIES[-0.5].chromatic_modifier == QUALITIES[-1].chromatic_modifier == -1
    assert QUALITIES[-1.5].chromatic_modifier == -2


def test_augment_and_diminish_are_inverses_within_the_table(interval_qualities):
    """Augmenting n times then diminishing n times is the identity, `+` and
    `-` are the same walk, and the family (perfect or major/minor) is kept."""
    for q in interval_qualities:
        assert q.augment(0) == q, q
        assert q + 0 == q, q
        for n in range(1, 5):
            if q.rel_number + n in QUALITIES:
                assert q.augment(n).diminish(n) == q, (q, n)
                assert (q + n) - n == q, (q, n)
                assert q.augment(n) == q + n, (q, n)
                assert _is_perfect_type(q.augment(n)) == _is_perfect_type(q), (q, n)
            if q.rel_number - n in QUALITIES:
                assert q.diminish(n).augment(n) == q, (q, n)
                assert (q - n) + n == q, (q, n)
                assert q.diminish(n) == q - n, (q, n)
            if q.rel_number + n in QUALITIES and q.rel_number + n - 1 in QUALITIES:
                assert q.augment(n) == q.augment(n - 1).augment(1), (q, n)


def test_abbreviation_parses_back_through_from_string(interval_qualities):
    """Each quality's abbreviation, in front of a degree of its own family,
    is a spelling `TonalVector.from_string` accepts, and the parsed interval
    carries that quality's chromatic modifier."""
    for q in interval_qualities:
        if _is_perfect_type(q):
            degree, base = 5, 7  # a fifth
        else:
            degree, base = 3, 4  # a third
        parsed = TonalVector.from_string(f"{q.abbr}{degree}")
        assert parsed == TonalVector((degree - 1, (base + q.chromatic_modifier) % 12)), q
        assert parsed.interval.abbr.replace(" ", "") == f"{q.abbr}{degree}".replace(" ", ""), q


def test_string_forms():
    assert str(QUALITIES[0]) == "perfect" and QUALITIES[0].abbr == "per"
    assert str(QUALITIES[0.5]) == "major" and QUALITIES[0.5].abbr == "maj"
    assert str(QUALITIES[-0.5]) == "minor" and QUALITIES[-0.5].abbr == "min"
    assert str(QUALITIES[-1.5]) == "diminished" and QUALITIES[-1.5].abbr == "dim"
    assert str(QUALITIES[2.5]) == "dbl augmented" and QUALITIES[2.5].abbr == "dbl aug"
    assert str(QUALITIES[-3]) == "trpl diminished" and QUALITIES[-3].abbr == "trp dim"
    assert str(QUALITIES[4.5]) == "quad augmented" and QUALITIES[4.5].abbr == "qua aug"
    assert repr(QUALITIES[0]) == 'IntervalQuality("perfect", 0)'
    for q in QUALITIES.values():
        assert eval(repr(q)) == q, q


def test_a_quality_is_a_frozen_hashable_value():
    q = QUALITIES[0.5]
    with pytest.raises(AttributeError):
        q.name = "other"
    assert hash(q) == hash(IntervalQuality("major", 0.5))
    assert q == IntervalQuality("major", 0.5)
    assert q != QUALITIES[-0.5]


def test_lookup_by_tuple_agrees_with_the_pitch_alteration():
    """The quality of an interval (d, c) has the chromatic modifier of the
    pitch's alteration, and the family of its degree, for all 35."""
    for v in ABSTRACT_VECTORS:
        q = _get_quality((v.d, v.c))
        assert q.chromatic_modifier == v.pitch.alteration, v
        assert _is_perfect_type(q) == (v.d in (0, 3, 4)), v
    assert _get_quality((0, 0)) is QUALITIES[0]
    assert _get_quality((2, 4)) is QUALITIES[0.5]
    assert _get_quality((0, 11)) is QUALITIES[-1]
    with pytest.raises(TypeError):
        _get_quality("major")


def test_walking_off_the_table_is_a_value_error():
    """Past quadruple augmentation or diminution there is no quality, and the
    class says so the way the string parser does."""
    with pytest.raises(ValueError):
        QUALITIES[4.5].augment(1)
    with pytest.raises(ValueError):
        QUALITIES[-4.5].diminish(1)
    with pytest.raises(ValueError):
        QUALITIES[0] + 5
