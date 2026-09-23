"""WSMN clefs: a sign on a line of the five-line staff."""

from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.clef import Clef


class ClefSign(StrEnum):
    """The sign a WSMN clef is drawn with: MusicXML's `<sign>` values, minus jianpu."""

    G = auto()
    F = auto()
    C = auto()
    PERCUSSION = auto()  # unpitched: the lines are instruments, not tones
    TAB = auto()  # the lines are strings
    NONE = auto()  # no clef is drawn


# The tone each pitched sign names on its line, middle C as octave 0: G4, F3, C4.
_REFERENCE_TONES = {ClefSign.G: (4, 7, 0), ClefSign.F: (3, 5, -1), ClefSign.C: (0, 0, 0)}


@dataclass(frozen=True, slots=True)
class StaffClef(Clef):
    """A WSMN clef: `sign` on staff line `line`
    (1 is the bottom line, MusicXML's numbering),
    sounding `octave_change` octaves from where it is written
    (MusicXML's clef-octave-change;
    -1 for the vocal tenor clef, the treble clef with an 8 below).
    The ready-made clefs are in `symbols`
    (`treble_clef`, `bass_clef`, `alto_clef`, `treble_clef_8vb`, `percussion_clef`, ...).

    Examples
    --------
    >>> StaffClef(ClefSign.G, 2)
    StaffClef(ClefSign.G, 2)
    >>> StaffClef(ClefSign.G, 2, octave_change=-1).reference_tone
    TonalVector((4, 7, -1))
    >>> StaffClef(ClefSign.PERCUSSION).reference_tone is None
    True
    >>> StaffClef(ClefSign.F)
    Traceback (most recent call last):
    ...
    ValueError: An F clef sits on a staff line 1 to 5; got None.
    >>> StaffClef(ClefSign.TAB, 3)
    Traceback (most recent call last):
    ...
    ValueError: A TAB clef sits on no particular line; got 3.
    """

    sign: ClefSign
    line: int | None = None
    octave_change: int = 0

    def __post_init__(self) -> None:
        article = "An" if self.sign is ClefSign.F else "A"
        if self.sign in _REFERENCE_TONES:
            if not isinstance(self.line, int) or not 1 <= self.line <= 5:
                raise ValueError(
                    f"{article} {self.sign.name} clef sits on a staff line 1 to 5; got {self.line!r}."
                )
        elif self.line is not None:
            raise ValueError(
                f"{article} {self.sign.name} clef sits on no particular line; got {self.line!r}."
            )

    @property
    def reference_tone(self) -> TonalVector | None:
        """The tone the sign names on its line, shifted by the octave change;
        None for the unpitched signs.

        >>> StaffClef(ClefSign.F, 4).reference_tone
        TonalVector((3, 5, -1))
        >>> StaffClef(ClefSign.C, 3).reference_tone.pitch.unicode
        'C4'
        """
        reference = _REFERENCE_TONES.get(self.sign)
        if reference is None:
            return None
        d, c, o = reference
        return TonalVector((d, c, o + self.octave_change))

    def __repr__(self) -> str:
        parts = [f"ClefSign.{self.sign.name}"]
        if self.line is not None:
            parts.append(str(self.line))
        if self.octave_change:
            parts.append(f"octave_change={self.octave_change}")
        return f"{type(self).__name__}({', '.join(parts)})"
