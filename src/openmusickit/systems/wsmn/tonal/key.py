from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from numbers import Real

from openmusickit.systems.wsmn.tonal.chords import ChordQuality
from openmusickit.systems.wsmn.tonal.constants import C_LEN, D_LEN, DIATONES, SHARP_ORDER
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection, TonalVector
from openmusickit.values.tone.modal_context import ModalContext
from openmusickit.values.tone.tone_collection import ToneCollection, apply_tone_operation


class KeySignature(tuple):
    """Representation of the flat or sharp alterations of a key signature,
    in semitones up or down from natural:
    - Sharps are positive, flats are negative
    - Handles double and triple sharps and flats
    - Use fractional values for microtones

    Positional order is C, D, E, F, G, A, B;
    each letter name is also available as a property.

    Examples
    --------

    >>> ks = KeySignature()
    >>> ks.c, ks.b
    (0, 0)

    >>> ks = KeySignature(c=1, f=1)
    >>> ks.f, ks.g
    (1, 0)

    >>> ks = KeySignature(e=-1, a=-1, b=-1)
    >>> ks.e, ks.d
    (-1, 0)

    >>> ks = KeySignature(c=-1, d=-1, e=-2, f=-1, g=-1, a=-2, b=-2) # double flats
    >>> ks.e, ks.f
    (-2, -1)

    >>> ks = KeySignature(f=1, b=-1) # non-standard key signatures
    >>> ks.f, ks.b
    (1, -1)

    Beyond a triple sharp or flat there is no signature:

    >>> KeySignature(f=4)
    Traceback (most recent call last):
    ...
    ValueError: Key signature alterations must be between -3 and 3
    """

    def __new__(
        cls,
        c: Real = 0,
        d: Real = 0,
        e: Real = 0,
        f: Real = 0,
        g: Real = 0,
        a: Real = 0,
        b: Real = 0,
    ):
        values = (c, d, e, f, g, a, b)

        if any(not -3 <= value <= 3 for value in values):
            raise ValueError("Key signature alterations must be between -3 and 3")

        return super().__new__(cls, values)

    def __getnewargs__(self) -> tuple:
        """Lets copy and pickle rebuild a KeySignature through `__new__`.

        >>> import copy
        >>> copy.deepcopy(KeySignature(c=1, f=1)) == KeySignature(c=1, f=1)
        True
        """
        return tuple(self)

    # Convenience constructor for "normal" keysignatures.

    @classmethod
    def from_alts(cls, alts: int) -> KeySignature:
        """Create a key signature by specifying the number of sharps (positive int) or flats (negative int).
        Assumes normal ordering (F C G D A E B | B E A D G C F) and should be symmetrical to `fifths`.

        Examples
        --------

        >>> KeySignature.from_alts(2)
        KeySignature(c=1, f=1)

        >>> KeySignature.from_alts(-3)
        KeySignature(e=-1, a=-1, b=-1)

        >>> KeySignature.from_alts(-10)
        KeySignature(c=-1, d=-1, e=-2, f=-1, g=-1, a=-2, b=-2)

        >>> KeySignature.from_alts(5).fifths
        5
        """
        order = SHARP_ORDER if alts > 0 else SHARP_ORDER[::-1]
        step = 1 if alts > 0 else -1

        values = [0] * 7
        for i in range(abs(alts)):
            values[order[i % D_LEN]] += step

        return cls(*values)

    @property
    def c(self) -> Real:
        return self[0]

    @property
    def d(self) -> Real:
        return self[1]

    @property
    def e(self) -> Real:
        return self[2]

    @property
    def f(self) -> Real:
        return self[3]

    @property
    def g(self) -> Real:
        return self[4]

    @property
    def a(self) -> Real:
        return self[5]

    @property
    def b(self) -> Real:
        return self[6]

    @property
    def fifths(self) -> int:
        """Returns the MusicXML representation of the key signature, which walks around the circle of fifths.
        For example, C major has 0 fifths, G major has 1 fifth, F major has -1 fifth, etc.

        Raises ValueError if self is a non-standard keysignature
        (for example, if the signature mixes sharps and flats or
        they do not go in the standard order [F# C# G# D# A# E# B# | Bb Eb Ab Db Gb Cb Fb]).
        This error should be caught by callers and another key signature resolution strategy should be used.

        Examples
        --------

        >>> KeySignature().fifths
        0

        >>> KeySignature(c=1, f=1).fifths
        2

        >>> KeySignature(e=-1, a=-1, b=-1).fifths
        -3

        >>> KeySignature(c=-1, d=-1, e=-2, f=-1, g=-1, a=-2, b=-2).fifths
        -10

        >>> KeySignature(f=1, b=-1).fifths
        Traceback (most recent call last):
            ...
        ValueError: This KeySignature is non-standard and has no fifths value.
        """
        error = ValueError("This KeySignature is non-standard and has no fifths value.")

        ordered = [self[i] for i in SHARP_ORDER]

        if any(not isinstance(value, int) or not -3 <= value <= 3 for value in ordered):
            raise error

        # Only two distinct values are allowed (or one, e.g. all zeros for C major),
        # and they must be exactly one apart.
        distinct = set(ordered)
        if len(distinct) > 2 or max(distinct) - min(distinct) > 1:
            raise error

        # Values must be clustered with the higher value on the left,
        # i.e. the sequence is non-increasing in sharp order.
        if any(left < right for left, right in zip(ordered, ordered[1:], strict=False)):
            raise error

        return sum(ordered)

    def transform(self, operation: Callable[..., TonalVector], *args, **kwargs) -> KeySignature:
        """Returns a new KeySignature made by applying `operation` to each of the
        seven letters, taken as the pitches C, D, E, F, G, A, B with this
        signature's alterations, and reading the new alteration of each letter
        from the result.

        `operation` is called as `operation(tone, *args, **kwargs)` and must
        return a TonalVector, or a TypeError is raised. If two letters are sent
        to the same letter, the result is not a key signature and a ValueError
        is raised. Alterations must be integers (the letter-pitches must be
        expressible as TonalVectors); otherwise a ValueError is raised.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import M2

        Transposition, including of a non-standard signature
        (C D E F♯ G A B♭ up a major second is D E F♯ G♯ A B C):

        >>> KeySignature().transform(TonalVector.transpose, M2)
        KeySignature(c=1, f=1)
        >>> KeySignature(f=1, b=-1).transform(TonalVector.transpose, M2)
        KeySignature(f=1, g=1)

        An operation that needs no operand:

        >>> def sharpen(tv):
        ...     return tv + TonalVector((0, 1))
        >>> KeySignature().transform(sharpen)
        KeySignature(c=1, d=1, e=1, f=1, g=1, a=1, b=1)

        An operation that does not produce a TonalVector is rejected:

        >>> KeySignature().transform(str)
        Traceback (most recent call last):
            ...
        TypeError: ...
        """
        if any(not isinstance(alt, int) for alt in self):
            raise ValueError("Only a KeySignature with integer alterations can be transformed.")

        alts: dict[int, int] = {}
        for d, alt in enumerate(self):
            tone = TonalVector((d, (DIATONES[d].chromatic + alt) % C_LEN))
            new_tone = apply_tone_operation(operation, tone, *args, expected=TonalVector, **kwargs)
            if new_tone.d in alts:
                raise ValueError(
                    f"Cannot build a KeySignature: `operation` sent two letters to "
                    f"{new_tone.pitch.letter}."
                )
            alts[new_tone.d] = new_tone.pitch.alteration

        return KeySignature(*(alts[i] for i in range(7)))

    def transpose(
        self, x: TonalVector, direction: TonalDirection = TonalDirection.UP
    ) -> KeySignature:
        """Returns this key signature transposed by the interval `x`: each letter
        moves by `x`, so a standard signature moves around the circle of fifths
        as if it were the signature of a key whose tonic is transposed by `x`.
        (Since relative keys share a signature, this is equally correct for any mode.)

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import M2, m3, P5, a4
        >>> KeySignature().transpose(M2)
        KeySignature(c=1, f=1)

        >>> KeySignature().transpose(m3)
        KeySignature(e=-1, a=-1, b=-1)

        >>> KeySignature(f=1).transpose(P5, TonalDirection.DOWN)
        KeySignature()

        >>> KeySignature.from_alts(3).transpose(a4).fifths
        9

        >>> KeySignature(f=1, b=-1).transpose(M2)
        KeySignature(f=1, g=1)
        """
        return self.transform(TonalVector.transpose, x, direction)

    def __repr__(self) -> str:
        """Only non-zero alterations are shown, matching how a KeySignature is typically constructed.

        Examples
        --------

        >>> KeySignature()
        KeySignature()

        >>> KeySignature(c=1, f=1)
        KeySignature(c=1, f=1)

        >>> KeySignature(e=-1, a=-1, b=-1)
        KeySignature(e=-1, a=-1, b=-1)
        """
        alts = ", ".join(
            f"{name}={value!r}" for name, value in zip("cdefgab", self, strict=False) if value
        )
        return f"{type(self).__name__}({alts})"


@dataclass(slots=True, kw_only=True, frozen=True)
class ModePattern:
    """A pattern of intervals from TonalVector((0, 0)), which defines a mode.

    >>> from openmusickit.systems.wsmn.tonal.symbols import Dorian
    >>> Dorian.name, len(Dorian.tones), Dorian.tones[0]
    ('Dorian', 7, TonalVector((0, 0)))
    >>> [format(t) for t in Dorian.tones]
    ['C', 'D', 'E♭', 'F', 'G', 'A', 'B♭']
    """

    name: str
    tones: ToneCollection
    quality: ChordQuality | None = None

    def __post_init__(self):
        if self.tones[0] != TonalVector((0, 0)):
            raise ValueError("A ModePattern must begin with TonalVector((0, 0))")


@dataclass(slots=True, kw_only=True, frozen=True)
class Key(ModalContext):
    """A key in the tonal or modal system: WSMN's ModalContext.

    `tonic` is None when no tonality is asserted. That is either "no key"
    (atonal music, unpitched parts: `symbols.NoKey`, which also has no
    signature, corresponding to MusicXML `<mode>none</mode>`), or a bare
    signature such as "three flats" that is not saying E-flat major or
    C minor (see `from_signature`). The two differ under transposition: a
    bare signature moves with the music; no key stays no key.

    >>> from openmusickit.systems.wsmn.tonal.symbols import D, Major, NoKey
    >>> d = Key.of(D, Major)
    >>> d.name, d.signature
    ('D Major', KeySignature(c=1, f=1))
    >>> [format(t) for t in d.tones]
    ['D', 'E', 'F♯', 'G', 'A', 'B', 'C♯']
    >>> NoKey.tonic is None, NoKey.name
    (True, 'No Key')
    """

    tonic: TonalVector | None
    signature: KeySignature | None
    tones: ToneCollection = field(default_factory=ToneCollection)  # empty: no tones asserted
    mode: ModePattern | None = None
    name: str | None = None

    def __post_init__(self):
        if self.name is None:
            object.__setattr__(self, "name", self._default_name())

    def _default_name(self) -> str:
        if self.tonic is None:
            if self.signature is None:
                return "No Key"
            fifths = self.signature.fifths
            if fifths == 0:
                return "no sharps or flats"
            return f"{abs(fifths)} {'sharps' if fifths > 0 else 'flats'}"
        if self.mode is not None:
            return f"{self.tonic.pitch.unicode} {self.mode.name}"
        return f"{self.tonic.pitch.unicode} (unspecified mode)"

    @classmethod
    def of(
        cls, tonic: TonalVector, mode: ModePattern, signature: KeySignature | None = None
    ) -> Key:
        """Convenience constructor for Key.

        The key's tones are the mode pattern transposed to the tonic.
        If `signature` is not given, it is derived from those tones:
        each letter takes the alteration of its tone in the key,
        and letters not present in the mode (e.g. in a pentatonic mode) stay natural.

        Raises ValueError if the same letter occurs with different alterations
        (e.g. a mode containing both F and F#); pass `signature` explicitly in that case.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, Eb, Fx, Major, Minor

        >>> c = Key.of(C, Major)
        >>> c.name, c.mode.name, c.signature
        ('C Major', 'Major', KeySignature())
        >>> [t.pitch.unicode for t in c.tones]
        ['C', 'D', 'E', 'F', 'G', 'A', 'B']

        >>> Key.of(Eb, Major).signature
        KeySignature(e=-1, a=-1, b=-1)

        >>> fs = Key.of(Fx, Minor)
        >>> fs.name, fs.signature.fifths
        ('F♯ Minor', 3)
        >>> fs.tones.root is Fx
        True

        An explicit signature is used as given, without inspection:

        >>> Key.of(C, Major, KeySignature.from_alts(-1)).signature
        KeySignature(b=-1)
        """
        transposed = mode.tones.transform(TonalVector.transpose, tonic)
        tones = ToneCollection(transposed, root=tonic, name=transposed.name_template)

        if signature is None:
            alts: dict[int, int] = {}
            for tone in tones:
                alt = tone.pitch.alteration
                if alts.setdefault(tone.d, alt) != alt:
                    raise ValueError(
                        f"Cannot derive a KeySignature: {tone.pitch.letter} occurs with "
                        f"more than one alteration in {mode.name}. Pass `signature` explicitly."
                    )
            signature = KeySignature(*(alts.get(i, 0) for i in range(7)))

        return cls(
            tonic=tonic,
            tones=tones,
            signature=signature,
            mode=mode,
        )

    @classmethod
    def from_signature(cls, signature: KeySignature) -> Key:
        """A key signature asserting no tonality: the alterations, and nothing else.

        >>> three_flats = Key.from_signature(KeySignature.from_alts(-3))
        >>> three_flats.name, three_flats.tonic, len(three_flats.tones)
        ('3 flats', None, 0)

        An empty signature is still a signature, unlike `NoKey`:

        >>> from openmusickit.systems.wsmn.tonal.symbols import NoKey
        >>> Key.from_signature(KeySignature()).name, NoKey.signature
        ('no sharps or flats', None)
        """
        return cls(tonic=None, signature=signature)

    def transform(self, operation: Callable[..., TonalVector], *args, **kwargs) -> Key:
        """Returns a new Key made by applying `operation` to this key's tonic
        (and to its tones and signature).

        If the key has a mode pattern, the new key is that mode on the new tonic
        (as in `Key.of`), with the signature transformed alongside so that an
        explicitly given signature is carried over. Otherwise the tones and
        signature are transformed directly. A bare signature (no tonic) is
        transformed letter by letter; `NoKey` has nothing to transform and is
        returned as it is.

        For operations other than transposition, "keep the mode" and "transform
        the tones" can disagree (C Major inverted about C is C Major by the
        first rule and C Phrygian by the second); the mode is kept.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, M2, Major, NoKey
        >>> Key.of(C, Major).transform(TonalVector.transpose, M2).name
        'D Major'
        >>> NoKey.transform(TonalVector.transpose, M2) == NoKey
        True
        >>> from openmusickit.systems.wsmn.tonal.symbols import m3
        >>> Key.from_signature(KeySignature()).transform(TonalVector.transpose, m3).signature
        KeySignature(e=-1, a=-1, b=-1)
        """
        if self.signature is None:
            return self
        signature = self.signature.transform(operation, *args, **kwargs)
        if self.tonic is None:
            return Key.from_signature(signature)

        new_tonic = apply_tone_operation(
            operation, self.tonic, *args, expected=TonalVector, **kwargs
        )

        if self.mode is not None:
            return Key.of(new_tonic, self.mode, signature)

        return Key(
            tonic=new_tonic,
            tones=self.tones.transform(operation, *args, **kwargs),
            signature=signature,
        )
