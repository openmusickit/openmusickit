"""The relationship between two tones."""
from __future__ import annotations
from abc import ABC, abstractmethod

class Interval(ABC):
    """An Interval is a relationship between two tones,
    as defined within a specific tonal or sonic system.
    
    """

    @classmethod
    def from_string(cls, s: str) -> Interval:
        """Parses a string and returns an Interval."""
        raise NotImplementedError

    @abstractmethod
    def to_array(self):
        """Returns an np.array used for ML and analysis.
        This method's docstring should, whenever possible,
        provide information about the meaning of each array member. """
        raise NotImplementedError
    
    def __array__(self):
        """Used by Numpy for conversion to np.array."""
        return self.to_array()

    @classmethod
    def abstract_array_len(cls):
        """Vector size for an unqualified or abstract category of interval.
        
        For example,
        TonalVector (pitch and interval) have an abstract_vector_len of 2,
        as they represent a pitch class (C, D-flat) or interval (Perfect 5th),
        without an octave designation.

        These are used in things like chord definitions and chord symbols.
        Whereas a pitch at a specific octave notated into a score
        is a qualified TonalVector, which has a length of 3.
        
        Docstrings for abstract_array_len should describe
        what constitutes an "abstract" vs "qualified" version of the Interval."""
        raise NotImplementedError
    
    @classmethod
    def qualified_array_len(self):
        """Vector size for a qualified instance of a specific interval.

        Typically, a qualified_vector_len has one (1) additional member,
        specifiying an octave.

        However, some musical systems or Interval types may need additional vector members,
        and some may need no additional information.

        Docstrings for qualified_array_len should describe
        what constitutes a "qualified" version of the Interval.
        
        See `abstact_vector_len` for more explanation."""
        raise NotImplementedError

class IntervalRepresentation:
    """The representation of an Interval in a human-readable context,
    normally attached as an attribute of an Interval.

    The methods required here are only a start,
    and each system will likely want to expose a specific API
    for various forms of notation and text output.

    For an example implementation, see TonalVector.Interval.
    """
    
    @property
    @abstractmethod
    def unicode(self):
        raise NotImplementedError
    
    @property
    @abstractmethod
    def ascii(self):
        raise NotImplementedError