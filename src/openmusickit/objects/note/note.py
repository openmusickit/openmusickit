from dataclasses import dataclass
from typing import Callable

from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.silent_tone import SilentTone
from openmusickit.values.tone.interval import Interval
from openmusickit.values.time.duration import Duration
from openmusickit.objects.omk_object import SequentialObject


@dataclass(kw_only=True)
class NoteEvent(SequentialObject):
    """A MultiNote is a SequentialObject that contains zero or more Tones played simultaneously within a single voice, line, or part.
    
    A NoteEvent with zero tones is not considered a rest, but rather a duration with unspecified tonal content ---
    either because the tonal content doesn't need to be specified (for example, a comping chart),
    or because it has not yet been specified (for example, in a sketch or draft).
    
    A Rest is represented as a NoteEvent with a SilentTone.
    Unpitched percussion notes are represented a NoteEvents with an UnpitchedTone. """
    tones: set[Tone]

    def __post_init__(self):
        if SilentTone in self.tones and len(self.tones) > 1:
            raise ValueError("A NoteEvent cannot contain a SilentTone and other tones simultaneously.")

    def add_tone(self, tone: Tone):
        self.tones.add(tone)
        if SilentTone in self.tones and len(self.tones) > 1:
            self.tones.remove(SilentTone)

    def remove_tone(self, tone: Tone):
        self.tones.remove(tone)

    def clear_tones(self):
        self.tones.clear()

    def make_rest(self):
        self.tones.clear()
        self.tones.add(SilentTone())

    def swap_tone(self, old_tone: Tone, new_tone: Tone):
        self.remove_tone(old_tone)
        self.add_tone(new_tone)

    def alter_tones(self, operation: Callable[[Tone, Tone | Interval], Tone], operand: Tone | Interval):
        """Alter all tones using the provided operation and operand."""
        new_notes = set()
        for tone in self.tones:
            if type(tone) is SilentTone:
                new_notes.add(tone)
            else:
                new_tone = operation(tone, operand)
                new_notes.add(new_tone)
        self.tones = new_notes

    def __repr__(self):
        if SilentTone in self.tones:
            return f"Rest(duration={self.duration})"
        tone_names = [tone.name for tone in self.tones]
        return f"NoteEvent(tones={tone_names}, duration={self.duration})"
    

def Rest(duration: Duration) -> NoteEvent:
    """Utility function that generates a Note with a Silent Tone."""
    
    return NoteEvent(tones={SilentTone()}, duration=duration)

    
        
