from typing import Callable, Any

from openmusickit.tone.tone import Tone
from openmusickit.tone.interval import Interval
from openmusickit.time.duration import Duration

class Note:
    """A Tone and a Duration."""

    def __init__(self, tone: Tone, duration: Duration):

        self._t = tone
        self._d = duration

    @property
    def tone(self):
        return self._t

    @property
    def pitch(self):
        return self._t.pitch
    
    @property
    def duration(self):
        return self._d
    
    def set_tone(self, tone: Tone):
        """Set a new tone directly."""
        self._t = tone

    def alter_tone(self, operation: Callable[[Tone, Tone | Interval], Tone], operand: Tone | Interval):
        """Set a new tone based on the current tone"""
        new_tone = operation(self._t, operand)
        self.set_tone(new_tone)

    def set_duration(self, duration: Duration):
        self._d = duration

    def alter_duration(self, operation: Callable[[Duration, Any], Duration], operand: Any):
        new_duration = operation(self._d, operand)
        self.set_duration(new_duration)

    def __repr__(self):
        return f"Note({self._t.__repr__()}, {self._d.__repr__()})"

    
        
