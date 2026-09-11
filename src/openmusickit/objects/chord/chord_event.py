from openmusickit.objects.omk_object import SequentialObject
from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.tone_collection import ToneCollection

@dataclass(kw_only=True)
class ChordEvent(SequentialObject):
    """A ChordEvent is a SequentialObject containing a ToneCollection, representing a named set of tones.
    ChordEvents are typically represented in a score as a single symbol (such as in a lead sheet or chord chart),
    with the specific voicing or realization of the chord left to the performer or arranger.
    
    In most WSMN contexts, a ChordEvent will use a systems.wsmn.tonal.Chord as its ToneCollection, 
    but other systems may use different ToneCollection types."""
    tones: ToneCollection | None = None
