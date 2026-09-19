"""The relationship between two tones."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Interval(ABC):  # noqa: B024 -- a marker base: the contract is set by each tonal system
    """An Interval is a relationship between two tones,
    as defined within a specific tonal or sonic system.

    Subclasses of Interval define the relationships of a tonal system,
    in concert with a subclass of Tone. A single class may play both roles;
    for example, TonalVector subclasses both Tone and Interval,
    since in Western notation a pitch and an interval share one representation.

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> isinstance(TonalVector((0, 0)), Interval)
    True
    """

    @classmethod
    def from_string(cls, s: str) -> Interval:
        """Parses a string and returns an Interval.

        An optional hook: systems with a string form override it; the base raises."""
        raise NotImplementedError


class IntervalRepresentation(ABC):
    """The representation of an Interval in a human-readable context,
    normally attached as an attribute of an Interval.

    The methods required here are only a start,
    and each system will likely want to expose a specific API
    for various forms of notation and text output.

    For an example implementation, see TonalVector._IntervalRepresentation.
    """

    @property
    @abstractmethod
    def unicode(self) -> str:
        """The unicode representation."""

    @property
    @abstractmethod
    def ascii(self) -> str:
        """The ascii representation."""
