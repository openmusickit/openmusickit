"""Durations based on clock time."""

from .duration import Duration

class ClockDuration(Duration):

    def __init__(self, seconds):
        self._seconds = seconds

    @property
    def rational_length(self):
        return self._seconds
    
    def scale(self, scalar):
        return ClockDuration(self._seconds * scalar)
    
    @property
    def temporal_system(self):
        return "RealTime"
    
    def __repr__(self):
        return f"ClockTime({str(self._seconds)})"

    
minute = ClockDuration(60)
