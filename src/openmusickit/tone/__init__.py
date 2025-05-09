"""
The `tones` module provides the foundational logic for pitch and interval operations.

It includes tools for transposing, inverting, and comparing tonal elements, as well as
the `TonalVector` class—a core abstraction that encodes both pitches and intervals
as direction-aware vectors suitable for algorithmic and music-theoretical analysis.
"""

from . import tone
from . import silent_tone

__all__ = [
    "tone",
    "silent_tone"
]