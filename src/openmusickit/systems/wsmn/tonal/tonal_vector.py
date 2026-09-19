from __future__ import annotations

import re
from enum import StrEnum, auto

from openmusickit.systems.wsmn.tonal import interval_quality as iq
from openmusickit.systems.wsmn.tonal import tonal_arithmetic as ta
from openmusickit.systems.wsmn.tonal.constants import (
    ACCIDENTALS,
    C_LEN,
    D_LEN,
    DIATONES,
    EURO_SF,
    Accidental,
    Diatone,
    QualityType,
    SolfegeStyle,
)
from openmusickit.utils.number_names import ORDINALS
from openmusickit.values.tone.interval import Interval, IntervalRepresentation
from openmusickit.values.tone.tone import PitchRepresentation, Tone

### Vocabulary and grammar for TonalVector.from_string / from_ly ###
#
# from_string strips all whitespace from its input, then matches it against
# regular expressions built from the lookup tables below. The tables are the
# single place where accepted spellings live; the patterns just glue them
# together.


class TonalDirection(StrEnum):
    """Direction for transposition or inversion of a TonalVector."""

    UP = auto()
    DOWN = auto()


def _alternation(spellings) -> str:
    """A regex alternation matching any one of the given literal spellings,
    longest first (so 'sol' is tried before 'so', and '##' before '#')."""
    return "|".join(re.escape(s) for s in sorted(spellings, key=len, reverse=True))


## Pitches ##

_LETTERS = {diatone.letter: diatone.degree for diatone in DIATONES}  # 'c' -> 0, 'd' -> 1, ...


def _pitch_names(solfege_style: SolfegeStyle) -> dict[str, tuple[int, int]]:
    """Maps every name a pitch string may begin with (a letter name or a
    solfege syllable, lowercase) to (d, half-steps above the natural).

    Letter names and EURO_FIXED syllables are always natural -- any
    accidental is spelled separately, after the name. OMK_MOVEABLE
    syllables carry their own chromatic alteration (e.g. 'di' is do-sharp).
    """
    names = {letter: (d, 0) for letter, d in _LETTERS.items()}
    if solfege_style == SolfegeStyle.EURO_FIXED:
        names.update({syllable: (d, 0) for d, syllable in EURO_SF.items()})
        names.update({"so": (4, 0), "ti": (6, 0)})  # common alternates for 'sol' and 'si'
    if solfege_style == SolfegeStyle.OMK_MOVEABLE:
        for diatone in DIATONES:
            names.update(
                {syllable: (diatone.degree, offset) for offset, syllable in diatone.solfege.items()}
            )
    return names


_PITCH_NAMES = {style: _pitch_names(style) for style in SolfegeStyle}


def _accidental_spellings() -> dict[str, int]:
    """Maps every accidental spelling from_string accepts -- ASCII ('#', 'bb'),
    Unicode ('♯', '𝄫'), and spelled out ('sharp', 'doubleflat') -- to its
    offset in half-steps. Spelled-out forms are stored without spaces,
    since from_string strips all whitespace before matching."""
    spellings = {}
    for offset, accidental in ACCIDENTALS.items():
        for spelling in (accidental.ascii, accidental.unicode, accidental.name.replace(" ", "")):
            if spelling:  # a natural has no ASCII spelling
                spellings[spelling] = offset
    return spellings


_ACCIDENTALS = _accidental_spellings()

# e.g. "c", "g#", "c𝄪", "csharp", "do-sharp", "bb3", "g-1"
_PITCH_PATTERNS = {
    style: re.compile(
        rf"""
        (?P<name>{_alternation(names)})
        (?:-?(?P<accidental>{_alternation(_ACCIDENTALS)}))?
        (?P<octave>-?\d+)?
    """,
        re.VERBOSE,
    )
    for style, names in _PITCH_NAMES.items()
}

# Lilypond note names, e.g. "c", "cis", "beses", "c'", "des,,"
_LY_PITCH_PATTERN = re.compile(
    r"""
    (?P<letter>[a-g])
    (?P<accidental>(?:is)*|(?:es)*)    # each 'is' raises a half-step, each 'es' lowers one
    (?P<octave_marks>'*|,*)            # each ' raises an octave, each , lowers one
""",
    re.VERBOSE,
)

# Lilypond also accepts the Dutch contractions 'as' for 'aes' and 'es' for
# 'ees' (and so 'ases' for 'aeses', 'eses' for 'eeses').
_LY_CONTRACTION = re.compile(r"^([ae])s")


def _ly_pitch_match(text: str) -> re.Match | None:
    """Matches a (lowercase) Lilypond note name, contractions included."""
    return _LY_PITCH_PATTERN.fullmatch(_LY_CONTRACTION.sub(r"\1es", text))


def _ly_relative_octave(d: int, prev: tuple) -> int:
    """The octave Lilypond's \\relative mode gives to letter name d when it
    follows prev: whichever octave puts it within a fourth (three letter
    names) of prev, above or below. As in Lilypond, accidentals play no part."""
    steps = (d - prev[0] + 3) % D_LEN - 3  # letter-name steps from prev, -3..3
    return (prev[2] * D_LEN + prev[0] + steps) // D_LEN


def _ly_octave_marks(octaves: int) -> str:
    """Lilypond octave marks for a signed octave distance: ' per octave up, , per octave down."""
    return ("'" if octaves >= 0 else ",") * abs(octaves)


def _pitch_from_match(m: re.Match, names: dict, mid_c: int) -> tuple:
    """(d, c[, o]) for a string matched by one of the _PITCH_PATTERNS."""
    d, chromatic_offset = names[m["name"]]
    if m["accidental"]:
        chromatic_offset += _ACCIDENTALS[m["accidental"]]
    c = (DIATONES[d].chromatic + chromatic_offset) % C_LEN

    if m["octave"] is None:
        return (d, c)
    return (d, c, int(m["octave"]) - mid_c)


## Intervals ##

# Quality words, mapped to a canonical kind. Bare 'M' (major) and bare 'm'
# (minor) are the only case-sensitive spellings; see _quality_kind.
_QUALITY_KINDS = {
    "p": "perfect",
    "per": "perfect",
    "perfect": "perfect",
    "M": "major",
    "maj": "major",
    "major": "major",
    "m": "minor",
    "min": "minor",
    "minor": "minor",
    "aug": "augmented",
    "augmented": "augmented",
    "dim": "diminished",
    "diminished": "diminished",
}

# Prefixes for multiply augmented/diminished intervals, mapped to how many
# times. The three-letter forms are what IntervalQuality.abbr produces.
_QUALITY_MULTIPLIERS = {
    "dbl": 2,
    "double": 2,
    "trp": 3,
    "trpl": 3,
    "triple": 3,
    "qua": 4,
    "quad": 4,
    "quadruple": 4,
}

_NUMBER_WORDS = {
    diatone.interval_name: diatone.degree + 1 for diatone in DIATONES
}  # 'unison' -> 1, 'second' -> 2, ...

# e.g. "P5", "m3", "aug4", "dbldim5", "perfectfifth", "M9th", "aug4+1"
_INTERVAL_PATTERN = re.compile(
    rf"""
    (?P<multiplier>{_alternation(_QUALITY_MULTIPLIERS)})?
    (?P<quality>{_alternation({k.lower() for k in _QUALITY_KINDS})})
    (?:
        (?P<number>\d+)(?P<ordinal>st|nd|rd|th)?
      | (?P<number_word>{_alternation(_NUMBER_WORDS)})
    )
    (?P<octave>[+-]\d+)?    # octave suffix as in IntervalQuality.abbr, e.g. "aug4+1"
""",
    re.VERBOSE | re.IGNORECASE,
)


def _quality_kind(word: str) -> str:
    """The canonical quality kind for a quality word matched by _INTERVAL_PATTERN."""
    if word in ("M", "m"):  # the one case-sensitive spelling
        return _QUALITY_KINDS[word]
    return _QUALITY_KINDS[word.lower()]


def _interval_quality(kind: str, times: int, d: int) -> iq.IntervalQuality:
    """The IntervalQuality named by a quality kind, for diatonic degree d.
    `times` is how many times augmented or diminished (1 = augmented,
    2 = double augmented); it is meaningless for perfect, major and minor.

    Unisons, 4ths and 5ths (and their compounds) are perfect-type, so they
    can't be major or minor. 2nds, 3rds, 6ths and 7ths (and their
    compounds) are major/minor-type, so they can't be perfect.
    """
    degree = DIATONES[d]
    is_perfect_type = degree.quality_type == QualityType.P
    if kind == "perfect" and not is_perfect_type:
        raise ValueError(
            f"A {degree.interval_name} cannot be perfect (only major, minor, augmented or diminished)."
        )
    if kind in ("major", "minor") and is_perfect_type:
        raise ValueError(
            f"A {degree.interval_name} cannot be {kind} (only perfect, augmented or diminished)."
        )

    # IntervalQuality is keyed by a "relative number": 0 for perfect,
    # +0.5/-0.5 for major/minor, and each augmentation or diminution moves
    # a further 1 away from there.
    base = degree.quality_type.value
    if kind == "perfect":
        rel_number = 0
    elif kind == "major":
        rel_number = base
    elif kind == "minor":
        rel_number = -base
    elif kind == "augmented":
        rel_number = base + times
    else:  # diminished
        rel_number = -base - times

    try:
        return iq._get_quality(rel_number)
    except KeyError:
        raise ValueError(
            f"{times} times {kind} is beyond the supported range of interval qualities."
        ) from None


def _interval_from_match(m: re.Match) -> tuple:
    """(d, c[, o]) for a string matched by _INTERVAL_PATTERN."""
    kind = _quality_kind(m["quality"])
    times = _QUALITY_MULTIPLIERS[m["multiplier"].lower()] if m["multiplier"] else 1
    if times > 1 and kind not in ("augmented", "diminished"):
        raise ValueError(f"'{m['multiplier']}' only applies to augmented or diminished intervals.")

    if m["number"]:
        number = int(m["number"])
    else:
        number = _NUMBER_WORDS[m["number_word"].lower()]
    if not 1 <= number < len(ORDINALS):
        raise ValueError(f"Interval numbers must be between 1 and {len(ORDINALS) - 1}.")
    if m["ordinal"] and ORDINALS[number] != m["number"] + m["ordinal"].lower():
        raise ValueError(
            f"'{m['number']}{m['ordinal']}' is not a valid ordinal (expected '{ORDINALS[number]}')."
        )

    # Numbers above 7 are compound: a 9th is a 2nd plus an octave.
    d, octave = (number - 1) % D_LEN, (number - 1) // D_LEN
    c = (DIATONES[d].chromatic + _interval_quality(kind, times, d).chromatic_modifier) % C_LEN

    if m["octave"]:
        octave += int(m["octave"])
    if number > D_LEN or m["octave"]:
        return (d, c, octave)
    return (d, c)


class TonalVector(tuple, Tone, Interval):
    """A tuple of form (d_iatonic, c_hromatic, (o_ctave)),
    representing either a pitch or interval (or both).
    TonalVector implements tonal arithmetic with __dunder__ methods,
    allowing use of standard operators (+, -, =, <, >).

    TonalVector is the WSMN implementation of both Tone and Interval:

    >>> isinstance(TonalVector((0, 0)), Tone)
    True
    >>> isinstance(TonalVector((0, 0)), Interval)
    True
    """

    _cache = {}

    def __new__(cls, *args):
        """TonalVector is immutable and interned.

        >>> TonalVector((0,0)) is TonalVector(0,0)
        True

        >>> TonalVector((0,0)).d = 1
        Traceback (most recent call last):
        ...
        AttributeError: ...

        The canonical way to create a TonalVector is to pass in a tuple:

        >>> TonalVector((0, 0, 0))
        TonalVector((0, 0, 0))

        For convenience, you can also pass in positional arguments:

        >>> TonalVector(0, 0, 0)
        TonalVector((0, 0, 0))
        """
        # Normalize input: if already a tuple/list, leave it
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            key = tuple(args[0])
        else:
            key = tuple(args)

        if key in cls._cache:
            return cls._cache[key]

        self = super().__new__(cls, key)
        cls._cache[key] = self
        return self

    def __init__(self, *args):
        """
        Examples
        --------

        >>> TonalVector(0,0) == TonalVector((0,0))
        True

        >>> TonalVector(0,0,0) == TonalVector((0,0,0,))
        True

        >>> TonalVector(0,0) is TonalVector((0,0))
        True
        """

        if hasattr(self, "_initialized"):
            return

        """
        self.d = self[0] # diatonic value
        self.c = self[1] # chromatic value

        self._diatone = DIATONES[self.d] # Q for source # rename?

        # if a third value (octave) supplied
        try:
            self.o = self[2]
            self.has_octave = True
        except IndexError:
            self.o = None
            self.has_octave = False
        """

        self._pitch = self._PitchRepresentation(self)
        self._interval = self._IntervalRepresentation(self)

        self._initialized = True

    ## Basic property interface

    @property
    def pitch(self) -> TonalVector._PitchRepresentation:
        """This TonalVector as a pitch (letter name, accidental, octave, ...).

        >>> TonalVector((0, 0)).pitch.unicode
        'C'
        """
        return self._pitch

    @property
    def interval(self) -> TonalVector._IntervalRepresentation:
        """This TonalVector as an interval (quality, number, ...).

        >>> TonalVector((4, 7)).interval.unicode
        'perfect 5'
        """
        return self._interval

    @property
    def d(self) -> int:
        return self[0]

    @property
    def c(self) -> int:
        return self[1]

    @property
    def o(self) -> int:
        try:
            return self[2]
        except IndexError:
            raise AttributeError("This TonalVector does not have an octave designation.") from None

    @property
    def _diatone(self) -> Diatone:
        return DIATONES[self.d]

    @property
    def has_octave(self) -> bool:
        """True if this TonalVector carries an octave designation.

        >>> TonalVector((0, 0)).has_octave, TonalVector((0, 0, 0)).has_octave
        (False, True)
        """
        return len(self) == 3

    @property
    def fifths_position(self) -> int:
        """The position of this TonalVector on the circle (line) of fifths,
        with C (or a perfect unison) at 0.

        Each natural letter sits 2 fifths from the last (F=-1, C=0, G=1, D=2, A=3, E=4, B=5),
        and each sharp adds 7 while each flat subtracts 7. The line does not wrap:
        B♯ is 12, not 0, since the spelling matters.

        Read as a pitch, this is the `fifths` of the major key on that tonic
        (see `KeySignature.fifths`).
        Read as an interval, it is how far a key signature moves around the circle
        when its tonic moves by this interval.

        Examples
        --------

        >>> TonalVector((0, 0)).fifths_position   # C
        0
        >>> TonalVector((4, 7)).fifths_position   # G / perfect 5
        1
        >>> TonalVector((3, 5)).fifths_position   # F / perfect 4
        -1
        >>> TonalVector((3, 6)).fifths_position   # F♯
        6
        >>> TonalVector((6, 10)).fifths_position  # B♭
        -2
        >>> TonalVector((0, 11)).fifths_position  # C♭
        -7
        >>> TonalVector((6, 0)).fifths_position   # B♯
        12
        >>> TonalVector((2, 4, 1)).fifths_position  # E, any octave
        4
        """
        return (2 * self.d + 1) % D_LEN - 1 + D_LEN * self.pitch.alteration

    @classmethod
    def from_string(
        cls, s: str, mid_c: int = 4, solfege_style: SolfegeStyle = SolfegeStyle.EURO_FIXED
    ) -> TonalVector:
        """Creates and returns a TonalVector,
        given a parsable string representation of a pitch or interval.

        Accepts letter names (A-G, case-insensitive) with ASCII, Unicode, or
        spelled-out accidentals; numeric octave designations (mid_c sets
        which octave number is treated as middle C); solfege syllables; and
        interval names (quality abbreviation or word, plus a number or
        ordinal). Lilypond-style spellings ("is"/"es" accidentals, "'"/","
        octave marks) are not accepted here -- use `from_ly` instead.

        Solfege syllables are ambiguous between two conventions, selected
        with `solfege_style`: EURO_FIXED (the default) treats each syllable
        as a fixed diatonic letter name with an optional separate accidental
        (e.g. "Si" = B, "Sol#" = G-sharp); OMK_MOVEABLE treats syllables as
        moveable-do, with dedicated chromatic syllables of their own (e.g.
        "Si" = so-sharp, "Di" = do-sharp).

        Examples
        --------

        >>> TonalVector.from_string('C')
        TonalVector((0, 0))

        >>> TonalVector.from_string('G#')
        TonalVector((4, 8))

        >>> TonalVector.from_string('Bb3')
        TonalVector((6, 10, -1))

        >>> TonalVector.from_string('perfect fifth')
        TonalVector((4, 7))

        >>> TonalVector.from_string('M9')
        TonalVector((1, 2, 1))

        """
        text = "".join(s.split())  # whitespace is never significant

        ly = _ly_pitch_match(text.lower())
        if ly and (ly["accidental"] or ly["octave_marks"]):
            raise ValueError(f"{s!r} is a Lilypond pitch name; use TonalVector.from_ly instead.")

        interval = _INTERVAL_PATTERN.fullmatch(text)
        if interval:
            return cls(_interval_from_match(interval))

        pitch = _PITCH_PATTERNS[solfege_style].fullmatch(text.lower())
        if pitch:
            return cls(_pitch_from_match(pitch, _PITCH_NAMES[solfege_style], mid_c))

        raise ValueError(f"{s!r} is not a recognized pitch or interval.")

    @classmethod
    def from_ly(cls, s: str, prev_note: tuple[int, ...] | None = None) -> TonalVector:
        """Creates and returns an octave-qualified TonalVector,
        given a Lilypond-style pitch string.

        Accepts Lilypond note names using "is"/"es" accidental suffixes
        (including the Dutch contractions "as"/"es" for "aes"/"ees"), and
        either absolute ("'"/",") or relative (resolved against `prev_note`)
        octave marks. Since Lilypond has no notion of an octave-less
        (abstract) pitch, the result is always octave-qualified -- with no
        octave mark and no `prev_note`, the pitch is assumed to be in
        Lilypond's default octave (OMK octave 0).

        Relative octaves follow Lilypond's \\relative rule: the note goes in
        whichever octave puts its letter name within a fourth of `prev_note`,
        ignoring accidentals, and any octave marks shift it from there.

        Examples
        --------

        >>> TonalVector.from_ly('cis')
        TonalVector((0, 1, 0))

        >>> TonalVector.from_ly("g'")
        TonalVector((4, 7, 1))

        >>> TonalVector.from_ly("g", prev_note=TonalVector((0, 0, 0)))
        TonalVector((4, 7, -1))

        >>> TonalVector.from_ly("as")
        TonalVector((5, 8, 0))

        """
        m = _ly_pitch_match(s.strip().lower())
        if not m:
            raise ValueError(f"{s!r} is not a Lilypond pitch name.")

        d = _LETTERS[m["letter"]]
        accidental = m["accidental"].count("is") - m["accidental"].count("es")
        if accidental not in ACCIDENTALS:
            raise ValueError(f"{s!r} has more sharps or flats than are supported.")
        c = (DIATONES[d].chromatic + accidental) % C_LEN

        if prev_note is None:
            octave = 0  # Lilypond's default octave is OMK's octave 0
        else:
            prev_note = cls(prev_note)
            if not prev_note.has_octave:
                raise ValueError("prev_note must be octave-qualified.")
            octave = _ly_relative_octave(d, prev_note)

        octave_shift = m["octave_marks"].count("'") - m["octave_marks"].count(",")
        return cls((d, c, octave + octave_shift))

    ### Util ###

    def __repr__(self) -> str:
        """
        >>> TonalVector((0,0))
        TonalVector((0, 0))

        >>> TonalVector((2,4,1))
        TonalVector((2, 4, 1))
        """
        return f"{type(self).__name__}({tuple(self)!r})"

    def __str__(self) -> str:
        """Returns a string that includes the __repr__ string,
        along with human readable pitch and interval annotations
        in a Python-style inline comment.

        This is a debug form. Note that f-strings and `str.format` do *not*
        use it: they go through `Tone.__format__`, which gives the display
        form (`pitch.unicode` by default).

        Examples
        --------

        >>> print(TonalVector((0,1)))
        TonalVector((0, 1)) # C♯
        >>> f"{TonalVector((0,1))}"
        'C♯'

        >>> print(TonalVector((2,3,1)))
        TonalVector((2, 3, 1)) # E♭5
        """
        return f"{repr(self)} # {self.pitch.unicode}"

    ### Tonal Arithmetic ###

    def __add__(self, x: tuple[int, ...]) -> TonalVector:
        """

        Examples
        --------

        >>> TonalVector((0,1)) + TonalVector((1,1))
        TonalVector((1, 2))

        >>> TonalVector((6,11,1)) + TonalVector((1,1))
        TonalVector((0, 0, 2))

        """
        return TonalVector(ta.tonal_sum(self, x))

    def __sub__(self, x: tuple[int, ...]) -> TonalVector:
        """

        Examples
        --------

        >>> TonalVector((0,1)) - TonalVector((1,1))
        TonalVector((6, 0))

        >>> TonalVector((6,11,1)) - TonalVector((1,1))
        TonalVector((5, 10, 1))

        >>> abs(TonalVector((6,11,1)) - TonalVector((1,1,0))) == abs(TonalVector((1,1,0)) - TonalVector((6,11,1)))
        True
        """
        return TonalVector(ta.tonal_diff(self, x))

    def distance(self, x: tuple[int, ...]) -> TonalVector:
        """Returns the smallest difference

        Examples
        --------

        >>> TonalVector((0,0,0)).distance(TonalVector((4,7,0)))
        TonalVector((4, 7, 0))

        >>> TonalVector((4,7,0)).distance(TonalVector((0,0,0)))
        TonalVector((4, 7, 0))

        >>> TonalVector((0,0)).distance(TonalVector((4,7)))
        TonalVector((3, 5))
        """
        return TonalVector(ta.tonal_abs_diff(self, x))

    def nearest_instance(self, x: tuple[int, ...]) -> TonalVector:
        """Returns a Tonal Vector that has the same pitch class or interval type as x,
        closest to self.

        Examples
        --------

        >>> TonalVector((0,0)).nearest_instance(TonalVector((1,1,-3)))
        TonalVector((1, 1))

        >>> TonalVector((0,0)).nearest_instance(TonalVector((6,11,3)))
        TonalVector((6, 11))

        >>> TonalVector((0,0,0)).nearest_instance(TonalVector((1,1,-3)))
        TonalVector((1, 1, 0))

        >>> TonalVector((0,0,0)).nearest_instance(TonalVector((6,11,3)))
        TonalVector((6, 11, -1))
        """

        return TonalVector(ta.tonal_nearest_instance(self, x))

    def __abs__(self) -> int:
        """Returns the distance, in half-steps, from self to the origin.

        Examples
        --------

        >>> abs(TonalVector((0,0,-1)))
        12

        >>> abs(TonalVector((0,0,1)))
        12
        """
        return ta.tonal_abs(self)

    def __int__(self) -> int:
        """Returns the signed distance, in half-steps, from self to the origin.

        Examples
        --------

        >>> int(TonalVector((0,0,-1)))
        -12

        >>> int(TonalVector((0,0,1)))
        12
        """
        return ta.tonal_int(self)

    def __gt__(self, x: tuple[int, ...]) -> bool:
        """Returns True if self is higher (in pitch)
        or larger (in interval size) than x,
        otherwise False.

        Examples
        --------

        >>> TonalVector((1,1,0)) > TonalVector((0,0,0))
        True

        >>> TonalVector((2,4,1)) > (3,5,1)
        False

        >>> TonalVector((3,6,1)) > 6
        True
        """
        try:
            return int(self) > int(x)
        except TypeError:
            return int(self) > ta.tonal_int(x)

    def __lt__(self, x: tuple[int, ...]) -> bool:
        """Returns True if self is lower (in pitch)
        or smaller (in interval size) than x,
        otherwise False.

        Examples
        --------

        >>> TonalVector((1,1,0)) < TonalVector((0,0,0))
        False

        >>> TonalVector((2,4,1)) < (3,5,1)
        True

        >>> TonalVector((3,6,1)) < 6
        False
        """
        try:
            return int(self) < int(x)
        except TypeError:
            return int(self) < ta.tonal_int(x)

    def transpose(
        self, x: tuple[int, ...], direction: TonalDirection = TonalDirection.UP
    ) -> TonalVector:
        """Returns a TonalVector transposed by x, in the given direction.

        Examples
        --------

        >>> TonalVector((0,0)).transpose(TonalVector((1,1)))
        TonalVector((1, 1))
        """
        if direction == TonalDirection.UP:
            return self + x
        elif direction == TonalDirection.DOWN:
            return self - x
        else:
            raise ValueError(f"Invalid TonalDirection: {direction}.")

    def inversion(self, x: tuple[int, ...] = (0, 0)) -> TonalVector:
        """Returns the inversion of self over x.

        When x is unspecified, returns the inversion of self over the origin,
        which is equivalent to the standard definition of inverting an interval.

        Examples
        --------

        >>> TonalVector((2,4)).inversion() # Maj3 --> min6
        TonalVector((5, 8))

        >>> TonalVector((5,8)).inversion() # min6 --> Maj3
        TonalVector((2, 4))

        >>> TonalVector((3,6)).inversion() # Aug4 --> dim5 (tritone)
        TonalVector((4, 6))

        >>> TonalVector((0,1,0)).inversion((0,0,0)) # augment unison --> diminished octave
        TonalVector((0, 11, 0))
        """
        return TonalVector(ta.tonal_invert(self, x))

    def __eq__(self, x) -> bool:
        """Returns True if self and x are the same (d, c, [o]) values.
        Can compare with TonalVectors and plain (d, c, [o]) tuples.

        Enharmonic equivalents are not equal (C♯ is not D♭); compare
        half-step values with `int()` for that.

        Examples
        --------

        >>> TonalVector((0,1,0)) == (0,1,0)
        True

        >>> TonalVector((0,1)) == TonalVector((1,1))
        False

        >>> TonalVector((0,1)) == 1
        False

        >>> int(TonalVector((0,1))) == int(TonalVector((1,1)))
        True
        """
        if isinstance(x, tuple):
            return tuple(self) == tuple(x)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(self))

    def __call__(self, other):
        if isinstance(other, TonalVector):
            return self + other
        try:
            return other(self)
        except TypeError as e:
            raise TypeError(f"'{type(other)}' does not have a call handler for TonalVector") from e

    def qualify_octave(self, oct: int = 0) -> TonalVector:
        """Returns a TonalVector with an octave designation set to `oct`.

        Example
        -------

        >>> TonalVector((1, 2)).qualify_octave()
        TonalVector((1, 2, 0))

        >>> TonalVector((3, 4)).qualify_octave(2)
        TonalVector((3, 4, 2))

        >>> TonalVector((1, 2, 1)).qualify_octave()
        TonalVector((1, 2, 0))

        >>> TonalVector((3, 4, -1)).qualify_octave(2)
        TonalVector((3, 4, 2))

        """
        return TonalVector((self.d, self.c, oct))

    def conditional_qualify_octave(self, oct: int = 0) -> TonalVector:
        """Returns a TonalVector with an octave designation set to `oct`,
        but does not change an existing octave designation if present."""
        if self.has_octave:
            return self
        return TonalVector((self.d, self.c, oct))

    def unqualify_octave(self) -> TonalVector:
        """Returns a TonalVector without an octave designation.

        Example
        -------

        >>> TonalVector.unqualify_octave(TonalVector((1, 2, 3)))
        TonalVector((1, 2))
        """

        return TonalVector((self.d, self.c))

    ### Represent as a pitch ###

    class _PitchRepresentation(PitchRepresentation):
        """A TonalVector's pitch representation,
        which holds relevant details such as letter name, accidental, etc.

        Strings meant for people (`unicode`, `ascii`, `verbose`) number octaves
        with middle C as C4, the common convention; the `*_at(mid_c)` methods let a
        caller pick another (C3 on some older MIDI gear, or 0 to see OMK's internal
        octave). Internally a TonalVector always keeps middle C at octave 0.

        Example
        -------

        >>> type(TonalVector((0,0)).pitch)
        <class 'openmusickit.systems.wsmn.tonal.tonal_vector.TonalVector._PitchRepresentation'>
        """

        def __init__(self, vector: TonalVector):
            self._v = vector

        @property
        def letter(self) -> str:
            """The letter name (without sharps or flats) of the pitch.

            Examples
            --------

            >>> TonalVector((0,0)).pitch.letter
            'C'

            >>> TonalVector((0,1)).pitch.letter
            'C'
            """
            return self._v._diatone.letter.upper()

        @property
        def alteration(self) -> int:
            """The distance in half steps between the named pitch
            and the natural version of the named pitch.

            >>> TonalVector((0,0)).pitch.alteration # C natural
            0

            >>> TonalVector((0,1)).pitch.alteration # C sharp
            1

            >>> TonalVector((0, 11)).pitch.alteration # C flat
            -1

            >>> TonalVector((4,6,1)).pitch.alteration # G flat
            -1

            >>> TonalVector((6,0)).pitch.alteration # B sharp
            1
            """
            natural = self._v._diatone.chromatic
            modifier = self._v.c - natural

            # correct for octave-break cases (C flat, B sharp)
            if abs(modifier) > 4:  # 4 = triple aug or triple dim
                if self._v.c < natural:
                    natural -= C_LEN
                else:
                    natural += C_LEN
                modifier = self._v.c - natural

            return modifier

        @property
        def accidental(self) -> Accidental:
            """The Accidental (sharp, flat, natural, ...) with its spellings.

            >>> TonalVector((0,0)).pitch.accidental
            Accidental(offset=0, name='natural', unicode='♮', ascii='', ly='')

            >>> TonalVector((0,0)).pitch.accidental.name
            'natural'
            """
            return ACCIDENTALS[self.alteration]

        def _spell(self, accidental: str, mid_c: int) -> str:
            """Letter, then `accidental` if altered, then the octave number if qualified."""
            text = self.letter
            if self.alteration:
                text += accidental
            if self._v.has_octave:
                text += str(self._v.o + mid_c)
            return text

        def unicode_at(self, mid_c: int = 4) -> str:
            """The pitch with Unicode accidentals (♯, ♭), numbering octaves so that
            middle C is C<mid_c>.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode_at()
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode_at(3)
            'D♭3'

            >>> TonalVector((1,1,0)).pitch.unicode_at(0)
            'D♭0'
            """
            return self._spell(self.accidental.unicode, mid_c)

        @property
        def unicode(self) -> str:
            """The pitch with Unicode accidentals (♯, ♭); middle C is C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode
            'D♭4'
            """
            return self.unicode_at()

        def ascii_at(self, mid_c: int = 4) -> str:
            """The pitch with ASCII accidentals (#, b), numbering octaves so that
            middle C is C<mid_c>.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii_at()
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii_at(0)
            'Db0'
            """
            return self._spell(self.accidental.ascii, mid_c)

        @property
        def ascii(self) -> str:
            """The pitch with ASCII accidentals (#, b); middle C is C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii
            'Db4'
            """
            return self.ascii_at()

        def verbose_at(self, mid_c: int = 4) -> str:
            """The pitch with the accidental spelled out, numbering octaves so that
            middle C is C<mid_c>.

            >>> TonalVector((0,1,1)).pitch.verbose_at(0)
            'Csharp1'
            """
            return self._spell(self.accidental.name, mid_c)

        @property
        def verbose(self) -> str:
            """The pitch with the accidental spelled out; middle C is C4.

            >>> TonalVector((0,0)).pitch.verbose
            'C'

            >>> TonalVector((0,1)).pitch.verbose
            'Csharp'

            >>> TonalVector((0,1,1)).pitch.verbose
            'Csharp5'
            """
            return self.verbose_at()

        @property
        def ly(self) -> str:
            """The Lilypond representation of the pitch name,
            without an octave designation.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ly # C sharp
            'cis'

            >>> TonalVector((6,10,1)).pitch.ly # B flat; the octave is not shown
            'bes'
            """
            return f"{self.letter.lower()}{self.accidental.ly}"

        @property
        def ly_absolute(self) -> str:
            """The Lilypond representation of the pitch name,
            with an absolute octave designation.
            (see: http://lilypond.org/doc/v2.18/Documentation/learning/absolute-pitch-names)

            Examples
            --------

            >>> TonalVector((0,0,1)).pitch.ly_absolute # C above middle C
            "c'"

            >>> TonalVector((6,10,-1)).pitch.ly_absolute # B flat below middle C
            'bes,'

            >>> TonalVector((3,6,0)).pitch.ly_absolute # F sharp in octave of middle c
            'fis'

            >>> TonalVector((3,6)).pitch.ly_absolute # F sharp, no octave designation
            'fis'

            >>> TonalVector((1,1,4)).pitch.ly_absolute # D flat, 4 octaves above middle c
            "des''''"

            >>> TonalVector((1,1,-4)).pitch.ly_absolute # D flat, 4 octaves below middle c
            'des,,,,'
            """
            if not self._v.has_octave:
                return self.ly
            return self.ly + _ly_octave_marks(self._v.o)

        def ly_relative(self, prev: tuple[int, ...] | None = None) -> str:
            """The Lilypond representation of the pitch name,
            with a relative octave designation, based on the previous pitch.

            >>> TonalVector((3,5,0)).pitch.ly_relative(TonalVector((0,0,0)))
            'f'

            >>> TonalVector((4,7,0)).pitch.ly_relative(TonalVector((0,0,0)))
            "g'"

            >>> TonalVector((3,5,-1)).pitch.ly_relative(TonalVector((0,0,0)))
            'f,'

            >>> TonalVector((4,7,-1)).pitch.ly_relative(TonalVector((0,0,0)))
            'g'

            >>> TonalVector((0,0,2)).pitch.ly_relative(TonalVector((0,0,0)))
            "c''"

            Accidentals don't affect the octave: F-sharp is a fourth above C
            and G-flat a fifth above, so G-flat gets an octave mark.

            >>> TonalVector((3,6,0)).pitch.ly_relative(TonalVector((0,0,0)))
            'fis'

            >>> TonalVector((4,6,0)).pitch.ly_relative(TonalVector((0,0,0)))
            "ges'"
            """
            if prev is None:
                return self.ly_absolute
            return self.ly + _ly_octave_marks(self._v.o - _ly_relative_octave(self._v.d, prev))

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).pitch
            TonalVector((0, 0, 0)).pitch
            """
            return f"{self._v!r}.pitch"

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).pitch)
            'C4 | (0, 0, 0)'
            """
            return f"{self.unicode} | {tuple(self._v)}"

    class _IntervalRepresentation(IntervalRepresentation):
        def __init__(self, vector: TonalVector):
            """
            >>> TonalVector((0, 0)).interval._v
            TonalVector((0, 0))

            >>> TonalVector((1, 2)).interval.quality
            IntervalQuality("major", 0.5)

            >>> TonalVector((2, 3)).interval.number
            3
            """
            self._v = vector
            self.quality = iq._get_quality(vector)
            self.number = vector.d + 1

            # Signed octave suffix ("+0", "+1", "-2"); empty for abstract vectors.
            if vector.has_octave:
                self.o = f"{vector.o:+d}"
            else:
                self.o = ""

        @property
        def abbr(self) -> str:
            """Returns the abbreviated quality and interval number, followed
            by a signed octave suffix if the vector is octave-qualified.

            Examples
            --------

            >>> TonalVector((0,0)).interval.abbr
            'per1'

            >>> TonalVector((0,0,0)).interval.abbr
            'per1+0'

            >>> TonalVector((3, 6, 1)).interval.abbr
            'aug4+1'

            >>> TonalVector((5, 8, -2)).interval.abbr
            'min6-2'
            """

            return f"{self.quality.abbr}{self.number}{self.o}"

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).interval
            TonalVector((0, 0, 0)).interval
            """
            return f"{self._v!r}.interval"

        @property
        def unicode(self) -> str:
            """
            >>> TonalVector((0,0)).interval.unicode
            'perfect 1'

            >>> TonalVector((3,6)).interval.unicode
            'augmented 4'
            """
            return f"{self.quality} {self.number}"

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).interval)
            'perfect 1 | (0, 0, 0)'
            """
            return f"{self.unicode} | {tuple(self._v)}"
