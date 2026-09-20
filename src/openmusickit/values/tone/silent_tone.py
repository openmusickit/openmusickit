"""SilentTone represents a rest or other notated silence
that occurs in the context of other notes or tones."""

from __future__ import annotations

from dataclasses import dataclass

from openmusickit.values.tone.tone import ANY_TONAL_SYSTEM, TonalSystem, Tone


@dataclass(frozen=True, slots=True)
class SilentTone(Tone):
    """
    A musical silence, for example a rest.

    Every SilentTone is equal to every other, so they can be used
    interchangeably as members of a set of Tones:

    >>> SilentTone() == SilentTone()
    True
    >>> SilentTone() in {SilentTone()}
    True
    >>> isinstance(SilentTone(), Tone)
    True

    A silence has no pitch, and belongs to no particular tonal system:

    >>> SilentTone().pitch is None
    True
    >>> SilentTone().tonal_system.universal
    True
    """

    @property
    def tonal_system(self) -> TonalSystem:
        return ANY_TONAL_SYSTEM
