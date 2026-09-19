from __future__ import annotations

from abc import ABC, abstractmethod


class TonalSystem:
    """A named system of tones, pitches, and intervals.

    To fully implement a TonalSystem:

    - Instantiate a TonalSystem with a name and description.
    - Subclass Tone along with PitchRepresentation
    - Subclass Interval along with IntervalRepresentation
    - Optionally, create a `symbols` module that instantiates and assigns
      commonly used Tones and Intervals to meaningfully named variables.

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

    @property
    def name(self):
        return self._name

    @property
    def desc(self):
        return self._desc


class Tone(ABC):
    """A Tone is a defined pitch or sound type within a TonalSystem.

    Subclasses of Tone define a type of musical sound, noise, or silence
    with its own logical system of relationships,
    which are defined within the Tone subclass
    in concert with a subclass of Interval.

    For example, see the following subclasses:

    - TonalVector encapsulates the 12-note diatonic/chromatic logic of Western music,
    and represents either a pitch or an interval. (TonalVector also subclasses Interval.)

    - PercussionTone represents unpitched percussion sounds.

    - SilentTone represents any rest or silence.

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> from openmusickit.values.tone.silent_tone import SilentTone
    >>> isinstance(TonalVector((0, 0)), Tone)
    True
    >>> isinstance(SilentTone(), Tone)
    True

    Tone and Interval should be subclassed to represent
    the members and relationships of any other pitch or sonic system.

    Subclasses of Tone should normally be immutable and internable,
    as they represent abstract values ('C# above middle C'),
    rather than concrete instance of a note in a score."""

    @classmethod
    def from_string(cls, s) -> Tone:
        """Parses a string and returns a Tone."""
        raise NotImplementedError

    @property
    def pitch(self) -> PitchRepresentation | None:
        """The PitchRepresentation of this Tone, defined within a specific
        musical system, which handles various string output methods
        (ex. `x.pitch.unicode`) and interpreters (ex. `TonalVector.pitch('g sharp')`).

        Unpitched tones (silence, percussion) have no pitch, so the default
        returns None. Pitched subclasses override this, typically like:

        ```
        class ToneSubclass(Tone):

            def __init__(self):
                self._pitch = PitchRepresentationSubclass(self)

            @property
            def pitch(self):
                return self._pitch
        ```
        """
        return None

    def __format__(self, spec: str) -> str:
        """Display form of the Tone, used by `str.format` and f-strings.

        For pitched tones, the format spec names an attribute of the Tone's
        PitchRepresentation, defaulting to `unicode`; unpitched tones fall
        back to `str()`. `str()` and `repr()` are unaffected, so they remain
        available as debug forms (use `{tone!r}` or `{tone!s}` in a template
        to get them).

        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>> from openmusickit.values.tone.silent_tone import SilentTone
        >>> Eb = TonalVector((2, 3))
        >>> f"{Eb} major"
        'E♭ major'
        >>> f"{Eb:ascii} major"
        'Eb major'
        >>> f"{Eb!r}"
        'TonalVector((2, 3))'
        >>> f"{SilentTone()}"
        'SilentTone()'

        The spec must name a string attribute of the PitchRepresentation:

        >>> f"{Eb:nonsense}"
        Traceback (most recent call last):
        ...
        ValueError: ...
        """
        if self.pitch is None:
            return str(self)

        spec = spec or "unicode"
        result = getattr(self.pitch, spec, None)
        if not isinstance(result, str):
            raise ValueError(
                f"Unknown format spec {spec!r} for {type(self).__name__}: "
                f"expected the name of a string attribute of its "
                f"PitchRepresentation, such as 'unicode' or 'ascii'."
            )
        return result


class PitchRepresentation(ABC):
    """The representation of a Tone as a pitch in a score or other human-readable context,
    normally attached as an attribute to a Tone.

    The methods required here are only a start,
    and each system will likely want to expose a specific API
    for various forms of notation and text output.

    For an example implementation, see TonalVector._PitchRepresentation.
    """

    @property
    @abstractmethod
    def unicode(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def ascii(self):
        raise NotImplementedError
