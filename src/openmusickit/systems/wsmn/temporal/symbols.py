"""Ready-to-go note durations, tuplet ratios, and time signatures.

```
from openmusickit.systems.wsmn.temporal.symbols import *
```

Examples
--------

>>> quarter
MeteredDuration(1, 4)

>>> dotted_half
MeteredDuration(1, 2, dots=1)

>>> breve
MeteredDuration(2, 1)

>>> eighth_in_triplet.rational_length
Fraction(1, 12)

>>> six_eight.rational_length
Fraction(3, 4)

>>> six_eight == two_dotted_quarters
True

>>> quarter + eighth == dotted_quarter
True
"""

from openmusickit.values.time.duration import TemporalUnit, TemporalRatio
from .metrical_duration import MeteredDuration
from .time_signature import TimeSignature

# --- plain note values -------------------------------------------------------

maxima = MeteredDuration(8, 1)
longa = MeteredDuration(4, 1)
breve = MeteredDuration(2, 1)
whole = MeteredDuration(1, 1)
half = MeteredDuration(1, 2)
quarter = MeteredDuration(1, 4)
eighth = MeteredDuration(1, 8)
sixteenth = MeteredDuration(1, 16)
thirtysecond = MeteredDuration(1, 32)
sixtyfourth = MeteredDuration(1, 64)
onehundredtwentyeighth = MeteredDuration(1, 128)

# --- dotted ------------------------------------------------------------------

dotted_maxima = MeteredDuration(8, 1, dots=1)
dotted_longa = MeteredDuration(4, 1, dots=1)
dotted_breve = MeteredDuration(2, 1, dots=1)
dotted_whole = MeteredDuration(1, 1, dots=1)
dotted_half = MeteredDuration(1, 2, dots=1)
dotted_quarter = MeteredDuration(1, 4, dots=1)
dotted_eighth = MeteredDuration(1, 8, dots=1)
dotted_sixteenth = MeteredDuration(1, 16, dots=1)
dotted_thirtysecond = MeteredDuration(1, 32, dots=1)
dotted_sixtyfourth = MeteredDuration(1, 64, dots=1)

# --- double dotted -----------------------------------------------------------

double_dotted_maxima = MeteredDuration(8, 1, dots=2)
double_dotted_longa = MeteredDuration(4, 1, dots=2)
double_dotted_breve = MeteredDuration(2, 1, dots=2)
double_dotted_whole = MeteredDuration(1, 1, dots=2)
double_dotted_half = MeteredDuration(1, 2, dots=2)
double_dotted_quarter = MeteredDuration(1, 4, dots=2)
double_dotted_eighth = MeteredDuration(1, 8, dots=2)
double_dotted_sixteenth = MeteredDuration(1, 16, dots=2)
double_dotted_thirtysecond = MeteredDuration(1, 32, dots=2)
double_dotted_sixtyfourth = MeteredDuration(1, 64, dots=2)

# --- tuplet ratios -----------------------------------------------------------

def tuplet(nominal_count: int, contextual_count: int, base: MeteredDuration) -> TemporalRatio:
    """`nominal_count` notes of `base` in the time of `contextual_count` notes of `base`.

    >>> tuplet(3, 2, quarter).r
    Fraction(2, 3)
    """
    return TemporalRatio(TemporalUnit(nominal_count, base), TemporalUnit(contextual_count, base))

def triplet(base: MeteredDuration) -> TemporalRatio:
    """3 in the time of 2."""
    return tuplet(3, 2, base)

def duplet(base: MeteredDuration) -> TemporalRatio:
    """2 in the time of 3 (for compound meters)."""
    return tuplet(2, 3, base)

def quintuplet(base: MeteredDuration) -> TemporalRatio:
    """5 in the time of 4."""
    return tuplet(5, 4, base)

def sextuplet(base: MeteredDuration) -> TemporalRatio:
    """6 in the time of 4."""
    return tuplet(6, 4, base)

def septuplet(base: MeteredDuration) -> TemporalRatio:
    """7 in the time of 4 (the common simple-meter septuplet; use tuplet(7, 6, ...) for the other)."""
    return tuplet(7, 4, base)

# --- notes inside a standard triplet of their own value ----------------------

breve_in_triplet = MeteredDuration(2, 1, tr=triplet(breve))
whole_in_triplet = MeteredDuration(1, 1, tr=triplet(whole))
half_in_triplet = MeteredDuration(1, 2, tr=triplet(half))
quarter_in_triplet = MeteredDuration(1, 4, tr=triplet(quarter))
eighth_in_triplet = MeteredDuration(1, 8, tr=triplet(eighth))
sixteenth_in_triplet = MeteredDuration(1, 16, tr=triplet(sixteenth))
thirtysecond_in_triplet = MeteredDuration(1, 32, tr=triplet(thirtysecond))
sixtyfourth_in_triplet = MeteredDuration(1, 64, tr=triplet(sixtyfourth))

# --- time signatures ---------------------------------------------------------

def time_signature(n: int, d: int) -> TimeSignature:
    """A simple time signature n/d, presented as written.

    >>> time_signature(3, 4)
    TimeSignature([TemporalUnit(3, MeteredDuration(1, 4))], ('3', '4'))
    """
    return TimeSignature(TemporalUnit(n, MeteredDuration(1, d)), presentation=(str(n), str(d)))

def additive_time_signature(groups: list[int], d: int) -> TimeSignature:
    """An additive time signature such as 2+2+3/8.

    >>> additive_time_signature([2, 2, 3], 8).n
    '2+2+3'
    """
    base = MeteredDuration(1, d)
    return TimeSignature([TemporalUnit(g, base) for g in groups],
                         presentation=("+".join(str(g) for g in groups), str(d)))

one_one = time_signature(1, 1)
two_one = time_signature(2, 1)
three_one = time_signature(3, 1)

one_two = time_signature(1, 2)
two_two = cut_time = time_signature(2, 2)
three_two = time_signature(3, 2)
four_two = time_signature(4, 2)

one_four = time_signature(1, 4)
two_four = time_signature(2, 4)
three_four = time_signature(3, 4)
four_four = common_time = time_signature(4, 4)
five_four = time_signature(5, 4)
six_four = time_signature(6, 4)
seven_four = time_signature(7, 4)

three_eight = time_signature(3, 8)
five_eight = time_signature(5, 8)
six_eight = time_signature(6, 8)
seven_eight = time_signature(7, 8)
nine_eight = time_signature(9, 8)
twelve_eight = time_signature(12, 8)

# compound meters expressed by their beat
one_dotted_quarter = TimeSignature(TemporalUnit(1, dotted_quarter), presentation=("3", "8"))
two_dotted_quarters = TimeSignature(TemporalUnit(2, dotted_quarter), presentation=("6", "8"))
three_dotted_quarters = TimeSignature(TemporalUnit(3, dotted_quarter), presentation=("9", "8"))
four_dotted_quarters = TimeSignature(TemporalUnit(4, dotted_quarter), presentation=("12", "8"))

# common additive groupings
five_eight_2_3 = additive_time_signature([2, 3], 8)
five_eight_3_2 = additive_time_signature([3, 2], 8)
seven_eight_2_2_3 = additive_time_signature([2, 2, 3], 8)
seven_eight_3_2_2 = additive_time_signature([3, 2, 2], 8)
seven_eight_2_3_2 = additive_time_signature([2, 3, 2], 8)
