import warnings
from dataclasses import dataclass
from typing import Callable

from openmusickit.objects.omk_object import SequentialObject, TonalObject
from openmusickit.utils.omk_warning import OmkWarning
from openmusickit.values.time.duration import Duration, ZeroDuration
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector

@dataclass(slots=True, kw_only=True)
class ContextEvent(SequentialObject):
    """An instantaneous event that changes the interpretation
    of subsequent material."""

    @property
    def duration(self) -> Duration:
        return ZeroDuration

@dataclass(slots=True, kw_only=True)
class KeySignatureEvent(ContextEvent, TonalObject):
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

        >>> event = KeySignatureEvent(_key=Key.of(C, Major))
        >>> event.transform_tones(TonalVector.transpose, M2)
        >>> event.key.name, event.key_signature
        ('D Major', KeySignature(c=1, f=1))

        >>> event.transform_tones(TonalVector.transpose, P5, TonalDirection.DOWN)
        >>> event.key.name
        'G Major'

        A bare KeySignature is transformed letter by letter:

        >>> event = KeySignatureEvent(_key_signature=KeySignature())
        >>> event.transform_tones(TonalVector.transpose, m3)
        >>> event.key_signature
        KeySignature(e=-1, a=-1, b=-1)
        >>> event.key is None
        True

        Empty and NoKey events warn and are unchanged:

        >>> import warnings
        >>> event = KeySignatureEvent(_key=NoKey)
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     event.transform_tones(TonalVector.transpose, M2)
        >>> event.key is NoKey, str(caught[0].message)
        (True, 'You are attempting to transform an empty key signature. Nothing will happen.')
        """
        key = self.key

        if key is None and self._key_signature is None or key is not None and key.tonic is None:
            warnings.warn(
                "You are attempting to transform an empty key signature. Nothing will happen.",
                OmkWarning,
                stacklevel=2,
            )
            return

        if key is None:
            self.set_key_signature(self._key_signature.transform(operation, *args, **kwargs))
        else:
            self.set_key(key.transform(operation, *args, **kwargs))
