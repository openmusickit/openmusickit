"""Ready-to-go note durations, tuplet ratios, and time signatures.

```
from openmusickit.systems.wsmn.temporal.symbols import *
```

Examples
--------

>>> quarter
MetricalDuration(1, 4)

>>> dotted_half
MetricalDuration(1, 2, dots=1)

>>> breve
MetricalDuration(2, 1)

>>> eighth_in_triplet.rational_length
Fraction(1, 12)

>>> six_eight.rational_length
Fraction(3, 4)

>>> six_eight == two_dotted_quarters
True

>>> quarter + eighth == dotted_quarter
True

>>> quarter + grace_eighth == quarter
True
"""

from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.values.time.duration import GraceDuration, TemporalRatio, TemporalUnit

# --- plain note values -------------------------------------------------------

maxima = MetricalDuration(8, 1)
longa = MetricalDuration(4, 1)
breve = MetricalDuration(2, 1)
whole = semibreve = MetricalDuration(1, 1)
half = minim = MetricalDuration(1, 2)
quarter = crotchet = MetricalDuration(1, 4)
eighth = quaver = MetricalDuration(1, 8)
sixteenth = semiquaver = MetricalDuration(1, 16)
thirtysecond = demisemiquaver = MetricalDuration(1, 32)
sixtyfourth = hemidemisemiquaver = MetricalDuration(1, 64)
onehundredtwentyeighth = semihemidemisemiquaver = MetricalDuration(1, 128)

# --- dotted ------------------------------------------------------------------

dotted_maxima = MetricalDuration(8, 1, dots=1)
dotted_longa = MetricalDuration(4, 1, dots=1)
dotted_breve = MetricalDuration(2, 1, dots=1)
dotted_whole = dotted_semibreve = MetricalDuration(1, 1, dots=1)
dotted_half = dotted_minim = MetricalDuration(1, 2, dots=1)
dotted_quarter = dotted_crotchet = MetricalDuration(1, 4, dots=1)
dotted_eighth = dotted_quaver = MetricalDuration(1, 8, dots=1)
dotted_sixteenth = dotted_semiquaver = MetricalDuration(1, 16, dots=1)
dotted_thirtysecond = dotted_demisemiquaver = MetricalDuration(1, 32, dots=1)
dotted_sixtyfourth = dotted_hemidemisemiquaver = MetricalDuration(1, 64, dots=1)

# --- double dotted -----------------------------------------------------------

double_dotted_maxima = MetricalDuration(8, 1, dots=2)
double_dotted_longa = MetricalDuration(4, 1, dots=2)
double_dotted_breve = MetricalDuration(2, 1, dots=2)
double_dotted_whole = double_dotted_semibreve = MetricalDuration(1, 1, dots=2)
double_dotted_half = double_dotted_minim = MetricalDuration(1, 2, dots=2)
double_dotted_quarter = double_dotted_crotchet = MetricalDuration(1, 4, dots=2)
double_dotted_eighth = double_dotted_quaver = MetricalDuration(1, 8, dots=2)
double_dotted_sixteenth = double_dotted_semiquaver = MetricalDuration(1, 16, dots=2)
double_dotted_thirtysecond = double_dotted_demisemiquaver = MetricalDuration(1, 32, dots=2)
double_dotted_sixtyfourth = double_dotted_hemidemisemiquaver = MetricalDuration(1, 64, dots=2)

# --- tuplet ratios -----------------------------------------------------------


def tuplet(nominal_count: int, contextual_count: int, base: MetricalDuration) -> TemporalRatio:
    """`nominal_count` notes of `base` in the time of `contextual_count` notes of `base`.

    >>> tuplet(3, 2, quarter).multiplier
    Fraction(2, 3)
    """
    return TemporalRatio(TemporalUnit(nominal_count, base), TemporalUnit(contextual_count, base))


def triplet(base: MetricalDuration) -> TemporalRatio:
    """3 in the time of 2."""
    return tuplet(3, 2, base)


def duplet(base: MetricalDuration) -> TemporalRatio:
    """2 in the time of 3 (for compound meters)."""
    return tuplet(2, 3, base)


def quintuplet(base: MetricalDuration) -> TemporalRatio:
    """5 in the time of 4."""
    return tuplet(5, 4, base)


def sextuplet(base: MetricalDuration) -> TemporalRatio:
    """6 in the time of 4."""
    return tuplet(6, 4, base)


def septuplet(base: MetricalDuration) -> TemporalRatio:
    """7 in the time of 4 (the common simple-meter septuplet; use tuplet(7, 6, ...) for the other)."""
    return tuplet(7, 4, base)


# --- notes inside a standard triplet of their own value ----------------------

breve_in_triplet = MetricalDuration(2, 1, ratio=triplet(breve))
whole_in_triplet = semibreve_in_triplet = MetricalDuration(1, 1, ratio=triplet(whole))
half_in_triplet = minim_in_triplet = MetricalDuration(1, 2, ratio=triplet(half))
quarter_in_triplet = crotchet_in_triplet = MetricalDuration(1, 4, ratio=triplet(quarter))
eighth_in_triplet = quaver_in_triplet = MetricalDuration(1, 8, ratio=triplet(eighth))
sixteenth_in_triplet = semiquaver_in_triplet = MetricalDuration(1, 16, ratio=triplet(sixteenth))
thirtysecond_in_triplet = demisemiquaver_in_triplet = MetricalDuration(
    1, 32, ratio=triplet(thirtysecond)
)
sixtyfourth_in_triplet = hemidemisemiquaver_in_triplet = MetricalDuration(
    1, 64, ratio=triplet(sixtyfourth)
)

# --- grace notes -------------------------------------------------------------
# zero metrical width; the nominal value is the symbol written.
# The slashed grace (acciaccatura) is played before the beat; the appoggiatura on it.

grace_eighth = acciaccatura_eighth = GraceDuration(eighth)
grace_sixteenth = acciaccatura_sixteenth = GraceDuration(sixteenth)
appoggiatura_quarter = GraceDuration(quarter, on_beat=True)
appoggiatura_eighth = GraceDuration(eighth, on_beat=True)
appoggiatura_sixteenth = GraceDuration(sixteenth, on_beat=True)

# --- time signatures ---------------------------------------------------------


def time_signature(n: int, d: int) -> TimeSignature:
    """A simple time signature n/d, presented as written.

    >>> time_signature(3, 4)
    TimeSignature([TemporalUnit(3, MetricalDuration(1, 4))], ('3', '4'))
    """
    return TimeSignature(TemporalUnit(n, MetricalDuration(1, d)), presentation=(str(n), str(d)))


def additive_time_signature(groups: list[int], d: int) -> TimeSignature:
    """An additive time signature such as 2+2+3/8.

    >>> additive_time_signature([2, 2, 3], 8).presentation
    ('2+2+3', '8')
    """
    base = MetricalDuration(1, d)
    return TimeSignature(
        [TemporalUnit(g, base) for g in groups],
        presentation=("+".join(str(g) for g in groups), str(d)),
    )


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
one_dotted_quarter = one_dotted_crotchet = TimeSignature(
    TemporalUnit(1, dotted_quarter), presentation=("3", "8")
)
two_dotted_quarters = two_dotted_crotchets = TimeSignature(
    TemporalUnit(2, dotted_quarter), presentation=("6", "8")
)
three_dotted_quarters = three_dotted_crotchets = TimeSignature(
    TemporalUnit(3, dotted_quarter), presentation=("9", "8")
)
four_dotted_quarters = four_dotted_crotchets = TimeSignature(
    TemporalUnit(4, dotted_quarter), presentation=("12", "8")
)

# common additive groupings
five_eight_2_3 = additive_time_signature([2, 3], 8)
five_eight_3_2 = additive_time_signature([3, 2], 8)
seven_eight_2_2_3 = additive_time_signature([2, 2, 3], 8)
seven_eight_3_2_2 = additive_time_signature([3, 2, 2], 8)
seven_eight_2_3_2 = additive_time_signature([2, 3, 2], 8)
