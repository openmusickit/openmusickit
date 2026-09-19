from __future__ import annotations

from fractions import Fraction as F
from numbers import Rational

from openmusickit.values.time.duration import Duration, TemporalRatio, TemporalUnit, ZeroDuration
from openmusickit.values.time.errors import ScalingError


class MeteredDuration(Duration):
    """The duration of notes, rests, or other temporal musical items
    as understood and notated in Western Standard Music Notation.

    Duration values are stored as nominal values,
    so a dotted quarter notes is stored as: {n: 1, d: 4, dots: 1}.
    Actual temporal values (3, 8) are calculated when queried.

    Notes longer than a whole note (breve, longa, maxima) are stored
    with a power-of-two numerator and a denominator of 1,
    so a breve is {n: 2, d: 1, dots: 0} and a dotted longa is {n: 4, d: 1, dots: 1}.

    Tuplet values are handled by storing a TemporalRatio,
    which is (n, TemporalElements) against (m, TemporalElements).

    A quarter note inside standard quarter note triplet would then be:

        Duration(
        n = 1, d = 4, dots = 0,
        TemporalRatio(
            (TemporalUnit(3, Duration(1,4)),
            (TemporalUnit(2, Duration(1,4))
            )
        )

    MeteredDurations compare, sort, and hash by their real length,
    so ``MeteredDuration(3, 8) == MeteredDuration(1, 4, dots=1)``.

    """

    def __init__(self, n: int, d: int, dots: int = 0, tr: TemporalRatio | None = None):
        """
        MeteredDuration is created with a two-argument nominal note value,
        which may optionally include dots,
        and an optional ``TemporalRatio`` that defines timing and placement
        within a tuplet figure.


        Examples
        --------

        ```
        quarter_note = MeteredDuration(1, 4)

        dotted_half_note = MeteredDuration(1, 2, 1)
        also_dotted_half = MeteredDuration(3, 4)

        breve = MeteredDuration(2, 1)
        dotted_breve = MeteredDuration(2, 1, dots=1)
        also_dotted_breve = MeteredDuration(3, 1)

        triplet_ratio = TemporalRatio(
            TemporalUnit(3, quarter_note),
            TemporalUnit(2, quarter_note)
        )
        quarter_note_in_triplet = MeteredDuration(1, 4, tr=triplet_ratio)
        ```

        Parameters
        ----------
        n : int
            The numerator of the nominal note value.

            This should normally be 1 for standard un-dotted note values,
            and should also be 1 if dots are specified.
            Dotted notes can be expressed as their full nominal value
            with n > 1 and dots = 0.

            Notes longer than a whole note use a power-of-two numerator
            over a denominator of 1: (2, 1) breve, (4, 1) longa, (8, 1) maxima.

        d : int
            The denominator of the nominal note value. Must be a power of two.

        dots : int (optional)
            The number of dots. Cannot be negative.

            When creating dotted duration, you have two options:

            1. Use the numerator and denominator of the base duration,
               and specify one or more dots.
            2. Use the numerator and denominator of the full duration,
               and do not specify any dots.

            These two cannot be mixed.

        tr: TemporalRatio (optional)
            The tuplet ratio of notated durations within the tuplet
            against the nominal values of the context.

        Raises
        ------
        ValueError
            If n/d is not a single notatable symbol (e.g. 5/8),
            if d is not a power of two, if n is not positive,
            if dots is negative, or if a full dotted value is given
            together with additional dots.

        """

        if isinstance(d, bool) or not isinstance(d, int) or not _is_power_of_two(d):
            raise ValueError("The denominator must be a positive integer power of 2.")

        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError(
                "The numerator must be a positive integer. (Use ZeroDuration for a zero-length duration.)"
            )

        if dots < 0:
            raise ValueError("A duration cannot have negative dots.")

        # reduce, then split the numerator into (power of two) * (odd part).
        # The odd part encodes the dots: 1 -> none, 3 -> one, 7 -> two, 15 -> three...
        value = F(n, d)
        odd = value.numerator
        while odd % 2 == 0:
            odd //= 2

        if not _is_power_of_two(odd + 1):
            raise ValueError(
                f"{n}/{d} is not a single notatable duration. "
                "The numerator must be 1 less than a power of 2 (a dotted value), "
                "or a power of two over 1 (breve, longa, maxima)."
            )

        implied_dots = (odd + 1).bit_length() - 2

        if implied_dots > 0 and dots > 0:
            raise ValueError(
                "Use a nominal value + dots, or an actual value without dots, never both."
            )

        # the base (undotted) value: strip the dot factor back out
        base = value * (2**implied_dots) / odd

        self._n = base.numerator
        self._d = base.denominator
        self._dots = dots + implied_dots
        self._tr = tr or None

    @classmethod
    def from_fraction(cls, value: Rational, tr: TemporalRatio | None = None) -> MeteredDuration:
        """Create a MeteredDuration from its full nominal value (e.g. 3/8 -> dotted quarter).

        Raises ValueError if the value is not a single notatable symbol."""
        value = F(value)
        return cls(value.numerator, value.denominator, tr=tr)

    @classmethod
    def from_length(
        cls, length: Rational, *, tr: TemporalRatio | None = None
    ) -> MeteredDuration | TiedDuration:
        """Resolve *any* positive rational length into notation:
        a single ``MeteredDuration`` where one exists, a tuplet member where the
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

        >>> MeteredDuration.from_length(F(3, 8))
        MeteredDuration(1, 4, dots=1)
        >>> MeteredDuration.from_length(2)
        MeteredDuration(2, 1)

        An odd factor in the denominator means a tuplet.
        1/3 is a half note in a half-note triplet (3 halves in the time of 2):

        >>> third = MeteredDuration.from_length(F(1, 3))
        >>> third
        MeteredDuration(1, 2, tr=TemporalRatio(TemporalUnit(3, MeteredDuration(1, 2)), TemporalUnit(2, MeteredDuration(1, 2))))
        >>> third.rational_length
        Fraction(1, 3)
        >>> third == half_in_triplet
        True

        1/6 is a quarter in a quarter-note triplet, 1/5 a quarter in a 5:4 quintuplet,
        1/7 a quarter in a 7:4 septuplet, 1/9 an eighth in a 9:8 tuplet:

        >>> MeteredDuration.from_length(F(1, 6)) == quarter_in_triplet
        True
        >>> [MeteredDuration.from_length(F(1, k)).tr.r for k in (5, 7, 9)]
        [Fraction(4, 5), Fraction(4, 7), Fraction(8, 9)]

        Lengths that need a tie come back as a ``TiedDuration``, split greedily
        largest-first (dotted values included):

        >>> MeteredDuration.from_length(F(5, 8))
        TiedDuration([MeteredDuration(1, 2), MeteredDuration(1, 8)])
        >>> MeteredDuration.from_length(F(13, 16))
        TiedDuration([MeteredDuration(1, 2, dots=1), MeteredDuration(1, 16)])
        >>> MeteredDuration.from_length(F(5, 8)).rational_length
        Fraction(5, 8)

        Ties and tuplets combine: 5/24 is a tied quarter + sixteenth inside a triplet.

        >>> tied = MeteredDuration.from_length(F(5, 24))
        >>> [m.nominal_length for m in tied], tied[0].tr.r, tied.rational_length
        ([Fraction(1, 4), Fraction(1, 16)], Fraction(2, 3), Fraction(5, 24))

        With ``tr``, ``length`` is the *notated* value inside an existing tuplet
        (as in the constructor), so no new ratio is synthesized unless that
        notated value itself needs one (which produces a nested tuplet):

        >>> MeteredDuration.from_length(F(1, 4), tr=triplet(quarter)) == quarter_in_triplet
        True
        >>> nested = MeteredDuration.from_length(F(1, 12), tr=triplet(quarter))
        >>> nested.rational_length
        Fraction(1, 18)

        Dividing a bar of 4/4 into five equal parts:

        >>> part = MeteredDuration.from_length(four_four.rational_length / 5)
        >>> part.rational_length
        Fraction(1, 5)
        >>> part.tr.r
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
        - **You already know the notation.** ``MeteredDuration(1, 4, dots=1)``
          says exactly what is written; ``from_length(F(3, 8))`` merely
          happens to agree. Prefer the constructor (or ``from_fraction``,
          which raises if the value is not one symbol) whenever the spelling
          is known.
        - **The tuplet already exists.** Members of a tuplet should share the
          group's ``TemporalRatio``; pass it as ``tr`` rather than letting this
          method invent a ratio that nothing else references.
        - **Metrical context matters.** The greedy tie split (5/8 = half +
          eighth) and the simple-meter tuplet convention (7:4 rather than 7:6)
          ignore the time signature and beat position, and a single symbol
          always wins over a tuplet: a bar of 6/8 divided by four gives
          dotted eighths, where an engraver would write a quadruplet.
          Notation-quality spelling is a job for a meter-aware layer built
          on top of this.

          >>> MeteredDuration.from_length(six_eight.rational_length / 4)
          MeteredDuration(1, 8, dots=1)

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
            return cls(length.numerator, length.denominator, tr=tr)
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
            unit_in_context = cls(unit_length.numerator, unit_length.denominator, tr=tr)
            ratio = TemporalRatio(
                TemporalUnit(odd, unit), TemporalUnit(contextual_count, unit_in_context)
            )
            return cls.from_length(notated, tr=ratio)

        # rule 3: greedy tie
        members = []
        remaining = length
        while remaining > 0:
            piece = _largest_single_value_at_most(remaining)
            members.append(cls(piece.numerator, piece.denominator, tr=tr))
            remaining -= piece
        return TiedDuration(members)

    @property
    def real_n(self):
        return self.real_note_duration[0]

    @property
    def real_d(self):
        return self.real_note_duration[1]

    @property
    def n(self) -> int:
        return self._n

    @property
    def d(self) -> int:
        return self._d

    @property
    def dots(self) -> int:
        return self._dots

    @property
    def tr(self) -> TemporalRatio | None:
        return self._tr

    @property
    def nominal_length(self) -> F:
        """The notated value, including dots but ignoring any tuplet ratio."""
        return F(*self.real_note_duration)

    @property
    def rational_length(self) -> F:
        if self._tr is None:
            return self.nominal_length
        return self.nominal_length * self._tr.r

    @property
    def scalar_length(self):
        return float(self.rational_length)

    @property
    def real_note_duration(self) -> tuple[int, int]:
        """
        Calculate the numerator and denominator of a dotted note duration
        (ignoring any tuplet ratio).

        Returns:
            (int, int): Tuple of (numerator, denominator) of the total duration.
        """
        f = F(self.n * (2 ** (self.dots + 1) - 1), self.d * (2**self.dots))
        return f.numerator, f.denominator

    def scale(self, scalar: int | F) -> MeteredDuration | TiedDuration:
        """Returns this duration augmented or diminished by ``scalar``.

        A power of two keeps the same spelling (a dotted eighth doubled is a dotted quarter).
        Any other positive scalar is resolved with ``from_length`` on the notated value,
        so the result may be a different single symbol (quarter * 3 = dotted half),
        a tuplet member (quarter * 2/3 = triplet quarter), or a ``TiedDuration``
        (quarter * 5 = whole tied to quarter). An existing tuplet ratio is kept.

        Raises:
            ScalingError: if ``scalar`` is not a positive rational.
        """
        try:
            scalar = F(scalar)
        except (TypeError, ValueError) as e:
            raise ScalingError(f"Cannot scale a MeteredDuration by {scalar!r}.") from e
        if scalar <= 0:
            raise ScalingError("A MeteredDuration can only be scaled by a positive scalar.")

        if _is_power_of_two(scalar):
            base = F(self.n, self.d) * scalar
            return MeteredDuration(base.numerator, base.denominator, self.dots, self._tr)

        return MeteredDuration.from_length(self.nominal_length * scalar, tr=self._tr)

    def __add__(self, other):
        """Add two durations.

        Returns a single MeteredDuration when the sum is notatable as one symbol
        (quarter + eighth = dotted quarter), otherwise a TiedDuration.
        Durations in different tuplets always produce a TiedDuration."""
        if isinstance(other, ZeroDuration):
            return self
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
        if self.dots == 0 and self._tr is None:
            return f"{type(self).__name__}({self.n}, {self.d})"
        elif self.dots == 0:
            return f"{type(self).__name__}({self.n}, {self.d}, tr={self._tr!r})"
        elif self._tr is None:
            return f"{type(self).__name__}({self.n}, {self.d}, dots={self.dots})"
        else:
            return f"{type(self).__name__}({self.n}, {self.d}, dots={self.dots}, tr={self._tr!r})"


class TiedDuration(Duration):
    """A single sounding duration notated as two or more tied symbols,
    e.g. quarter tied to sixteenth (5/16).

    Produced by adding MeteredDurations whose sum is not a single notatable value.
    Adding to a TiedDuration merges neighbouring members wherever possible,
    and collapses back to a plain MeteredDuration when the total becomes notatable.
    """

    def __init__(self, members: list[Duration]):
        members = list(members)
        if len(members) < 2:
            raise ValueError(
                "A TiedDuration needs at least two members. Use a plain Duration for one."
            )
        self._members = members

    @property
    def members(self) -> list[Duration]:
        return list(self._members)

    def __iter__(self):
        return iter(self._members)

    def __len__(self):
        return len(self._members)

    def __getitem__(self, index):
        return self._members[index]

    @property
    def rational_length(self) -> F:
        return sum((m.rational_length for m in self._members), F(0))

    def scale(self, scalar) -> Duration:
        """Scale every member; the result is re-merged, so it may collapse to a single symbol."""
        result = self._members[0].scale(scalar)
        for m in self._members[1:]:
            result = result + m.scale(scalar)
        return result

    def __add__(self, other):
        if isinstance(other, ZeroDuration):
            return self
        if isinstance(other, TiedDuration):
            result = self
            for m in other:
                result = result + m
            return result
        if not isinstance(other, Duration):
            return NotImplemented

        # fold `other` into the tail, merging as far back as it will go
        members = list(self._members)
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
        return f"{type(self).__name__}({self._members!r})"


def _merge(a: Duration, b: Duration) -> MeteredDuration | None:
    """Return a single MeteredDuration equal to a + b, or None if there isn't one."""
    if not (isinstance(a, MeteredDuration) and isinstance(b, MeteredDuration)):
        return None
    if a.tr != b.tr:
        return None
    try:
        return MeteredDuration.from_fraction(a.nominal_length + b.nominal_length, tr=a.tr)
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
