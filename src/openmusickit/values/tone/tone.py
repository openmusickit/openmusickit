from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TonalSystem:
    """A named system of tones, pitches, and intervals
    (see `TemporalSystem` for the temporal counterpart).

    Every Tone and Interval reports its system through `tonal_system`, so that
    code combining them can refuse to mix systems. A `universal` system is one
    whose members belong to no system in particular (a SilentTone) and may be
    combined with anything.

    To fully implement a TonalSystem:

    - Instantiate a TonalSystem with a name and description.
    - Subclass Tone along with PitchRepresentation
    - Subclass Interval along with IntervalRepresentation
    - Return the TonalSystem instance from their `tonal_system` property
    - Optionally, create a `symbols` module that instantiates and assigns
      commonly used Tones and Intervals to meaningfully named variables.

    To implement a complete musical system, you might also create:

    - A TemporalSystem, using base classes defined in `values.time`.
    - Chords or other harmonic structures, subclassing `ToneCollection`.
    - Unpitched (percussion) tones, and structural units such as measures
      and sections; base classes for these do not exist yet.

    All of these elements of a complete musical system are optional,
    and are decoupled from each other (there is no `MusicalSystem` class),
    so you are free to implement only what you need,
    as well as mix-and-match (for example, combining a TonalSystem
    from one musical culture with the TemporalSystem from another).
    """

    name: str
    description: str
    universal: bool = False

    def compatible_with(self, other: TonalSystem) -> bool:
        """True if members of the two systems may be combined:
        the same system, or either one universal.

        >>> from openmusickit.systems.wsmn.tonal.wsmn import WSMN
        >>> WSMN.compatible_with(TonalSystem("Other", "..."))
        False
        >>> WSMN.compatible_with(ANY_TONAL_SYSTEM)
        True
        """
        return self.universal or other.universal or self == other


ANY_TONAL_SYSTEM = TonalSystem(
    "Any",
    "Placeholder for tones that belong to no particular tonal system.",
    universal=True,
)


class Tone(ABC):
    """A Tone is a defined pitch or sound type within a TonalSystem.

    Subclasses of Tone define a type of musical sound, noise, or silence
    with its own logical system of relationships,
    which are defined within the Tone subclass
    in concert with a subclass of Interval.

    For example, see the following subclasses:

    - TonalVector encapsulates the 12-note diatonic/chromatic logic of Western music,
    and represents either a pitch or an interval. (TonalVector also subclasses Interval.)

    - SilentTone represents any rest or silence.

    (An unpitched percussion tone would be another subclass; it does not exist yet.)

    >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
    >>> from openmusickit.values.tone.silent_tone import SilentTone
    >>> isinstance(TonalVector((0, 0)), Tone)
    True
    >>> isinstance(SilentTone(), Tone)
    True

    Tone and Interval should be subclassed to represent
    the members and relationships of any other pitch or sonic system.

    Subclasses of Tone should be immutable and hashable, comparing by value,
    as they represent abstract values ('C# above middle C'),
    rather than concrete instances of a note in a score."""

    __slots__ = ()

    @property
    @abstractmethod
    def tonal_system(self) -> TonalSystem:
        """The TonalSystem this tone belongs to (for introspection and compatibility checks)."""

    @classmethod
    def from_string(cls, s: str) -> Tone:
        """Parses a string and returns a Tone.

        An optional hook: systems with a string form override it; the base raises."""
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
    def unicode(self) -> str:
        """The unicode representation."""

    @property
    @abstractmethod
    def ascii(self) -> str:
        """The ascii representation."""
