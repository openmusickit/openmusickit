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

    def _resolve_inversion(self, inv: int|TonalVector, name: str|None) -> tuple[TonalVector, str|None]:
        """Shared logic for `inversion()`: finds the new bass tone and,
        if `name` was not supplied, builds a default name for the inversion.
        Used by both ChordType and Chord, since inverting a Chord follows
        the same rule as inverting a ChordType, just producing a Chord."""

        if isinstance(inv, TonalVector):
            bass = inv
            if name is None and self.name:
                name = self.name + f" - {ordinals[list(self).index(bass)]} inversion"
        elif isinstance(inv, int):
            try:
                bass = list(self)[inv]
            except IndexError:
                raise IndexError(f"Max inversion is {len(self)-1}.")
            if name is None and self.name:
                name = self.name + f" / {bass.unqualify_octave().pitch.unicode}"
        else:
            raise TypeError("`inv` must be a TonalVector or an int.")

        return bass, name

    # FIX naming
    def inversion(self, inv: int|TonalVector, name: str=None) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone."""
        bass, name = self._resolve_inversion(inv, name)
        return ChordType(self, name, bass, self.quality)

    def __call__(self, tv: TonalVector) -> "Chord":
        """Returns a Chord: this ChordType realized with its root at `tv`.
        
        Intended to be used with TonalVector's *reverse* __call__ method:
        
            tv = TonalVector(..)
            chord_type = ChordType(...)
            chord = tv(chord_type)  # chord is a Chord with root at tv

            particularly useful with symbols:

            from openmusickit.values.symbols import *

            C_major_chord = C(maj) 
        """
        tones = [t + tv for t in self]
        root = tv
        bass = self.bass + tv

        return Chord(root, tones, bass, self.name)

    def __truediv__(self, tv: TonalVector) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone.
        
        This is an overload for the `/` operator, so you can write slash chords like this:
        
            C_major_over_E = C(maj) / E
        """
        return self.inversion(tv)

class Chord(ToneCollection):
    """A concrete realization of a ChordType at a specific root pitch.

    Unlike ChordType, a Chord's root is not necessarily `TonalVector(0,0)` --
    it is wherever the ChordType was realized (e.g. `maj(E)` produces a Chord
    rooted at E)."""

    def __init__(self, root: TonalVector, tones: Iterable[TonalVector],
                 bass: TonalVector=None, name: str=None):

        super().__init__(tuple(tones), root=root, name=name)
        self.bass = bass or self.root

    def inversion(self, inv: int|TonalVector, name: str=None) -> "Chord":
        """Returns a Chord with the same tones and root, but a different bass tone."""
        bass, name = ChordType._resolve_inversion(self, inv, name)
        return Chord(self.root, self, bass, name)

    def __truediv__(self, tv: TonalVector) -> "Chord":
        """Returns a Chord with the same tones and root, but a different bass tone.

        This is an overload for the `/` operator, so you can write slash chords like this:

            C_major_over_E = C(maj) / E
        """
        return self.inversion(tv)

