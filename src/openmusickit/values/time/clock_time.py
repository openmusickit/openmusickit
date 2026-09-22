"""Durations based on clock time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction

from openmusickit.errors import ScalingError, TemporalCompatibilityError
from openmusickit.values.time.duration import (
    Duration,
    Measurable,
    TemporalRatio,
    TemporalSystem,
    TemporalUnit,
)

CLOCK_TIME = TemporalSystem("Clock time", "Real time, measured in microseconds.")


@dataclass(frozen=True, slots=True, eq=False)
class ClockDuration(Duration, Measurable):
    """A duration measured in microseconds of real time.

    The stored value may be a Fraction so that conversions from metrical time
    (e.g. a triplet eighth at quarter = 100) stay exact;
    the accessors (`whole_microseconds`, `seconds`, `str()`) present ordinary numbers.

    >>> ClockDuration.from_seconds(90)
    ClockDuration(microseconds=90000000)
    >>> str(ClockDuration.from_seconds(90))
    '00:01:30.000000'
    >>> ClockDuration.from_seconds(1) + ClockDuration.from_milliseconds(500) == ClockDuration(1_500_000)
    True
    """

    microseconds: int | Fraction

    @property
    def rational_length(self) -> Fraction:
        """The microseconds, as a Fraction.

        >>> ClockDuration(250_000).rational_length
        Fraction(250000, 1)
        """
        return Fraction(self.microseconds)

    def scale(self, scalar: int | Fraction) -> ClockDuration:
        """The same operation as `*`; exact for a Fraction scalar.

        >>> ClockDuration.from_seconds(1).scale(Fraction(1, 4)).milliseconds
        Fraction(250, 1)

        Raises
        ------
        ScalingError
            if ``scalar`` is not a positive rational.

        >>> ClockDuration(7).scale(0)
        Traceback (most recent call last):
        ...
        openmusickit.errors.ScalingError: A ClockDuration can only be scaled by a positive scalar.
        """
        try:
            scalar = Fraction(scalar)
        except (TypeError, ValueError) as e:
            raise ScalingError(f"Cannot scale a ClockDuration by {scalar!r}.") from e
        if scalar <= 0:
            raise ScalingError("A ClockDuration can only be scaled by a positive scalar.")
        return ClockDuration(self.microseconds * scalar)

    def __add__(self, other):
        """Clock time adds only to clock time.

        >>> ClockDuration(1) + ClockDuration(2)
        ClockDuration(microseconds=3)
        """
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self.microseconds + other.microseconds)

    def __radd__(self, other):
        """Lets `sum(clock_durations)` work from its default start value of 0.

        >>> sum([ClockDuration(1), ClockDuration(2)])
        ClockDuration(microseconds=3)
        """
        if other == 0:
            return self
        return NotImplemented

    def __sub__(self, other):
        """The signed difference of two clock durations.

        >>> ClockDuration(5) - ClockDuration(7)
        ClockDuration(microseconds=-2)
        """
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self.microseconds - other.microseconds)

    def __neg__(self) -> ClockDuration:
        """The same length backwards.

        >>> -ClockDuration(5)
        ClockDuration(microseconds=-5)
        """
        return ClockDuration(-self.microseconds)

    def __mul__(self, scalar):
        """
        >>> ClockDuration(5) * 3
        ClockDuration(microseconds=15)
        """
        return ClockDuration(self.microseconds * scalar)

    def __truediv__(self, scalar):
        """Exact for any rational divisor: the result is a Fraction, never a float.

        >>> ClockDuration(6) / Fraction(3)
        ClockDuration(microseconds=Fraction(2, 1))
        >>> ClockDuration(7) / 3
        ClockDuration(microseconds=Fraction(7, 3))
        """
        return ClockDuration(Fraction(self.microseconds) / scalar)

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
        """
        >>> ClockDuration.from_minutes(90).hours
        1.5
        """
        return self.microseconds / 3_600_000_000

    @property
    def minutes(self) -> float:
        """
        >>> ClockDuration.from_seconds(90).minutes
        1.5
        """
        return self.microseconds / 60_000_000

    @property
    def seconds(self) -> float:
        """
        >>> ClockDuration.from_milliseconds(1500).seconds
        1.5
        """
        return self.microseconds / 1_000_000

    @property
    def milliseconds(self) -> float:
        """
        >>> ClockDuration(1500).milliseconds
        1.5
        """
        return self.microseconds / 1_000

    @property
    def whole_microseconds(self) -> int:
        """The microseconds rounded to an int, for a Fraction-valued duration.

        >>> ClockDuration(Fraction(5, 3)).whole_microseconds
        2
        """
        return int(round(self.microseconds))

    @property
    def timedelta(self) -> timedelta:
        """The same length as a standard-library `timedelta`, to whole microseconds.

        >>> ClockDuration.from_seconds(90).timedelta
        datetime.timedelta(seconds=90)
        """
        return timedelta(microseconds=self.whole_microseconds)

    @classmethod
    def from_minutes(cls, n: int | Fraction) -> ClockDuration:
        """
        >>> ClockDuration.from_minutes(2).seconds
        120.0
        """
        return cls(n * 60_000_000)

    @classmethod
    def from_seconds(cls, n: int | Fraction) -> ClockDuration:
        """
        >>> ClockDuration.from_seconds(2).whole_microseconds
        2000000
        """
        return cls(n * 1_000_000)

    @classmethod
    def from_milliseconds(cls, n: int | Fraction) -> ClockDuration:
        """
        >>> ClockDuration.from_milliseconds(2).whole_microseconds
        2000
        """
        return cls(n * 1_000)

    @classmethod
    def from_timedelta(cls, td: timedelta) -> ClockDuration:
        """
        >>> ClockDuration.from_timedelta(timedelta(minutes=1)) == ONE_MINUTE
        True
        """
        total_microseconds = (td.days * 86_400 + td.seconds) * 1_000_000 + td.microseconds
        return cls(total_microseconds)

    @classmethod
    def from_duration(cls, duration: Measurable, ratio: TemporalRatio) -> ClockDuration:
        """Convert any Measurable (a note value, a TemporalUnit,
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

    def __repr__(self):
        """The constructor's arguments; the clock time only when it is not the default minute.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
        >>> Tempo(120, quarter)
        Tempo(120, MetricalDuration(1, 4))
        >>> Tempo(2, quarter, ClockDuration.from_seconds(1))
        Tempo(2, MetricalDuration(1, 4), ClockDuration(microseconds=1000000))
        """
        n, beat, clock_time = self.nominal.count, self.nominal.base, self.contextual.base
        if clock_time == ONE_MINUTE:
            return f"{type(self).__name__}({n}, {beat!r})"
        return f"{type(self).__name__}({n}, {beat!r}, {clock_time!r})"
