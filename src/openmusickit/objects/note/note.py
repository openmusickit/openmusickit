from dataclasses import dataclass
from typing import Callable

from openmusickit.values.tone.tone import Tone
from openmusickit.values.tone.silent_tone import SilentTone
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
        """
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E
        >>> NoteEvent(tones={C, E}, duration=None)
        NoteEvent(tones=[TonalVector((0, 0)), TonalVector((2, 4))], duration=None)

        A SilentTone cannot coexist with other tones:

        >>> NoteEvent(tones={C, SilentTone()}, duration=None)
        Traceback (most recent call last):
        ...
        ValueError: A NoteEvent cannot contain a SilentTone and other tones simultaneously.
        """
        if self.is_rest and len(self.tones) > 1:
            raise ValueError("A NoteEvent cannot contain a SilentTone and other tones simultaneously.")

    @property
    def is_rest(self) -> bool:
        """True if this NoteEvent contains a SilentTone.

        >>> Rest(None).is_rest
        True
        >>> NoteEvent(tones=set(), duration=None).is_rest
        False
        """
        return SilentTone() in self.tones

    def add_tone(self, tone: Tone):
        """Adds a tone. Adding a pitched tone to a rest un-rests it;
        adding a SilentTone to a pitched NoteEvent is a no-op.

        >>> from openmusickit.systems.wsmn.tonal.symbols import C
        >>> rest = Rest(None)
        >>> rest.add_tone(C)
        >>> rest.tones == {C}
        True
        >>> rest.add_tone(SilentTone())
        >>> rest.tones == {C}
        True
        """
        self.tones.add(tone)
        if self.is_rest and len(self.tones) > 1:
            self.tones.remove(SilentTone())

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

    def transform(self, operation: Callable[..., Tone], *args, **kwargs):
        """Replaces every tone of this NoteEvent with the result of
        `operation(tone, *args, **kwargs)`. SilentTones are left as they are.

        `operation` is typically a method of the relevant Tone subclass
        (such as `TonalVector.transpose`), but any callable that accepts a
        Tone as its first argument and returns a Tone will do. The result
        need not be of the same type (an operation may translate tones
        from one tonal system to another), but if it is not a Tone at all,
        a TypeError is raised and the NoteEvent is unchanged.

        Examples
        --------

        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Gx, B, M3
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection

        Transposition, with the interval passed as the operand:

        >>> note = NoteEvent(tones={C, E, G})
        >>> note.transform(TonalVector.transpose, M3)
        >>> note.tones == {E, Gx, B}
        True
        >>> note.transform(TonalVector.transpose, M3, TonalDirection.DOWN)
        >>> note.tones == {C, E, G}
        True

        A user-defined operation that needs no operand:

        >>> def sharpen(tv):
        ...     return tv + TonalVector((0, 1))
        >>> note.transform(sharpen)
        >>> note.tones == {TonalVector((0, 1)), TonalVector((2, 5)), TonalVector((4, 8))}
        True

        An operation that does not produce a Tone is rejected:

        >>> note.transform(str)
        Traceback (most recent call last):
        ...
        TypeError: ...

        A rest stays a rest:

        >>> rest = Rest(None)
        >>> rest.transform(TonalVector.transpose, M3)
        >>> rest
        Rest(duration=None)
        """
        new_tones = set()
        for tone in self.tones:
            if type(tone) is SilentTone:
                new_tones.add(tone)
                continue
            new_tone = operation(tone, *args, **kwargs)
            if not isinstance(new_tone, Tone):
                raise TypeError(
                    f"`operation` must return a Tone, "
                    f"but returned {new_tone!r} for {tone!r}."
                )
            new_tones.add(new_tone)
        self.tones = new_tones

    def __repr__(self):
        """
        >>> from openmusickit.systems.wsmn.tonal.symbols import C
        >>> NoteEvent(tones={C}, duration=None)
        NoteEvent(tones=[TonalVector((0, 0))], duration=None)
        >>> Rest(None)
        Rest(duration=None)
        """
        if self.is_rest:
            return f"Rest(duration={self.duration})"
        tones = sorted(repr(tone) for tone in self.tones)
        return f"NoteEvent(tones=[{', '.join(tones)}], duration={self.duration})"
    

def Rest(duration: Duration) -> NoteEvent:
    """Utility function that generates a Note with a Silent Tone.

    >>> Rest(None)
    Rest(duration=None)
    >>> Rest(None).tones == {SilentTone()}
    True
    """
    
    return NoteEvent(tones={SilentTone()}, duration=duration)

    
        
