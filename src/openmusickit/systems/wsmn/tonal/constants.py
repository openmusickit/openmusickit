from enum import Enum

D_LEN = 7  # "Diatonic Length" - The number of tones in a diatonic scale.
C_LEN = 12  # "Chromatic Length" - The number of tones in a chromatic scale.


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


class SolfegeStyle(Enum):
    """Which solfege naming convention a solfege string belongs to.

    OMK_MOVEABLE uses moveable-do syllables with chromatic variants
    (e.g. 'di' = do-sharp, 'so' = the natural 5th, 'si' = so-sharp).

    EURO_FIXED uses fixed-do syllables, one per diatonic letter name,
    with no chromatic variants of their own (accidentals are applied as
    separate modifiers, e.g. 'Do#', 'Sib').
    """

    OMK_MOVEABLE = "omk_moveable"
    EURO_FIXED = "euro_fixed"


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


class Diatone:
    """A major or perfect pitch or interval.

    All pitch values, interval qualities, and scales are based on
    the diatonic major scale.
    """

    def __init__(self, d: int, c: int, q: QualityType, i: str, ln: str, sf: dict, f: str, z: int):
        self._d = d  # diatonic scale degree (zero indexed)
        self._c = c  # chromatic (12-tone) value (zero indexed)
        self._q = q  # quality type - Perfect or Major/Minor
        self._i = i  # interval name - "unison", "second", etc
        self._ln = ln  # letter name in C major
        self._sf = sf  # solfege (moveable do)
        self._f = f  # functional name
        self._z = z  # dissonance score

    @property
    def d(self) -> int:
        return self._d

    @property
    def c(self) -> int:
        return self._c

    @property
    def q(self) -> QualityType:
        return self._q

    @property
    def i(self) -> str:
        return self._i

    @property
    def ln(self) -> str:
        return self._ln

    @property
    def sf(self) -> dict[int:str]:
        return self._sf

    @property
    def f(self) -> str:
        return self._f

    @property
    def z(self) -> int:
        return self._z

    def __repr__(self):
        return f"Diatone(d={self.d}, c={self.c}, q={self.q}, i='{self.i}', ln='{self.ln}', sf={self.sf}, f='{self.f}', z={self.z})"


# Set up Diatones for Major Scale

MS = [
    # diatonic value, chromatic value, interval quality (0 or 0.5), interval name,  letter name, solfege list, function, diszonance
    {"d": 0, "c": 0, "q": P, "in": "unison", "ln": "c", "sf": DO, "f": "tonic", "z": 0},
    {"d": 1, "c": 2, "q": Mm, "in": "second", "ln": "d", "sf": RE, "f": "subtonic", "z": 2},
    {"d": 2, "c": 4, "q": Mm, "in": "third", "ln": "e", "sf": MI, "f": "mediant", "z": 1},
    {"d": 3, "c": 5, "q": P, "in": "fourth", "ln": "f", "sf": FA, "f": "subdominant", "z": 2},
    {"d": 4, "c": 7, "q": P, "in": "fifth", "ln": "g", "sf": SO, "f": "dominant", "z": 0},
    {"d": 5, "c": 9, "q": Mm, "in": "sixth", "ln": "a", "sf": LA, "f": "submediant", "z": 1},
    {"d": 6, "c": 11, "q": Mm, "in": "seventh", "ln": "b", "sf": TI, "f": "leading tone", "z": 3},
]

MS = [
    Diatone(d=x["d"], c=x["c"], q=x["q"], i=x["in"], ln=x["ln"], sf=x["sf"], f=x["f"], z=x["z"])
    for x in MS
]


class Accidental:
    def __init__(self, offset: int, v: str, uni: str, asc: str, ly: str):
        self._offset = offset  # half-steps from natural
        self._v = v  # verbose name; e.g. "flat", "double sharp"
        self._uni = uni  # unicode symbol
        self._asc = asc  # ASCII symbol
        self._ly = ly  # Lilypond symbol

    @property
    def offset(self) -> int:
        """Chromatic offset from the base note, in half steps.
        Positive is sharp and negative is flat."""
        return self._offset

    @property
    def v(self) -> str:
        """The English name of the accidental, spelled out.
        For example, 'flat' or 'double sharp'."""
        return self._v

    @property
    def u(self) -> str:
        """The Unicode representation."""
        return self._uni

    @property
    def a(self) -> str:
        """The ASCII representation."""
        return self._asc

    @property
    def ly(self) -> str:
        """The Lilypond command."""
        return self._ly

    def __repr__(self) -> str:
        return f"Accidental(offset={self.offset}, v='{self.v}', uni='{self.u}', asc='{self.a}', ly='{self.ly}')"


# Accidentals
AC = {
    # halfsteps : verbose, unicode, ascii, ly
    -4: {"v": "quadruple flat", "u": "𝄫𝄫", "a": "bbbb", "ly": "eseseses"},
    -3: {"v": "triple flat", "u": "𝄫♭", "a": "bbb", "ly": "eseses"},
    -2: {"v": "double flat", "u": "𝄫", "a": "bb", "ly": "eses"},
    -1: {"v": "flat", "u": "♭", "a": "b", "ly": "es"},
    0: {"v": "natural", "u": "♮", "a": "", "ly": ""},
    1: {"v": "sharp", "u": "♯", "a": "#", "ly": "is"},
    2: {"v": "double sharp", "u": "𝄪", "a": "##", "ly": "isis"},
    3: {"v": "triple sharp", "u": "𝄪♯", "a": "###", "ly": "isisis"},
    4: {"v": "quadruple sharp", "u": "𝄪𝄪", "a": "####", "ly": "isisisis"},
}

AC = {i: Accidental(offset=i, v=x["v"], uni=x["u"], asc=x["a"], ly=x["ly"]) for i, x in AC.items()}
