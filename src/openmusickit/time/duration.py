from __future__ import annotations

from abc import ABC, abstractmethod
from fractions import Fraction
from functools import singledispatchmethod
from numbers import Real
from typing import List, Iterable
from .errors import ScalingError


class TemporalSystem:
    """A named system of musical time"""
    pass

class TemporalElement(ABC):
    """Any class that represents a structured period of time 
    which can be measured and subdivided. For example:
    note durations, measures, beat cycles, gong cycles, and other units of time.

    Any internally-consistent rhthmic/temporal system should be constructable
    using a subclasses of TemporalElement and AbstractDuration.

    """
    
    @property
    @abstractmethod
    def rational_length(self) -> Fraction:
        """Returns a fraction value representing the length of the TemporalElement,
        as defined within the TemporalSystem."""
        raise NotImplementedError
    
    #@property
    #@abstractmethod
    #def temporal_system(self) -> TemporalSystem:
    #    """The Temporal System which the duration belongs to (for introspection purposes)."""
    #    raise NotImplementedError
    
    @abstractmethod
    def scale(self, scalar: int|Fraction):
        """Return a TemporalElement scaled by a scalar according to its TemporalSystem.

        Implementations should return a new TemporalElement of the same type.

        Raises:
            ScalingError: If the scaled value is musically valid in the TemporalSystem
                but cannot be represented as a single TemporalElement of this type.
                For example, a WSMN MeteredDuration may only support scaling by powers of two;
                other scalar values may require a composite representation,
                such as tied durations.
    """
        raise NotImplementedError

class Duration(TemporalElement):
    """Any class that represents a basic unit of time and is notated as a single symbol.
    
    Subclass Duration to create the specific duration unit(s) of a particular system.
    For example, WSMN's note durations (quarter, half note, tuplets, etc),
    are managed by MeteredDuration.
    
    WSMN only requires a single note duration type to cover standard note durations.
    Some temporal systems will may need many different Duration types.
    """


class TemporalUnit(TemporalElement):
    """A length of musical time defined as n number of TemporalElements.
    This is used to represent (among other things) 
    time signatures and tuple definitions.
    
    Example: WSMN Time Signatures
    ---------------

    A time signature has:
     - a numerator (top number),
       which defines "how many" of some MeteredDuration.
     - a denominator (bottom number),
       which defines some MeteredDuration.

    So 4/4 time is 4 quarter notes and is expressed as:

    ```
    TemporalUnit(4, MeteredDuration(1,4))
    ```

    Compound meters such as 6/8 can be expressed using 
    the dotted duration or the base duration:

    ```
    TemporalUnit(6, MeteredDuration(1,8))

    TemporalUnit(2, MeteredDuration(1,4, dots=1))
    ```

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

    def __init__(self, count: int, base: Duration):
        self.count = count
        self.base = base

    @property
    def temporal_system(self) -> TemporalSystem:
        return self.base.temporal_system

    @property
    def rational_length(self) -> Fraction:
        return self.count * self.base.rational_length 
    
    def scale(self, scalar: int):
        """Scale the Temporal Unit"""
        # TODO: Need to account for fractions
        return self.__class__(self.count * scalar, self.base)

    def __eq__(self, durations: List[Duration]):
        """Compares self to the combined value of an iterable of durations."""
        pass

    def __repr__(self):
        return f'TemporalUnit({self.count}, {repr(self.base)})'


class CompoundTemporalUnit(TemporalElement):
    """An iterable defining a series of ordered temporal elements."""

    def __init__(self, units: list[TemporalUnit]):
        self._units = units

    def __iter__(self):
        return iter(self._units)

    def __getitem__(self, index):
        return self._units[index]
    
    def __len__(self):
        return len(self._units)

    def __contains__(self, item):
        return item in self._units
    
    def index(self, item):
        return self._units.index(item)
    
    def count(self, item):
        return self._units.count(item)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._units!r})"

    @property
    def rational_length(self):
        return sum([tu.count * (tu.base.rational_length) for tu in self._units])
    
    def first_out_of_bounds(self, series: Iterable[Duration]):
        """Returns the index of the first items in `series`
        that exceeds the length of self.
        Returns None if the total length of series is <= length of self."""

        srl = self.rational_length
        for i in len(series):
            srl -= series[i].rational_length
            if srl < 0:
                return i
        return None
    
    def scale(self, scalar):
        try:
            new_units = [tu.scale(scalar) for tu in self.units]
        except ScalingError as e:
            raise ScalingError(f"One or more members cannot complete the requested scaling operation: {e}")
        return CompoundTemporalUnit(new_units)
    


class TemporalRatio:
    """The ratio of two TemporalUnits.
    
    Used for the following:

    - In WSMN, tuplets are a ratio of n number of nominal units which take place during d number of contextual (or actual units).
    - In WSMN, a metronome marking or tempo is ratio of n number of MeteredDurations during d number of ClockTime seconds.
    - In mixed-system contexts, a ratio of n TemporalUnits in one system to d TemporalUnits of another system can be used for syncing.
      (For example, one puntum in Gregorian chant may equal one quarter note in WSMN)

    Other temporal systems may find other uses (for example, defining duration ratios within a gong cycle).

    n: numerator or nominal units, the number and type of notes notated and played
    d: denominator (sometimes called "actual" or "contextual), the length of time (expressed as a multiple of Durations)
        as measured in the surrounding context.
             
    So, for example, a standard quarternote triple (3 quarters in the time/space of 2 quarters) would be:

    ```python
    quarter = Duration(1, 4)
    two_quarters = TemporalUnit(2, quarter)
    three_quarters = TemporalUnit(3, quarter)
    triplet = TemporalRatio(two_quarters, three_quarters)
    ```

    Note that this only defines the relationship, and is not the tuplet itself.
    The ratio is then used in the definition of a Duration instance.
    (To calculate the RationalLength of the actual note, as opposed to its notated value.)

    (It is also used in the definition of a Tuplet node, which groups the constituent Notes.)

    """

    def __init__(self, nominal: TemporalUnit, contextual: TemporalUnit):

        #if nominal.temporal_system != contextual.temporal_system:
        #    raise TypeError('Both members of TemporalRatio must be in the same TemporalSystem. For mixed system ratios, use MixedTemporalRatio.')
        # QUESTION: Do I need to check for this, and do I need a separate MixedTemporalRatio?   

        self._n = nominal
        self._c = contextual

    @property
    def r(self):

        if self._nominal.base == self._contextual.base:
            return Fraction(self._contextual.count, self._nominal.count)

        t1 = self._nominal.count
        n1 = self._nominal.base.n
        d1 = self._nominal.base.d

        t2 = self._contextual.count
        n2 = self._contextual.base.n
        d2 = self._contextual.base.d

        dur1 = Fraction(n1, d1)
        dur2 = Fraction(n2, d2)

        t_dur1 = dur1 * t1
        t_dur2 = dur2 * t2

        tuplet_ratio = Fraction(t_dur2, t_dur1)

        return tuplet_ratio

    @property
    def _nominal(self):
        return self._n 
    
    @property
    def _contextual(self):
        return self._c


class MixedTemporalRatio:
    pass