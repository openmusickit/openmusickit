import warnings
from collections.abc import Callable
from dataclasses import dataclass, field

from openmusickit.errors import OmkWarning
from openmusickit.objects.omk_object import SequentialEvent, TonalObject
from openmusickit.values.time.duration import Duration, ZeroDuration
from openmusickit.values.tone.modal_context import ModalContext
from openmusickit.values.tone.tone import Tone


@dataclass(kw_only=True, slots=True)
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


@dataclass(kw_only=True, slots=True)
class ModalContextEvent(ContextEvent, TonalObject):
    """Sets the modal context (in WSMN, the key or key signature) for the
    material that follows.

    `None` means undefined or undecided. For WSMN, "no key" is
    `symbols.NoKey` and a bare key signature is `Key.from_signature(...)`;
    the printed signature is reached through the Key
    (`event.modal_context.signature`), never through the event.
    """

    modal_context: ModalContext | None = None

    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces the modal context, in place, with `modal_context.transform(operation, ...)`.

        An event with no modal context is left as it is, with an `OmkWarning`
        that callers can catch or filter.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, M2, m3, P5, Major
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection

        A Key moves to a new tonic, keeping its mode:

        >>> event = ModalContextEvent(modal_context=Key.of(C, Major))
        >>> event.transform_tones(TonalVector.transpose, M2)
        >>> event.modal_context.name, event.modal_context.signature
        ('D Major', KeySignature(c=1, f=1))

        >>> event.transform_tones(TonalVector.transpose, P5, TonalDirection.DOWN)
        >>> event.modal_context.name
        'G Major'

        A bare key signature is transformed letter by letter:

        >>> event = ModalContextEvent(modal_context=Key.from_signature(KeySignature()))
        >>> event.transform_tones(TonalVector.transpose, m3)
        >>> event.modal_context.signature, event.modal_context.tonic
        (KeySignature(e=-1, a=-1, b=-1), None)

        An empty event warns and is unchanged:

        >>> import warnings
        >>> event = ModalContextEvent()
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     event.transform_tones(TonalVector.transpose, M2)
        >>> event.modal_context is None, str(caught[0].message)
        (True, 'You are attempting to transform an event with no modal context. Nothing will happen.')
        """
        if self.modal_context is None:
            warnings.warn(
                "You are attempting to transform an event with no modal context. Nothing will happen.",
                OmkWarning,
                stacklevel=2,
            )
            return

        self.modal_context = self.modal_context.transform(operation, *args, **kwargs)
