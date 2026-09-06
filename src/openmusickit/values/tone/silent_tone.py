"""SilentTone represents a rest or other notated silence 
that occurs in the context of other notes or tones."""
from __future__ import annotations
from dataclasses import dataclass


from .tone import Tone

@dataclass(frozen=True)
class SilentTone(Tone):
    """
    A musical silence, for example a rest.

    """
    
    def __repr__(self):
        return f'SilentTone()'
    
    def __eq__(self, other):
        return type(other) is SilentTone
    
