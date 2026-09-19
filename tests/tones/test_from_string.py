"""Tests for TonalVector.from_string.

from_string() must parse a wide range of string spellings of pitches and
intervals into the appropriate TonalVector. See individual test cases and
docstrings below for the forms that are expected to be supported.
"""

import pytest

from openmusickit.systems.wsmn.tonal.constants import SolfegeStyle
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector

# --- Pitches: bare letters, no accidental, no octave ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("C", (0, 0)),
        ("c", (0, 0)),
        ("D", (1, 2)),
        ("d", (1, 2)),
        ("E", (2, 4)),
        ("F", (3, 5)),
        ("G", (4, 7)),
        ("A", (5, 9)),
        ("B", (6, 11)),
    ],
)
def test_bare_letter_pitches(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: ASCII accidentals ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("C#", (0, 1)),
        ("c#", (0, 1)),
        ("C##", (0, 2)),
        ("Cb", (0, 11)),
        ("cb", (0, 11)),
        ("Cbb", (0, 10)),
        ("G#", (4, 8)),
        ("Gb", (4, 6)),
        ("F##", (3, 7)),
        ("Bbb", (6, 9)),
    ],
)
def test_ascii_accidental_pitches(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: Unicode accidentals ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("C♯", (0, 1)),
        ("C♭", (0, 11)),
        ("C𝄪", (0, 2)),  # double sharp
        ("C𝄫", (0, 10)),  # double flat
        ("G♯", (4, 8)),
        ("G♭", (4, 6)),
    ],
)
def test_unicode_accidental_pitches(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Lilypond-style spellings are NOT accepted by from_string ---
# Lilypond note names ("is"/"es" accidental suffixes, "'"/"," octave marks)
# are handled by the separate TonalVector.from_ly classmethod (see
# test_from_ly.py), because Lilypond has no notion of an "abstract"
# (octave-less) pitch the way from_string's other input forms do. from_string
# rejects these forms outright rather than guessing.


@pytest.mark.parametrize(
    "s",
    [
        "cis",
        "ces",
        "gis",
        "c'",
        "c,",
    ],
)
def test_lilypond_style_strings_are_rejected(s):
    with pytest.raises(ValueError):
        TonalVector.from_string(s)


# --- Pitches: word modifiers ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("C sharp", (0, 1)),
        ("Csharp", (0, 1)),
        ("C flat", (0, 11)),
        ("Cflat", (0, 11)),
        ("C natural", (0, 0)),
        ("C double sharp", (0, 2)),
        ("C double flat", (0, 10)),
        ("G sharp", (4, 8)),
    ],
)
def test_word_modifier_pitches(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: with numeric octave designation ---
# mid_c defaults to 4: C4 is middle C == internal octave 0.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("C4", (0, 0, 0)),
        ("C0", (0, 0, -4)),
        ("C1", (0, 0, -3)),
        ("C5", (0, 0, 1)),
        ("D4", (1, 2, 0)),
        ("G3", (4, 7, -1)),
        ("A4", (5, 9, 0)),
        ("Bb3", (6, 10, -1)),
        ("C#4", (0, 1, 0)),
    ],
)
def test_pitches_with_octave(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


def test_pitches_with_octave_custom_mid_c():
    """mid_c can be overridden, e.g. to treat C3 as middle C (as in some
    non-MIDI conventions)."""
    assert TonalVector.from_string("C3", mid_c=3) == TonalVector((0, 0, 0))
    assert TonalVector.from_string("C4", mid_c=3) == TonalVector((0, 0, 1))


def test_pitches_with_octave_mid_c_zero():
    """mid_c=0 treats the octave number itself as OMK's internal octave
    (i.e. C0 is middle C, matching TonalVector's own convention)."""
    assert TonalVector.from_string("C0", mid_c=0) == TonalVector((0, 0, 0))
    assert TonalVector.from_string("G-1", mid_c=0) == TonalVector((4, 7, -1))
    assert TonalVector.from_string("D1", mid_c=0) == TonalVector((1, 2, 1))


# --- Pitches: case sensitivity edge cases ---
# Capital A/D followed directly by a number is always a pitch (regardless of
# case). Interval augmented/diminished qualities must be spelled "aug"/"dim"
# (or "augmented"/"diminished"), never a bare "a"/"d" letter.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("A4", (5, 9, 0)),  # pitch A above middle C
        ("a4", (5, 9, 0)),  # pitch A above middle C (case-insensitive)
        ("D4", (1, 2, 0)),  # pitch D above middle C
        ("d4", (1, 2, 0)),  # pitch D above middle C (case-insensitive)
    ],
)
def test_bare_a_d_letters_are_always_pitches(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: solfege, default style (EURO_FIXED) ---
# EURO_FIXED assigns one syllable per diatonic letter name; there are no
# dedicated chromatic syllables, so "Si" is simply the fixed name for B
# (matching Latin/French solfege convention), not "so-sharp".


@pytest.mark.parametrize(
    "s, expected",
    [
        ("Do", (0, 0)),
        ("do", (0, 0)),
        ("Re", (1, 2)),
        ("Mi", (2, 4)),
        ("Fa", (3, 5)),
        ("Sol", (4, 7)),
        ("So", (4, 7)),
        ("La", (5, 9)),
        ("Ti", (6, 11)),
        ("Si", (6, 11)),
    ],
)
def test_euro_fixed_solfege_is_default(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: EURO_FIXED solfege with an explicit accidental ---
# accidentals are appended just like they are to a letter name, since
# EURO_FIXED syllables have no chromatic variants of their own.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("Do-sharp", (0, 1)),
        ("Do#", (0, 1)),
        ("Do♯", (0, 1)),
        ("Re-flat", (1, 1)),
        ("Reb", (1, 1)),
        ("Sol#", (4, 8)),
        ("Sib", (6, 10)),
    ],
)
def test_euro_fixed_solfege_with_accidental(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Pitches: OMK_MOVEABLE solfege, chromatic ---
# OMK_MOVEABLE uses moveable-do syllables with dedicated chromatic
# variants; here "Si" means so-sharp, not B, and accidentals are not
# appended separately -- the chromatic alteration is baked into the
# syllable itself.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("Do", (0, 0)),
        ("Re", (1, 2)),
        ("Mi", (2, 4)),
        ("Fa", (3, 5)),
        ("So", (4, 7)),
        ("La", (5, 9)),
        ("Ti", (6, 11)),
        ("Di", (0, 1)),  # do-sharp
        ("Ra", (1, 1)),  # re-flat
        ("Fi", (3, 6)),  # fa-sharp
        ("Si", (4, 8)),  # so-sharp
        ("Te", (6, 10)),  # ti-flat
    ],
)
def test_omk_moveable_solfege(s, expected):
    assert TonalVector.from_string(s, solfege_style=SolfegeStyle.OMK_MOVEABLE) == TonalVector(
        expected
    )


# --- Intervals: letter/abbreviation quality + number ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("P1", (0, 0)),
        ("P4", (3, 5)),
        ("P5", (4, 7)),
        ("M2", (1, 2)),
        ("M3", (2, 4)),
        ("M6", (5, 9)),
        ("M7", (6, 11)),
        ("m2", (1, 1)),
        ("m3", (2, 3)),
        ("m6", (5, 8)),
        ("m7", (6, 10)),
    ],
)
def test_abbreviated_quality_intervals(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Intervals: aug/dim (spelled out, not bare letters) ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("aug4", (3, 6)),
        ("Aug4", (3, 6)),
        ("augmented4", (3, 6)),
        ("aug 4", (3, 6)),
        ("dim5", (4, 6)),
        ("diminished5", (4, 6)),
        ("dim 5", (4, 6)),
        ("aug1", (0, 1)),
        ("dim1", (0, 11)),
        ("double diminished 5", (4, 5)),
        ("dbl dim5", (4, 5)),
        ("double augmented4", (3, 7)),
    ],
)
def test_aug_dim_word_intervals(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Intervals: spelled-out quality words ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("Perfect 1", (0, 0)),
        ("perfect fifth", (4, 7)),
        ("Major 3", (2, 4)),
        ("major third", (2, 4)),
        ("minor 3", (2, 3)),
        ("minor third", (2, 3)),
        ("Minor Sixth", (5, 8)),
    ],
)
def test_spelled_out_quality_intervals(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Intervals: ordinal-suffixed numbers ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("P1st", (0, 0)),
        ("M3rd", (2, 4)),
        ("P5th", (4, 7)),
        ("m7th", (6, 10)),
        ("aug4th", (3, 6)),
        ("M9th", (1, 2, 1)),
    ],
)
def test_ordinal_suffixed_intervals(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Intervals: compound (8-13), octave-qualified result ---


@pytest.mark.parametrize(
    "s, expected",
    [
        ("P8", (0, 0, 1)),
        ("M9", (1, 2, 1)),
        ("m10", (2, 3, 1)),
        ("P11", (3, 5, 1)),
        ("aug11", (3, 6, 1)),
        ("P12", (4, 7, 1)),
        ("M13", (5, 9, 1)),
        ("m13", (5, 8, 1)),
    ],
)
def test_compound_intervals(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Case sensitivity: bare capital M / lowercase m ---
# Standalone "M" means major; standalone "m" means minor.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("M3", (2, 4)),  # Major 3rd
        ("m3", (2, 3)),  # minor 3rd
        ("M6", (5, 9)),
        ("m6", (5, 8)),
    ],
)
def test_bare_m_case_sensitivity(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Whitespace / punctuation robustness ---


@pytest.mark.parametrize(
    "s, expected",
    [
        (" C ", (0, 0)),
        ("C #", (0, 1)),
        ("  M3  ", (2, 4)),
        ("perfect  fifth", (4, 7)),
    ],
)
def test_extra_whitespace_is_tolerated(s, expected):
    assert TonalVector.from_string(s) == TonalVector(expected)


# --- Invalid input should raise, not silently guess ---


@pytest.mark.parametrize(
    "s",
    [
        "",
        "H",  # not a valid letter name
        "Z9",
        "P15",  # out of supported interval range (1-13)
        "M0",  # no zero interval number (1 = unison)
        "banana",
    ],
)
def test_invalid_strings_raise(s):
    with pytest.raises(ValueError):
        TonalVector.from_string(s)


# --- Invalid interval quality/number combinations should raise ---
# Unisons, 4ths, 5ths, and octaves (and their compounds) are always
# Perfect-type: they can be perfect, augmented, or diminished, but never
# major/minor. 2nds, 3rds, 6ths, and 7ths (and their compounds) are always
# Major/minor-type: they can be major, minor, augmented, or diminished, but
# never perfect. Any string combining an interval number with a quality
# from the wrong family is invalid.


@pytest.mark.parametrize(
    "s",
    [
        "P2",  # 2nd can't be perfect
        "P3",  # 3rd can't be perfect
        "P6",  # 6th can't be perfect
        "P7",  # 7th can't be perfect
        "M1",  # unison can't be major
        "m1",  # unison can't be minor
        "M4",  # 4th can't be major
        "m5",  # 5th can't be minor
        "M8",  # octave can't be major
        "P9",  # 9th (compound 2nd) can't be perfect
    ],
)
def test_invalid_interval_quality_number_combinations_raise(s):
    with pytest.raises(ValueError):
        TonalVector.from_string(s)
