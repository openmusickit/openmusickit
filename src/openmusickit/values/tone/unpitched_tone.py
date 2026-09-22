"""A sound with no pitch."""

from __future__ import annotations

from openmusickit.values.tone.tone import Tone


class UnpitchedTone(Tone):
    """A Tone that is a sound with no pitch.

    This is the general idea behind a drum stroke, a tabla bol, a cymbal
    crash, a hand clap: WSMN's `PercussionTone` (a relative pitch and a
    stroke, on whatever instrument the Part names) is one implementation.
    `pitch` is None, as for any unpitched Tone, so `Tone.__format__` gives
    the tone's `str()`; a system decides what else a sound is made of, and
    declares its own `TonalSystem`.

    Silence is not a sound: `SilentTone` is a Tone but not an UnpitchedTone.

    >>> from openmusickit.values.tone.silent_tone import SilentTone
    >>> from openmusickit.values.tone.tone import ANY_TONAL_SYSTEM
    >>> class Knock(UnpitchedTone):
    ...     @property
    ...     def tonal_system(self):
    ...         return ANY_TONAL_SYSTEM
    >>> isinstance(Knock(), Tone), Knock().pitch is None
    (True, True)
    >>> isinstance(SilentTone(), UnpitchedTone)
    False
    """

    __slots__ = ()
