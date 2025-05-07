from __future__ import annotations
from abc import ABC, abstractmethod
from openmusickit.meta.meta import FrozenMeta

class TonalSystem:
    """A named system of tones, pitches, and intervals.
    
    To fully implement a TonalSystem:

    - Instantiate a TonalSystem with a name and description.
    - Subclass Tone along with PitchRepresentation
    - Subclass Interval along with IntervalRepresentation
    - Optionally, create a `symbols` module that instantiates and assigns
      commonly used Tones and Intervals to meaningful names variables.

    To implement a complete musical system,
    you might also create:

    - A TemporalSystem, using base classes defined in the `time` subpackage.
    - A percussion system, instantiating `PercussionTone` and `Gesture`
      into relevant atomic units with meaningfully named variables.
    - Chords or other harmonic structures, instantiating or extending classes 
      in the `harmony` subpackage.
    - Structural units (analogous to WSMN's measure, section, movement, etc.)
      using base classes defined in the `structure` subpackage.

    All of these elements of a complete musical system are optional,
    and are decoupled from each other (there is no `MusicalSystem` class),
    so you are free to implement only what you need,
    as well as mix-and-match
    (for example,
    combining a TonalSystem from one musical culture
    with the RhythmicSystem from another).
    
    """

    def __init__(self, name, desc):
        self._name = name
        self._desc = desc
        self.tone_type = None 

    @property
    def name(self):
        return self._name
    
    @property
    def desc(self):
        return self._desc


    def register_tone_type(self):
        def decorator(cls):
            cls.tonal_system = self
            self.tone_type = cls
            return cls
        return decorator



class Tone(ABC, FrozenMeta):

    """A Tone is a defined pitch or sound type within a TonalSystem,
    with a defined vectorization that is mathematically meaningful and consistent
    within that system. 

    Subclasses of Tone define a type of musical sound, noise, or silence
    with its own logical system of relationships, 
    which are defined within the Tone subclass
    in concert with a subclass of Interval.

    For example, see the following subclasses:

    - TonalVector encapsulates the 12-note diatonic/chromatic logic of Western music,
    and represents either a pitch or an interval. (TonalVector also subclasses Interval.)

    - PercussionTone represents unpitched percussion sounds.

    - SilentTone represents any rest or silence.

    Tone and Interval should be subclassed to represent 
    the members and relationships of any other pitch or sonic system.
    
    Subclasses of Tone should normally be immutable and internable,
    as they represent abstract values ('C# above middle C'), 
    rather than concrete instance of a note in a score."""

    TONAL_SYSTEM: TonalSystem

    def __init_subclass__(cls):
        super().__init_subclass__()
        if not hasattr(cls, 'TONAL_SYSTEM'):
            raise TypeError(f"{cls.__name__} must define 'TONAL_SYSTEM'")

    @classmethod
    def from_string(cls, s) -> Tone:
        """Parses a string and returns a Tone."""
        raise NotImplementedError

    @abstractmethod
    def to_array(self):
        """Returns an np.array used for ML and analysis.
        This method's docstring should, whenever possible,
        provide information about the meaning of each array member. """
        raise NotImplementedError
    
    @abstractmethod
    def __array__(self):
        return self.to_array()
    
    @classmethod
    def abstract_array_len(cls):
        """Vector size for an unqualified or abstract category of tone.
        
        For example,
        TonalVector (pitch and interval) have an abstract_vector_len of 2,
        as they represent a pitch class (C, D-flat) or interval (Perfect 5th),
        without an octave designation.

        These are used in things like chord definitions and chord symbols.
        Whereas a pitch at a specific octave notated into a score
        is a qualified TonalVector, which has a length of 3.
        
        Docstrings for abstract_array_len should describe
        what constitutes an "abstract" vs "qualified" version of the Tone."""
        raise NotImplementedError
    
    @classmethod
    def qualified_array_len(self):
        """Vector size for a qualified instance of a specific tone.

        Typically, a qualified_vector_len has one (1) additional member,
        specifiying an octave.

        However, some musical systems or Tone types may need additional vector members,
        and some may need no additional information.

        Docstrings for qualified_array_len should describe
        what constitutes a "qualified" version of the Tone.
        
        See `abstact_vector_len` for more explanation."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def pitch(self) -> PitchRepresentation:
        """Returns a PitchRepresentation defined within a specific musical system,
        which handles various string output methods (ex. `x.pitch.unicode`)
        and interpreters (ex. `TonalVector.pitch('g sharp')`).

        Under most circumstances, this would be handled like:

        ```
        class ToneSubclass(Tone):
        
            def __init__(self): 
                self._pitch = PitchRepresentationSubclass(self)
                # or, in __new__ with __setattr__

            @property
            def pitch(self):
                return self._pitch
        ```
            
        """
        raise NotImplementedError

    

class PitchRepresentation(ABC):
    """The representation of a Tone as a pitch in a score or other human-readable context,
    normally attached as an attribute to a Tone.

    The methods required here are only a start,
    and each system will likely want to expose a specific API
    for various forms of notation and text output.

    For an example implementation, see TonalVector.Pitch.
    """

    @property
    @abstractmethod
    def unicode(self):
        raise NotImplementedError
    
    @property
    @abstractmethod
    def ascii(self):
        raise NotImplementedError
