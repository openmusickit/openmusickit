from collections.abc import Callable, Iterable
from enum import StrEnum, auto

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.utils.number_names import ORDINALS
from openmusickit.values.tone.tone_collection import ToneCollection


class ChordQuality(StrEnum):
    """The broad family a chord type belongs to."""

    MAJ = auto()
    MIN = auto()
    SUS = auto()
    POW = auto()  # open / power chord
    AUG = auto()
    DIM = auto()
    DOM = auto()
    HDM = auto()  # half diminished


class ChordType(ToneCollection):
    """Chord definition, as an ordered collection of TonalVectors representing
    intervals from the root (0,0).

    Tone order is significant: it distinguishes chords that share the same
    pitch classes but are conventionally named/voiced differently
    (for example, an added 2nd vs. an added 9th)."""

    def __init__(
        self,
        tones: Iterable[TonalVector],
        name: str,
        bass: TonalVector | None = None,
        quality: ChordQuality | None = None,
        suffix: str | None = None,
    ):

        tones = tuple(tones)
        if TonalVector(0, 0) not in tones:
            raise ValueError("Include `TonalVector(0,0)` as root of chord type.")

        super().__init__(tones, root=TonalVector(0, 0), name=name)

        self.bass = bass or self.root
        self.quality = quality
        # Lead-sheet suffix, e.g. "maj7", "sus4", "7♭9". Empty string for a plain major triad.
        self.suffix = suffix

    def __eq__(self, other) -> bool:
        """Equal when tones, root and bass all match; name, suffix and quality
        are ignored (as `name` is for ToneCollection).

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, maj7, C, E, G
        >>> maj == ChordType([C, E, G], name="anything")
        True
        >>> maj == maj.inversion(1)
        False
        """
        if not isinstance(other, ChordType):
            return NotImplemented
        return super().__eq__(other) and self.bass == other.bass

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.bass))

    def arpeggiate(self) -> ToneCollection:
        """Returns the chord's tones as a ToneCollection, rotated so that the
        bass tone comes first and the remaining tones follow in their
        original (cyclic) order. Root and name are preserved.

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj7
        >>> def names(tc): return [t.pitch.unicode for t in tc]
        >>> names(maj7.arpeggiate())
        ['C', 'E', 'G', 'B']
        >>> names(maj7.inversion(1).arpeggiate())
        ['E', 'G', 'B', 'C']
        >>> names(maj7.inversion(2).arpeggiate())
        ['G', 'B', 'C', 'E']
        >>> names(maj7.inversion(3).arpeggiate())
        ['B', 'C', 'E', 'G']
        """
        return ChordType._rotate_to_bass(self)

    def _rotate_to_bass(self) -> ToneCollection:
        """Shared logic for `arpeggiate()`: the tones rotated so the bass
        comes first, as a plain ToneCollection with root and name preserved.
        Used by both ChordType and Chord."""
        tones = list(self)
        i = tones.index(self.bass)
        return ToneCollection(tones[i:] + tones[:i], root=self.root, name=self._name_template)

    def _resolve_inversion(
        self, inv: int | TonalVector, name: str | None
    ) -> tuple[TonalVector, str | None]:
        """Shared logic for `inversion()`: finds the new bass tone, and
        keeps the existing name unless `name` was supplied (inversions are
        reflected in `__str__`, not in the name).
        Used by both ChordType and Chord, since inverting a Chord follows
        the same rule as inverting a ChordType, just producing a Chord."""

        if isinstance(inv, TonalVector):
            bass = inv
        elif isinstance(inv, int):
            try:
                bass = list(self)[inv]
            except IndexError:
                raise IndexError(f"Max inversion is {len(self) - 1}.") from None
        else:
            raise TypeError("`inv` must be a TonalVector or an int.")

        if name is None:
            name = self._name_template

        return bass, name

    def inversion(self, inv: int | TonalVector, name: str | None = None) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone."""
        bass, name = self._resolve_inversion(inv, name)
        return ChordType(self, name, bass, self.quality, self.suffix)

    def transform(self, *args, **kwargs):
        """ChordTypes are interval patterns rooted at `TonalVector(0,0)`, so
        there is nothing to transform: realize the type at a root first
        (`C(maj)`), then transform the resulting Chord.

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, M3
        >>> maj.transform(TonalVector.transpose, M3)
        Traceback (most recent call last):
        ...
        NotImplementedError: ChordTypes do not transform.
        """
        raise NotImplementedError("ChordTypes do not transform.")

    def __str__(self) -> str:
        """Lead-sheet style label: the suffix if there is a non-empty one,
        otherwise the name, followed by the ordinal inversion when the bass
        is not the root. (The inversion is the index of the bass within the
        chord type's tones.)

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, maj7, G

        Non-empty suffix, root position and inverted:

        >>> str(maj7)
        'maj7'
        >>> str(maj7.inversion(1))
        'maj7 1st inv.'
        >>> str(maj7 / G)
        'maj7 2nd inv.'

        Empty suffix falls back to the name:

        >>> str(maj)
        'major'
        >>> str(maj.inversion(1))
        'major 1st inv.'

        No suffix or name at all (degenerate; falls back to `__repr__`):

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E
        >>> str(ChordType([C, E, G], name=None))
        'ChordType([TonalVector((0, 0)), TonalVector((2, 4)), TonalVector((4, 7))], root=TonalVector((0, 0)))'
        """
        label = self.suffix or self.name or ""
        inv = list(self).index(self.bass)
        if inv:
            label = f"{label} {ORDINALS[inv]} inv."
        return label.strip() or repr(self)

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

        return Chord(root, tones, bass, self.name, self.suffix)

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

    def __init__(
        self,
        root: TonalVector,
        tones: Iterable[TonalVector],
        bass: TonalVector | None = None,
        name: str | None = None,
        suffix: str | None = None,
    ):

        super().__init__(tuple(tones), root=root, name=name)
        self.bass = bass or self.root
        self.suffix = suffix

    def __eq__(self, other) -> bool:
        """Equal when tones, root and bass all match; name and suffix are ignored.

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, C, E
        >>> C(maj) == C(maj), C(maj) == C(maj) / E
        (True, False)
        """
        if not isinstance(other, Chord):
            return NotImplemented
        return super().__eq__(other) and self.bass == other.bass

    def __hash__(self) -> int:
        return hash((super().__hash__(), self.bass))

    def inversion(self, inv: int | TonalVector, name: str | None = None) -> "Chord":
        """Returns a Chord with the same tones and root, but a different bass tone."""
        bass, name = ChordType._resolve_inversion(self, inv, name)
        return Chord(self.root, self, bass, name, self.suffix)

    def arpeggiate(self) -> ToneCollection:
        """Returns the chord's tones as a ToneCollection, rotated so that the
        bass tone comes first and the remaining tones follow in their
        original (cyclic) order. Root and name are preserved.

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, maj7
        >>> def names(tc): return [t.pitch.unicode for t in tc]
        >>> names(C(maj7).arpeggiate())
        ['C', 'E', 'G', 'B']
        >>> names((C(maj7) / E).arpeggiate())
        ['E', 'G', 'B', 'C']
        >>> names((C(maj7) / G).arpeggiate())
        ['G', 'B', 'C', 'E']
        >>> names(C(maj7).inversion(3).arpeggiate())
        ['B', 'C', 'E', 'G']
        """
        return ChordType._rotate_to_bass(self)

    def transform(
        self,
        operation: Callable[..., TonalVector],
        *args,
        new_name: str | None = None,
        new_suffix: str | None = None,
        **kwargs,
    ) -> "Chord":
        """Returns a new Chord made by applying `operation` to every tone
        of this chord (root, tones, and bass).

        `operation` is called as `operation(tone, *args, **kwargs)` for each
        tone. It is typically a TonalVector method (such as
        `TonalVector.transpose`), but any callable that accepts a TonalVector
        as its first argument and returns a TonalVector will do. The
        operation is validated against the root first; if it does not
        return a TonalVector, a TypeError is raised.

        The new chord keeps this chord's name and suffix unless `new_name`
        and/or `new_suffix` are given.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, G, min_, maj, M3
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection

        Transposition, with the interval passed as the operand:

        >>> str(C(min_).transform(TonalVector.transpose, M3))
        'Emin'
        >>> str(C(min_).transform(TonalVector.transpose, M3, TonalDirection.DOWN))
        'A♭min'

        The bass is transformed along with the rest of the chord:

        >>> str((C(maj) / G).transform(TonalVector.transpose, M3))
        'E/B'

        A user-defined operation that needs no operand, with a new suffix:

        >>> def sharpen(tv):
        ...     return tv + TonalVector((0, 1))
        >>> str(C(maj).transform(sharpen, new_suffix="maj"))
        'C♯maj'

        An operation that does not produce a TonalVector is rejected:

        >>> C(maj).transform(str)
        Traceback (most recent call last):
        ...
        TypeError: ...
        """
        root = operation(self.root, *args, **kwargs)
        if not isinstance(root, TonalVector):
            raise TypeError(
                f"`operation` must return a TonalVector, but returned {root!r} for the root."
            )

        tones = [operation(t, *args, **kwargs) for t in self]
        bass = operation(self.bass, *args, **kwargs)

        if new_name is None:
            new_name = self._name_template
        if new_suffix is None:
            new_suffix = self.suffix

        return Chord(root, tones, bass, new_name, new_suffix)

    def __str__(self) -> str:
        """Lead-sheet chord symbol: the root's pitch name followed by the
        suffix, plus "/bass" when the bass is not the root. Falls back to
        `name` (with a separating space) when there is no suffix.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Eb, maj, maj7, hdim7

        Non-empty suffix, root position and inverted:

        >>> str(C(maj7))
        'Cmaj7'
        >>> str(C(maj7) / E)
        'Cmaj7/E'
        >>> str(Eb(hdim7).inversion(2))
        'E♭ø7/B𝄫'

        Empty suffix (the plain major triad) shows just the root:

        >>> str(C(maj))
        'C'
        >>> str(C(maj) / G)
        'C/G'

        No suffix at all falls back to the name:

        >>> str(Chord(C, [C, E, G], name="major"))
        'C major'
        >>> str(Chord(C, [C, E, G], name="major") / E)
        'C major/E'
        """
        root = self.root.unqualify_octave()
        bass = self.bass.unqualify_octave()

        if self.suffix is not None:
            symbol = root.pitch.unicode + self.suffix
        elif self.name:
            symbol = f"{root.pitch.unicode} {self.name}"
        else:
            symbol = root.pitch.unicode

        if bass != root:
            symbol = f"{symbol}/{bass.pitch.unicode}"
        return symbol

    def __truediv__(self, tv: TonalVector) -> "Chord":
        """Returns a Chord with the same tones and root, but a different bass tone.

        This is an overload for the `/` operator, so you can write slash chords like this:

            C_major_over_E = C(maj) / E
        """
        return self.inversion(tv)
