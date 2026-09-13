from __future__ import annotations
from fractions import Fraction as F
from numbers import Rational

from openmusickit.values.time.duration import Duration, ZeroDuration, TemporalElement, TemporalRatio
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

    def __init__(self, n:int, d: int, dots: int= 0, tr: TemporalRatio = None):
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
            raise ValueError("The numerator must be a positive integer. (Use ZeroDuration for a zero-length duration.)")

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
                "or a power of two over 1 (breve, longa, maxima).")

        implied_dots = (odd + 1).bit_length() - 2

        if implied_dots > 0 and dots > 0:
            raise ValueError("Use a nominal value + dots, or an actual value without dots, never both.")

        # the base (undotted) value: strip the dot factor back out
        base = value * (2 ** implied_dots) / odd

        self._n = base.numerator
        self._d = base.denominator
        self._dots = dots + implied_dots
        self._tr = tr or None

    @classmethod
    def from_fraction(cls, value: Rational, tr: TemporalRatio = None) -> MeteredDuration:
        """Create a MeteredDuration from its full nominal value (e.g. 3/8 -> dotted quarter).

        Raises ValueError if the value is not a single notatable symbol."""
        value = F(value)
        return cls(value.numerator, value.denominator, tr=tr)

    @property
    def real_n(self):
        return self.real_note_duration[0]

    @property
    def real_d(self):
        return self.real_note_duration[1]

    @property
    def n(self):
        return self._n

    @property
    def d(self):
        return self._d

    @property
    def dots(self):
        return self._dots

    @property
    def tr(self) -> TemporalRatio | None:
        return self._tr

    @property
    def nominal_length(self) -> F:
        """The notated value, including dots but ignoring any tuplet ratio."""
        return F(*self.real_note_duration)
    
    @property
    def rational_length(self):
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
        f = F(self.n * (2 ** (self.dots + 1) - 1), self.d * (2 ** self.dots))
        return f.numerator, f.denominator
    
    def scale(self, scalar: int | F) -> MeteredDuration:
        """Returns a MeteredDuration augmented of diminished by a power of two."""
        try:
            scalar = F(scalar)
        except (TypeError, ValueError):
            raise ScalingError(f"Cannot scale a MeteredDuration by {scalar!r}.")

        if not _is_power_of_two(scalar):
            raise ScalingError("You can only scale a MeteredDuration by a power of 2.\n Try creating a new Duration from scratch.")
            # TODO: Handle scaling for non-mulitples of 2 (make dots, make tuplets)
            # TODO: Handle scaling for tuplets correctly (adjust temporal ratios)

        base = F(self.n, self.d) * scalar
        return MeteredDuration(base.numerator, base.denominator, self.dots, self._tr)

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
            return f"MeteredDuration({self.n}, {self.d})"
        elif self.dots == 0:
            return f"MeteredDuration({self.n}, {self.d}, tr={self._tr!r})"
        elif self._tr is None:
            return f"MeteredDuration({self.n}, {self.d}, dots={self.dots})"
        else:
            return f"MeteredDuration({self.n}, {self.d}, dots={self.dots}, tr={self._tr!r})" 


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
            raise ValueError("A TiedDuration needs at least two members. Use a plain Duration for one.")
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

    def scale(self, scalar) -> TiedDuration:
        return TiedDuration([m.scale(scalar) for m in self._members])

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
        return f"TiedDuration({self._members!r})"


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
