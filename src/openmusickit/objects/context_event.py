import warnings
from collections.abc import Callable
from dataclasses import dataclass, field

from openmusickit.objects.omk_object import SequentialEvent, TonalObject
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.utils.omk_warning import OmkWarning
from openmusickit.values.time.duration import Duration, ZeroDuration


@dataclass(kw_only=True)
class ContextEvent(SequentialEvent):
    """An instantaneous event that changes the interpretation
    of subsequent material.

    A ContextEvent always has zero duration; it cannot be given one.

    >>> isinstance(ContextEvent().duration, ZeroDuration)
    True
    >>> ContextEvent(duration=None)
    Traceback (most recent call last):
    ...
    TypeError: ...
    """

    duration: Duration = field(default_factory=ZeroDuration, init=False)


@dataclass(kw_only=True)
class KeySignatureEvent(ContextEvent, TonalObject):
    """A key signature in a score, defined using a Key (which specifies tonality and alterations)
    xor a KeySignature (which only specifies alterations).

    `None` for both implies an undefined or undecided key signature.
    For an empty key signature with no alterations and no tonal implications,
    use `key=openmusickit.systems.wsmn.tonal.symbols.NoKey`.

    `key` and `key_signature` are what was given; `signature` is the effective
    KeySignature either way. Use `set_key`/`set_key_signature` to replace one
    with the other.
    """

    key: Key | None = None
    key_signature: KeySignature | None = None

    def __post_init__(self):
        if self.key is not None and self.key_signature is not None:
            raise ValueError("A Key includes a KeySignature, do not specify both.")

    @property
    def signature(self) -> KeySignature | None:
        """The effective key signature: the Key's, or the bare KeySignature, or None."""
        if self.key is not None:
            return self.key.signature
        return self.key_signature

    def set_key(self, key: Key) -> None:
        self.key_signature = None
        self.key = key

    def set_key_signature(self, key_signature: KeySignature) -> None:
        self.key = None
        self.key_signature = key_signature

    def transform_tones(self, operation: Callable[..., TonalVector], *args, **kwargs) -> None:
        """Transforms this key signature event in place: the Key is replaced by
        `Key.transform(operation, ...)`, or the bare KeySignature by
        `KeySignature.transform(operation, ...)`.

        An empty event (no Key and no KeySignature) and one holding `NoKey` are left
        as they are, with an `OmkWarning` that callers can catch or filter.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, M2, m3, P5, Major, NoKey
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalDirection

        A Key moves to a new tonic, keeping its mode:

        >>> event = KeySignatureEvent(key=Key.of(C, Major))
        >>> event.transform_tones(TonalVector.transpose, M2)
        >>> event.key.name, event.signature
        ('D Major', KeySignature(c=1, f=1))

        >>> event.transform_tones(TonalVector.transpose, P5, TonalDirection.DOWN)
        >>> event.key.name
        'G Major'

        A bare KeySignature is transformed letter by letter:

        >>> event = KeySignatureEvent(key_signature=KeySignature())
        >>> event.transform_tones(TonalVector.transpose, m3)
        >>> event.signature
        KeySignature(e=-1, a=-1, b=-1)
        >>> event.key is None
        True

        Empty and NoKey events warn and are unchanged:

        >>> import warnings
        >>> event = KeySignatureEvent(key=NoKey)
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     event.transform_tones(TonalVector.transpose, M2)
        >>> event.key is NoKey, str(caught[0].message)
        (True, 'You are attempting to transform an empty key signature. Nothing will happen.')
        """
        key = self.key

        if (key is None and self.key_signature is None) or (key is not None and key.tonic is None):
            warnings.warn(
                "You are attempting to transform an empty key signature. Nothing will happen.",
                OmkWarning,
                stacklevel=2,
            )
            return

        if key is None:
            self.set_key_signature(self.key_signature.transform(operation, *args, **kwargs))
        else:
            self.set_key(key.transform(operation, *args, **kwargs))
