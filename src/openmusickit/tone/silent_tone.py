"""SilentTone represents a rest or other notated silence 
that occurs in the context of other notes or tones."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import ClassVar, Dict


from numpy import array

from .tone import Tone

@dataclass(frozen=True)
class SilentTone(Tone):
    """
    An iterable filled with the value -1.
    
    This value (-1) is a sentinel value representing rest or silence,
    in any place a Tone might be used.
    
    For example, the notes in a standard Western score
    are a combination of a three-member TonalVector and a duration:
    
    ```
    # quarter note on middle c
    Note(TonalVector((0,0,0)), Duration(1,4))
    ```

    When vectorized for an ML model or other analysis tool,
    a rest should be the same size at the TonalVector.

    So, a rest in the same score:

    ```
    # quarter rest in WSMN
    Note(SilentTone(3), Duration(1,4))

    # for context, note this shorthand:
    Rest(Duration(1,4))
    ```

    Note that you can create a SilentTone from any Tone subclass or instance:

    ```
    # These are all the same thing

    SilentTone(3)
    SilentTone(TonalVector)
    SilentTone(TonalVector(0,0,0))
    ```

    Or in an unpitched percussion line, a rest would be:

    ```
    # These are the same thing

    SilentTone(14)
    SilentTone(PercussionTone)
    ```

    """
    _size: int
    _cache: ClassVar[Dict[int, SilentTone]] = {}

    def __new__(cls, size: int|type|Tone = 1):
        if type(size) == int:
            _size = size
        elif type(size) == type:
            _size = size.qualified_vector_len()
        else:
            _size = len(size)

        if _size in cls._cache:
            return cls._cache[_size]
        
        self = super().__new__(cls)
        object.__setattr__(self, '_size', _size)

        cls._cache[_size] = self
        return self
    
    @classmethod
    def abstract_vector_len(cls):
        return 1

    def __iter__(self):
        for _ in range(self._size):
            yield -1

    def __len__(self):
        return self._size

    def to_array(self):
        """Returns np.array of length self._size, filled with -1.
        """
        return array([-1 for _ in range(self._size)])
    
    def __repr__(self):
        return f'SilentTone({self._size})'
    
    def __hash__(self):
        return hash(f'SilentTone({self._size})')
    
    def __eq__(self, other):
        try:
            return self.to_array() == other.to_array()
        except AttributeError:
            return False
    
