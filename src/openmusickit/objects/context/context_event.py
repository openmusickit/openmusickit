import warnings
from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.objects.omk_object import SequentialObject
from openmusickit.utils.omk_warning import OmkWarning
from openmusickit.values.time.duration import Duration, ZeroDuration
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection

@dataclass(slots=True, kw_only=True)
class ContextEvent(SequentialObject):
    """An instantaneous event that changes the interpretation
    of subsequent material."""

    @property
    def duration(self) -> Duration:
        return ZeroDuration

class TransposeDirection(StrEnum):
    UP = auto()
    DOWN = auto()
    TO_TONIC = auto()


@dataclass(slots=True, kw_only=True)
class KeySignatureEvent(ContextEvent):
    """A key signature in a score, defined using a Key (which specifies tonality and alterations)
    xor a KeySignature (which only specifies alterations).

    'None' values in both Key and KeySignature imply an undefined or undecided key signature.
    For an empty key signature with no alterations and no tonal implications,
    use `_key = openmusickit.systems.wsmn.tonal.symbols.NoKey`
    """
    _key: Key | None = None
    _key_signature: KeySignature | None = None

    def __post_init__(self):
        if self._key is not None and self._key_signature is not None:
            raise ValueError("A Key includes a KeySignature, do not specify both.")

    @property
    def key(self) -> Key | None:
        return self._key

    @property
    def key_signature(self) -> KeySignature | None:
        return self._key_signature or (self.key.signature if self.key is not None else None) or None

    def set_key(self, key: Key) -> None:
        self._key_signature = None
        self._key = key

    def set_key_signature(self, key_signature: KeySignature) -> None:
        self._key = None
        self._key_signature = key_signature

    def transpose(self, x: TonalVector, direction: TransposeDirection = TransposeDirection.UP) -> None:
        """Transposes this key signature event in place.

        With UP or DOWN, `x` is an interval and the tonic moves by that interval.
        With TO_TONIC, `x` is a pitch and becomes the new tonic.

        If the event holds a Key, a new Key is built on the new tonic:
        from the Key's mode pattern if it has one (so the signature is re-derived
        from the mode, as in `Key.of`), or otherwise by transposing its tones and
        signature directly.

        If the event holds only a KeySignature, there is no tonic, so TO_TONIC raises
        a ValueError. UP and DOWN move the signature around the circle of fifths
        (see `KeySignature.transpose`); this raises an AttributeError for a
        non-standard signature, which cannot be transposed without knowing the key.

        An empty event (no Key and no KeySignature) and one holding `NoKey` are left
        as they are, with an `OmkWarning` that callers can catch or filter.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, Eb, A, M2, m3, P5, Major, Minor, NoKey

        A Key moves to a new tonic, keeping its mode:

        >>> event = KeySignatureEvent(_key=Key.of(C, Major))
        >>> event.transpose(M2)
        >>> event.key.name, event.key_signature
        ('D Major', KeySignature(c=1, f=1))

        >>> event.transpose(P5, TransposeDirection.DOWN)
        >>> event.key.name
        'G Major'

        >>> event.transpose(Eb, TransposeDirection.TO_TONIC)
        >>> event.key.name, event.key_signature.fifths
        ('E♭ Major', -3)

        A bare KeySignature moves around the circle of fifths:

        >>> event = KeySignatureEvent(_key_signature=KeySignature())
        >>> event.transpose(m3)
        >>> event.key_signature
        KeySignature(e=-1, a=-1, b=-1)
        >>> event.key is None
        True

        ... but has no tonic to move:

        >>> event.transpose(A, TransposeDirection.TO_TONIC)
        Traceback (most recent call last):
            ...
        ValueError: Cannot transpose TO_TONIC: this event has a KeySignature but no Key, so it has no tonic.

        Empty and NoKey events warn and are unchanged:

        >>> import warnings
        >>> event = KeySignatureEvent(_key=NoKey)
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     event.transpose(M2)
        >>> event.key is NoKey, str(caught[0].message)
        (True, 'You are attempting to transpose an empty key signature. Nothing will happen.')
        """
        key = self.key

        if key is None and self._key_signature is None or key is not None and key.tonic is None:
            warnings.warn(
                "You are attempting to transpose an empty key signature. Nothing will happen.",
                OmkWarning,
                stacklevel=2,
            )
            return

        if key is None:
            if direction == TransposeDirection.TO_TONIC:
                raise ValueError(
                    "Cannot transpose TO_TONIC: this event has a KeySignature but no Key, "
                    "so it has no tonic."
                )
            self.set_key_signature(self._key_signature.transpose(x, TonalDirection(direction)))
            return

        if direction == TransposeDirection.TO_TONIC:
            new_tonic = x
            # Express the move as an upward interval so tones and signature can follow the tonic.
            interval, tonal_direction = x - key.tonic, TonalDirection.UP
        else:
            tonal_direction = TonalDirection(direction)
            new_tonic = key.tonic.transpose(x, tonal_direction)
            interval = x

        if key._mode is not None:
            self.set_key(Key.of(new_tonic, key._mode))
        else:
            self.set_key(Key(
                tonic=new_tonic,
                tones=key.tones.transform(TonalVector.transpose, interval, tonal_direction),
                signature=key.signature.transpose(interval, tonal_direction),
            ))