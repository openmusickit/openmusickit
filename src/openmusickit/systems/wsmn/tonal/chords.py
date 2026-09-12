from enum import Enum
from typing import Iterable
from openmusickit.values.tone.tone_collection import ToneCollection, ToneSequence
from openmusickit.utils.number_names import ordinals
from .tonal_vector import TonalVector

class Quality(Enum):
    MAJ = "major"
    MIN = "minor"
    SUS = "suspended"
    POW = "open/power"
    AUG = "augmented"
    DIM = "diminished"
    DOM = "dominant"
    HDM = "half diminished"

class ChordType(ToneCollection):
    """Chord definition, as an ordered collection of TonalVectors representing
    intervals from the root (0,0).

    Tone order is significant: it distinguishes chords that share the same
    pitch classes but are conventionally named/voiced differently
    (for example, an added 2nd vs. an added 9th)."""

    def __init__(self, tones: Iterable[TonalVector],
                 name: str, bass: TonalVector=None, quality: Quality=None):

        tones = tuple(tones)
        if TonalVector(0, 0) not in tones:
            raise ValueError("Include `TonalVector(0,0)` as root of chord type.")

        super().__init__(tones, root=TonalVector(0, 0), name=name)

        self.bass = bass or self.root
        self.quality = quality

    def arpegiate(self) -> ToneSequence:
        """Returns the chord's tones as a ToneSequence, bass tone first."""
        rest = [t for t in self if t != self.bass]
        return ToneSequence([self.bass] + rest)

    # FIX naming
    def inversion(self, inv: int|TonalVector, name: str=None) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone."""

        if isinstance(inv, TonalVector):
            bass = inv
            name = name or (self.name and self.name + f" - {ordinals[list(self).index(bass)]} inversion")
        elif isinstance(inv, int):
            try:
                bass = list(self)[inv]
            except IndexError:
                raise IndexError(f"Max inversion is {len(self)-1}.")
            name = name or (self.name and self.name + f" / {bass.unqualify_octave().pitch.unicode}")
        else:
            raise TypeError("`inv` must be a TonalVector or an int.")

        return ChordType(self, name, bass, self.quality)

    def __call__(self, tv: TonalVector) -> "Chord":
        """Returns a Chord: this ChordType realized with its root at `tv`."""
        tones = [t + tv for t in self]
        root = tv
        bass = self.bass + tv

        return Chord(root, tones, bass, self.name)

    def __div__(self, tv: TonalVector) -> "ChordType":
        return self.inversion(tv)

class Chord(ToneCollection):
    """A concrete realization of a ChordType at a specific root pitch."""

    def __init__(self, root: TonalVector, tones: Iterable[TonalVector],
                 bass: TonalVector=None, name: str=None):

        super().__init__(tones, root=root, name=name)
        self.bass = bass or self.root

