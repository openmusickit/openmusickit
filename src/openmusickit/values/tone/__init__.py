"""
The `tones` module provides the foundational logic for pitch and interval operations.

It includes tools for transposing, inverting, and comparing tonal elements, as well as
the `TonalVector` class—a core abstraction that encodes both pitches and intervals
as direction-aware vectors suitable for algorithmic and music-theoretical analysis.
"""

from openmusickit.values.tone import interval, silent_tone, tone, tone_collection

__all__ = [
    "interval",
    "silent_tone",
    "tone",
    "tone_collection",
]
