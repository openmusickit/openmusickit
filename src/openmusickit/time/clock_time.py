"""Durations based on clock time."""

from .duration import AbstractDuration

class ClockDuration(AbstractDuration):

    def __init__(self, seconds):
        self._seconds = seconds

    @property
    def rational_length(self):
        return self._seconds
    
minute = ClockDuration(60)
