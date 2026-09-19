"""SilentTone represents a rest or other notated silence
that occurs in the context of other notes or tones."""

from __future__ import annotations

from dataclasses import dataclass

from openmusickit.values.tone.tone import Tone


@dataclass(frozen=True)
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

    A silence has no pitch:

    >>> SilentTone().pitch is None
    True
    """
