from dataclasses import dataclass
from numbers import Real

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.tone.tone_collection import ToneCollection
from openmusickit.systems.wsmn.tonal.chords import Quality



class KeySignature(tuple):
    """Representation of the flat or sharp alterations of a key signature,
    in semitones up or down from natural:
    - Sharps are positive, flats are negative
    - Handles double and triple sharps and flats
    - Use fractional values for microtones

    Positional order is C, D, E, F, G, A, B;
    each letter name is also available as a property.

    Examples:

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
        """Returns the MusicXML representation of the key signature, which is jumps around the circle of fifths. 
        For example, C major has 0 fifths, G major has 1 fifth, F major has -1 fifth, etc.
        
        Raises AttributeError if self is a non-standard keysignature 
        (for example, if the signature mixes sharps and flats or 
        they do not go in the standard order [F# C# G# D# A# E# B# | Bb Eb Ab Db Gb Cb Fb]).
        This error should be caught by callers and another key signature resolution strategy should be used.

        Examples:

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
            AttributeError: This KeySignature has no valid fifths property.
        """
        sharp_order = [3, 0, 4, 1, 5, 2, 6]
        error = AttributeError("This KeySignature has no valid fifths property.")

        ordered = [self[i] for i in sharp_order]

        if any(not isinstance(value, int) or not -3 <= value <= 3 for value in ordered):
            raise error

        # Only two distinct values are allowed (or one, e.g. all zeros for C major),
        # and they must be exactly one apart.
        distinct = set(ordered)
        if len(distinct) > 2 or max(distinct) - min(distinct) > 1:
            raise error

        # Values must be clustered with the higher value on the left,
        # i.e. the sequence is non-increasing in sharp order.
        if any(left < right for left, right in zip(ordered, ordered[1:])):
            raise error

        return sum(ordered)


@dataclass(slots=True, kw_only=True, frozen=True)
class ModePattern:
    """A pattern of intervals from TonalVector((0, 0)), which defines a mode."""
    name: str
    tones: ToneCollection
    quality: Quality | None = None

    def __post_init__(self):
        if self.tones[0] is not TonalVector((0, 0)):
            raise ValueError("A ModePattern must begin with TonalVector((0, 0))")

@dataclass(slots=True, kw_only=True, frozen=True)
class Key:
    """A key in the tonal or modal system."""
    tonic: TonalVector
    tones: ToneCollection
    signature: KeySignature
    _mode: ModePattern | None = None
    _name: str | None = None

    @property
    def mode(self) -> str | None:
        """Returns the mode pattern of this key, if it has one."""
        return self._mode.name if self._mode else None

    @property
    def name(self) -> str | None:
        """Returns the name of this key, if it has one."""
        if self._name:
            return self._name

        if self._mode:
            return f"{self.tonic.pitch.unicode} {self._mode.name}"

        return f"{self.tonic.pitch.unicode} (unspecified mode)"