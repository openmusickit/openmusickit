"""Durations based on clock time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction

from openmusickit.errors import TemporalCompatibilityError
from openmusickit.values.time.duration import (
    Duration,
    TemporalElement,
    TemporalRatio,
    TemporalSystem,
    TemporalUnit,
)

CLOCK_TIME = TemporalSystem("Clock time", "Real time, measured in microseconds.")


@dataclass(frozen=True, slots=True)
class ClockDuration(Duration):
    """A duration measured in microseconds of real time.

    The stored value may be a Fraction so that conversions from metrical time
    (e.g. a triplet eighth at quarter = 100) stay exact; the accessors
    (`whole_microseconds`, `seconds`, `str()`) present ordinary numbers.
    """

    microseconds: int | Fraction

    @property
    def rational_length(self) -> Fraction:
        return Fraction(self.microseconds)

    def scale(self, scalar: int | Fraction) -> ClockDuration:
        return ClockDuration(self.microseconds * scalar)

    def __add__(self, other):
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self.microseconds + other.microseconds)

    def __radd__(self, other):
        # lets `sum(clock_durations)` work with the default start value of 0
        if other == 0:
            return self
        return NotImplemented

    def __sub__(self, other):
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self.microseconds - other.microseconds)

    def __mul__(self, scalar):
        return ClockDuration(self.microseconds * scalar)

    def __truediv__(self, scalar):
        return ClockDuration(self.microseconds / scalar)

    # Clock time is deliberately not comparable to metrical time: `rational_length`
    # is a WSMN notion (the named fractional value), whereas here it is a count of
    # microseconds. To compare or combine the two, convert first with
    # `ClockDuration.from_duration(duration, ratio)` using a TemporalRatio/Tempo.
    def __eq__(self, other):
        if isinstance(other, ClockDuration):
            return self.microseconds == other.microseconds
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, ClockDuration):
            return self.microseconds < other.microseconds
        return NotImplemented

    @property
    def temporal_system(self) -> TemporalSystem:
        return CLOCK_TIME

    def __str__(self):
        total_microseconds = int(round(self.microseconds))
        hours, remainder = divmod(total_microseconds, 3_600_000_000)
        minutes, remainder = divmod(remainder, 60_000_000)
        seconds, microseconds = divmod(remainder, 1_000_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"

    @property
    def hours(self) -> float:
        return self.microseconds / 3_600_000_000

    @property
    def minutes(self) -> float:
        return self.microseconds / 60_000_000

    @property
    def seconds(self) -> float:
        return self.microseconds / 1_000_000

    @property
    def milliseconds(self) -> float:
        return self.microseconds / 1_000

    @property
    def whole_microseconds(self) -> int:
        return int(round(self.microseconds))

    @property
    def timedelta(self) -> timedelta:
        return timedelta(microseconds=self.whole_microseconds)

    @classmethod
    def from_minutes(cls, n: int | Fraction) -> ClockDuration:
        return cls(n * 60_000_000)

    @classmethod
    def from_seconds(cls, n: int | Fraction) -> ClockDuration:
        return cls(n * 1_000_000)

    @classmethod
    def from_milliseconds(cls, n: int | Fraction) -> ClockDuration:
        return cls(n * 1_000)

    @classmethod
    def from_timedelta(cls, td: timedelta) -> ClockDuration:
        total_microseconds = (td.days * 86_400 + td.seconds) * 1_000_000 + td.microseconds
        return cls(total_microseconds)

    @classmethod
    def from_duration(cls, duration: TemporalElement, ratio: TemporalRatio) -> ClockDuration:
        """Convert any metered TemporalElement (a note value, a TemporalUnit,
        a time signature, a tied duration...) into clock time.

        `ratio` relates metrical time to clock time; it is usually built with `Tempo`:

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, dotted_half
        >>> ClockDuration.from_duration(dotted_half, Tempo(120, quarter)).seconds
        Fraction(3, 2)

        Raises
        ------
        TemporalCompatibilityError
            if the contextual side of `ratio` is not clock time.
        """
        contextual = ratio.contextual
        contextual_base = getattr(contextual, "base", contextual)
        if not isinstance(contextual_base, ClockDuration):
            raise TemporalCompatibilityError(
                "The contextual side of the ratio must be a ClockDuration. (Use Tempo to build one.)"
            )
        return cls(Fraction(duration.rational_length) * ratio.multiplier)


ONE_MINUTE = ClockDuration.from_minutes(1)


class Tempo(TemporalRatio):
    """A TemporalRatio of `n` beats per `clock_time` (default: one minute).

    Examples
    --------

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, dotted_quarter
    >>> Tempo(120, quarter).multiplier  # microseconds per whole note
    Fraction(2000000, 1)
    >>> ClockDuration.from_duration(quarter, Tempo(120, quarter)).seconds
    Fraction(1, 2)
    >>> ClockDuration.from_duration(dotted_quarter, Tempo(60, dotted_quarter)).seconds
    Fraction(1, 1)
    """

    def __init__(self, n: int, beat: Duration, clock_time: ClockDuration = ONE_MINUTE):
        super().__init__(TemporalUnit(n, beat), TemporalUnit(1, clock_time))
