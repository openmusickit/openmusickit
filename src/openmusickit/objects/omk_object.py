from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from openmusickit.utils.id import OmkId
from openmusickit.values.time.duration import Duration
from openmusickit.values.tone.tone import Tone


@dataclass(kw_only=True)
class OmkObject:
    """Base class for everything that can be a node in the graph.

    Equality means "same musical content": the id (which stands for the
    object's place in a graph) and the free-form metadata are excluded, so
    two separately built B-flat quarter notes compare equal while remaining
    distinct objects (`is` is unaffected). Objects are mutable and unhashable.
    """

    _id: OmkId = field(default_factory=OmkId.new, init=False, repr=False, compare=False)
    _meta: dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)

    @property
    def id(self) -> OmkId:
        return self._id

    @property
    def meta(self) -> dict[str, Any]:
        return self._meta


@dataclass(kw_only=True)
class SequentialEvent(OmkObject):
    duration: Duration | None = None

    def alter_duration(self, operation: Callable[[Duration, Any], Duration], operand: Any) -> None:
        new_duration = operation(self.duration, operand)
        self.duration = new_duration


class TonalObject(ABC):
    """Mixin for objects with tonal content that a Tone -> Tone operation
    can be pushed through (notes, chord symbols, key signatures, ...)."""

    __slots__ = ()

    @abstractmethod
    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces this object's tonal content, in place, with the result of
        applying `operation(tone, *args, **kwargs)` to it."""


@dataclass(kw_only=True)
class Spanner(OmkObject):
    """Used with OmkEdges of type STARTS_AT and ENDS_AT
    to group a sequence of SequentialEvents together.

    Articulations (such as slurs and crescendos) and other objects
    which normally attach to a single OmkObject can attach to a Spanner
    to indicate that they apply to the entire sequence of objects."""

    pass
