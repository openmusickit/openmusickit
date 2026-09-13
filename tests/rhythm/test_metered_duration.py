from datetime import timedelta
from fractions import Fraction as F

import pytest

from openmusickit.systems.wsmn.temporal import metrical_duration as md
from openmusickit.systems.wsmn.temporal import time_signature as ts
from openmusickit.values.time.duration import TemporalUnit, TemporalRatio, CompoundTemporalUnit
from openmusickit.values.time.clock_time import ClockDuration, Tempo
from openmusickit.values.time.errors import ScalingError, TemporalCompatibilityError
from openmusickit.systems.wsmn.temporal import symbols as sym

standard_duration_denominators = [1, 2, 4, 8, 16, 32, 64]
reasonable_tuple_ratios = [(3, 2), (5, 4), (7, 6), (11, 10)]
common_time_signature = [(2,4), (3,4), (4,4), (5,4), (1,2), (2,2), (3,2), (3,8), (6,8), (7,8), (9,8)]

# --- helpers ---------------------------------------------------------------

def _tuplet(nominal_count: int, contextual_count: int, base: md.MeteredDuration) -> TemporalRatio:
    """nominal_count notes of `base` in the time of contextual_count notes of `base`."""
    return TemporalRatio(TemporalUnit(nominal_count, base), TemporalUnit(contextual_count, base))

def _sig(n: int, d: int) -> ts.TimeSignature:
    """A simple time signature n/d built from a single TemporalUnit."""
    return ts.TimeSignature(TemporalUnit(n, md.MeteredDuration(1, d)), presentation=(str(n), str(d)))

def _real_time(dur, tempo: TemporalRatio) -> ClockDuration:
    return ClockDuration.from_duration(dur, tempo)


# --- basic creation --------------------------------------------------------

def test_standard_duration_creation():
    """
    Test that every standard note duration can be created without error.
    """
    for d in standard_duration_denominators:
        dur = md.MeteredDuration(1, d)
        assert dur.rational_length == F(1, d)
        assert dur.n == 1
        assert dur.d == d
        assert dur.dots == 0

def test_dotted_duration_creation():
    """Test that every standard note duration can be created with up to five dots, without error,
    and that the two ways of creating a dotted duration are equivalent."""
    for d in standard_duration_denominators:
        for n_dots in range(1,6):

            dotted_dur_nominal = md.MeteredDuration(1, d, dots = n_dots)

            numerator = (2**(n_dots+1))-1
            denominator = d * (2**n_dots)

            dotted_dur_actual = md.MeteredDuration(numerator, denominator)

            assert dotted_dur_nominal == dotted_dur_actual
            assert dotted_dur_nominal.rational_length == F(numerator, denominator)

            # both forms should normalize to the same nominal representation
            assert dotted_dur_actual.n == 1
            assert dotted_dur_actual.d == d
            assert dotted_dur_actual.dots == n_dots

def test_invalid_duration_creation():
    """Non-power-of-two denominators, negative dots, mixed dotted forms,
    and zero-length durations should all be rejected."""
    with pytest.raises(ValueError):
        md.MeteredDuration(1, 3)
    with pytest.raises(ValueError):
        md.MeteredDuration(1, 6)
    with pytest.raises(ValueError):
        md.MeteredDuration(1, 0)
    with pytest.raises(ValueError):
        md.MeteredDuration(1, 4, dots=-1)
    with pytest.raises(ValueError):
        md.MeteredDuration(3, 8, dots=1)   # 3/8 is already dotted; can't dot it again this way
    with pytest.raises(ValueError):
        md.MeteredDuration(5, 8)           # not a single notatable symbol (would need a tie)
    with pytest.raises(ValueError):
        md.MeteredDuration(0, 4)           # zero-length is not a note value; use ZeroDuration


# --- long durations: breve, longa, maxima -----------------------------------

def test_breve_creation():
    """A breve (double whole note) is exactly two whole notes."""
    breve = md.MeteredDuration(2, 1)
    assert breve.rational_length == F(2, 1)
    assert breve.dots == 0
    assert breve == TemporalUnit(2, md.MeteredDuration(1, 1))

def test_dotted_breve_creation():
    """A dotted breve is three whole notes, whether built with a dot
    or as its full value (3, 1). A double-dotted breve is 3 1/2 whole notes."""
    dotted_breve_nominal = md.MeteredDuration(2, 1, dots=1)
    dotted_breve_actual = md.MeteredDuration(3, 1)
    assert dotted_breve_nominal.rational_length == F(3, 1)
    assert dotted_breve_actual.rational_length == F(3, 1)
    assert dotted_breve_nominal == dotted_breve_actual
    assert dotted_breve_actual.dots == 1

    double_dotted_breve = md.MeteredDuration(2, 1, dots=2)
    assert double_dotted_breve.rational_length == F(7, 2)
    assert double_dotted_breve == md.MeteredDuration(7, 2)

def test_longa_and_maxima_creation():
    """A longa (quadruple whole note) is four whole notes, a maxima is eight.
    Dotted versions follow the usual rule."""
    longa = md.MeteredDuration(4, 1)
    assert longa.rational_length == F(4, 1)
    assert longa.dots == 0

    dotted_longa = md.MeteredDuration(4, 1, dots=1)
    assert dotted_longa.rational_length == F(6, 1)
    assert dotted_longa == md.MeteredDuration(6, 1)

    maxima = md.MeteredDuration(8, 1)
    assert maxima.rational_length == F(8, 1)

def test_long_duration_multiples():
    """Two wholes are a breve, two breves are a longa, two longas are a maxima."""
    whole = md.MeteredDuration(1, 1)
    breve = md.MeteredDuration(2, 1)
    longa = md.MeteredDuration(4, 1)
    maxima = md.MeteredDuration(8, 1)

    assert TemporalUnit(2, whole).rational_length == breve.rational_length
    assert TemporalUnit(2, breve).rational_length == longa.rational_length
    assert TemporalUnit(2, longa).rational_length == maxima.rational_length
    assert TemporalUnit(4, md.MeteredDuration(1, 2)).rational_length == breve.rational_length

def test_long_duration_scaling():
    """Scaling across the whole-note boundary should work in both directions."""
    whole = md.MeteredDuration(1, 1)
    half = md.MeteredDuration(1, 2)
    breve = md.MeteredDuration(2, 1)
    longa = md.MeteredDuration(4, 1)

    assert whole.scale(2) == breve
    assert half.scale(4) == breve
    assert breve.scale(2) == longa
    assert breve.scale(F(1, 2)) == whole
    assert longa.scale(F(1, 4)) == whole
    assert md.MeteredDuration(1, 1, dots=1).scale(2) == md.MeteredDuration(2, 1, dots=1)
    assert md.MeteredDuration(2, 1, dots=1).scale(F(1, 2)) == md.MeteredDuration(1, 1, dots=1)

def test_breve_fills_measures():
    """A breve fills a bar of 4/2 or 2/1; a dotted breve fills 6/2 or 3/1."""
    breve = md.MeteredDuration(2, 1)
    dotted_breve = md.MeteredDuration(2, 1, dots=1)
    assert breve.rational_length == _sig(4, 2).rational_length
    assert breve.rational_length == _sig(2, 1).rational_length
    assert breve.rational_length == _sig(8, 4).rational_length
    assert dotted_breve.rational_length == _sig(6, 2).rational_length
    assert dotted_breve.rational_length == _sig(3, 1).rational_length


# --- tuplets ----------------------------------------------------------------

def test_basic_tuple_duration_creation():
    """Test that a reasonable set of tuple-duration (3:2, 5:4, 7:6) can be created without error,
    and that values are appropriate."""
    for d in standard_duration_denominators:
        for tr in reasonable_tuple_ratios:
            nominal = TemporalUnit(tr[0], md.MeteredDuration(1, d))
            contextual = TemporalUnit(tr[1], md.MeteredDuration(1, d))
            r = TemporalRatio(nominal, contextual)
            tup_dur = md.MeteredDuration(1, d, tr=r)
            nom_dur = md.MeteredDuration(1, d)

            assert tup_dur.rational_length * tr[0] == nom_dur.rational_length * tr[1]

def test_tuplets():
    """Test that tuplets resolve to the correct RationalLength"""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    sixteenth = md.MeteredDuration(1, 16)
    half = md.MeteredDuration(1, 2)

    # quarter-note triplet: 3 in the time of 2
    quarter_in_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, quarter))
    assert quarter_in_triplet.rational_length == F(1, 6)

    # eighth-note triplet
    eighth_in_triplet = md.MeteredDuration(1, 8, tr=_tuplet(3, 2, eighth))
    assert eighth_in_triplet.rational_length == F(1, 12)

    # sixteenth quintuplet: 5 in the time of 4
    sixteenth_in_quintuplet = md.MeteredDuration(1, 16, tr=_tuplet(5, 4, sixteenth))
    assert sixteenth_in_quintuplet.rational_length == F(1, 20)

    # half-note triplet fills a bar of 4/4
    half_in_triplet = md.MeteredDuration(1, 2, tr=_tuplet(3, 2, half))
    assert TemporalUnit(3, half_in_triplet).rational_length == F(1, 1)

    # a quarter-note quintuplet fills a bar of 4/4
    quarter_in_quintuplet = md.MeteredDuration(1, 4, tr=_tuplet(5, 4, quarter))
    assert TemporalUnit(5, quarter_in_quintuplet).rational_length == F(1, 1)

    # duplet in 6/8: 2 eighths in the time of 3 eighths
    eighth_in_duplet = md.MeteredDuration(1, 8, tr=_tuplet(2, 3, eighth))
    assert eighth_in_duplet.rational_length == F(3, 16)
    assert TemporalUnit(2, eighth_in_duplet).rational_length == md.MeteredDuration(1, 4, dots=1).rational_length

    # the ratio of a tuplet is independent of which member note is queried:
    # a quarter inside an eighth-note triplet is two triplet eighths
    quarter_in_eighth_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, eighth))
    assert quarter_in_eighth_triplet.rational_length == 2 * eighth_in_triplet.rational_length

    # a dotted quarter takes up an entire eighth-note triplet (i.e. one quarter of real time)
    dotted_quarter_in_eighth_triplet = md.MeteredDuration(1, 4, dots=1, tr=_tuplet(3, 2, eighth))
    assert dotted_quarter_in_eighth_triplet.rational_length == F(1, 4)

def test_tuplet_ratio_with_mixed_bases():
    """The nominal and contextual sides of a tuplet need not use the same base duration.
    The ratio must be computed from the *full* length of each side (including dots and tuplets)."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    sixteenth = md.MeteredDuration(1, 16)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)

    # 3 eighths in the time of 1 quarter == standard eighth triplet
    r = TemporalRatio(TemporalUnit(3, eighth), TemporalUnit(1, quarter))
    assert r.r == F(2, 3)
    assert md.MeteredDuration(1, 8, tr=r).rational_length == F(1, 12)

    # 7 sixteenths in the time of one dotted quarter (a septuplet in 6/8)
    r = TemporalRatio(TemporalUnit(7, sixteenth), TemporalUnit(1, dotted_quarter))
    assert r.r == F(6, 7)
    assert md.MeteredDuration(1, 16, tr=r).rational_length == F(3, 56)
    assert TemporalUnit(7, md.MeteredDuration(1, 16, tr=r)).rational_length == F(3, 8)

    # 4 eighths in the time of a dotted quarter (quadruplet in 6/8)
    r = TemporalRatio(TemporalUnit(4, eighth), TemporalUnit(1, dotted_quarter))
    assert r.r == F(3, 4)
    assert TemporalUnit(4, md.MeteredDuration(1, 8, tr=r)).rational_length == F(3, 8)

def test_nested_tuplets():
    """An eighth-note triplet nested inside one member of a quarter-note triplet.
    Each outer triplet quarter is 1/6; the inner eighth is a third of that: 1/18."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)

    quarter_in_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, quarter))
    assert quarter_in_triplet.rational_length == F(1, 6)

    # 3 eighths in the time of one (tupleted) quarter
    inner = TemporalRatio(TemporalUnit(3, eighth), TemporalUnit(1, quarter_in_triplet))
    nested_eighth = md.MeteredDuration(1, 8, tr=inner)
    assert nested_eighth.rational_length == F(1, 18)
    assert TemporalUnit(3, nested_eighth).rational_length == quarter_in_triplet.rational_length

def test_tuplet_scaling():
    """Scaling a tupleted duration by a power of two scales its real length by the same amount."""
    eighth = md.MeteredDuration(1, 8)
    eighth_in_triplet = md.MeteredDuration(1, 8, tr=_tuplet(3, 2, eighth))

    assert eighth_in_triplet.scale(2).rational_length == F(1, 6)
    assert eighth_in_triplet.scale(F(1, 2)).rational_length == F(1, 24)
    assert eighth_in_triplet.scale(2).scale(F(1, 2)) == eighth_in_triplet


# --- arithmetic and structure ----------------------------------------------

def test_standard_multiples():
    """Test that 2 16ths equals an 8th, 2 8ths equal a quarter, etc."""
    for d in standard_duration_denominators:
        single_duration = md.MeteredDuration(1, d)
        half_duration = md.MeteredDuration(1, d*2)
        assert single_duration.rational_length == half_duration.rational_length * 2
        
        one_single_duration = TemporalUnit(1, single_duration)
        two_half_durations = TemporalUnit(2, half_duration)
        assert one_single_duration.rational_length == two_half_durations.rational_length

def test_dotted_equals_base_plus_half():
    """A dotted note equals the base note plus the next smaller note;
    a double dotted note adds the one after that as well."""
    for d in standard_duration_denominators:
        base = md.MeteredDuration(1, d)
        half_of_base = md.MeteredDuration(1, d * 2)
        quarter_of_base = md.MeteredDuration(1, d * 4)
        dotted = md.MeteredDuration(1, d, dots=1)
        double_dotted = md.MeteredDuration(1, d, dots=2)

        assert dotted.rational_length == base.rational_length + half_of_base.rational_length
        assert double_dotted.rational_length == dotted.rational_length + quarter_of_base.rational_length

def test_compound_temporal_units_and_duration_addition_commutative():
    """Test quarter + 8th is same as 8th plus quarter, etc"""
    for d1 in standard_duration_denominators:
        for d2 in standard_duration_denominators:
            duration_one = md.MeteredDuration(1, d1)
            duration_two = md.MeteredDuration(1, d2)

            temporal_unit_one = TemporalUnit(1, duration_one)
            temporal_unit_two = TemporalUnit(1, duration_two)

            compound_temporal_unit_a = CompoundTemporalUnit([temporal_unit_one, temporal_unit_two])
            compound_temporal_unit_b = CompoundTemporalUnit([temporal_unit_two, temporal_unit_one])

            assert compound_temporal_unit_a.rational_length == compound_temporal_unit_b.rational_length

def test_compound_temporal_units_with_duration_addition_associative():
    for d1 in standard_duration_denominators:
        for d2 in standard_duration_denominators:
            duration_one = md.MeteredDuration(1, d1)
            duration_two = md.MeteredDuration(1, d2)
            duration_three = md.MeteredDuration(3, d2) # dotted

            temporal_unit_one = TemporalUnit(1, duration_one)
            temporal_unit_two = TemporalUnit(2, duration_two)
            temporal_unit_three = TemporalUnit(3, duration_three)

            compound_temporal_unit_a = CompoundTemporalUnit([temporal_unit_one, temporal_unit_two])
            compound_temporal_unit_b = CompoundTemporalUnit([temporal_unit_two, temporal_unit_three])

            assert (
                        compound_temporal_unit_a.rational_length + 
                        temporal_unit_three.rational_length
                    ) == ( 
                        compound_temporal_unit_b.rational_length +
                        temporal_unit_one.rational_length
                    )

def test_compound_temporal_unit_sequence_protocol():
    """CompoundTemporalUnit behaves like an ordered sequence of its units."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    tu_q = TemporalUnit(1, quarter)
    tu_e = TemporalUnit(2, eighth)
    ctu = CompoundTemporalUnit([tu_q, tu_e])

    assert len(ctu) == 2
    assert ctu[0] is tu_q
    assert ctu[1] is tu_e
    assert list(ctu) == [tu_q, tu_e]
    assert tu_q in ctu

    # membership, index and count use value equality (1 quarter == 2 eighths),
    # consistent with TemporalElement.__eq__
    assert ctu.index(tu_e) == 0
    assert ctu.count(tu_q) == 2
    assert TemporalUnit(1, md.MeteredDuration(1, 2)) not in ctu

def test_duration_equality_and_comparison():
    """Durations compare by real length: a dotted quarter is longer than a quarter,
    3/8 is a dotted quarter, and 2 eighths are a quarter."""
    quarter = md.MeteredDuration(1, 4)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)
    eighth = md.MeteredDuration(1, 8)

    assert quarter == md.MeteredDuration(1, 4)
    assert quarter != eighth
    assert dotted_quarter == md.MeteredDuration(3, 8)
    assert eighth < quarter < dotted_quarter
    assert dotted_quarter > quarter
    assert quarter <= md.MeteredDuration(1, 4)
    assert quarter >= eighth
    assert sorted([dotted_quarter, eighth, quarter]) == [eighth, quarter, dotted_quarter]
    assert max([dotted_quarter, eighth, quarter]) == dotted_quarter

def test_duration_hashable():
    """Equal durations should be usable as dict keys / set members
    (e.g. counting how many of each note value appear in a phrase)."""
    quarter = md.MeteredDuration(1, 4)
    also_quarter = md.MeteredDuration(1, 4)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)
    also_dotted_quarter = md.MeteredDuration(3, 8)

    assert hash(quarter) == hash(also_quarter)
    assert hash(dotted_quarter) == hash(also_dotted_quarter)
    assert len({quarter, also_quarter, dotted_quarter, also_dotted_quarter}) == 2

def test_repr_roundtrip():
    """repr() of a non-tuplet duration should evaluate back to an equal duration."""
    MeteredDuration = md.MeteredDuration  # noqa: F841  (used by eval)
    for d in standard_duration_denominators:
        for n_dots in range(3):
            dur = md.MeteredDuration(1, d, dots=n_dots)
            assert eval(repr(dur)) == dur
    breve = md.MeteredDuration(2, 1)
    assert eval(repr(breve)) == breve

def test_temporal_unit_equality():
    """TemporalUnits are equal if they represent the same total length."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    assert TemporalUnit(4, quarter) == TemporalUnit(4, quarter)
    assert TemporalUnit(4, quarter) == TemporalUnit(8, eighth)
    assert TemporalUnit(1, quarter) != TemporalUnit(1, eighth)
    assert not (TemporalUnit(3, quarter) == TemporalUnit(2, quarter))


# --- scaling ----------------------------------------------------------------

def test_duration_scaling():
    """Test 8th.scale(2) is quarter, etc."""
    for d in standard_duration_denominators:
        assert md.MeteredDuration(1, d*2).scale(2) == md.MeteredDuration(1, d)

    for d in standard_duration_denominators:
        for n_dots in range(5):
            assert md.MeteredDuration(1, d*2, dots=n_dots).scale(2) == md.MeteredDuration(1, d, dots=n_dots)

def test_duration_scaling_down():
    """Scaling by 1/2 is the inverse of scaling by 2, for every standard value,
    and scaling by 4 / 1/4 is the same as scaling twice."""
    for d in standard_duration_denominators:
        for n_dots in range(3):
            dur = md.MeteredDuration(1, d, dots=n_dots)
            assert dur.scale(F(1, 2)) == md.MeteredDuration(1, d * 2, dots=n_dots)
            assert dur.scale(2).scale(F(1, 2)) == dur
            assert dur.scale(F(1, 2)).scale(2) == dur
            assert dur.scale(4) == dur.scale(2).scale(2)
            assert dur.scale(F(1, 4)) == dur.scale(F(1, 2)).scale(F(1, 2))
            assert dur.scale(1) == dur

def test_duration_scaling_preserves_dots():
    """Augmenting or diminishing a dotted note keeps it dotted."""
    for d in standard_duration_denominators:
        for n_dots in range(1, 4):
            scaled = md.MeteredDuration(1, d, dots=n_dots).scale(2)
            assert scaled.dots == n_dots
            scaled = md.MeteredDuration(1, d, dots=n_dots).scale(F(1, 2))
            assert scaled.dots == n_dots

def test_duration_scaling_rejects_non_powers_of_two():
    """A single MeteredDuration can only be augmented/diminished by powers of two.
    Other scalars need a tuplet or tie and must raise ScalingError."""
    quarter = md.MeteredDuration(1, 4)
    for bad in (3, 5, 6, F(2, 3), F(3, 2), F(1, 3)):
        with pytest.raises(ScalingError):
            quarter.scale(bad)

def test_temporal_unit_scaling():
    """Scaling a TemporalUnit scales its total length (by any scalar, not just powers of 2)."""
    quarter = md.MeteredDuration(1, 4)
    four_quarters = TemporalUnit(4, quarter)

    assert four_quarters.scale(2).rational_length == F(2, 1)
    assert four_quarters.scale(3).rational_length == F(3, 1)
    assert four_quarters.scale(F(1, 2)).rational_length == F(1, 2)
    assert four_quarters.scale(F(1, 4)).rational_length == F(1, 4)
    assert four_quarters.scale(F(3, 2)).rational_length == F(3, 2)
    assert four_quarters.scale(1).rational_length == four_quarters.rational_length

    # the base duration stays a MeteredDuration and the result is still a TemporalUnit
    scaled = four_quarters.scale(2)
    assert isinstance(scaled, TemporalUnit)
    assert isinstance(scaled.base, md.MeteredDuration)

    # dotted base
    two_dotted_quarters = TemporalUnit(2, md.MeteredDuration(1, 4, dots=1))
    assert two_dotted_quarters.scale(2).rational_length == F(3, 2)

def test_compound_temporal_unit_scaling():
    """Scaling a compound unit scales every member and the total."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    ctu = CompoundTemporalUnit([TemporalUnit(2, quarter), TemporalUnit(3, eighth)])  # 7/8
    assert ctu.rational_length == F(7, 8)

    doubled = ctu.scale(2)
    assert isinstance(doubled, CompoundTemporalUnit)
    assert doubled.rational_length == F(7, 4)
    assert len(doubled) == 2
    assert doubled[0].rational_length == F(1, 1)
    assert doubled[1].rational_length == F(3, 4)

    halved = ctu.scale(F(1, 2))
    assert halved.rational_length == F(7, 16)

    assert ctu.scale(3).rational_length == F(21, 8)


# --- time signatures --------------------------------------------------------

def test_common_time_signature_creation():
    """Test that common time signatures can be created"""
    for n, d in common_time_signature:
        sig = _sig(n, d)
        assert sig.rational_length == F(n, d)
        assert sig.n == str(n)
        assert sig.d == str(d)
        assert len(sig.spec) == 1
        assert isinstance(sig, CompoundTemporalUnit)

def test_time_signature_creation_from_list_and_compound():
    """A TimeSignature can be built from a single TemporalUnit, a list of TemporalUnits,
    or an existing CompoundTemporalUnit, with the same resulting length."""
    quarter = md.MeteredDuration(1, 4)
    from_unit = ts.TimeSignature(TemporalUnit(4, quarter))
    from_list = ts.TimeSignature([TemporalUnit(4, quarter)])
    from_compound = ts.TimeSignature(CompoundTemporalUnit([TemporalUnit(4, quarter)]))

    assert from_unit.rational_length == F(1, 1)
    assert from_list.rational_length == F(1, 1)
    assert from_compound.rational_length == F(1, 1)
    assert len(from_compound.spec) == 1

    # no presentation given
    assert from_unit.n is None
    assert from_unit.d is None

def test_compound_meter_equivalent_forms():
    """6/8 is 6 eighths or 2 dotted quarters; 9/8 is 3 dotted quarters; 3/8 is one."""
    eighth = md.MeteredDuration(1, 8)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)

    six_eight_a = ts.TimeSignature(TemporalUnit(6, eighth), presentation=("6", "8"))
    six_eight_b = ts.TimeSignature(TemporalUnit(2, dotted_quarter), presentation=("6", "8"))
    assert six_eight_a.rational_length == six_eight_b.rational_length == F(3, 4)

    assert ts.TimeSignature(TemporalUnit(3, dotted_quarter)).rational_length == _sig(9, 8).rational_length
    assert ts.TimeSignature(TemporalUnit(1, dotted_quarter)).rational_length == _sig(3, 8).rational_length
    assert ts.TimeSignature(TemporalUnit(4, dotted_quarter)).rational_length == _sig(12, 8).rational_length

def test_additive_time_signature():
    """7/8 grouped as 2+2+3 and 3+2+2 both total 7/8; 5/4 as 3+2 totals 5/4."""
    eighth = md.MeteredDuration(1, 8)
    quarter = md.MeteredDuration(1, 4)

    seven_eight_223 = ts.TimeSignature(
        [TemporalUnit(2, eighth), TemporalUnit(2, eighth), TemporalUnit(3, eighth)],
        presentation=("2+2+3", "8"))
    seven_eight_322 = ts.TimeSignature(
        [TemporalUnit(3, eighth), TemporalUnit(2, eighth), TemporalUnit(2, eighth)],
        presentation=("3+2+2", "8"))
    assert seven_eight_223.rational_length == F(7, 8)
    assert seven_eight_322.rational_length == F(7, 8)
    assert seven_eight_223.rational_length == _sig(7, 8).rational_length
    assert len(seven_eight_223.spec) == 3
    assert seven_eight_223.n == "2+2+3"

    five_four = ts.TimeSignature([TemporalUnit(3, quarter), TemporalUnit(2, quarter)])
    assert five_four.rational_length == F(5, 4)

def test_time_signature_repr():
    """repr() should be well-formed with or without a presentation."""
    with_pres = repr(_sig(4, 4))
    without_pres = repr(ts.TimeSignature(TemporalUnit(4, md.MeteredDuration(1, 4))))
    for r in (with_pres, without_pres):
        assert r.startswith("TimeSignature(")
        assert r.count("(") == r.count(")")

def test_time_signature_scaling():
    """Scaling a time signature scales its total length: 3/4 doubled is as long as 3/2,
    6/8 halved is as long as 6/16, etc."""
    for n, d in common_time_signature:
        sig = _sig(n, d)
        doubled = sig.scale(2)
        assert doubled.rational_length == F(n, d) * 2
        assert doubled.rational_length == F(n * 2, d)
        if d > 1:
            assert doubled.rational_length == _sig(n, d // 2).rational_length

        halved = sig.scale(F(1, 2))
        assert halved.rational_length == F(n, d) / 2
        assert halved.rational_length == _sig(n, d * 2).rational_length

        assert isinstance(doubled, CompoundTemporalUnit)
        assert len(doubled) == len(sig)

    # additive signatures scale member by member
    eighth = md.MeteredDuration(1, 8)
    seven_eight = ts.TimeSignature([TemporalUnit(2, eighth), TemporalUnit(2, eighth), TemporalUnit(3, eighth)])
    doubled = seven_eight.scale(2)
    assert doubled.rational_length == F(7, 4)
    assert len(doubled) == 3
    assert doubled[2].rational_length == F(3, 4)

def test_common_time_signature_filling():
    """Test that 4/4 is same length as 4 quarters, or eight 8ths, etc.
    (For all common time signatures and standard durations)"""
    for n, d_sig in common_time_signature:
        sig = _sig(n, d_sig)
        for d in standard_duration_denominators:
            how_many = F(n, d_sig) / F(1, d)
            if how_many.denominator != 1:
                continue  # e.g. a bar of 3/4 can't be filled with only half notes
            k = int(how_many)
            unit = md.MeteredDuration(1, d)

            # as a TemporalUnit
            assert TemporalUnit(k, unit).rational_length == sig.rational_length

            # as a series of individual durations
            series = [md.MeteredDuration(1, d) for _ in range(k)]
            assert sum(x.rational_length for x in series) == sig.rational_length
            assert sig.first_out_of_bounds(series) is None

            # one more overflows, and it is the one at index k
            assert sig.first_out_of_bounds(series + [md.MeteredDuration(1, d)]) == k

def test_time_signature_filling_with_dotted_values():
    """Compound meters are filled by dotted values: 6/8 by two dotted quarters,
    9/8 by three, 3/8 by one; 3/4 by a dotted half; 4/4 by a dotted half plus a quarter."""
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)
    dotted_half = md.MeteredDuration(1, 2, dots=1)
    quarter = md.MeteredDuration(1, 4)

    assert _sig(6, 8).first_out_of_bounds([dotted_quarter, dotted_quarter]) is None
    assert TemporalUnit(2, dotted_quarter).rational_length == _sig(6, 8).rational_length
    assert TemporalUnit(3, dotted_quarter).rational_length == _sig(9, 8).rational_length
    assert TemporalUnit(1, dotted_quarter).rational_length == _sig(3, 8).rational_length
    assert TemporalUnit(1, dotted_half).rational_length == _sig(3, 4).rational_length
    assert _sig(4, 4).first_out_of_bounds([dotted_half, quarter]) is None
    assert _sig(4, 4).first_out_of_bounds([dotted_half, dotted_quarter]) == 1

def test_time_signature_filling_with_tuplets():
    """A bar of 4/4 is filled by two quarter-note triplets (six triplet quarters)
    or by a half-note triplet; 6/8 is filled by two duplets."""
    quarter = md.MeteredDuration(1, 4)
    half = md.MeteredDuration(1, 2)
    eighth = md.MeteredDuration(1, 8)
    quarter_in_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, quarter))
    half_in_triplet = md.MeteredDuration(1, 2, tr=_tuplet(3, 2, half))
    eighth_in_duplet = md.MeteredDuration(1, 8, tr=_tuplet(2, 3, eighth))

    assert TemporalUnit(6, quarter_in_triplet).rational_length == _sig(4, 4).rational_length
    assert TemporalUnit(3, half_in_triplet).rational_length == _sig(4, 4).rational_length
    assert TemporalUnit(4, eighth_in_duplet).rational_length == _sig(6, 8).rational_length
    assert _sig(4, 4).first_out_of_bounds([quarter_in_triplet] * 6) is None
    assert _sig(4, 4).first_out_of_bounds([quarter_in_triplet] * 7) == 6

def test_time_signature_remainder():
    """test that a time signature and several durations result in the correct remainder"""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)
    dotted_half = md.MeteredDuration(1, 2, dots=1)
    quarter_in_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, quarter))

    def remainder(sig, series):
        return sig.remainder(series)

    assert remainder(_sig(4, 4), [quarter, dotted_quarter, eighth]) == F(1, 4)
    assert remainder(_sig(3, 4), [dotted_half]) == F(0, 1)
    assert remainder(_sig(6, 8), [dotted_quarter, eighth, eighth]) == F(1, 8)
    assert remainder(_sig(7, 8), [quarter, quarter]) == F(3, 8)
    assert remainder(_sig(4, 4), [quarter_in_triplet] * 3) == F(1, 2)
    assert remainder(_sig(2, 2), []) == F(1, 1)

    # overflow is a negative remainder, and first_out_of_bounds identifies the culprit
    assert remainder(_sig(3, 4), [quarter, quarter, dotted_quarter]) == F(-1, 8)
    assert _sig(3, 4).first_out_of_bounds([quarter, quarter, dotted_quarter]) == 2
    assert _sig(3, 4).first_out_of_bounds([dotted_half, eighth]) == 1
    assert _sig(3, 4).first_out_of_bounds([]) is None


# --- clock time and tempo ---------------------------------------------------

def test_clock_time_simple():
    """Test that clock time works as expected."""
    one_second = ClockDuration.from_seconds(1)
    assert one_second == ClockDuration(1_000_000)
    assert one_second.microseconds == 1_000_000
    assert one_second.milliseconds == 1_000
    assert one_second.seconds == 1
    assert one_second.minutes == pytest.approx(1 / 60)

    ninety_seconds = ClockDuration.from_seconds(90)
    assert ninety_seconds.minutes == 1.5
    assert str(ninety_seconds) == "00:01:30.000000"
    assert ClockDuration.from_minutes(90).hours == 1.5
    assert str(ClockDuration.from_milliseconds(1_500)) == "00:00:01.500000"
    assert ClockDuration.from_milliseconds(250).seconds == 0.25

    # arithmetic
    assert one_second + one_second == ClockDuration.from_seconds(2)
    assert ninety_seconds - one_second == ClockDuration.from_seconds(89)
    assert one_second.scale(2) == ClockDuration.from_seconds(2)
    assert one_second * 3 == ClockDuration.from_seconds(3)
    assert (one_second / 2).seconds == 0.5
    assert (ClockDuration.from_seconds(1) + ClockDuration.from_milliseconds(500)).seconds == 1.5

    # timedelta interop
    td = timedelta(minutes=2, seconds=3, microseconds=4)
    assert ClockDuration.from_timedelta(td).microseconds == 123_000_004
    assert ClockDuration.from_timedelta(td).to_timedelta == td
    assert ClockDuration.from_seconds(1).to_timedelta == timedelta(seconds=1)

def test_tempo_creation():
    """A tempo marking is n beats per clock duration."""
    quarter = md.MeteredDuration(1, 4)
    tempo = Tempo(120, quarter)
    assert isinstance(tempo, TemporalRatio)
    # 120 quarters (30 whole notes) per 60_000_000 µs → 2_000_000 µs per whole note
    assert tempo.r == F(2_000_000, 1)

    # a tempo can be expressed against a different clock duration
    tempo_per_second = Tempo(2, quarter, ClockDuration.from_seconds(1))
    assert tempo_per_second.r == tempo.r

def test_real_time_ratio_simple():
    """Test that a MeteredDuration and a tempo marking can calculate a real-time duration."""
    quarter = md.MeteredDuration(1, 4)
    half = md.MeteredDuration(1, 2)
    eighth = md.MeteredDuration(1, 8)
    whole = md.MeteredDuration(1, 1)

    q60 = Tempo(60, quarter)
    assert _real_time(quarter, q60).seconds == pytest.approx(1.0)
    assert _real_time(half, q60).seconds == pytest.approx(2.0)
    assert _real_time(eighth, q60).seconds == pytest.approx(0.5)
    assert _real_time(whole, q60).seconds == pytest.approx(4.0)

    q120 = Tempo(120, quarter)
    assert _real_time(quarter, q120).seconds == pytest.approx(0.5)
    assert _real_time(whole, q120).seconds == pytest.approx(2.0)

    # the beat unit matters: half = 60 is twice as slow per quarter
    h60 = Tempo(60, half)
    assert _real_time(quarter, h60).seconds == pytest.approx(0.5)

    # a bar of 4/4 at quarter = 120 lasts 2 seconds
    assert _real_time(_sig(4, 4), q120).seconds == pytest.approx(2.0)
    assert _real_time(TemporalUnit(4, quarter), q120).seconds == pytest.approx(2.0)

    # a breve at quarter = 60 lasts 8 seconds
    assert _real_time(md.MeteredDuration(2, 1), q60).seconds == pytest.approx(8.0)

def test_real_time_ratio_dots():
    """Test that a dotted MeteredDuration and a tempo marking can calculate a real-time duration."""
    quarter = md.MeteredDuration(1, 4)
    dotted_quarter = md.MeteredDuration(1, 4, dots=1)
    dotted_half = md.MeteredDuration(1, 2, dots=1)
    double_dotted_quarter = md.MeteredDuration(1, 4, dots=2)
    eighth = md.MeteredDuration(1, 8)

    q60 = Tempo(60, quarter)
    assert _real_time(dotted_quarter, q60).seconds == pytest.approx(1.5)
    assert _real_time(dotted_half, q60).seconds == pytest.approx(3.0)
    assert _real_time(double_dotted_quarter, q60).seconds == pytest.approx(1.75)

    # tempo given with a dotted beat: dotted quarter = 60 (typical for 6/8)
    dq60 = Tempo(60, dotted_quarter)
    assert _real_time(dotted_quarter, dq60).seconds == pytest.approx(1.0)
    assert _real_time(eighth, dq60).seconds == pytest.approx(1 / 3)
    assert _real_time(_sig(6, 8), dq60).seconds == pytest.approx(2.0)

def test_real_time_ratio_tuplets():
    """Test that a tuplet duration and a tempo marking can calculate a real-time duration."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    sixteenth = md.MeteredDuration(1, 16)
    quarter_in_triplet = md.MeteredDuration(1, 4, tr=_tuplet(3, 2, quarter))
    eighth_in_triplet = md.MeteredDuration(1, 8, tr=_tuplet(3, 2, eighth))
    sixteenth_in_quintuplet = md.MeteredDuration(1, 16, tr=_tuplet(5, 4, sixteenth))

    q60 = Tempo(60, quarter)
    assert _real_time(quarter_in_triplet, q60).seconds == pytest.approx(2 / 3)
    assert _real_time(eighth_in_triplet, q60).seconds == pytest.approx(1 / 3)
    assert _real_time(sixteenth_in_quintuplet, q60).seconds == pytest.approx(0.2)

    # three triplet eighths take exactly one beat
    assert _real_time(TemporalUnit(3, eighth_in_triplet), q60).seconds == pytest.approx(1.0)

def test_real_time_ratio_complex():
    """Test that a collection of MeteredDurations and a tempo marking can calculate a real-time duration."""
    quarter = md.MeteredDuration(1, 4)
    eighth = md.MeteredDuration(1, 8)
    sixteenth = md.MeteredDuration(1, 16)
    dotted_eighth = md.MeteredDuration(1, 8, dots=1)
    eighth_in_triplet = md.MeteredDuration(1, 8, tr=_tuplet(3, 2, eighth))

    # a rhythm: quarter | dotted-eighth sixteenth | eighth-triplet (x3) | two eighths
    # = 1/4 + 3/16 + 1/16 + 3 * 1/12 + 2 * 1/8 = 1 whole note = 4 quarters
    phrase = [quarter, dotted_eighth, sixteenth,
              eighth_in_triplet, eighth_in_triplet, eighth_in_triplet,
              eighth, eighth]
    assert sum(x.rational_length for x in phrase) == F(1, 1)

    q100 = Tempo(100, quarter)
    total = sum((_real_time(x, q100) for x in phrase), ClockDuration(0))
    assert total.seconds == pytest.approx(4 * 0.6)

    # the same phrase as a CompoundTemporalUnit
    ctu = CompoundTemporalUnit([
        TemporalUnit(1, quarter), TemporalUnit(1, dotted_eighth), TemporalUnit(1, sixteenth),
        TemporalUnit(3, eighth_in_triplet), TemporalUnit(2, eighth)])
    assert _real_time(ctu, q100).seconds == pytest.approx(2.4)

    # two bars of 3/4 at quarter = 90 take 4 seconds
    q90 = Tempo(90, quarter)
    assert _real_time(TemporalUnit(2, md.MeteredDuration(1, 2, dots=1)), q90).seconds == pytest.approx(4.0)


# --- TemporalUnit scaling edge cases (Q5) -----------------------------------

def test_temporal_unit_scaling_prefers_count():
    """When the scaled count is whole, the base stays the same: 4 quarters * 2 = 8 quarters."""
    four_quarters = TemporalUnit(4, sym.quarter)
    doubled = four_quarters.scale(2)
    assert doubled.count == 8
    assert doubled.base == sym.quarter
    halved = four_quarters.scale(F(1, 2))
    assert halved.count == 2
    assert halved.base == sym.quarter
    six_eighths = TemporalUnit(6, sym.eighth)
    assert six_eighths.scale(F(1, 3)).count == 2
    assert six_eighths.scale(F(1, 3)).base == sym.eighth

def test_temporal_unit_scaling_pushes_into_base():
    """When the count won't divide, the leftover power of two moves into the base:
    3 eighths / 2 = 3 sixteenths; 1 quarter * 3/2 = 3 eighths; 5 quarters / 4 = 5 sixteenths."""
    three_eighths = TemporalUnit(3, sym.eighth)
    halved = three_eighths.scale(F(1, 2))
    assert halved.count == 3
    assert halved.base == sym.sixteenth
    assert halved == md.MeteredDuration(1, 8, dots=1)

    one_quarter = TemporalUnit(1, sym.quarter)
    three_halves = one_quarter.scale(F(3, 2))
    assert three_halves.count == 3
    assert three_halves.base == sym.eighth
    assert three_halves == sym.dotted_quarter

    five_quarters = TemporalUnit(5, sym.quarter)
    assert five_quarters.scale(F(1, 4)).count == 5
    assert five_quarters.scale(F(1, 4)).base == sym.sixteenth

    # a dotted base keeps its dot
    one_dotted_quarter = TemporalUnit(1, sym.dotted_quarter)
    assert one_dotted_quarter.scale(F(1, 2)).base == sym.dotted_eighth
    assert one_dotted_quarter.scale(F(1, 2)).count == 1

    # count is always an int
    for scalar in (2, F(1, 2), F(3, 2), 3, F(1, 4)):
        assert isinstance(TemporalUnit(4, sym.quarter).scale(scalar).count, int)

def test_temporal_unit_scaling_rejects_non_notatable():
    """4 quarters / 3 has no notatable form without a tuplet."""
    with pytest.raises(ScalingError):
        TemporalUnit(4, sym.quarter).scale(F(1, 3))
    with pytest.raises(ScalingError):
        TemporalUnit(1, sym.quarter).scale(F(2, 3))
    with pytest.raises(ScalingError):
        TemporalUnit(4, sym.quarter).scale(0)
    with pytest.raises(ScalingError):
        TemporalUnit(4, sym.quarter).scale(-2)

def test_temporal_unit_with_tuplet_base_scaling():
    """A tupleted base is left alone when the count absorbs the scalar."""
    three_triplet_quarters = TemporalUnit(3, sym.quarter_in_triplet)  # one half note
    assert three_triplet_quarters.rational_length == F(1, 2)
    assert three_triplet_quarters.scale(2).count == 6
    assert three_triplet_quarters.scale(2) == sym.whole
    assert three_triplet_quarters.scale(F(1, 3)) == sym.quarter_in_triplet


# --- TimeSignature scaling with presentation (Q4) ---------------------------

def test_time_signature_scaling_returns_time_signature():
    doubled = sym.four_four.scale(2)
    assert isinstance(doubled, ts.TimeSignature)
    assert doubled == sym.time_signature(8, 4)
    assert doubled.presentation == ("8", "4")

def test_time_signature_scaling_presentation():
    """4/4 * 2 = 8/4; 4/4 / 2 = 2/4; 6/8 / 2 = 3/8; 3/8 / 2 = 3/16; 3/4 * 3 = 9/4."""
    assert sym.four_four.scale(F(1, 2)).presentation == ("2", "4")
    assert sym.six_eight.scale(F(1, 2)).presentation == ("3", "8")
    assert sym.three_eight.scale(F(1, 2)).presentation == ("3", "16")
    assert sym.three_four.scale(3).presentation == ("9", "4")
    assert sym.three_four.scale(F(1, 2)).presentation == ("3", "8")
    assert sym.three_four.scale(F(1, 4)).presentation == ("3", "16")
    assert sym.six_eight.scale(F(1, 3)).presentation == ("2", "8")

    # the units agree with the presentation
    assert sym.three_eight.scale(F(1, 2)).spec[0].base == sym.sixteenth
    assert sym.three_eight.scale(F(1, 2)).spec[0].count == 3

    # compound meter spelled with its beat: 6/8 as 2 dotted quarters, halved -> 1 dotted quarter, "3/8"
    halved = sym.two_dotted_quarters.scale(F(1, 2))
    assert halved.presentation == ("3", "8")
    assert halved.spec[0].count == 1
    assert halved.spec[0].base == sym.dotted_quarter

def test_additive_time_signature_scaling_presentation():
    doubled = sym.seven_eight_2_2_3.scale(2)
    assert doubled.presentation == ("4+4+6", "8")
    assert doubled.rational_length == F(7, 4)
    halved = sym.seven_eight_2_2_3.scale(F(1, 2))
    assert halved.presentation == ("2+2+3", "16")
    assert halved.rational_length == F(7, 16)
    assert [tu.base for tu in halved] == [sym.sixteenth] * 3

def test_time_signature_scaling_rejects_non_notatable():
    with pytest.raises(ScalingError):
        sym.four_four.scale(F(1, 3))
    with pytest.raises(ScalingError):
        sym.seven_eight_2_2_3.scale(F(1, 3))

def test_time_signature_scaling_non_numeric_presentation():
    """A presentation that isn't numeric (e.g. common time 'C') can't be scaled and is dropped."""
    common = ts.TimeSignature(TemporalUnit(4, sym.quarter), presentation=("C", ""))
    doubled = common.scale(2)
    assert doubled.rational_length == F(2, 1)
    assert doubled.presentation is None

def test_time_signature_equality():
    """Time signatures of the same total length are equal: 4/4 == 2/2 == 8/8 == 12/8 as 4 dotted quarters."""
    assert sym.four_four == sym.two_two
    assert sym.four_four == sym.time_signature(8, 8)
    assert sym.six_eight == sym.two_dotted_quarters
    assert sym.twelve_eight == sym.four_dotted_quarters
    assert sym.seven_eight == sym.seven_eight_2_2_3 == sym.seven_eight_3_2_2
    assert sym.three_four == sym.six_eight   # same length, different grouping
    assert sym.three_four != sym.two_four
    assert sym.three_four == sym.dotted_half
    assert sym.four_four == [sym.quarter] * 4
    assert sym.six_eight == [sym.dotted_quarter, sym.eighth, sym.eighth, sym.eighth]
    assert sym.three_four < sym.four_four
    assert sym.six_eight > sym.three_eight


# --- clock time conversion (Q2) --------------------------------------------

def test_clock_duration_from_duration():
    q120 = Tempo(120, sym.quarter)
    assert ClockDuration.from_duration(sym.quarter, q120) == ClockDuration.from_milliseconds(500)
    assert ClockDuration.from_duration(sym.dotted_half, q120) == ClockDuration.from_seconds(1.5)
    assert ClockDuration.from_duration(sym.four_four, q120) == ClockDuration.from_seconds(2)
    assert ClockDuration.from_duration(TemporalUnit(3, sym.eighth_in_triplet), q120).seconds == pytest.approx(0.5)
    assert ClockDuration.from_duration(sym.breve, q120) == ClockDuration.from_seconds(4)

    # tempo against a different clock base
    per_second = Tempo(2, sym.quarter, ClockDuration.from_seconds(1))
    assert ClockDuration.from_duration(sym.quarter, per_second) == ClockDuration.from_milliseconds(500)

    # exactness: a triplet eighth at quarter = 100 is exactly 200_000 µs
    assert ClockDuration.from_duration(sym.eighth_in_triplet, Tempo(100, sym.quarter)).microseconds == 200_000

    # a tuplet ratio is not a tempo
    with pytest.raises(TemporalCompatibilityError):
        ClockDuration.from_duration(sym.quarter, sym.triplet(sym.quarter))

def test_clock_duration_hashable_and_ordered():
    a = ClockDuration.from_seconds(1)
    b = ClockDuration(1_000_000)
    c = ClockDuration.from_seconds(2)
    assert hash(a) == hash(b)
    assert len({a, b, c}) == 2
    assert a < c
    assert sorted([c, a]) == [a, c]
    assert sum([a, c]) == ClockDuration.from_seconds(3)


# --- duration addition and ties (Q7) ---------------------------------------

def test_duration_addition_to_single_symbol():
    """Sums that are notatable as one symbol come back as a MeteredDuration."""
    assert sym.quarter + sym.eighth == sym.dotted_quarter
    assert isinstance(sym.quarter + sym.eighth, md.MeteredDuration)
    assert (sym.quarter + sym.eighth).dots == 1
    assert sym.eighth + sym.quarter == sym.dotted_quarter
    assert sym.quarter + sym.quarter == sym.half
    assert sym.half + sym.quarter == sym.dotted_half
    assert sym.dotted_quarter + sym.eighth == sym.half
    assert sym.dotted_quarter + sym.sixteenth == sym.double_dotted_quarter
    assert sym.whole + sym.whole == sym.breve
    assert sym.breve + sym.whole == sym.dotted_breve
    assert sym.breve + sym.breve == sym.longa
    assert isinstance(sym.whole + sym.whole, md.MeteredDuration)
    assert (sym.whole + sym.whole).dots == 0

def test_duration_addition_to_tied():
    """Sums that need a tie come back as a TiedDuration with the correct length."""
    tied = sym.quarter + sym.sixteenth
    assert isinstance(tied, md.TiedDuration)
    assert tied.rational_length == F(5, 16)
    assert len(tied) == 2
    assert list(tied) == [sym.quarter, sym.sixteenth]

    five_eighths = sym.half + sym.eighth
    assert isinstance(five_eighths, md.TiedDuration)
    assert five_eighths == md.MeteredDuration(1, 2) + md.MeteredDuration(1, 8)
    assert five_eighths.rational_length == F(5, 8)
    assert five_eighths == TemporalUnit(5, sym.eighth)

def test_tied_duration_collapses_when_possible():
    """quarter + sixteenth + sixteenth = quarter + eighth = dotted quarter."""
    result = sym.quarter + sym.sixteenth + sym.sixteenth
    assert isinstance(result, md.MeteredDuration)
    assert result == sym.dotted_quarter

    # 5/8 tied + 3/8 = whole
    assert (sym.half + sym.eighth) + sym.dotted_quarter == sym.whole
    assert isinstance((sym.half + sym.eighth) + sym.dotted_quarter, md.MeteredDuration)

    # sum() over a phrase
    phrase = [sym.quarter, sym.dotted_eighth, sym.sixteenth, sym.eighth, sym.eighth]
    assert sum(phrase) == sym.dotted_half
    assert sum(phrase) == sym.three_four

def test_tied_duration_scaling_and_tuplets():
    tied = sym.quarter + sym.sixteenth
    assert tied.scale(2) == sym.half + sym.eighth
    assert tied.scale(F(1, 2)).rational_length == F(5, 32)

    # a tuplet member added to a non-tuplet note can only be tied
    mixed = sym.quarter + sym.quarter_in_triplet
    assert isinstance(mixed, md.TiedDuration)
    assert mixed.rational_length == F(1, 4) + F(1, 6)

    # two members of the same triplet merge into a single tupleted value
    two_triplet_quarters = sym.quarter_in_triplet + sym.quarter_in_triplet
    assert isinstance(two_triplet_quarters, md.MeteredDuration)
    assert two_triplet_quarters.rational_length == F(1, 3)
    assert two_triplet_quarters.n == 1 and two_triplet_quarters.d == 2
    assert two_triplet_quarters.tr == sym.triplet(sym.quarter)

def test_from_fraction():
    assert md.MeteredDuration.from_fraction(F(3, 8)) == sym.dotted_quarter
    assert md.MeteredDuration.from_fraction(2) == sym.breve
    assert md.MeteredDuration.from_fraction(F(7, 4)) == sym.double_dotted_whole
    with pytest.raises(ValueError):
        md.MeteredDuration.from_fraction(F(5, 8))


# --- symbols ----------------------------------------------------------------

def test_symbols_note_values():
    expected = {
        sym.maxima: 8, sym.longa: 4, sym.breve: 2, sym.whole: 1, sym.half: F(1, 2),
        sym.quarter: F(1, 4), sym.eighth: F(1, 8), sym.sixteenth: F(1, 16),
        sym.thirtysecond: F(1, 32), sym.sixtyfourth: F(1, 64),
        sym.dotted_breve: 3, sym.dotted_whole: F(3, 2), sym.dotted_half: F(3, 4),
        sym.dotted_quarter: F(3, 8), sym.dotted_eighth: F(3, 16),
        sym.double_dotted_half: F(7, 8), sym.double_dotted_quarter: F(7, 16),
        sym.half_in_triplet: F(1, 3), sym.quarter_in_triplet: F(1, 6),
        sym.eighth_in_triplet: F(1, 12), sym.sixteenth_in_triplet: F(1, 24),
    }
    for symbol, length in expected.items():
        assert symbol.rational_length == length, symbol

def test_symbols_time_signatures():
    assert sym.four_four.rational_length == 1
    assert sym.four_four.presentation == ("4", "4")
    assert sym.common_time is sym.four_four
    assert sym.cut_time is sym.two_two
    assert sym.six_eight.rational_length == F(3, 4)
    assert sym.twelve_eight.rational_length == F(3, 2)
    assert sym.seven_eight_2_2_3.rational_length == F(7, 8)
    assert sym.seven_eight_2_2_3.n == "2+2+3"
    assert sym.five_eight_3_2.rational_length == F(5, 8)

def test_symbols_tuplet_helpers():
    assert sym.triplet(sym.quarter).r == F(2, 3)
    assert sym.duplet(sym.eighth).r == F(3, 2)
    assert sym.quintuplet(sym.sixteenth).r == F(4, 5)
    assert sym.sextuplet(sym.sixteenth).r == F(2, 3)
    assert sym.septuplet(sym.sixteenth).r == F(4, 7)
    assert md.MeteredDuration(1, 16, tr=sym.quintuplet(sym.sixteenth)).rational_length == F(1, 20)
