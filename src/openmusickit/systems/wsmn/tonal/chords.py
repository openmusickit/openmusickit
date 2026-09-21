from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum, auto

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.utils.number_names import ORDINALS
from openmusickit.values.tone.tone_collection import ToneCollection, apply_tone_operation


class ChordQuality(StrEnum):
    """The broad family a chord type belongs to.

    >>> from openmusickit.systems.wsmn.tonal.symbols import maj, hdim7
    >>> maj.quality, hdim7.quality is ChordQuality.HDM
    (<ChordQuality.MAJ: 'maj'>, True)
    """

    MAJ = auto()
    MIN = auto()
    SUS = auto()
    POW = auto()  # open / power chord
    AUG = auto()
    DIM = auto()
    DOM = auto()
    HDM = auto()  # half diminished


@dataclass(frozen=True, slots=True, init=False, repr=False)
class _ChordBase(ToneCollection):
    """What ChordType and Chord share: a bass tone, a lead-sheet suffix, and the
    inversion/arpeggiation logic. Equality and hashing are by tones, root and bass;
    name and suffix are ignored (as `name` is for ToneCollection).

    >>> from openmusickit.systems.wsmn.tonal.symbols import maj, C, E, G
    >>> maj == ChordType([C, E, G], name="anything"), maj == maj.inversion(1)
    (True, False)
    >>> C(maj) == C(maj), C(maj) == C(maj) / E
    (True, False)
    """

    bass: TonalVector = field(kw_only=True)
    suffix: str | None = field(default=None, kw_only=True, compare=False)

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
        return self._rotate_to_bass()

    def _rotate_to_bass(self) -> ToneCollection:
        """Shared logic for `arpeggiate()`: the tones rotated so the bass
        comes first, as a plain ToneCollection with root and name preserved.
        Used by both ChordType and Chord."""
        tones = list(self)
        i = tones.index(self.bass)
        return ToneCollection(tones[i:] + tones[:i], root=self.root, name=self.name_template)

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
            name = self.name_template

        return bass, name


@dataclass(frozen=True, slots=True, repr=False)
class ChordType(_ChordBase):
    """Chord definition, as an ordered collection of TonalVectors
    representing intervals from the root (0,0).

    Tone order is significant:
    it distinguishes chords that share the same pitch classes
    but are conventionally named/voiced differently
    (for example, an added 2nd vs. an added 9th).

    A ChordType is realized at a root by calling it (or the root) to get a `Chord`:

    >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Bb, dom7
    >>> list(dom7) == [C, E, G, Bb], dom7.root, str(dom7)
    (True, TonalVector((0, 0)), '7')
    >>> str(G(dom7))
    'G7'
    """

    quality: ChordQuality | None = field(default=None, kw_only=True, compare=False)

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
        object.__setattr__(self, "bass", self.root if bass is None else bass)
        object.__setattr__(self, "quality", quality)
        # Lead-sheet suffix, e.g. "maj7", "sus4", "7♭9". Empty string for a plain major triad.
        object.__setattr__(self, "suffix", suffix)

    def inversion(self, inv: int | TonalVector, name: str | None = None) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone:
        the `inv`-th tone, or the tone given.

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, G
        >>> maj.inversion(1).bass, str(maj.inversion(1))
        (TonalVector((2, 4)), 'major 1st inv.')
        >>> maj.inversion(G) == maj.inversion(2)
        True
        """
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

        Intended to be used with TonalVector's *reverse* `__call__`,
        so that a chord reads root first, as on a lead sheet:

        >>> from openmusickit.systems.wsmn.tonal.symbols import E, maj
        >>> [format(t) for t in maj(E)]
        ['E', 'G♯', 'B']
        >>> E(maj) == maj(E), str(E(maj))
        (True, 'E')
        """
        tones = [t + tv for t in self]
        root = tv
        bass = self.bass + tv

        return Chord(root, tones, bass, self.name_template, self.suffix)

    def __truediv__(self, tv: TonalVector) -> "ChordType":
        """Returns a ChordType with the same tones, but a different bass tone.

        This is an overload for the `/` operator, so a slash chord reads as written:

        >>> from openmusickit.systems.wsmn.tonal.symbols import maj, G
        >>> (maj / G).bass, str(maj / G)
        (TonalVector((4, 7)), 'major 2nd inv.')
        """
        return self.inversion(tv)


@dataclass(frozen=True, slots=True, repr=False)
class Chord(_ChordBase):
    """A concrete realization of a ChordType at a specific root pitch.

    Unlike ChordType, a Chord's root is not necessarily `TonalVector(0,0)`;
    it is wherever the ChordType was realized
    (e.g. `E(maj)` produces a Chord rooted at E).

    >>> from openmusickit.systems.wsmn.tonal.symbols import E, maj
    >>> chord = E(maj)
    >>> chord.root, chord.bass, str(chord)
    (TonalVector((2, 4)), TonalVector((2, 4)), 'E')
    """

    def __init__(
        self,
        root: TonalVector,
        tones: Iterable[TonalVector],
        bass: TonalVector | None = None,
        name: str | None = None,
        suffix: str | None = None,
    ):

        super().__init__(tuple(tones), root=root, name=name)
        object.__setattr__(self, "bass", self.root if bass is None else bass)
        object.__setattr__(self, "suffix", suffix)

    def inversion(self, inv: int | TonalVector, name: str | None = None) -> "Chord":
        """Returns a Chord with the same tones and root, but a different bass tone.

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, maj
        >>> second = C(maj).inversion(2)
        >>> str(second), second.root
        ('C/G', TonalVector((0, 0)))
        """
        bass, name = self._resolve_inversion(inv, name)
        return Chord(self.root, self, bass, name, self.suffix)

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
        as its first argument and returns a TonalVector will do; if it does
        not return a TonalVector, a TypeError is raised.

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

        def apply(tone: TonalVector) -> TonalVector:
            return apply_tone_operation(operation, tone, *args, expected=TonalVector, **kwargs)

        root = apply(self.root)
        tones = [apply(t) for t in self]
        bass = apply(self.bass)

        if new_name is None:
            new_name = self.name_template
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

        This is an overload for the `/` operator, so a slash chord reads as written:

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, maj
        >>> str(C(maj) / E)
        'C/E'
        """
        return self.inversion(tv)
