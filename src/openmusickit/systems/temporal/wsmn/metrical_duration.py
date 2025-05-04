from __future__ import annotations
from fractions import Fraction as F
from numbers import Rational

from openmusickit.time.duration import Duration, TemporalElement, TemporalRatio

class MeteredDuration(Duration):
    """The duration of notes, rests, or other temporal musical items
    as understood and notated in Western Standard Music Notation.
    
    Duration values are stored as nominal values,
    so a dotted quarter notes is stored as: {n: 1, d: 4, dots: 1}.
    Actual temporal values (3, 8) are calculated when queried.
    
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

    """

    def __init__(self, n:int, d: int, dots: int= 0, tr: TemporalRatio = None):
        """
        MeteredDuration is created with a two-argument nominal note value,
        which may optionally include dots,
        and an optional ``TemporalRatio`` that defines timing and placement
        within a tuplet figure.

        
        Examples
        --------

        >>> quarter_note = MeteredDuration(1, 4)

        >>> dotted_half_note = MeteredDuration(1, 2, 1)
        >>> also_dotted_half = MeteredDuration(3, 4)
            
        >>> triplet_ratio = TemporalRatio(
        ...     TemporalUnit(3, quarter_note),
        ...     TemporalUnit(2, quarter_note)
        ... )
        ... quarter_note_in_triplet = MeteredDuration(1, 4, tr=triplet_ratio)

        
        Parameters
        ----------
        n : int
            The numerator of the nominal note value.
            
            This should normally be 1 for standard un-dotted note values,
            and should also be 1 if dots are specified.
            Dotted notes can be expressed as their full nominal value
            with n > 1 and dots = 0.


        d : int
            The denominator of the nominal note value.

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

        """    

        # check if denominator is valid
        if not _is_power_of_two(d):
            raise ValueError("The denominator must be a power of 2.")
        
        # check if numerator is valid
        if not _is_one_less_than_pow_of_two(n):
            if not _is_a_breve(n, d):
                raise ValueError("The numerator must be 1 less than a power of 2, \n unless the note is a breve (double whole note).")

        # check dots are valid
        if dots < 0:
            raise ValueError("A duration cannot have negative dots.")

        # check not dotting an already dotted duration
        if dots > 0 and n > 1:
            raise ValueError("Use a nominal value + dots, or an actual value without dots, never both.")
        
        
        if n > 1:
            self._n, self._d, self.dots = self._nominal_value(n, d)
        else:
            self._n = n
            self._d = d
            self._dots = dots

        self._tr = tr

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
    def rational_length(self):
        n, d = self.real_note_duration
        if TemporalRatio is None:
            return F(n, d)
        return F(n, d) * self._tr.r
    
    @property
    def scalar_length(self):
        return float(self.rational_length)
        
    @property
    def real_note_duration(self) -> tuple[int, int]:
        """
        Calculate the numerator and denominator of a dotted note duration.

        Args:
            base_numerator (int): Numerator of the base note (usually 1).
            base_denominator (int): Denominator of the base note (e.g. 4 for quarter note).
            dots (int): Number of dots (0 = undotted, 1 = dotted, etc.).

        Returns:
            (int, int): Tuple of (numerator, denominator) of the total duration.
        """
        numerator = self.n * (2 ** (self.dots + 1) - 1)
        denominator = self.d * (2 ** self.dots)
        return numerator, denominator


    def _nominal_value(self, n: int, d: int):
        """
        Given a dotted note as (n, d), return (base_n, base_d, num_dots),
        """
        dots = 0

        while n > 1:

            n = n - 1
            dots = dots + 1

            n = n/2
            d = d/2

        if d < 1:
            n = 1/d
            d = 1

        return int(n), int(d), dots
    
    def scale(self, scalar: int | F) -> MeteredDuration:
        """Returns a MeteredDuration augmented of diminished by a power of two."""
        if not _is_power_of_two(scalar):
            raise ValueError("You can only scale a MeteredDuration by a power of 2.\n Try creating a new Duration from scratch.")
            # We could do 3 and 1/3 as well, but they wouldn't be valid for all values of self.

        # scale the numerator and reduce the fraction
        f = F((self.n * scalar), self.d)

        return MeteredDuration(f.numerator, f.denominator, self.dots, repr(self._tr))
            

    
    def __repr__(self):
        if self.dots == 0 and self._tr is None:
            return f"MeteredDuration({self.n}, {self.d})"
        elif self.dots == 0:
            return f"MeteredDuration({self.n}, {self.d}, tr={repr(self._tr)})"
        elif self._tr is None:
            return f"MeteredDuration({self.n}, {self.d}, {self.dots})"
        else:
            return f"MeteredDuration({self.n}, {self.d}, {self.dots}, {repr(self._tr)})" 



    
def _is_power_of_two(n: int | F) -> bool:
    try:
        return n > 0 and (n & (n - 1)) == 0
    except TypeError:
        if n.numerator == 1:
            d = n.denominator
            return _is_power_of_two(d)
        else:
            return False

def _is_one_less_than_pow_of_two(x):
  return _is_power_of_two(x + 1)

def _is_a_breve(n, d):
    if d != 1:
        return False
    if n not in (2, 3):
        return False
    return True