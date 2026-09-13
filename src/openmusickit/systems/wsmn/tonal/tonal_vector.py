from __future__ import annotations

import re

from openmusickit.utils.number_names import ordinals
from openmusickit.values.tone.tone import TonalSystem, Tone, PitchRepresentation
from openmusickit.values.tone.interval import Interval, IntervalRepresentation
from .wsmn import WSMN
from . import tonal_arithmetic as ta
from . import interval_quality as iq
from .constants import D_LEN, C_LEN, MS, AC, EURO_SF, QualityType, Accidental, SolfegeStyle


### Vocabulary and grammar for TonalVector.from_string / from_ly ###
#
# from_string strips all whitespace from its input, then matches it against
# regular expressions built from the lookup tables below. The tables are the
# single place where accepted spellings live; the patterns just glue them
# together.

def _alternation(spellings) -> str:
    """A regex alternation matching any one of the given literal spellings,
    longest first (so 'sol' is tried before 'so', and '##' before '#')."""
    return "|".join(re.escape(s) for s in sorted(spellings, key=len, reverse=True))


## Pitches ##

_LETTERS = {diatone.ln: diatone.d for diatone in MS}   # 'c' -> 0, 'd' -> 1, ...


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
        names.update({'so': (4, 0), 'ti': (6, 0)})   # common alternates for 'sol' and 'si'
    if solfege_style == SolfegeStyle.OMK_MOVEABLE:
        for diatone in MS:
            names.update({syllable: (diatone.d, offset) for offset, syllable in diatone.sf.items()})
    return names

_PITCH_NAMES = {style: _pitch_names(style) for style in SolfegeStyle}


def _accidental_spellings() -> dict[str, int]:
    """Maps every accidental spelling from_string accepts -- ASCII ('#', 'bb'),
    Unicode ('♯', '𝄫'), and spelled out ('sharp', 'doubleflat') -- to its
    offset in half-steps. Spelled-out forms are stored without spaces,
    since from_string strips all whitespace before matching."""
    spellings = {}
    for offset, accidental in AC.items():
        for spelling in (accidental.a, accidental.u, accidental.v.replace(" ", "")):
            if spelling:   # a natural has no ASCII spelling
                spellings[spelling] = offset
    return spellings

_ACCIDENTALS = _accidental_spellings()

# e.g. "c", "g#", "c𝄪", "csharp", "do-sharp", "bb3", "g-1"
_PITCH_PATTERNS = {
    style: re.compile(rf"""
        (?P<name>{_alternation(names)})
        (?:-?(?P<accidental>{_alternation(_ACCIDENTALS)}))?
        (?P<octave>-?\d+)?
    """, re.VERBOSE)
    for style, names in _PITCH_NAMES.items()
}

# Lilypond note names, e.g. "c", "cis", "beses", "c'", "des,,"
_LY_PITCH_PATTERN = re.compile(r"""
    (?P<letter>[a-g])
    (?P<accidental>(?:is)*|(?:es)*)    # each 'is' raises a half-step, each 'es' lowers one
    (?P<octave_marks>'*|,*)            # each ' raises an octave, each , lowers one
""", re.VERBOSE)

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
    steps = (d - prev[0] + 3) % D_LEN - 3   # letter-name steps from prev, -3..3
    return (prev[2] * D_LEN + prev[0] + steps) // D_LEN


def _pitch_from_match(m: re.Match, names: dict, mid_c: int) -> tuple:
    """(d, c[, o]) for a string matched by one of the _PITCH_PATTERNS."""
    d, chromatic_offset = names[m['name']]
    if m['accidental']:
        chromatic_offset += _ACCIDENTALS[m['accidental']]
    c = (MS[d].c + chromatic_offset) % C_LEN

    if m['octave'] is None:
        return (d, c)
    return (d, c, int(m['octave']) - mid_c)


## Intervals ##

# Quality words, mapped to a canonical kind. Bare 'M' (major) and bare 'm'
# (minor) are the only case-sensitive spellings; see _quality_kind.
_QUALITY_KINDS = {
    'p': 'perfect', 'per': 'perfect', 'perfect': 'perfect',
    'M': 'major', 'maj': 'major', 'major': 'major',
    'm': 'minor', 'min': 'minor', 'minor': 'minor',
    'aug': 'augmented', 'augmented': 'augmented',
    'dim': 'diminished', 'diminished': 'diminished',
}

# Prefixes for multiply augmented/diminished intervals, mapped to how many
# times. The three-letter forms are what IntervalQuality.abbr produces.
_QUALITY_MULTIPLIERS = {
    'dbl': 2, 'double': 2,
    'trp': 3, 'trpl': 3, 'triple': 3,
    'qua': 4, 'quad': 4, 'quadruple': 4,
}

_NUMBER_WORDS = {diatone.i: diatone.d + 1 for diatone in MS}   # 'unison' -> 1, 'second' -> 2, ...

# e.g. "P5", "m3", "aug4", "dbldim5", "perfectfifth", "M9th", "aug4+1"
_INTERVAL_PATTERN = re.compile(rf"""
    (?P<multiplier>{_alternation(_QUALITY_MULTIPLIERS)})?
    (?P<quality>{_alternation({k.lower() for k in _QUALITY_KINDS})})
    (?:
        (?P<number>\d+)(?P<ordinal>st|nd|rd|th)?
      | (?P<number_word>{_alternation(_NUMBER_WORDS)})
    )
    (?P<octave>[+-]\d+)?    # octave suffix as in IntervalQuality.abbr, e.g. "aug4+1"
""", re.VERBOSE | re.IGNORECASE)


def _quality_kind(word: str) -> str:
    """The canonical quality kind for a quality word matched by _INTERVAL_PATTERN."""
    if word in ('M', 'm'):   # the one case-sensitive spelling
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
    degree = MS[d]
    is_perfect_type = degree.q == QualityType.P
    if kind == 'perfect' and not is_perfect_type:
        raise ValueError(f"A {degree.i} cannot be perfect (only major, minor, augmented or diminished).")
    if kind in ('major', 'minor') and is_perfect_type:
        raise ValueError(f"A {degree.i} cannot be {kind} (only perfect, augmented or diminished).")

    # IntervalQuality is keyed by a "relative number": 0 for perfect,
    # +0.5/-0.5 for major/minor, and each augmentation or diminution moves
    # a further 1 away from there.
    base = degree.q.value
    if kind == 'perfect':
        rel_number = 0
    elif kind == 'major':
        rel_number = base
    elif kind == 'minor':
        rel_number = -base
    elif kind == 'augmented':
        rel_number = base + times
    else:  # diminished
        rel_number = -base - times

    try:
        return iq._get_quality(rel_number)
    except KeyError:
        raise ValueError(f"{times} times {kind} is beyond the supported range of interval qualities.") from None


def _interval_from_match(m: re.Match) -> tuple:
    """(d, c[, o]) for a string matched by _INTERVAL_PATTERN."""
    kind = _quality_kind(m['quality'])
    times = _QUALITY_MULTIPLIERS[m['multiplier'].lower()] if m['multiplier'] else 1
    if times > 1 and kind not in ('augmented', 'diminished'):
        raise ValueError(f"'{m['multiplier']}' only applies to augmented or diminished intervals.")

    if m['number']:
        number = int(m['number'])
    else:
        number = _NUMBER_WORDS[m['number_word'].lower()]
    if not 1 <= number < len(ordinals):
        raise ValueError(f"Interval numbers must be between 1 and {len(ordinals) - 1}.")
    if m['ordinal'] and ordinals[number] != m['number'] + m['ordinal'].lower():
        raise ValueError(f"'{m['number']}{m['ordinal']}' is not a valid ordinal (expected '{ordinals[number]}').")

    # Numbers above 7 are compound: a 9th is a 2nd plus an octave.
    d, octave = (number - 1) % D_LEN, (number - 1) // D_LEN
    c = (MS[d].c + _interval_quality(kind, times, d).chromatic_modifier) % C_LEN

    if m['octave']:
        octave += int(m['octave'])
    if number > D_LEN or m['octave']:
        return (d, c, octave)
    return (d, c)


@WSMN.register_tone_type()
class TonalVector(tuple):
    """A tuple of form (d_iatonic, c_hromatic, (o_ctave)),
    representing either a pitch or interval (or both).
    TonalVector implements tonal arithmetic with __dunder__ methods,
    allowing use of standard operators (+, -, =, <, >)."""
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

        if hasattr(self, '__initialized'):
            return

        """
        self.d = self[0] # diatonic value
        self.c = self[1] # chromatic value

        self._diatone = MS[self.d] # Q for source # rename?
        
        # if a third value (octave) supplied
        try:
            self.o = self[2]
            self._has_octave = True
        except IndexError:
            self.o = None
            self._has_octave = False
        """
            
        self.pitch = self.Pitch(self)
        self.interval = self.Interval(self)

        self.__initialized = True

    ## Basic property interface

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
        except:
            raise AttributeError("This TonalVector does not have an octave designation.")
        
    @property
    def _diatone(self) -> dict:
        return MS[self.d]
    
    @property
    def _has_octave(self) -> bool:
        if len(self) == 2:
            return False
        if len(self) == 3:
            return True
        raise ValueError("Somehow, unexpectedly, this TonalVector has the wrong size.")


    @classmethod
    def abstract_vector_len(cls):
        """An abstract TonalVector has two members (diatonic, chromatic),
        and represents an abstract pitch class (C; A-flat; F-sharp) 
        or interval (Perfect Unison; Minor Sixth; Augmented Fourth)
        without an octave designation."""
        return 2
    
    @classmethod
    def qualified_vector_len(cls):
        """A qualified TonalVector has three members (diatonic, chromatic, octave),
        and represents a specfic, octave qualified pitch (C above middle C)
        or interval (Perfect fifth plus 2 octaves; Minor sixth minus 1 octave)."""
        return 3
    
    @classmethod
    def from_string(cls, s, mid_c=4, solfege_style=SolfegeStyle.EURO_FIXED):
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
        text = "".join(s.split())   # whitespace is never significant

        ly = _ly_pitch_match(text.lower())
        if ly and (ly['accidental'] or ly['octave_marks']):
            raise ValueError(f"{s!r} is a Lilypond pitch name; use TonalVector.from_ly instead.")

        interval = _INTERVAL_PATTERN.fullmatch(text)
        if interval:
            return cls(_interval_from_match(interval))

        pitch = _PITCH_PATTERNS[solfege_style].fullmatch(text.lower())
        if pitch:
            return cls(_pitch_from_match(pitch, _PITCH_NAMES[solfege_style], mid_c))

        raise ValueError(f"{s!r} is not a recognized pitch or interval.")

    @classmethod
    def from_ly(cls, s, prev_note=None):
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

        d = _LETTERS[m['letter']]
        accidental = m['accidental'].count('is') - m['accidental'].count('es')
        if accidental not in AC:
            raise ValueError(f"{s!r} has more sharps or flats than are supported.")
        c = (MS[d].c + accidental) % C_LEN

        if prev_note is None:
            octave = 0   # Lilypond's default octave is OMK's octave 0
        else:
            prev_note = cls(prev_note)
            if not prev_note._has_octave:
                raise ValueError("prev_note must be octave-qualified.")
            octave = _ly_relative_octave(d, prev_note)

        octave_shift = m['octave_marks'].count("'") - m['octave_marks'].count(',')
        return cls((d, c, octave + octave_shift))
    

    ### Util ###

    def __repr__(self) -> str:
        """
        >>> TonalVector((0,0))
        TonalVector((0, 0))

        >>> TonalVector((2,4,1))
        TonalVector((2, 4, 1))
        """
        return "TonalVector({})".format(repr(tuple(self)))

    def __str__(self) -> str:
        """Returns a string that includes the __repr__ string,
        along with human readable pitch and interval annotations
        in a Python-style inline comment.

        Examples
        --------

        >>> print(TonalVector((0,1)))
        TonalVector((0, 1)) # C♯

        >>> print(TonalVector((2,3,1)))
        TonalVector((2, 3, 1)) # E♭1
        """
        return "{} # {}".format(repr(self), self.pitch.unicode)

    ### Tonal Arithmetic ###

    def __add__(self, x: tuple[int]) -> TonalVector:
        """

        Examples
        --------

        >>> TonalVector((0,1)) + TonalVector((1,1))
        TonalVector((1, 2))

        >>> TonalVector((6,11,1)) + TonalVector((1,1))
        TonalVector((0, 0, 2))

        """
        return TonalVector(ta.tonal_sum(self, x))

    def __sub__(self, x: tuple[int]) -> TonalVector:
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

    def distance(self, x: tuple[int]) -> TonalVector:
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

    def nearest_instance(self, x: tuple[int]) -> TonalVector:
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

        return TonalVector(ta.tonal_nearest_instance(self,x))


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

    def __gt__(self, x: tuple[int]) -> bool:
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

    def __lt__(self, x: tuple[int]) -> bool:
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

    def inversion(self, x: tuple[int]=(0,0)) -> TonalVector:
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
        """Returns true if self and x are equal or equivalent.
        Can compare with TonalVectors, (d, c, [o]) tuples, 
        or integers representing half-steps or 12-tone pitches.

        Examples
        --------

        >>> TonalVector((0,1,0)) == (0,1,0)
        True

        >>> TonalVector((0,1)) == TonalVector((1,1))
        False

        >>> TonalVector((0,1)) == 1
        True

        >>> int(TonalVector((0,1))) == int(TonalVector((1,1)))
        True
        """
        if type(self) == type(x):
            return tuple(self) == tuple(x)
        return tuple(self) == x or int(self) == x

    def __hash__(self) -> int:
        return hash(tuple(self))
    
    def __call__(self, other):
        if isinstance(other, TonalVector):
            return self + other
        try:
            return other(self)
        except TypeError:
            raise TypeError(f"'{type(other)}' does not have a call handler for TonalVector")


    def qualify_octave(self, oct: int=0):
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
    
    def conditional_qualify_octave(self, oct: int=0):
        """Returns a TonalVector with an octave designation set to `oct`,
        but does not change an existing octave designation if present."""
        if len(self) == 3:
            return self
        return TonalVector((self.d, self.c, oct))

    def unqualify_octave(self):
        """Returns a TonalVector without an octave designation.
        
        Example
        -------
        
        >>> TonalVector.unqualify_octave(TonalVector((1, 2, 3)))
        TonalVector((1, 2))
        """

        return TonalVector((self.d, self.c))


    ### Represent as a pitch ###

    class Pitch(PitchRepresentation):
        """A TonalVector's pitch representation,
        which holds relevant details such as letter name, accidental, etc.
        
        Example
        -------

        >>> type(TonalVector((0,0)).pitch)
        <class 'openmusickit.systems.wsmn.tonal.tonal_vector.TonalVector.Pitch'>
        """
        
        def __init__(self, vector: TonalVector):
            self._v = vector


        # letter name
        @property
        def _ln(self) -> str:
            """The letter name (without sharps or flats) of the pitch.
            
            Examples
            --------

            >>> TonalVector((0,0)).pitch._ln
            'C'

            >>> TonalVector((0,1)).pitch._ln
            'C'
            """
            return self._v._diatone.ln.upper()

        # how sharp or flat
        @property
        def _modifier_value(self) -> int:
            """A number representing the distance in halfsteps between the named pitch
            and the natural version of the named pitch.

            >>> TonalVector((0,0)).pitch._modifier_value # C natural
            0
            
            >>> TonalVector((0,1)).pitch._modifier_value # C sharp
            1

            >>> TonalVector((0, 11)).pitch._modifier_value # C flat
            -1

            >>> TonalVector((4,6,1)).pitch._modifier_value # G flat
            -1

            >>> TonalVector((6,0)).pitch._modifier_value # B sharp
            1
            """
            
            modifier = self._v.c - self._v._diatone.c


            if abs(modifier) > 4: # 4 = triple aug or triple dim
                if self._v.c < self._v._diatone.c:
                    d_val_c = self._v._diatone.c - C_LEN
                if self._v.c > self._v._diatone.c:
                    d_val_c = self._v._diatone.c + C_LEN
                modifier = self._v.c - d_val_c

            return modifier
            

        @property
        def _modifier(self) -> Accidental:
            """Returns an Accidental, which contains
            information about how to represent the modifier (sharp, flat, natural).

            >>> TonalVector((0,0)).pitch._modifier
            Accidental(offset=0, v='natural', uni='♮', asc='', ly='')
            
            >>> TonalVector((0,0)).pitch._modifier.v
            'natural'
            """
            return AC[self._modifier_value]

        def _unicode(self, mid_c: int = 0) -> str:
            """Returns a human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            The mid_c arg can be used to set the octave designation for middle C.
            (In OMK, middle C == C0. In MIDI etc., middle C == C4).

            Examples
            --------

            >>> TonalVector((0,1)).pitch._unicode()
            'C♯'

            >>> TonalVector((1,1,0)).pitch._unicode(4)
            'D♭4'
            """
            u_str = self._ln

            if self._modifier_value:
                u_str = "".join([u_str, self._modifier.u])

            if self._v._has_octave:
                u_str = "".join([u_str, str(self._v.o + mid_c)])
            
            return u_str

        @property
        def unicode(self) -> str:
            """A human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            If the pitch has an octave designation, middle C == C0.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode
            'D♭0'
            """
            return self._unicode()

        @property
        def unicode_C4(self) -> str:
            """A human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            If the pitch has an octave designation, middle C == C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode_C4
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode_C4
            'D♭4'
            """
            return self._unicode(mid_c=4)

        def _ascii(self, octave_modifier: int=0, show_nat: bool = False):
            """Returns a human readable representation of the pitch, with ascii modifiers (#, b).
            The octave_modifier can be used to set the octave designation for middle C.
            (In OMK, middle C == C0. In MIDI etc., middle C == C4).

            Examples
            --------

            >>> TonalVector((0,1)).pitch._ascii()
            'C#'

            >>> TonalVector((1,1,0)).pitch._ascii(4)
            'Db4'
            """
            astr = self._ln

            if self._modifier_value:
                astr = "".join([astr, self._modifier.a])

            if self._v._has_octave:
                astr = "".join([astr, str(self._v.o + octave_modifier)])
            
            return astr
            
        @property
        def ascii(self):
            """A human readable representation of the pitch, with Ascii modifiers (#, b).
            If the pitch has an octave designation, middle C == C0.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii
            'Db0'
            """
            return self._ascii()

        @property
        def ascii_C4(self):
            """A human readable representation of the pitch, with Ascii modifiers (#, b).
            If the pitch has an octave designation, middle C == C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii_C4
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii_C4
            'Db4'
            """
            return self._ascii(octave_modifier=4)

        @property
        def ly(self):
            """The Lilypond representation of the pitch name, 
            without an octave designation.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ly # C sharp
            'cis'

            >>> TonalVector((6,10,1)).pitch.ly # B flat, with an octave designation
            'bes'
            """

            return "".join([self._ln.lower(), self._modifier.ly])

        @property
        def ly_abs8ve(self):
            """The Lilypond representation of the pitch name,
            with an absolute octave designation. 
            (see: http://lilypond.org/doc/v2.18/Documentation/learning/absolute-pitch-names)

            Examples
            --------

            >>> TonalVector((0,0,1)).pitch.ly_abs8ve # C above middle C
            "c'"

            >>> TonalVector((6,10,-1)).pitch.ly_abs8ve # B flat below middle C
            'bes,'

            >>> TonalVector((3,6,0)).pitch.ly_abs8ve # F sharp in octave of middle c
            'fis'

            >>> TonalVector((3,6)).pitch.ly_abs8ve # F sharp, no octave designation
            'fis'

            >>> TonalVector((1,1,4)).pitch.ly_abs8ve # D flat, 4 octaves above middle c
            "des''''"

            >>> TonalVector((1,1,-4)).pitch.ly_abs8ve # D flat, 4 octaves below middle c
            'des,,,,'
            """

            if not self._v._has_octave:
                return self.ly

            if self._v.o < 0:
                ostr = ","
            else:
                ostr = "'"

            return "".join([self.ly, ostr*abs(self._v.o)])


        def ly_rel8ve(self, prev=None):
            """Returns the Lilypond representation of the pitch name,
            with a relative octave designation, based on the previous pitch.

            >>> TonalVector((3,5,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'f'

            >>> TonalVector((4,7,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            "g'"

            >>> TonalVector((3,5,-1)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'f,'

            >>> TonalVector((4,7,-1)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'g'

            >>> TonalVector((0,0,2)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            "c''"

            Accidentals don't affect the octave: F-sharp is a fourth above C
            and G-flat a fifth above, so G-flat gets an octave mark.

            >>> TonalVector((3,6,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'fis'

            >>> TonalVector((4,6,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            "ges'"
            """
            if prev == None:
                return self.ly_abs8ve

            octave_distance = self._v.o - _ly_relative_octave(self._v.d, prev)

            if octave_distance < 0:
                ostr = ","
            else:
                ostr = "'"

            return "".join([self.ly, ostr*abs(octave_distance)])


        @property
        def verbose(self):
            """
            >>> TonalVector((0,0)).pitch.verbose
            'C'
            
            >>> TonalVector((0,1)).pitch.verbose
            'Csharp'

            >>> TonalVector((0,1,1)).pitch.verbose
            'Csharp1'

            """ 

            try:
                o = str(self._v.o)
            except AttributeError:
                o = ""

            if self._modifier_value == 0:
                mod_text = ""
            else:
                mod_text = self._modifier.v

            return "".join([self._ln, mod_text, o])

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).pitch
            TonalVector((0, 0, 0)).pitch
            """
            return "".join([self._v.__repr__(), ".pitch"])

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).pitch)
            'C0 | (0, 0, 0)'
            """
            return "".join([self.unicode, " | ", str(tuple(self._v))])

    
    class Interval(IntervalRepresentation):

        def __init__(self, vector):
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
            if vector._has_octave:
                self.o = f"{vector.o:+d}"
            else:
                self.o = ""

        @property
        def abbr(self):
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


            return "".join([self.quality.abbr, str(self.number), self.o])

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).interval
            TonalVector((0, 0, 0)).interval
            """
            return "".join([self._v.__repr__(), ".interval"])
        
        @property
        def unicode(self):
            """
            >>> TonalVector((0,0)).interval.unicode
            'perfect 1'

            >>> TonalVector((3,6)).interval.unicode
            'augmented 4'
            """
            return f"{self.quality.__str__()} {self.number}"

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).interval)
            'perfect 1 | (0, 0, 0)'
            """
            return "".join([self.unicode, " | ", str(tuple(self._v))])
