from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from functools import total_ordering

from openmusickit.errors import ScalingError


@dataclass(frozen=True, slots=True)
class TemporalSystem:
    """A named system of musical time (see `TonalSystem` for the tonal counterpart).

    Every Duration reports its system through `temporal_system`,
    so that code combining durations can refuse to mix systems.
    A `universal` system is one whose elements belong to no system in particular
    (a ZeroDuration) and may be combined with anything.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> quarter.temporal_system.name
    'Western Standard Music Notation'
    >>> ANY_TEMPORAL_SYSTEM.universal
    True
    """

    name: str
    description: str
    universal: bool = False

    def compatible_with(self, other: TemporalSystem) -> bool:
        """True if elements of the two systems may be combined:
        the same system, or either one universal.

        >>> from openmusickit.values.time.clock_time import CLOCK_TIME
        >>> from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
        >>> WSMN_TEMPORAL.compatible_with(CLOCK_TIME)
        False
        >>> WSMN_TEMPORAL.compatible_with(ANY_TEMPORAL_SYSTEM)
        True
        """
        return self.universal or other.universal or self == other


class TemporalElement(ABC):
    """Any class that represents a structured period of time.
    For example: note durations, measures, beat cycles, gong cycles,
    and other units of time.

    Any internally-consistent rhythmic/temporal system should be constructable
    using subclasses of TemporalElement and Duration.

    The base contract is only that an element belongs to a TemporalSystem.
    How elements compare is the system's business:
    systems whose elements reduce to a single number use `Measurable`,
    which supplies comparison, hashing and scaling from that number;
    systems whose elements do not (a chant notation, say)
    define their own comparison, or none.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, four_four
    >>> isinstance(quarter, TemporalElement), isinstance(four_four, TemporalElement)
    (True, True)
    >>> quarter.temporal_system is four_four.temporal_system
    True
    """

    __slots__ = ()

    @property
    @abstractmethod
    def temporal_system(self) -> TemporalSystem:
        """The TemporalSystem this element belongs to (for introspection and compatibility checks)."""


def _measure(other) -> tuple[Fraction, TemporalSystem] | None:
    """The rational length and system of anything measurable:
    a Measurable, or an iterable of them (measured as the sum of its members,
    in the system of the first). Returns None if `other` cannot be measured."""
    if isinstance(other, Measurable):
        return other.rational_length, other.temporal_system
    if isinstance(other, (str, bytes)):
        return None
    try:
        members = list(other)
    except TypeError:
        return None
    if not all(isinstance(m, Measurable) for m in members):
        return None
    total = sum((m.rational_length for m in members), Fraction(0))
    system = members[0].temporal_system if members else ANY_TEMPORAL_SYSTEM
    return total, system


@total_ordering
class Measurable(TemporalElement):
    """A TemporalElement that reduces to a single rational length,
    in its system's own unit (fractions of a whole note in WSMN,
    microseconds in clock time).

    Measurables compare (and hash) by their rational_length,
    so a dotted quarter == 3 eighths == TemporalUnit(3, eighth),
    and can be compared against an iterable of Measurables,
    which is measured as the sum of its members.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth, dotted_quarter
    >>> dotted_quarter.rational_length
    Fraction(3, 8)
    >>> dotted_quarter == [eighth, eighth, eighth] == TemporalUnit(3, eighth)
    True
    >>> quarter < dotted_quarter, quarter.scale(3)
    (True, MetricalDuration(1, 2, dots=1))

    Comparison is only defined within a temporal system
    (or with a universal element such as ZeroDuration);
    elements of incompatible systems are never equal,
    and ordering them raises TypeError.
    To relate them, convert first with a TemporalRatio.

    >>> from openmusickit.values.time.clock_time import ClockDuration
    >>> quarter == ClockDuration(250_000)
    False
    >>> quarter < ClockDuration(250_000)
    Traceback (most recent call last):
    ...
    TypeError: ...
    """

    __slots__ = ()

    @property
    @abstractmethod
    def rational_length(self) -> Fraction:
        """Returns a fraction value representing the length of the element,
        as defined within its TemporalSystem."""

    @abstractmethod
    def scale(self, scalar: int | Fraction) -> Measurable:
        """Return this element scaled by a positive scalar, according to its TemporalSystem.

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
        measured = _measure(other)
        if measured is None:
            return NotImplemented
        length, system = measured
        if not self.temporal_system.compatible_with(system):
            return NotImplemented
        return self.rational_length == length

    def __lt__(self, other) -> bool:
        """Shorter than `other`, by rational length, within compatible systems.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, dotted_quarter
        >>> quarter < dotted_quarter, dotted_quarter < quarter
        (True, False)
        """
        measured = _measure(other)
        if measured is None:
            return NotImplemented
        length, system = measured
        if not self.temporal_system.compatible_with(system):
            return NotImplemented
        return self.rational_length < length

    def __hash__(self):
        return hash(self.rational_length)


class Duration(TemporalElement):
    """Any class that represents a basic unit of time and is notated as a single symbol.

    Subclass Duration to create the specific duration unit(s) of a particular system.
    For example, WSMN's note durations (quarter, half note, tuplets, etc),
    are managed by MetricalDuration.

    WSMN only requires a single note duration type to cover standard note durations.
    Some temporal systems may need many different Duration types.

    A Duration is a signed quantity: it can be negated and subtracted,
    so that a displacement between two events is a plain Duration.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
    >>> -quarter
    MetricalDuration(-1, 4)
    >>> quarter - eighth, eighth - quarter
    (MetricalDuration(1, 8), MetricalDuration(-1, 8))
    """

    __slots__ = ()

    @abstractmethod
    def __neg__(self) -> Duration:
        """The same length in the opposite direction.

        Durations are signed quantities so that displacements (see `TimedEdge.nudge`)
        can be computed with ordinary arithmetic. A negative duration is never
        the length of an event: `SequentialEvent` rejects one.
        """

    def __sub__(self, other):
        """`self + (-other)`: the difference of two durations, in whatever notation it takes.

        >>> from openmusickit.systems.wsmn.temporal.symbols import half, quarter
        >>> half - quarter, quarter - half
        (MetricalDuration(1, 4), MetricalDuration(-1, 4))
        """
        if not isinstance(other, Duration):
            return NotImplemented
        return self + (-other)


ANY_TEMPORAL_SYSTEM = TemporalSystem(
    "Any",
    "Placeholder for durations that belong to no particular temporal system.",
    universal=True,
)


class ZeroDuration(Duration, Measurable):
    """A Duration of zero length (instantaneous), belonging to every system.

    It is the additive identity: adding it to any Duration gives that Duration back,
    and it is its own negation.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> ZeroDuration() + quarter, quarter + ZeroDuration()
    (MetricalDuration(1, 4), MetricalDuration(1, 4))
    >>> quarter - quarter
    ZeroDuration()
    >>> ZeroDuration().rational_length, -ZeroDuration()
    (Fraction(0, 1), ZeroDuration())
    """

    __slots__ = ()

    @property
    def temporal_system(self) -> TemporalSystem:
        return ANY_TEMPORAL_SYSTEM

    @property
    def rational_length(self) -> Fraction:
        return Fraction(0, 1)

    def scale(self, scalar: int | Fraction) -> ZeroDuration:
        """Nothing scaled is still nothing.

        >>> ZeroDuration().scale(3)
        ZeroDuration()
        """
        return self

    def __add__(self, other: Duration):
        """Zero plus any Duration is that Duration, of any system.

        >>> from openmusickit.values.time.clock_time import ClockDuration
        >>> ZeroDuration() + ClockDuration(5)
        ClockDuration(microseconds=5)
        """
        if not isinstance(other, Duration):
            raise TypeError(f"Cannot add {type(other)} to a Duration.")
        return other

    def __radd__(self, other):
        """Any Duration plus zero is that Duration, even one that does not know
        about ZeroDuration (`ClockDuration`); and `sum` may start from 0.

        >>> from openmusickit.values.time.clock_time import ClockDuration
        >>> ClockDuration(5) + ZeroDuration()
        ClockDuration(microseconds=5)
        >>> sum([ZeroDuration(), ZeroDuration()])
        ZeroDuration()
        """
        if isinstance(other, Duration):
            return other
        if other == 0:
            return self
        return NotImplemented

    def __neg__(self) -> ZeroDuration:
        return self

    def __repr__(self):
        return f"{type(self).__name__}()"


@dataclass(frozen=True, slots=True, eq=False)
class GraceDuration(ZeroDuration):
    """A notated duration that takes no metrical time: a grace note.

    `nominal` is the symbol written (an eighth, a sixteenth); the width of the
    event in its line is zero, so a run of grace notes adds nothing to the
    length of a line, and a grace note stays in the NEXT chain like any other
    event. How much time it actually steals, and from which neighbour, is a
    matter of realization, outside core.

    `on_beat` records the semantic distinction that notation marks with a
    slash: False for the acciaccatura (before the beat, stealing from the
    preceding note), True for the appoggiatura (on the beat, stealing from
    the note it decorates).

    Like every Measurable, a grace compares and hashes by its length, which is
    zero, so all graces are equal to each other and to ZeroDuration; compare
    `nominal` to tell them apart:

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth, sixteenth
    >>> GraceDuration(eighth) == GraceDuration(sixteenth)
    True
    >>> GraceDuration(eighth).nominal == GraceDuration(sixteenth).nominal
    False
    >>> quarter + GraceDuration(eighth) + GraceDuration(sixteenth) == quarter
    True
    >>> GraceDuration(eighth).temporal_system.name
    'Western Standard Music Notation'
    >>> GraceDuration(eighth).scale(2)
    GraceDuration(MetricalDuration(1, 4))
    """

    nominal: Duration
    on_beat: bool = False

    @property
    def temporal_system(self) -> TemporalSystem:
        return self.nominal.temporal_system

    def scale(self, scalar: int | Fraction) -> GraceDuration:
        """Scales the notated symbol; the width stays zero.

        >>> from openmusickit.systems.wsmn.temporal.symbols import grace_eighth
        >>> grace_eighth.scale(2)
        GraceDuration(MetricalDuration(1, 4))
        >>> grace_eighth.scale(2).rational_length
        Fraction(0, 1)
        """
        return GraceDuration(self.nominal.scale(scalar), self.on_beat)

    def __radd__(self, other):
        """A grace is absorbed by whatever is on its left, `sum`'s starting 0 included.

        >>> from openmusickit.systems.wsmn.temporal.symbols import grace_eighth, quarter
        >>> sum([grace_eighth, quarter, grace_eighth])
        MetricalDuration(1, 4)
        """
        # a Duration that does not know about graces (`ClockDuration + grace`)
        # absorbs one, and `sum(durations)` may start from 0
        if isinstance(other, Duration):
            return other
        if other == 0:
            return self
        return NotImplemented

    def __repr__(self):
        if self.on_beat:
            return f"{type(self).__name__}({self.nominal!r}, on_beat=True)"
        return f"{type(self).__name__}({self.nominal!r})"


@dataclass(frozen=True, slots=True, eq=False)
class TemporalUnit(Measurable):
    """A length of musical time defined as n number of a Measurable Duration.
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
    base: Measurable

    def __post_init__(self):
        if self.count < 0:
            raise ValueError("A TemporalUnit cannot have a negative count.")

    @property
    def temporal_system(self) -> TemporalSystem:
        return self.base.temporal_system

    @property
    def rational_length(self) -> Fraction:
        """The count times the base: three eighths are three eighths of a whole note.

        >>> from openmusickit.systems.wsmn.temporal.symbols import eighth
        >>> TemporalUnit(3, eighth).rational_length
        Fraction(3, 8)
        """
        return self.count * self.base.rational_length

    def scale(self, scalar: int | Fraction) -> TemporalUnit:
        """Scale the Temporal Unit.

        The count is scaled whenever the result is a whole number
        (4 quarters * 2 = 8 quarters; 6 eighths / 2 = 3 eighths).
        Otherwise the remaining factor is pushed into the base duration
        (3 eighths / 2 = 3 sixteenths; 1 quarter * 3/2 = 3 eighths;
        4 quarters / 3 = 4 triplet eighths, if the base supports tuplets).

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
        >>> TemporalUnit(4, quarter).scale(2)
        TemporalUnit(8, MetricalDuration(1, 4))
        >>> TemporalUnit(3, eighth).scale(Fraction(1, 2))
        TemporalUnit(3, MetricalDuration(1, 16))
        >>> TemporalUnit(4, quarter).scale(Fraction(1, 3)).base.rational_length
        Fraction(1, 12)

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
class CompoundTemporalUnit(Measurable):
    """An ordered series of Measurables, measured as their total length.

    It is a sequence of its members (length, indexing, membership, iteration),
    and a Measurable of their sum.

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
    >>> bar = CompoundTemporalUnit([TemporalUnit(2, quarter), TemporalUnit(3, eighth)])
    >>> bar.rational_length, len(bar), TemporalUnit(2, quarter) in bar
    (Fraction(7, 8), 2, True)
    >>> bar[1]
    TemporalUnit(3, MetricalDuration(1, 8))
    """

    units: tuple[Measurable, ...]

    def __init__(self, units: Iterable[Measurable]):
        object.__setattr__(self, "units", tuple(units))

    @property
    def temporal_system(self) -> TemporalSystem:
        """The system of the first member (an empty series belongs to every system)."""
        return self.units[0].temporal_system if self.units else ANY_TEMPORAL_SYSTEM

    def __iter__(self):
        return iter(self.units)

    def __getitem__(self, index):
        return self.units[index]

    def __len__(self):
        return len(self.units)

    def __contains__(self, item):
        return item in self.units

    def index(self, item: Measurable) -> int:
        """The position of the first member equal to `item`.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
        >>> CompoundTemporalUnit([TemporalUnit(2, quarter), TemporalUnit(3, eighth)]).index(TemporalUnit(3, eighth))
        1
        """
        return self.units.index(item)

    def count(self, item: Measurable) -> int:
        """How many members equal `item`.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
        >>> CompoundTemporalUnit([TemporalUnit(2, quarter), TemporalUnit(2, quarter)]).count(TemporalUnit(2, quarter))
        2
        """
        return self.units.count(item)

    def __repr__(self):
        return f"{type(self).__name__}({list(self.units)!r})"

    @property
    def rational_length(self) -> Fraction:
        return sum((tu.rational_length for tu in self.units), Fraction(0))

    def remainder(self, series: Iterable[Measurable]) -> Fraction:
        """Returns the length of self minus the total length of `series`.
        Negative if `series` overflows self.

        >>> from openmusickit.systems.wsmn.temporal.symbols import three_four, quarter, half
        >>> three_four.remainder([quarter, quarter])
        Fraction(1, 4)
        >>> three_four.remainder([half, half])
        Fraction(-1, 4)
        """
        return self.rational_length - sum((s.rational_length for s in series), Fraction(0))

    def first_out_of_bounds(self, series: Iterable[Measurable]) -> int | None:
        """Returns the index of the first item in `series`
        that exceeds the length of self.
        Returns None if the total length of series is <= length of self.

        >>> from openmusickit.systems.wsmn.temporal.symbols import three_four, quarter
        >>> three_four.first_out_of_bounds([quarter] * 4)
        3
        >>> three_four.first_out_of_bounds([quarter] * 3) is None
        True
        """

        srl = self.rational_length
        for i, item in enumerate(series):
            srl -= item.rational_length
            if srl < 0:
                return i
        return None

    def scale(self, scalar: int | Fraction) -> CompoundTemporalUnit:
        """Scales every member.

        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
        >>> CompoundTemporalUnit([TemporalUnit(2, quarter), TemporalUnit(3, eighth)]).scale(2)
        CompoundTemporalUnit([TemporalUnit(4, MetricalDuration(1, 4)), TemporalUnit(6, MetricalDuration(1, 8))])

        Raises
        ------
        ScalingError
            if any member cannot be scaled by `scalar`.
        """
        try:
            new_units = [tu.scale(scalar) for tu in self.units]
        except ScalingError as e:
            raise ScalingError(
                f"One or more members cannot complete the requested scaling operation: {e}"
            ) from e
        return type(self)(new_units)


@dataclass(frozen=True, slots=True)
class TemporalRatio:
    """The ratio of two Measurables (usually TemporalUnits).

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

    nominal: Measurable
    contextual: Measurable

    @property
    def multiplier(self) -> Fraction:
        """The multiplier that converts a nominal length into a contextual length:
        contextual_length / nominal_length.

        For a quarter-note triplet this is 2/3;
        for a tempo of quarter = 60 it is microseconds-per-whole-note (4_000_000).

        >>> from openmusickit.systems.wsmn.temporal.symbols import triplet, quarter
        >>> triplet(quarter).multiplier
        Fraction(2, 3)
        >>> from openmusickit.values.time.clock_time import Tempo
        >>> Tempo(60, quarter).multiplier
        Fraction(4000000, 1)
        """
        return Fraction(self.contextual.rational_length) / Fraction(self.nominal.rational_length)

    def __eq__(self, other):
        if not isinstance(other, TemporalRatio):
            return NotImplemented
        return self.multiplier == other.multiplier

    def __hash__(self):
        return hash(self.multiplier)

    def __repr__(self):
        return f"{type(self).__name__}({self.nominal!r}, {self.contextual!r})"
