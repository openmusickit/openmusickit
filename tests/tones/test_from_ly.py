"""Tests for TonalVector.from_ly.

from_ly() parses Lilypond-style pitch names ("is"/"es" accidentals,
"'"/"," absolute octave marks, or an octave resolved relative to a
`prev_note`). Unlike from_string, the result is always octave-qualified,
since Lilypond has no notion of an abstract (octave-less) pitch.
"""

import pytest

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector


### No octave mark, no prev_note: defaults to Lilypond's default octave (0) ###

@pytest.mark.parametrize("s, expected", [
    ("c", (0, 0, 0)),
    ("C", (0, 0, 0)),
    ("d", (1, 2, 0)),
    ("e", (2, 4, 0)),
    ("f", (3, 5, 0)),
    ("g", (4, 7, 0)),
    ("a", (5, 9, 0)),
    ("b", (6, 11, 0)),
    ("cis", (0, 1, 0)),
    ("CIS", (0, 1, 0)),
    ("ces", (0, 11, 0)),
    ("cisis", (0, 2, 0)),
    ("ceses", (0, 10, 0)),
    ("gis", (4, 8, 0)),
    ("ges", (4, 6, 0)),
    ("fisis", (3, 7, 0)),
    ("beses", (6, 9, 0)),
])
def test_ly_default_octave(s, expected):
    assert TonalVector.from_ly(s) == TonalVector(expected)


### Absolute octave marks: ' raises an octave, , lowers an octave ###

@pytest.mark.parametrize("s, expected", [
    ("c'", (0, 0, 1)),
    ("c,", (0, 0, -1)),
    ("g'", (4, 7, 1)),
    ("g,", (4, 7, -1)),
    ("cis'", (0, 1, 1)),
    ("des,", (1, 1, -1)),
    ("c''", (0, 0, 2)),
    ("c,,", (0, 0, -2)),
    ("dis''''", (1, 3, 4)),
    ("dis,,,,", (1, 3, -4)),
])
def test_ly_absolute_octave_marks(s, expected):
    assert TonalVector.from_ly(s) == TonalVector(expected)


### Relative octave, resolved against prev_note ###
# Lilypond's relative-octave convention: an unmarked note is placed in
# whichever octave puts it within a tritone (<= a fourth by letter-name
# distance) of the previous note; ' and , then shift that by an additional
# octave in either direction.

@pytest.mark.parametrize("s, prev, expected", [
    ("c", (0, 0, 0), (0, 0, 0)),
    ("f", (0, 0, 0), (3, 5, 0)),
    ("g", (0, 0, 0), (4, 7, -1)),
    ("g'", (0, 0, 0), (4, 7, 0)),
    ("d", (0, 0, 0), (1, 2, 0)),
    ("b", (4, 7, 0), (6, 11, 0)),
    ("c", (4, 7, 0), (0, 0, 1)),
    ("c,", (4, 7, 0), (0, 0, 0)),
])
def test_ly_relative_octave(s, prev, expected):
    prev_note = TonalVector(prev)
    assert TonalVector.from_ly(s, prev_note=prev_note) == TonalVector(expected)


### Invalid input should raise, not silently guess ###

@pytest.mark.parametrize("s", [
    "",
    "h",       # not a valid Lilypond letter name
    "c#",      # ASCII accidentals are not Lilypond syntax
    "cx",
    "banana",
])
def test_invalid_ly_strings_raise(s):
    with pytest.raises(ValueError):
        TonalVector.from_ly(s)
