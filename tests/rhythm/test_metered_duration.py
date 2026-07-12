from openmusickit.systems.temporal.wsmn import metrical_duration as md
from openmusickit.systems.temporal.wsmn import time_signature as ts
from openmusickit.time.duration import TemporalUnit, TemporalRatio

standard_duration_denominators = [1, 2, 4, 8, 16, 32, 64]
reasonable_tuple_ratios = [(3, 2), (5, 4), (7, 6), (11, 10)]
common_time_signature = [(2,4), (3,4), (4,4), (5,4), (1,2), (2,2), (3,2), (3,8), (6,8), (7,8), (9,8)]

def test_standard_duration_creation():
    """
    Test that every standard note duration can be created without error.
    """
    for d in standard_duration_denominators:
        dur = md.MeteredDuration(1, d)
        print(dur)

def test_dotted_duration_creation():
    """Test that every standard note duration can be created with one or two dots, without error,
    and that the two ways of creating a dotted duration are equivalent."""
    for d in standard_duration_denominators:
        dur_one_dot_a = md.MeteredDuration(1, d, dots = 1)
        dur_one_dot_b = md.MeteredDuration(3, d*2)
        assert dur_one_dot_a == dur_one_dot_b

        dur_two_dot_a = md.MeteredDuration(1, d, dots = 2)
        dur_two_dot_b = md.MeteredDuration(7, d*4)
        assert dur_two_dot_a == dur_two_dot_b


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

def test_standard_multiples():
    """Test that 2 16ths equals an 8th, 2 8ths equal a quarter, etc."""
    pass

def test_standard_dots():
    """Test that dotted quarter is same length as 3 8ths, etc."""
    pass


def test_duration_addition_commutative():
    """Test quarter + 8th is same as 8th plus quarter, etc"""
    pass

def test_duration_addition_associative():
    """Test (8th + 8th) + 8th is same as 8th + (8th + 8th), etc"""
    pass

def test_duration_scaling():
    """Test 8th.scaled(2) is quarter, etc."""
    pass

def test_weird_dots():
    """Test multiple dots (3-5) for correct duration."""
    pass

def test_tuplets():
    """Test that tuplets resolve to the correct RationalLength"""
    pass

def test_common_time_signature_creation():
    """Test that common time signatures can be created"""

def test_common_time_signature_filling():
    """Test that 4/4 is same length as 4 quarters, or eight 8ths, etc.
    (For all common time signatures and standard durations)"""
    pass

def test_time_signature_remainder():
    """test that a time signature and several durations result in the correct remainder"""
    pass

def test_real_time_ratio_simple():
    """Test that a MeteredDuration and a tempo marking can calculate a real-time duration."""
    pass

def test_real_time_ratio_dots():
    """Test that a dotted MeteredDuration and a tempo marking can calculate a real-time duration."""
    pass

def test_real_time_ratio_tuplets():
    """Test that a tuplet duration and a tempo marking can calculate a real-time duration."""
    pass

def test_real_time_ratio_complex():
    """Test that a collection of MeteredDurations and a tempo marking can calculate a real-time duration."""
    pass