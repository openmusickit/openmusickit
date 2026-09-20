from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from functools import total_ordering

from openmusickit.errors import ScalingError


@dataclass(frozen=True, slots=True)
class TemporalSystem:
    """A named system of musical time (see `TonalSystem` for the tonal counterpart)."""

    name: str
    description: str

    pass


def _length_of(other) -> Fraction | None:
    """Return the rational length of anything that can be measured:
    a TemporalElement, or an iterable of TemporalElements.
    Returns None if `other` cannot be measured."""
    if isinstance(other, TemporalElement):
        return other.rational_length
    if isinstance(other, (str, bytes)):
        return None
    try:
        members = list(other)
    except TypeError:
        return None
    if not all(isinstance(m, TemporalElement) for m in members):
        return None
    return sum((m.rational_length for m in members), Fraction(0))


@total_ordering
class TemporalElement(ABC):
    """Any class that represents a structured period of time
    which can be measured and subdivided. For example:
    note durations, measures, beat cycles, gong cycles, and other units of time.

    Any internally-consistent rhythmic/temporal system should be constructable
    using subclasses of TemporalElement and Duration.

    TemporalElements compare (and hash) by their rational_length,
    so a dotted quarter == 3 eighths == TemporalUnit(3, eighth).
    Any TemporalElement can also be compared against an iterable of TemporalElements,
    which is measured as the sum of its members.

    """

    @property
    @abstractmethod
    def rational_length(self) -> Fraction:
        """Returns a fraction value representing the length of the TemporalElement,
        as defined within the TemporalSystem."""

    @abstractmethod
    def scale(self, scalar: int | Fraction) -> TemporalElement:
        """Return a TemporalElement scaled by a positive scalar, according to its TemporalSystem.

        The result's ``rational_length`` must equal ``self.rational_length * scalar``.
        Implementations should return an element of the same type where the system
        allows it, and otherwise the closest thing the system offers: WSMN's
        ``MetricalDuration`` returns a ``MetricalDuration`` for powers of two and may
        return a tuplet member or a ``TiedDuration`` for other scalars.

        Raises
        ------
        ScalingError
            If ``scalar`` is not a positive rational, or if the scaled value cannot be
            represented in this TemporalSystem at all. Callers may catch this and fall
            back to an alternate strategy.
        """

    def __eq__(self, other) -> bool:
        other_length = _length_of(other)
        if other_length is None:
            return NotImplemented
        return self.rational_length == other_length

    def __lt__(self, other) -> bool:
        other_length = _length_of(other)
        if other_length is None:
            return NotImplemented
        return self.rational_length < other_length

    def __hash__(self):
        return hash(self.rational_length)


class Duration(TemporalElement):
    """Any class that represents a basic unit of time and is notated as a single symbol.

    Subclass Duration to create the specific duration unit(s) of a particular system.
    For example, WSMN's note durations (quarter, half note, tuplets, etc),
    are managed by MetricalDuration.

    WSMN only requires a single note duration type to cover standard note durations.
    Some temporal systems may need many different Duration types.
    """

    @property
    @abstractmethod
    def temporal_system(self) -> TemporalSystem:
        """The TemporalSystem this duration belongs to (for introspection)."""

    @abstractmethod
    def __neg__(self) -> Duration:
        """The same length in the opposite direction.

        Durations are signed quantities so that displacements (see `Next.nudge`)
        can be computed with ordinary arithmetic. A negative duration is never
        the length of an event: `SequentialEvent` rejects one.
        """

    def __sub__(self, other):
        if not isinstance(other, Duration):
            return NotImplemented
        return self + (-other)


ANY_TEMPORAL_SYSTEM = TemporalSystem(
    "Any", "Placeholder for durations that belong to no particular temporal system."
)


class ZeroDuration(Duration):
    """A Duration of zero length (instantaneous)."""

    @property
    def temporal_system(self) -> TemporalSystem:
        return ANY_TEMPORAL_SYSTEM

    @property
    def rational_length(self) -> Fraction:
        return Fraction(0, 1)

    def scale(self, scalar: int | Fraction) -> ZeroDuration:
        return self

    def __add__(self, other: Duration):
        if not isinstance(other, Duration):
            raise TypeError(f"Cannot add {type(other)} to a Duration.")
        return other

    def __neg__(self) -> ZeroDuration:
        return self


@dataclass(frozen=True, slots=True, eq=False)
class TemporalUnit(TemporalElement):
    """A length of musical time defined as n number of TemporalElements.
    This is used to represent (among other things)
    time signatures and tuple definitions.

    Example: WSMN Time Signatures
    ---------------

    A time signature has:
     - a numerator (top number),
       which defines "how many" of some MetricalDuration.
     - a denominator (bottom number),
       which defines some MetricalDuration.

    So 4/4 time is 4 quarter notes and is expressed as:

    >>> from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
    >>> TemporalUnit(4, MetricalDuration(1, 4)).rational_length
    Fraction(1, 1)

    Compound meters such as 6/8 can be expressed using
    the dotted duration or the base duration:

    >>> TemporalUnit(6, MetricalDuration(1, 8)) == TemporalUnit(2, MetricalDuration(1, 4, dots=1))
    True

    More exotic time signatures can be achieved
    by using tupleted durations as the denominator.

    Tuplets
    -------

    Musically, a tuplet is defined as a ratio of
    notated notes (expressed as nominal Durations)
    to the amount of time those notes take up
    as expressed in the surrounding musical context.

    A standard quarter note triplet, then,
    is:
     - three quarter notes, which take up the time of
     - two quarter notes.

    Each of these (nominal and actual) is defined as a TemporalUnit,
    and combined into a tuplet definition using a TemporalRatio.

    """

    count: int
    base: Duration

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("A TemporalUnit cannot have a negative count.")

    @property
    def temporal_system(self) -> TemporalSystem:
        return self.base.temporal_system

    @property
    def rational_length(self) -> Fraction:
        return self.count * self.base.rational_length

    def scale(self, scalar: int | Fraction) -> TemporalUnit:
        """Scale the Temporal Unit.

        The count is scaled whenever the result is a whole number
        (4 quarters * 2 = 8 quarters; 6 eighths / 2 = 3 eighths).
        Otherwise the remaining factor is pushed into the base duration
        (3 eighths / 2 = 3 sixteenths; 1 quarter * 3/2 = 3 eighths;
        4 quarters / 3 = 4 triplet eighths, if the base supports tuplets).

        Raises
        ------
        ScalingError
            if the scalar is not positive, or if the base cannot absorb the leftover factor.
        """
        scalar = Fraction(scalar)
        if scalar <= 0:
            raise ScalingError("A TemporalUnit can only be scaled by a positive scalar.")

        new_count = self.count * scalar
        if new_count.denominator == 1:
            return type(self)(int(new_count), self.base)

        # push the leftover denominator into the base
        leftover = Fraction(1, new_count.denominator)
        try:
            new_base = self.base.scale(leftover)
        except ScalingError as e:
            raise ScalingError(
                f"Cannot scale {self!r} by {scalar}: "
                f"{new_count.denominator} does not divide the count, "
                f"and the base cannot be scaled by {leftover}: {e}"
            ) from e
        return type(self)(new_count.numerator, new_base)

    def __repr__(self):
        return f"{type(self).__name__}({self.count}, {self.base!r})"


@dataclass(frozen=True, slots=True, eq=False)
class CompoundTemporalUnit(TemporalElement):
    """An ordered series of temporal elements, measured as their total length."""

    units: tuple[TemporalElement, ...]

    def __init__(self, units: Iterable[TemporalElement]):
        object.__setattr__(self, "units", tuple(units))

    def __iter__(self):
        return iter(self.units)

    def __getitem__(self, index):
        return self.units[index]

    def __len__(self):
        return len(self.units)

    def __contains__(self, item):
        return item in self.units

    def index(self, item: TemporalElement) -> int:
        return self.units.index(item)

    def count(self, item: TemporalElement) -> int:
        return self.units.count(item)

    def __repr__(self):
        return f"{type(self).__name__}({list(self.units)!r})"

    @property
    def rational_length(self) -> Fraction:
        return sum((tu.rational_length for tu in self.units), Fraction(0))

    def remainder(self, series: Iterable[TemporalElement]) -> Fraction:
        """Returns the length of self minus the total length of `series`.
        Negative if `series` overflows self."""
        return self.rational_length - sum((s.rational_length for s in series), Fraction(0))

    def first_out_of_bounds(self, series: Iterable[TemporalElement]) -> int | None:
        """Returns the index of the first items in `series`
        that exceeds the length of self.
        Returns None if the total length of series is <= length of self."""

        srl = self.rational_length
        for i, item in enumerate(series):
            srl -= item.rational_length
            if srl < 0:
                return i
        return None

    def scale(self, scalar: int | Fraction) -> CompoundTemporalUnit:
        try:
            new_units = [tu.scale(scalar) for tu in self.units]
        except ScalingError as e:
            raise ScalingError(
                f"One or more members cannot complete the requested scaling operation: {e}"
            ) from e
        return type(self)(new_units)


@dataclass(frozen=True, slots=True)
class TemporalRatio:
    """The ratio of two TemporalUnits.

    Used for the following:

    - In WSMN, tuplets are a ratio of n number of nominal units which take place during d number of contextual (or actual units).
    - In WSMN, a metronome marking or tempo is ratio of n number of MetricalDurations during d number of ClockTime seconds.
    - In mixed-system contexts, a ratio of n TemporalUnits in one system to d TemporalUnits of another system can be used for syncing.
      (For example, one puntum in Gregorian chant may equal one quarter note in WSMN)

    Other temporal systems may find other uses (for example, defining duration ratios within a gong cycle).

    nominal: the number and type of notes notated and played
    contextual: (sometimes called "actual") the length of time (expressed as a multiple of Durations)
        as measured in the surrounding context.

    So, for example, a standard quarter note triplet (3 quarters in the time/space of 2 quarters) would be:

    >>> from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
    >>> quarter = MetricalDuration(1, 4)
    >>> triplet = TemporalRatio(nominal=TemporalUnit(3, quarter), contextual=TemporalUnit(2, quarter))
    >>> triplet.multiplier
    Fraction(2, 3)

    Note that this only defines the relationship, and is not the tuplet itself.
    The ratio is then used in the definition of a Duration instance.
    (To calculate the RationalLength of the actual note, as opposed to its notated value.)

    (It is also used in the definition of a Tuplet node, which groups the constituent Notes.)

    """

    nominal: TemporalElement
    contextual: TemporalElement

    @property
    def multiplier(self) -> Fraction:
        """The multiplier that converts a nominal length into a contextual length:
        contextual_length / nominal_length.

        For a quarter-note triplet this is 2/3;
        for a tempo of quarter = 60 it is microseconds-per-whole-note (4_000_000)."""
        return Fraction(self.contextual.rational_length) / Fraction(self.nominal.rational_length)

    def __eq__(self, other):
        if not isinstance(other, TemporalRatio):
            return NotImplemented
        return self.multiplier == other.multiplier

    def __hash__(self):
        return hash(self.multiplier)

    def __repr__(self):
        return f"{type(self).__name__}({self.nominal!r}, {self.contextual!r})"
