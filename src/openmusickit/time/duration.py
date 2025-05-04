from __future__ import annotations

from abc import ABC, abstractmethod
from fractions import Fraction as F
from functools import singledispatchmethod
from numbers import Real
from typing import List



class TemporalSystem:
    """A named system of musical time"""

class TemporalElement(ABC):
    """Any class that represents a structured period of time 
    which can be measured and subdivided. For example:
    note durations, measures, beat cycles, gong cycles, and other units of time.

    Any internally-consistent rhthmic/temporal system should be constructable
    using a subclasses of TemporalElement and AbstractDuration.

    """
    
    @property
    @abstractmethod
    def rational_length(self) -> F:
        """Returns a fraction value representing the length of the TemporalElement,
        as defined within the TemporalSystem."""
        raise NotImplementedError
    
    @property
    @abstractmethod
    def temporal_system(self) -> TemporalSystem:
        raise NotImplementedError
    
    @abstractmethod
    def scale(self, scalar: Real):
        raise NotImplementedError

class Duration(TemporalElement):
    """Any class that represents a basic unit of time and is notated as a single symbol.
    
    Subclass Duration to create the specific duration units of a particular system.
    For example, WSMN's note durations (quarter, half note, tuplets, etc),
    are managed by MeteredDuration."""


class TemporalUnit(TemporalElement):
    """A length of musical time defined as n number of TemporalElements.
    This is used to represent (among other things) 
    time signatures and tuple definitions.
    
    Time Signatures
    ---------------

    A time signature has:
     - a numerator (top number),
       which defines "how many" of some note duration.
     - a denominator (bottom number),
       which defines some note duration.

    So 4/4 time is 4 quarter notes and is expressed as:

    >>> TemporalUnit(4, Duration(1,4))
    TemporalUnit(4, Duration(1,4))

    Compound meters such as 6/8 can be expressed using 
    the dotted duration or the base duration:

    >>> TemporalUnit(6, Duration(1,8))
    TemporalUnit(6, Duration(1,8))

    >>> TemporalUnit(2, Duration(1,4, dots=1))
    TemporalUnit(2, Duration(1,4, dots=1))

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
    def rational_length(self) -> F:
        return self.count * self.base.rational_length 

    def __eq__(self, durations: List[Duration]):
        """Compares self to the combined value of an iterable of durations."""
        pass

    def __repr__(self):
        return f'TemporalUnit({self.count}, {repr(self.base)})'


class CompoundTemporalUnit(TemporalElement):
    """An iterable defining a series of ordered temporal elements."""

    def __init__(self, units: list[TemporalUnit]):
        self.units = units


class TemporalRatio:
    """The ratio of two TemporalUnits, usually used to define a tuplet.

    n: numerator or nominal units, the number and type of notes notated and played
    d: denominator (sometimes called "actual" or "contextual), the length of time (expressed as a multiple of Durations)
        as measured in the surrounding context.
         
    So a standard quarternote triple (3 quarters in the time/space of 2 quarters) would be:

    >>> quarter = Duration(1, 4)
    ... two_quarters = TemporalUnit(2, quarter)
    ... three_quarters = TemporalUnity(3, quarter)
    ... triplet = TemporalRatio(two_quarters, three_quarters)
    ... triplet


    Note that this only defines the relationship, and is not the tuplet itself.
    The ratio is used in the definition of a Duration, which is used in the definition of a Note.
    It is also used in the definition of a Tuplet node, which groups the constituent Notes.

    """

    def __init__(self, nominal: TemporalUnit, contextual: TemporalUnit):

        if nominal.temporal_system != contextual.temporal_system:
            raise TypeError('Both members of TemporalRatio must be in the same TemporalSystem. For mixed system ratios, use MixedTemporalRatio.')
            

        self._nominal = nominal
        self._contextual = contextual

    @property
    def r(self):

        if self._nominal.base == self._contextual.base:
            return F(self._contextual.count, self._nominal.count)

        t1 = self._nominal.count
        n1 = self._nominal.base.n
        d1 = self._nominal.base.d

        t2 = self._contextual.count
        n2 = self._contextual.base.n
        d2 = self._contextual.base.d

        dur1 = F(n1, d1)
        dur2 = F(n2, d2)

        t_dur1 = dur1 * t1
        t_dur2 = dur2 * t2

        tuplet_ratio = F(t_dur2, t_dur1)

        return tuplet_ratio

    @property
    def _nominal(self):
        return self._n 
    
    @property
    def _contextual(self):
        return self._d


class MixedTemporalRatio:
    pass