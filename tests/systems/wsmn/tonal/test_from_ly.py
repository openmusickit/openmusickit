"""Tests for TonalVector.from_ly.

from_ly() parses Lilypond-style pitch names ("is"/"es" accidentals,
"'"/"," absolute octave marks, or an octave resolved relative to a
`prev_note`). Unlike from_string, the result is always octave-qualified,
since Lilypond has no notion of an abstract (octave-less) pitch.
"""

import pytest

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector

# --- No octave mark, no prev_note: defaults to Lilypond's default octave (0) ---


@pytest.mark.parametrize(
    "s, expected",
    [
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
    ],
)
def test_ly_default_octave(s, expected):
    assert TonalVector.from_ly(s) == TonalVector(expected)


# --- Dutch contractions: Lilypond accepts "as" for "aes" and "es" for "ees" ---
# (and likewise "ases"/"eses" for the double flats), alongside the long forms.


@pytest.mark.parametrize(
    "s, expected",
    [
        ("as", (5, 8, 0)),
        ("aes", (5, 8, 0)),
        ("es", (2, 3, 0)),
        ("ees", (2, 3, 0)),
        ("ases", (5, 7, 0)),
        ("aeses", (5, 7, 0)),
        ("eses", (2, 2, 0)),
        ("eeses", (2, 2, 0)),
        ("as'", (5, 8, 1)),
        ("es,", (2, 3, -1)),
    ],
)
def test_ly_dutch_contractions(s, expected):
    assert TonalVector.from_ly(s) == TonalVector(expected)


# --- Absolute octave marks: ' raises an octave, , lowers an octave ---


@pytest.mark.parametrize(
    "s, expected",
    [
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
    ],
)
def test_ly_absolute_octave_marks(s, expected):
    assert TonalVector.from_ly(s) == TonalVector(expected)


# --- Relative octave, resolved against prev_note ---
# Lilypond's relative-octave convention: an unmarked note is placed in
# whichever octave puts its letter name within a fourth of the previous
# note's letter name (accidentals are ignored); ' and , then shift that by
# an additional octave in either direction.


@pytest.mark.parametrize(
    "s, prev, expected",
    [
        ("c", (0, 0, 0), (0, 0, 0)),
        ("f", (0, 0, 0), (3, 5, 0)),
        ("g", (0, 0, 0), (4, 7, -1)),
        ("g'", (0, 0, 0), (4, 7, 0)),
        ("d", (0, 0, 0), (1, 2, 0)),
        ("b", (4, 7, 0), (6, 11, 0)),
        ("c", (4, 7, 0), (0, 0, 1)),
        ("c,", (4, 7, 0), (0, 0, 0)),
    ],
)
def test_ly_relative_octave(s, prev, expected):
    prev_note = TonalVector(prev)
    assert TonalVector.from_ly(s, prev_note=prev_note) == TonalVector(expected)


# --- Relative octave ignores accidentals ---
# Per the Lilypond docs, the interval to the previous note "is determined
# without considering accidentals": after C, F-sharp is a fourth (placed
# above) and G-flat is a fifth (placed below), even though both are a
# tritone away; "a double-augmented fourth is considered a smaller interval
# than a double-diminished fifth".


@pytest.mark.parametrize(
    "s, prev, expected",
    [
        ("fis", (0, 0, 0), (3, 6, 0)),
        ("ges", (0, 0, 0), (4, 6, -1)),
        ("fisis", (0, 0, 0), (3, 7, 0)),
        ("geses", (0, 0, 0), (4, 5, -1)),
        ("eisis", (6, 11, 0), (2, 6, 1)),  # E double-sharp after B goes up (a fourth)
        ("feses", (6, 11, 0), (3, 3, 0)),  # F double-flat after B goes down (a fifth)
    ],
)
def test_ly_relative_octave_ignores_accidentals(s, prev, expected):
    prev_note = TonalVector(prev)
    assert TonalVector.from_ly(s, prev_note=prev_note) == TonalVector(expected)


# --- Invalid input should raise, not silently guess ---


@pytest.mark.parametrize(
    "s",
    [
        "",
        "h",  # not a valid Lilypond letter name
        "c#",  # ASCII accidentals are not Lilypond syntax
        "cx",
        "banana",
    ],
)
def test_invalid_ly_strings_raise(s):
    with pytest.raises(ValueError):
        TonalVector.from_ly(s)


# ===========================================================================
# Generated coverage: every octave-qualified vector as `prev_note` against
# every Lilypond note name (up to double sharps and flats, contractions
# included), with the relative-octave rule computed independently.
# ===========================================================================

from openmusickit.systems.wsmn.tonal.constants import ACCIDENTALS, DIATONES  # noqa: E402
from tests.domains import ABSTRACT_VECTORS, QUALIFIED_VECTORS  # noqa: E402


def _ly_names() -> list[tuple[str, int, int]]:
    """(name, d, c) for every Lilypond spelling of the 35 pitch classes:
    the letter plus `is`/`es` suffixes, and the Dutch contractions `as`,
    `ases`, `es`, `eses` for the flattened a and e."""
    names = []
    for diatone in DIATONES:
        for offset, accidental in ACCIDENTALS.items():
            if abs(offset) > 2:
                continue
            c = (diatone.chromatic + offset) % 12
            names.append((diatone.letter + accidental.ly, diatone.degree, c))
            if diatone.letter in "ae" and offset < 0:
                names.append((diatone.letter + accidental.ly[1:], diatone.degree, c))
    return names


def _letter_position(d: int, octave: int) -> int:
    return d + 7 * octave


def test_relative_octave_puts_every_note_within_a_fourth_of_every_previous_note():
    """Lilypond's rule, stated independently: of the three octaves around
    the previous note, exactly one puts the new letter within three letter
    names of the previous letter, accidentals ignored; `'` and `,` then
    shift by whole octaves from there."""
    names = _ly_names()
    assert len(names) == 35 + 4
    for prev in QUALIFIED_VECTORS:
        for name, d, c in names:
            candidates = [
                octave
                for octave in (prev.o - 1, prev.o, prev.o + 1)
                if abs(_letter_position(d, octave) - _letter_position(prev.d, prev.o)) <= 3
            ]
            assert len(candidates) == 1, (prev, name)
            for marks, shift in (("", 0), ("'", 1), (",", -1), ("''", 2), (",,", -2)):
                expected = TonalVector((d, c, candidates[0] + shift))
                assert TonalVector.from_ly(name + marks, prev_note=prev) == expected, (
                    name + marks,
                    prev,
                )


def test_absolute_octave_marks_for_every_name():
    for name, d, c in _ly_names():
        for marks, octave in (("", 0), ("'", 1), (",", -1), ("'''", 3), (",,,", -3)):
            assert TonalVector.from_ly(name + marks) == TonalVector((d, c, octave)), name + marks
            assert TonalVector.from_ly(f"  {name.upper()}{marks} ") == TonalVector((d, c, octave))


def test_prev_note_must_be_octave_qualified():
    for prev in ABSTRACT_VECTORS:
        with pytest.raises(ValueError):
            TonalVector.from_ly("c", prev_note=prev)


@pytest.mark.parametrize(
    "s",
    [
        "cisisisisis",  # five sharps: beyond the accidental table
        "ceseseseses",
        "cises",  # sharps and flats cannot mix
        "cis'',",  # up and down marks cannot mix
        "c#", "c♯", "csharp",  # not Lilypond syntax
        "h", "s", "",
    ],
)  # fmt: skip
def test_ly_grammar_edge_rejections(s):
    with pytest.raises(ValueError):
        TonalVector.from_ly(s)
