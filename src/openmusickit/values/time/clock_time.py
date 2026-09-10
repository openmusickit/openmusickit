"""Durations based on clock time."""

from dataclasses import dataclass
from datetime import timedelta
from .duration import Duration

@dataclass
class ClockDuration(Duration):
    _microseconds: int

    @property
    def rational_length(self):
        return self._microseconds

    def scale(self, scalar):
        return ClockDuration(self._microseconds * scalar)

    def __add__(self, other):
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self._microseconds + other._microseconds)

    def __sub__(self, other):
        if not isinstance(other, ClockDuration):
            return NotImplemented
        return ClockDuration(self._microseconds - other._microseconds)

    def __mul__(self, scalar):
        return ClockDuration(self._microseconds * scalar)

    def __truediv__(self, scalar):
        return ClockDuration(self._microseconds / scalar)

    @property
    def temporal_system(self):
        return "RealTime"

    def __repr__(self):
        return f"ClockTime({str(self._microseconds)})"

    def __str__(self):
        total_microseconds = int(self._microseconds)
        hours, remainder = divmod(total_microseconds, 3_600_000_000)
        minutes, remainder = divmod(remainder, 60_000_000)
        seconds, microseconds = divmod(remainder, 1_000_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{microseconds:06d}"

    @property
    def hours(self) -> float:
        return self._microseconds / 3_600_000_000

    @property
    def minutes(self) -> float:
        return self._microseconds / 60_000_000

    @property
    def seconds(self) -> float:
        return self._microseconds / 1_000_000

    @property
    def milliseconds(self) -> float:
        return self._microseconds / 1_000

    @property
    def microseconds(self) -> int:
        return int(self._microseconds)

    @property
    def to_timedelta(self) -> timedelta:
        return timedelta(microseconds=self._microseconds)

    @classmethod
    def from_minutes(cls, n):
        return cls(n * 60_000_000)

    @classmethod
    def from_seconds(cls, n):
        return cls(n * 1_000_000)

    @classmethod
    def from_milliseconds(cls, n):
        return cls(n * 1_000)

    @classmethod
    def from_timedelta(cls, td: timedelta):
        total_microseconds = (td.days * 86_400 + td.seconds) * 1_000_000 + td.microseconds
        return cls(total_microseconds)

