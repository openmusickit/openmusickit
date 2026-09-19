from dataclasses import dataclass
from enum import Enum, StrEnum, auto

D_LEN = 7  # "Diatonic Length" - The number of tones in a diatonic scale.
C_LEN = 12  # "Chromatic Length" - The number of tones in a chromatic scale.

# Letter names (as diatonic values) in the order sharps are added to a key signature:
# F C G D A E B. Flats are added in the reverse order.
SHARP_ORDER = (3, 0, 4, 1, 5, 2, 6)


class QualityType(Enum):
    """All Diatones are either Perfect or Major/Minor.
    When a Perfect interval is reduced by one half-step,
    it becomes 'diminished'.
    Whereas, when a Major interval is reduced by one half-step,
    it becomes 'minor'.
    """

    P = 0
    Mm = 0.5


P = QualityType.P
Mm = QualityType.Mm


class SolfegeStyle(StrEnum):
    """Which solfege naming convention a solfege string belongs to.

    OMK_MOVEABLE uses moveable-do syllables with chromatic variants
    (e.g. 'di' = do-sharp, 'so' = the natural 5th, 'si' = so-sharp).

    EURO_FIXED uses fixed-do syllables, one per diatonic letter name,
    with no chromatic variants of their own (accidentals are applied as
    separate modifiers, e.g. 'Do#', 'Sib').
    """

    OMK_MOVEABLE = auto()
    EURO_FIXED = auto()


# CHROMATIC SOLFEGE SYLLABLES
# Based on 'standard' American Moveable Do
# The following are invented here:
# b1 b4 - de and fe, based on other flatted syllables (except ra)
# #3 #7 - ma and to, rhyme with fa and do (enharmonic equiv.)

DO = {-1: "de", 0: "do", 1: "di"}
RE = {-1: "ra", 0: "re", 1: "ri"}
MI = {-1: "me", 0: "mi", 1: "ma"}
FA = {-1: "fe", 0: "fa", 1: "fi"}
SO = {-1: "se", 0: "so", 1: "si"}
LA = {-1: "le", 0: "la", 1: "li"}
TI = {-1: "te", 0: "ti", 1: "to"}


# EURO-STYLE FIXED DO SOLFEGE SYLLABLES
# One syllable per diatonic letter name (C-B). No chromatic variants:
# accidentals are represented separately (e.g. "Do#", "Sib").
EURO_SF = {0: "do", 1: "re", 2: "mi", 3: "fa", 4: "sol", 5: "la", 6: "si"}


@dataclass(frozen=True, slots=True)
class Diatone:
    """A degree of the major scale: a major or perfect pitch or interval.

    All pitch values, interval qualities, and scales are based on
    the diatonic major scale.
    """

    degree: int  # diatonic scale degree (zero indexed)
    chromatic: int  # chromatic (12-tone) value (zero indexed)
    quality_type: QualityType  # Perfect or Major/Minor
    interval_name: str  # "unison", "second", ...
    letter: str  # letter name in C major
    solfege: dict[int, str]  # moveable-do syllables by chromatic offset (see DO, RE, ...)
    function: str  # "tonic", "dominant", ...
    dissonance: int  # dissonance score


DIATONES = (
    Diatone(0, 0, P, "unison", "c", DO, "tonic", 0),
    Diatone(1, 2, Mm, "second", "d", RE, "subtonic", 2),
    Diatone(2, 4, Mm, "third", "e", MI, "mediant", 1),
    Diatone(3, 5, P, "fourth", "f", FA, "subdominant", 2),
    Diatone(4, 7, P, "fifth", "g", SO, "dominant", 0),
    Diatone(5, 9, Mm, "sixth", "a", LA, "submediant", 1),
    Diatone(6, 11, Mm, "seventh", "b", TI, "leading tone", 3),
)
"""The seven degrees of the major scale, indexed by diatonic value."""


@dataclass(frozen=True, slots=True)
class Accidental:
    """A chromatic alteration of a letter name, with its spellings."""

    offset: int  # half-steps from natural; positive is sharp, negative is flat
    name: str  # spelled out: "flat", "double sharp", ...
    unicode: str
    ascii: str
    ly: str  # Lilypond suffix


ACCIDENTALS = {
    -4: Accidental(-4, "quadruple flat", "𝄫𝄫", "bbbb", "eseseses"),
    -3: Accidental(-3, "triple flat", "𝄫♭", "bbb", "eseses"),
    -2: Accidental(-2, "double flat", "𝄫", "bb", "eses"),
    -1: Accidental(-1, "flat", "♭", "b", "es"),
    0: Accidental(0, "natural", "♮", "", ""),
    1: Accidental(1, "sharp", "♯", "#", "is"),
    2: Accidental(2, "double sharp", "𝄪", "##", "isis"),
    3: Accidental(3, "triple sharp", "𝄪♯", "###", "isisis"),
    4: Accidental(4, "quadruple sharp", "𝄪𝄪", "####", "isisisis"),
}
"""Accidentals by chromatic offset from natural."""
