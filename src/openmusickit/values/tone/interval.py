"""The relationship between two tones."""

from __future__ import annotations

from abc import ABC, abstractmethod

from openmusickit.values.tone.tone import TonalSystem


class Interval(ABC):
    """An Interval is a relationship between two tones,
    as defined within a specific tonal or sonic system.

    Subclasses of Interval define the relationships of a tonal system,
    in concert with a subclass of Tone. A single class may play both roles;
    for example, TonalVector subclasses both Tone and Interval,
    since in Western notation a pitch and an interval share one representation.

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> isinstance(TonalVector((0, 0)), Interval)
    True
    >>> TonalVector((2, 4)).tonal_system.name
    'Western Standard Music Notation'
    """

    __slots__ = ()

    @property
    @abstractmethod
    def tonal_system(self) -> TonalSystem:
        """The TonalSystem this interval belongs to (for introspection and compatibility checks)."""

    @classmethod
    def from_string(cls, s: str) -> Interval:
        """Parses a string and returns an Interval.

        An optional hook: systems with a string form override it; the base raises.

        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>> TonalVector.from_string("M3")
        TonalVector((2, 4))
        >>> Interval.from_string("M3")
        Traceback (most recent call last):
        ...
        NotImplementedError
        """
        raise NotImplementedError


class IntervalRepresentation(ABC):
    """The representation of an Interval in a human-readable context,
    normally attached as an attribute of an Interval.

    The methods required here are only a start,
    and each system will likely want to expose a specific API
    for various forms of notation and text output.

    For an example implementation, see TonalVector._IntervalRepresentation:

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> interval = TonalVector((2, 4)).interval
    >>> isinstance(interval, IntervalRepresentation), interval.unicode, interval.abbr
    (True, 'major 3', 'maj3')
    """

    @property
    @abstractmethod
    def unicode(self) -> str:
        """The unicode representation."""

    @property
    @abstractmethod
    def ascii(self) -> str:
        """The ascii representation."""
