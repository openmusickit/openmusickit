from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from openmusickit.values.time.duration import Duration, Measurable
from openmusickit.values.tone.tone import Tone


@dataclass(kw_only=True, slots=True)
class OmkObject:
    """Base class for everything that can be a node in the graph.

    Every object has an `id`: a UUID that stays with it across sessions and
    storage, distinct from any ids a graph backend or database assigns. Value
    types (a pitch, a chord type, a quarter note) have no id; only things that
    appear in a score do.

    Equality means "same musical content": the id (which stands for the
    object's place in a graph) and `meta` are excluded, so two separately
    built B-flat quarter notes compare equal while remaining distinct objects
    (`is` is unaffected). Objects are mutable and unhashable.

    `meta` is free-form storage for consumers of OMK (an app's on-screen
    placement of a note, an importer's source reference); OMK itself never
    reads it. Objects are slotted, so no other attributes can be added:

    >>> OmkObject().anything = 1
    Traceback (most recent call last):
    ...
    AttributeError: ...
    """

    _id: UUID = field(default_factory=uuid4, init=False, repr=False, compare=False)
    meta: dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def id(self) -> UUID:
        return self._id


@dataclass(kw_only=True, slots=True)
class SequentialEvent(OmkObject):
    """An OmkObject that takes up time and can be placed in sequence (with NEXT edges).

    The duration is a length, so it cannot be negative, however it is set:

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> SequentialEvent(duration=-quarter)
    Traceback (most recent call last):
    ...
    ValueError: A SequentialEvent cannot have a negative duration: MetricalDuration(-1, 4)
    """

    duration: Duration | None = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "duration" and isinstance(value, Measurable) and value.rational_length < 0:
            raise ValueError(f"A SequentialEvent cannot have a negative duration: {value!r}")
        super().__setattr__(name, value)

    def alter_duration(self, operation: Callable[[Duration, Any], Duration], operand: Any) -> None:
        new_duration = operation(self.duration, operand)
        self.duration = new_duration


class TonalObject(ABC):
    """Mixin for objects with tonal content that a Tone -> Tone operation
    can be pushed through (notes, chord symbols, key signatures, ...).

    `OmkGraph.transform_tones` applies one operation to every TonalObject on
    a span; each object decides what its tonal content is.

    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, M2
    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> note = NoteEvent(tones={C})
    >>> isinstance(note, TonalObject)
    True
    >>> note.transform_tones(TonalVector.transpose, M2)
    >>> note.tones == {D}
    True
    """

    __slots__ = ()

    @abstractmethod
    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces this object's tonal content, in place, with the result of
        applying `operation(tone, *args, **kwargs)` to it."""


@dataclass(kw_only=True, slots=True)
class Spanner(OmkObject):
    """Used with edges of type STARTS_AT and ENDS_AT
    to group a sequence of SequentialEvents together.

    Articulations (such as slurs and crescendos) and other objects
    which normally attach to a single OmkObject can attach to a Spanner
    to indicate that they apply to the entire sequence of objects.

    >>> from openmusickit.objects.marking import MarkSpanner
    >>> from openmusickit.objects.part import Stint
    >>> from openmusickit.systems.wsmn.scoring.symbols import slur
    >>> isinstance(MarkSpanner(mark=slur), Spanner), isinstance(Stint(), Spanner)
    (True, True)
    """

    pass
