"""The modal context a passage is heard in."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.tone_collection import ToneCollection


class ModalContext(ABC):
    """A tonal centre and the tones heard in relation to it.

    This is the general idea behind what different systems call a key, a
    mode, a maqam, a raga, or a pathet: WSMN's `Key` (tonic, mode pattern
    and key signature) is one implementation. A `ModalContextEvent` places
    one in a score to govern the material that follows.

    Anything that is notation rather than musical content (WSMN's printed
    key signature, for instance) belongs to the implementing system, not here.

    >>> from openmusickit.systems.wsmn.tonal.symbols import C, Major
    >>> from openmusickit.systems.wsmn.tonal.key import Key
    >>> isinstance(Key.of(C, Major), ModalContext)
    True
    """

    __slots__ = ()

    @property
    @abstractmethod
    def tonic(self) -> Tone | None:
        """The tonal centre; None for material with no modal context (atonal music, unpitched parts)."""

    @property
    @abstractmethod
    def tones(self) -> ToneCollection:
        """The tones of the context, in relation to the tonic."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A human-readable name, such as 'D Major' or 'No Key'."""

    @abstractmethod
    def transform(self, operation: Callable[..., Tone], *args, **kwargs) -> ModalContext:
        """Returns a new ModalContext made by applying `operation(tone, *args, **kwargs)`
        to the tonic and tones, in whatever way keeps the context coherent for its system."""
