from collections.abc import Callable
from dataclasses import dataclass

from openmusickit.objects.omk_object import SequentialEvent, TonalObject
from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.tone_collection import ToneCollection


@dataclass(kw_only=True, slots=True)
class ChordEvent(SequentialEvent, TonalObject):
    """A ChordEvent is a SequentialEvent containing a ToneCollection, representing a named set of tones.
    ChordEvents are typically represented in a score as a single symbol (such as in a lead sheet or chord chart),
    with the specific voicing or realization of the chord left to the performer or arranger.

    In most WSMN contexts, a ChordEvent will use a systems.wsmn.tonal.Chord as its ToneCollection,
    but other systems may use different ToneCollection types."""

    chord: ToneCollection

    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces the chord with `self.chord.transform(operation, *args, **kwargs)`.

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, maj, M3
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>>
        >>> event = ChordEvent(chord=C(maj))
        >>> event.transform_tones(TonalVector.transpose, M3)
        >>> str(event.chord)
        'E'
        """
        self.chord = self.chord.transform(operation, *args, **kwargs)
