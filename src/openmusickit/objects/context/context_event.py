from dataclasses import dataclass

from openmusickit.objects.omk_object import SequentialObject
from openmusickit.values.time.duration import Duration, ZeroDuration
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature

@dataclass(slots=True, kw_only=True)
class ContextEvent(SequentialObject):
    """An instantaneous event that changes the interpretation
    of subsequent material."""

    @property
    def duration(self) -> Duration:
        return ZeroDuration

@dataclass(slots=True, kw_only=True)
class KeySignatureEvent(ContextEvent):
    """A key signature in a score, defined using a Key (which specifies tonality and alterations)
    or just a KeySignature (which only specifies alterations).

    'None' values in both Key and KeySignature imply an undefined or undecided key signature.
    For an empty key signature with no alterations and no tonal implications,
    use systems.wsmn.tonal.symbols.NoKey
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

    # TODO: Transpose