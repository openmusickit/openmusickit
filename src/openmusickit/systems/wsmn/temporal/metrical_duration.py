from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction as F
from numbers import Rational

from openmusickit.errors import ScalingError
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.values.time.duration import (
    Duration,
    Measurable,
    TemporalRatio,
    TemporalSystem,
    TemporalUnit,
    ZeroDuration,
)


@dataclass(frozen=True, slots=True, eq=False)
class MetricalDuration(Duration, Measurable):
    """The duration of notes, rests, or other temporal musical items
    as understood and notated in Western Standard Music Notation.

    Duration values are stored as nominal values,
    so a dotted quarter note is stored as numerator 1, denominator 4, dots 1.
    Actual temporal values (3/8) are calculated when queried.

    Notes longer than a whole note (breve, longa, maxima) are stored
    with a power-of-two numerator and a denominator of 1,
    so a breve is (2, 1) and a dotted longa is (4, 1, dots=1).

    Tuplet values are handled by storing a TemporalRatio,
    which is (n, TemporalElements) against (m, TemporalElements).

    A quarter note inside a standard quarter-note triplet would then be:

    >>> from openmusickit.values.time.duration import TemporalRatio, TemporalUnit
    >>> quarter = MetricalDuration(1, 4)
    >>> triplet = TemporalRatio(TemporalUnit(3, quarter), TemporalUnit(2, quarter))
    >>> MetricalDuration(1, 4, ratio=triplet).rational_length
    Fraction(1, 6)

    MetricalDurations compare, sort, and hash by their real length,
    so ``MetricalDuration(3, 8) == MetricalDuration(1, 4, dots=1)``.

    A negative numerator is a negative duration: the same notated value in the
    opposite direction, produced by ``-duration`` or by subtraction. It is a
    signed quantity for arithmetic (an edge displacement, for instance), never
    the length of an event.

    >>> quarter - MetricalDuration(1, 2)
    MetricalDuration(-1, 4)

    """

    numerator: int
    denominator: int
    dots: int = 0
    ratio: TemporalRatio | None = None

    def __post_init__(self):
        """Validates and normalises the nominal value.

        MetricalDuration is created with a two-argument nominal note value,
        which may optionally include dots,
        and an optional ``TemporalRatio`` that defines timing and placement
        within a tuplet figure.


        Examples
        --------

        >>> quarter_note = MetricalDuration(1, 4)

        >>> MetricalDuration(1, 2, 1) == MetricalDuration(3, 4)  # dotted half, two ways
        True

        >>> MetricalDuration(2, 1)  # breve
        MetricalDuration(2, 1)
        >>> MetricalDuration(2, 1, dots=1) == MetricalDuration(3, 1)  # dotted breve, two ways
        True

        >>> triplet_ratio = TemporalRatio(TemporalUnit(3, quarter_note), TemporalUnit(2, quarter_note))
        >>> MetricalDuration(1, 4, ratio=triplet_ratio).rational_length
        Fraction(1, 6)

        Parameters
        ----------
        numerator : int
            The numerator of the nominal note value.

            This should normally be 1 for standard un-dotted note values,
            and should also be 1 if dots are specified.
            Dotted notes can be expressed as their full nominal value
            with numerator > 1 and dots = 0.

            Notes longer than a whole note use a power-of-two numerator
            over a denominator of 1: (2, 1) breve, (4, 1) longa, (8, 1) maxima.

            A negative numerator gives a negative duration.

        denominator : int
            The denominator of the nominal note value. Must be a power of two.

        dots : int (optional)
            The number of dots. Cannot be negative.

            When creating dotted duration, you have two options:

            1. Use the numerator and denominator of the base duration,
               and specify one or more dots.
            2. Use the numerator and denominator of the full duration,
               and do not specify any dots.

            These two cannot be mixed.

        ratio: TemporalRatio (optional)
            The tuplet ratio of notated durations within the tuplet
            against the nominal values of the context.

        Raises
        ------
        ValueError
            If numerator/denominator is not a single notatable symbol (e.g. 5/8),
            if the denominator is not a power of two, if the numerator is zero,
            if dots is negative, or if a full dotted value is given
            together with additional dots.

        """

        if (
            isinstance(self.denominator, bool)
            or not isinstance(self.denominator, int)
            or not _is_power_of_two(self.denominator)
        ):
            raise ValueError("The denominator must be a positive integer power of 2.")

        if (
            isinstance(self.numerator, bool)
            or not isinstance(self.numerator, int)
            or self.numerator == 0
        ):
            raise ValueError(
                "The numerator must be a non-zero integer. (Use ZeroDuration for a zero-length duration.)"
            )

        if self.dots < 0:
            raise ValueError("A duration cannot have negative dots.")

        # The sign is carried on the numerator; normalise the magnitude.
        sign = -1 if self.numerator < 0 else 1

        # reduce, then split the numerator into (power of two) * (odd part).
        # The odd part encodes the dots: 1 -> none, 3 -> one, 7 -> two, 15 -> three...
        value = F(abs(self.numerator), self.denominator)
        odd = value.numerator
        while odd % 2 == 0:
            odd //= 2

        if not _is_power_of_two(odd + 1):
            raise ValueError(
                f"{self.numerator}/{self.denominator} is not a single notatable duration. "
                "The numerator must be 1 less than a power of 2 (a dotted value), "
                "or a power of two over 1 (breve, longa, maxima)."
            )

        implied_dots = (odd + 1).bit_length() - 2

        if implied_dots > 0 and self.dots > 0:
            raise ValueError(
                "Use a nominal value + dots, or an actual value without dots, never both."
            )

        # the base (undotted) value: strip the dot factor back out
        base = value * (2**implied_dots) / odd

        object.__setattr__(self, "numerator", sign * base.numerator)
        object.__setattr__(self, "denominator", base.denominator)
        object.__setattr__(self, "dots", self.dots + implied_dots)

    @classmethod
    def from_fraction(
        cls, value: Rational, *, ratio: TemporalRatio | None = None
    ) -> MetricalDuration:
        """Create a MetricalDuration from its full nominal value (e.g. 3/8 -> dotted quarter).

        Raises ValueError if the value is not a single notatable symbol."""
        value = F(value)
        return cls(value.numerator, value.denominator, ratio=ratio)

    @classmethod
    def from_length(
        cls, length: Rational, *, ratio: TemporalRatio | None = None
    ) -> MetricalDuration | TiedDuration:
        """Resolve *any* positive rational length into notation:
        a single ``MetricalDuration`` where one exists, a tuplet member where the
        length needs one, and a ``TiedDuration`` where it needs a tie.

        This is the front door for lengths that arrive as *numbers* rather than
        as notation: quantized MIDI or audio, dividing a bar into ``n`` equal
        parts, scaling by 3, and so on. It always succeeds for a positive
        rational, and it always picks the *canonical* spelling described below,
        so the result is predictable but not necessarily the one a composer
        would choose in a particular metrical context (see "When not to use").

        Examples
        --------

        >>> from fractions import Fraction as F
        >>> from openmusickit.systems.wsmn.temporal.symbols import *

        A notatable length comes back as one symbol (equivalent to ``from_fraction``):

        >>> MetricalDuration.from_length(F(3, 8))
        MetricalDuration(1, 4, dots=1)
        >>> MetricalDuration.from_length(2)
        MetricalDuration(2, 1)

        An odd factor in the denominator means a tuplet.
        1/3 is a half note in a half-note triplet (3 halves in the time of 2):

        >>> third = MetricalDuration.from_length(F(1, 3))
        >>> third
        MetricalDuration(1, 2, ratio=TemporalRatio(TemporalUnit(3, MetricalDuration(1, 2)), TemporalUnit(2, MetricalDuration(1, 2))))
        >>> third.rational_length
        Fraction(1, 3)
        >>> third == half_in_triplet
        True

        1/6 is a quarter in a quarter-note triplet, 1/5 a quarter in a 5:4 quintuplet,
        1/7 a quarter in a 7:4 septuplet, 1/9 an eighth in a 9:8 tuplet:

        >>> MetricalDuration.from_length(F(1, 6)) == quarter_in_triplet
        True
        >>> [MetricalDuration.from_length(F(1, k)).ratio.multiplier for k in (5, 7, 9)]
        [Fraction(4, 5), Fraction(4, 7), Fraction(8, 9)]

        Lengths that need a tie come back as a ``TiedDuration``, split greedily
        largest-first (dotted values included):

        >>> MetricalDuration.from_length(F(5, 8))
        TiedDuration([MetricalDuration(1, 2), MetricalDuration(1, 8)])
        >>> MetricalDuration.from_length(F(13, 16))
        TiedDuration([MetricalDuration(1, 2, dots=1), MetricalDuration(1, 16)])
        >>> MetricalDuration.from_length(F(5, 8)).rational_length
        Fraction(5, 8)

        Ties and tuplets combine: 5/24 is a tied quarter + sixteenth inside a triplet.

        >>> tied = MetricalDuration.from_length(F(5, 24))
        >>> [m.nominal_length for m in tied], tied[0].ratio.multiplier, tied.rational_length
        ([Fraction(1, 4), Fraction(1, 16)], Fraction(2, 3), Fraction(5, 24))

        With ``ratio``, ``length`` is the *notated* value inside an existing tuplet
        (as in the constructor), so no new ratio is synthesized unless that
        notated value itself needs one (which produces a nested tuplet):

        >>> MetricalDuration.from_length(F(1, 4), ratio=triplet(quarter)) == quarter_in_triplet
        True
        >>> nested = MetricalDuration.from_length(F(1, 12), ratio=triplet(quarter))
        >>> nested.rational_length
        Fraction(1, 18)

        Dividing a bar of 4/4 into five equal parts:

        >>> part = MetricalDuration.from_length(four_four.rational_length / 5)
        >>> part.rational_length
        Fraction(1, 5)
        >>> part.ratio.multiplier
        Fraction(4, 5)
        >>> TemporalUnit(5, part) == four_four
        True

        Canonical spelling
        ------------------
        1. Reduce the fraction. If it is a single symbol (``n = 2^k`` over 1,
           or ``n = 2^(dots+1) - 1`` over a power of two), return it.
        2. If the denominator has an odd factor ``k``, the length is a tuplet
           member: ``k`` in the time of ``c``, where ``c`` is the largest power
           of two below ``k`` (3:2, 5:4, 7:4, 9:8, 11:8, ...). The ratio's unit
           is the largest plain note value that fits the notated length, and
           the notated length is then resolved by rule 1 or 3.
        3. Otherwise split largest-first into single symbols and tie them.

        When not to use
        ---------------
        - **You already know the notation.** ``MetricalDuration(1, 4, dots=1)``
          says exactly what is written; ``from_length(F(3, 8))`` merely
          happens to agree. Prefer the constructor (or ``from_fraction``,
          which raises if the value is not one symbol) whenever the spelling
          is known.
        - **The tuplet already exists.** Members of a tuplet should share the
          group's ``TemporalRatio``; pass it as ``ratio`` rather than letting this
          method invent a ratio that nothing else references.
        - **Metrical context matters.** The greedy tie split (5/8 = half +
          eighth) and the simple-meter tuplet convention (7:4 rather than 7:6)
          ignore the time signature and beat position, and a single symbol
          always wins over a tuplet: a bar of 6/8 divided by four gives
          dotted eighths, where an engraver would write a quadruplet.
          Notation-quality spelling is a job for a meter-aware layer built
          on top of this.

          >>> MetricalDuration.from_length(six_eight.rational_length / 4)
          MetricalDuration(1, 8, dots=1)

        - **Floats.** Pass ``Fraction`` or ``int``. A float is converted
          exactly, and binary floats have power-of-two denominators, so
          ``from_length(1/3)`` is not a triplet but a chain of 27 tied notes
          ending in a 1/18014398509481984th. Quantize first, e.g.
          ``Fraction(x).limit_denominator(64)``.

        Raises
        ------
        ValueError
            If ``length`` is not positive (use ``ZeroDuration`` for zero).
        """
        length = F(length)
        if length <= 0:
            raise ValueError(
                "from_length needs a positive length. (Use ZeroDuration for a zero-length duration.)"
            )

        # rule 1
        try:
            return cls(length.numerator, length.denominator, ratio=ratio)
        except ValueError:
            pass

        # rule 2: strip the odd factor out of the denominator with a tuplet
        den = length.denominator
        power_of_two_part = den & -den
        odd = den // power_of_two_part
        if odd > 1:
            contextual_count = 1 << (odd.bit_length() - 1)  # largest power of two below odd
            notated = length * odd / contextual_count  # power-of-two denominator now
            unit_length = _largest_plain_value_at_most(notated)
            unit = cls(unit_length.numerator, unit_length.denominator)
            unit_in_context = cls(unit_length.numerator, unit_length.denominator, ratio=ratio)
            ratio = TemporalRatio(
                TemporalUnit(odd, unit), TemporalUnit(contextual_count, unit_in_context)
            )
            return cls.from_length(notated, ratio=ratio)

        # rule 3: greedy tie
        members = []
        remaining = length
        while remaining > 0:
            piece = _largest_single_value_at_most(remaining)
            members.append(cls(piece.numerator, piece.denominator, ratio=ratio))
            remaining -= piece
        return TiedDuration(members)

    @property
    def temporal_system(self) -> TemporalSystem:
        return WSMN_TEMPORAL

    @property
    def nominal_length(self) -> F:
        """The notated value, including dots but ignoring any tuplet ratio."""
        return F(self.numerator * (2 ** (self.dots + 1) - 1), self.denominator * (2**self.dots))

    @property
    def rational_length(self) -> F:
        if self.ratio is None:
            return self.nominal_length
        return self.nominal_length * self.ratio.multiplier

    def scale(self, scalar: int | F) -> MetricalDuration | TiedDuration:
        """Returns this duration augmented or diminished by ``scalar``.

        A power of two keeps the same spelling (a dotted eighth doubled is a dotted quarter).
        Any other positive scalar is resolved with ``from_length`` on the notated value,
        so the result may be a different single symbol (quarter * 3 = dotted half),
        a tuplet member (quarter * 2/3 = triplet quarter), or a ``TiedDuration``
        (quarter * 5 = whole tied to quarter). An existing tuplet ratio is kept.

        Raises
        ------
        ScalingError
            if ``scalar`` is not a positive rational.
        """
        try:
            scalar = F(scalar)
        except (TypeError, ValueError) as e:
            raise ScalingError(f"Cannot scale a MetricalDuration by {scalar!r}.") from e
        if scalar <= 0:
            raise ScalingError("A MetricalDuration can only be scaled by a positive scalar.")

        if _is_power_of_two(scalar):
            base = F(self.numerator, self.denominator) * scalar
            return MetricalDuration(base.numerator, base.denominator, self.dots, self.ratio)

        return _from_signed_length(self.nominal_length * scalar, ratio=self.ratio)

    def __neg__(self) -> MetricalDuration:
        return MetricalDuration(-self.numerator, self.denominator, self.dots, self.ratio)

    def __add__(self, other):
        """Add two durations.

        Returns a single MetricalDuration when the sum is notatable as one symbol
        (quarter + eighth = dotted quarter), otherwise a TiedDuration.
        Durations in different tuplets always produce a TiedDuration.
        Durations of opposite sign are resolved by length, so the result is
        the canonical spelling of the difference (``from_length``), or
        ZeroDuration when they cancel."""
        if isinstance(other, ZeroDuration):
            return self
        if isinstance(other, Duration) and _is_negative(self) != _is_negative(other):
            return _from_signed_length(self.rational_length + other.rational_length)
        if isinstance(other, TiedDuration):
            return TiedDuration([self]) + other
        if isinstance(other, Duration):
            merged = _merge(self, other)
            return merged if merged is not None else TiedDuration([self, other])
        return NotImplemented

    def __radd__(self, other):
        # lets `sum(durations)` work with the default start value of 0
        if other == 0:
            return self
        return NotImplemented

    def __repr__(self):
        if self.dots == 0 and self.ratio is None:
            return f"{type(self).__name__}({self.numerator}, {self.denominator})"
        elif self.dots == 0:
            return (
                f"{type(self).__name__}({self.numerator}, {self.denominator}, ratio={self.ratio!r})"
            )
        elif self.ratio is None:
            return f"{type(self).__name__}({self.numerator}, {self.denominator}, dots={self.dots})"
        else:
            return f"{type(self).__name__}({self.numerator}, {self.denominator}, dots={self.dots}, ratio={self.ratio!r})"


@dataclass(frozen=True, slots=True, eq=False)
class TiedDuration(Duration, Measurable):
    """A single sounding duration notated as two or more tied symbols,
    e.g. quarter tied to sixteenth (5/16).

    Produced by adding MetricalDurations whose sum is not a single notatable value.
    Adding to a TiedDuration merges neighbouring members wherever possible,
    and collapses back to a plain MetricalDuration when the total becomes notatable.
    """

    members: tuple[Duration, ...]

    def __init__(self, members: Iterable[Duration]):
        members = tuple(members)
        if len(members) < 2:
            raise ValueError(
                "A TiedDuration needs at least two members. Use a plain Duration for one."
            )
        object.__setattr__(self, "members", members)

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __getitem__(self, index):
        return self.members[index]

    @property
    def temporal_system(self) -> TemporalSystem:
        return WSMN_TEMPORAL

    @property
    def rational_length(self) -> F:
        return sum((m.rational_length for m in self.members), F(0))

    def scale(self, scalar) -> Duration:
        """Scale every member; the result is re-merged, so it may collapse to a single symbol."""
        result = self.members[0].scale(scalar)
        for m in self.members[1:]:
            result = result + m.scale(scalar)
        return result

    def __neg__(self) -> TiedDuration:
        return TiedDuration(-m for m in self.members)

    def __add__(self, other):
        if isinstance(other, ZeroDuration):
            return self
        if isinstance(other, Duration) and _is_negative(self) != _is_negative(other):
            return _from_signed_length(self.rational_length + other.rational_length)
        if isinstance(other, TiedDuration):
            result = self
            for m in other:
                result = result + m
            return result
        if not isinstance(other, Duration):
            return NotImplemented

        # fold `other` into the tail, merging as far back as it will go
        members = list(self.members)
        current = other
        while members:
            merged = _merge(members[-1], current)
            if merged is None:
                break
            members.pop()
            current = merged
        members.append(current)

        if len(members) == 1:
            return members[0]
        return TiedDuration(members)

    def __radd__(self, other):
        if other == 0:
            return self
        return NotImplemented

    def __repr__(self):
        return f"{type(self).__name__}({list(self.members)!r})"


def _is_negative(d: Duration) -> bool:
    return d.rational_length < 0


def _from_signed_length(length: F, *, ratio: TemporalRatio | None = None) -> Duration:
    """``from_length`` for a length of either sign; zero becomes ZeroDuration.

    >>> _from_signed_length(F(-3, 8))
    MetricalDuration(-1, 4, dots=1)
    >>> isinstance(_from_signed_length(F(0)), ZeroDuration)
    True
    """
    if length == 0:
        return ZeroDuration()
    if length < 0:
        return -MetricalDuration.from_length(-length, ratio=ratio)
    return MetricalDuration.from_length(length, ratio=ratio)


def _merge(a: Duration, b: Duration) -> MetricalDuration | None:
    """Return a single MetricalDuration equal to a + b, or None if there isn't one."""
    if not (isinstance(a, MetricalDuration) and isinstance(b, MetricalDuration)):
        return None
    if a.ratio != b.ratio:
        return None
    try:
        return MetricalDuration.from_fraction(a.nominal_length + b.nominal_length, ratio=a.ratio)
    except ValueError:
        return None


def _largest_plain_value_at_most(x: F) -> F:
    """The largest undotted note value (a power of two) that is <= x."""
    value = F(1)
    while value > x:
        value /= 2
    while value * 2 <= x:
        value *= 2
    return value


def _largest_single_value_at_most(x: F) -> F:
    """The largest single notatable value (dots allowed) that is <= x.
    Used for greedy tie splitting."""
    base = _largest_plain_value_at_most(x)
    dots = 0
    while base * (2 ** (dots + 2) - 1) / (2 ** (dots + 1)) <= x:
        dots += 1
    return base * (2 ** (dots + 1) - 1) / (2**dots)


def _is_power_of_two(n: int | F) -> bool:
    """True for 1, 2, 4, 8... and also for 1/2, 1/4, 1/8..."""
    if isinstance(n, bool):
        return False
    if isinstance(n, int):
        return n > 0 and (n & (n - 1)) == 0
    if isinstance(n, Rational):
        if n.numerator == 1:
            return _is_power_of_two(n.denominator)
        if n.denominator == 1:
            return _is_power_of_two(n.numerator)
        return False
    return False
