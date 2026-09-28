"""Text values: the words of a lyric, as they are sung.

Unlike tones and durations, these are not system-specific and are not meant
to be subclassed."""

from . import word
from .word import LexicalStress, Word

__all__ = [
    "word",
    "LexicalStress",
    "Word",
]
