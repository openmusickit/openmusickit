from __future__ import annotations

from . import tonal_arithmetic as ta
from . import interval_quality as iq
from .constants import D_LEN, C_LEN, MS, AC, Accidental


class TonalVector(tuple):
    """A tuple of form (d_iatonic, c_hromatic, (o_ctave)),
    representing either a pitch or interval (or both).
    TonalVector implements tonal arithmetic with __dunder__ methods,
    allowing use of standard operators (+, -, =, <, >)."""
    _cache = {}

    def __new__(cls, *args):
        # Normalize input: if already a tuple/list, leave it
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            key = tuple(args[0])
        else:
            key = tuple(args)

        if key in cls._cache:
            return cls._cache[key]

        self = super().__new__(cls, key)
        cls._cache[key] = self
        return self

    def __init__(self, *args):
        """
        Examples
        --------

        >>> TonalVector(0,0) == TonalVector((0,0))
        True

        >>> TonalVector(0,0,0) == TonalVector((0,0,0,))
        True

        >>> TonalVector(0,0) is TonalVector((0,0))
        True
        """

        if hasattr(self, '__initialized'):
            return

        self.d = self[0] # diatonic value
        self.c = self[1] # chromatic value

        self._diatone = MS[self.d] # Q for source # rename?
        
        # if a third value (octave) supplied
        try:
            self.o = self[2]
            self._has_octave = True
        except IndexError:
            self.o = None
            self._has_octave = False

        self.pitch = self.Pitch(self)
        self.interval = self.Interval(self)

        self.__initialized = True

    @classmethod
    def vector_len(cls):
        return 

    ### Util ###

    def __repr__(self) -> str:
        """
        >>> TonalVector((0,0))
        TonalVector((0, 0))

        >>> TonalVector((2,4,1))
        TonalVector((2, 4, 1))
        """
        return "TonalVector({})".format(repr(tuple(self)))

    def __str__(self) -> str:
        """Returns a string that includes the __repr__ string,
        along with human readable pitch and interval annotations
        in a Python-style inline comment.

        Examples
        --------

        >>> print(TonalVector((0,1)))
        TonalVector((0, 1)) # C♯

        >>> print(TonalVector((2,3,1)))
        TonalVector((2, 3, 1)) # E♭1
        """
        return "{} # {}".format(repr(self), self.pitch.unicode)

    ### Tonal Arithmetic ###

    def __add__(self, x: tuple[int]) -> TonalVector:
        """

        Examples
        --------

        >>> TonalVector((0,1)) + TonalVector((1,1))
        TonalVector((1, 2))

        >>> TonalVector((6,11,1)) + TonalVector((1,1))
        TonalVector((0, 0, 2))

        """
        return TonalVector(ta.tonal_sum(self, x))

    def __sub__(self, x: tuple[int]) -> TonalVector:
        """

        Examples
        --------

        >>> TonalVector((0,1)) - TonalVector((1,1))
        TonalVector((6, 0))

        >>> TonalVector((6,11,1)) - TonalVector((1,1))
        TonalVector((5, 10, 1))

        >>> abs(TonalVector((6,11,1)) - TonalVector((1,1,0))) == abs(TonalVector((1,1,0)) - TonalVector((6,11,1)))
        True
        """
        return TonalVector(ta.tonal_diff(self, x))

    def distance(self, x: tuple[int]) -> TonalVector:
        """Returns the smallest difference 
        
        Examples
        --------

        >>> TonalVector((0,0,0)).distance(TonalVector((4,7,0)))
        TonalVector((4, 7, 0))

        >>> TonalVector((4,7,0)).distance(TonalVector((0,0,0)))
        TonalVector((4, 7, 0))

        >>> TonalVector((0,0)).distance(TonalVector((4,7)))
        TonalVector((3, 5))
        """
        return TonalVector(ta.tonal_abs_diff(self, x))

    def nearest_instance(self, x: tuple[int]) -> TonalVector:
        """Returns a Tonal Vector that has the same pitch class or interval type as x,
        closest to self.

        Examples
        --------

        >>> TonalVector((0,0)).nearest_instance(TonalVector((1,1,-3)))
        TonalVector((1, 1))

        >>> TonalVector((0,0)).nearest_instance(TonalVector((6,11,3)))
        TonalVector((6, 11))

        >>> TonalVector((0,0,0)).nearest_instance(TonalVector((1,1,-3)))
        TonalVector((1, 1, 0))

        >>> TonalVector((0,0,0)).nearest_instance(TonalVector((6,11,3)))
        TonalVector((6, 11, -1))
        """

        return TonalVector(ta.tonal_nearest_instance(self,x))


    def __abs__(self) -> int:
        """Returns the distance, in half-steps, from self to the origin.

        Examples
        --------

        >>> abs(TonalVector((0,0,-1)))
        12

        >>> abs(TonalVector((0,0,1)))
        12
        """
        return ta.tonal_abs(self)

    def __int__(self) -> int:
        """Returns the signed distance, in half-steps, from self to the origin.

        Examples
        --------

        >>> int(TonalVector((0,0,-1)))
        -12

        >>> int(TonalVector((0,0,1)))
        12
        """
        return ta.tonal_int(self)

    def __gt__(self, x: tuple[int]) -> bool:
        """Returns True if self is higher (in pitch)
        or larger (in interval size) than x,
        otherwise False.

        Examples
        --------

        >>> TonalVector((1,1,0)) > TonalVector((0,0,0))
        True

        >>> TonalVector((2,4,1)) > (3,5,1)
        False

        >>> TonalVector((3,6,1)) > 6
        True
        """
        try:
            return int(self) > int(x)
        except TypeError:
            return int(self) > ta.tonal_int(x)

    def __lt__(self, x: tuple[int]) -> bool:
        """Returns True if self is lower (in pitch)
        or smaller (in interval size) than x,
        otherwise False.

        Examples
        --------

        >>> TonalVector((1,1,0)) < TonalVector((0,0,0))
        False

        >>> TonalVector((2,4,1)) < (3,5,1)
        True

        >>> TonalVector((3,6,1)) < 6
        False
        """
        try:
            return int(self) < int(x)
        except TypeError:
            return int(self) < ta.tonal_int(x)

    def inversion(self, x: tuple[int]=(0,0)) -> TonalVector:
        """Returns the inversion of self over x.

        When x is unspecified, returns the inversion of self over the origin,
        which is equivalent to the standard definition of inverting an interval.

        Examples
        --------

        >>> TonalVector((2,4)).inversion() # Maj3 --> min6
        TonalVector((5, 8))

        >>> TonalVector((5,8)).inversion() # min6 --> Maj3
        TonalVector((2, 4))

        >>> TonalVector((3,6)).inversion() # Aug4 --> dim5 (tritone)
        TonalVector((4, 6))

        >>> TonalVector((0,1,0)).inversion((0,0,0)) # augment unison --> diminished octave
        TonalVector((0, 11, 0))
        """
        return TonalVector(ta.tonal_invert(self, x))

    def __eq__(self, x) -> bool:
        """Returns true if self and x are equal or equivalent.
        Can compare with TonalVectors, (d, c, [o]) tuples, 
        or integers representing half-steps or 12-tone pitches.

        Examples
        --------

        >>> TonalVector((0,1,0)) == (0,1,0)
        True

        >>> TonalVector((0,1)) == TonalVector((1,1))
        False

        >>> TonalVector((0,1)) == 1
        True

        >>> int(TonalVector((0,1))) == int(TonalVector((1,1)))
        True
        """
        if type(self) == type(x):
            return tuple(self) == tuple(x)
        return tuple(self) == x or int(self) == x

    def __hash__(self) -> int:
        return hash(tuple(self))




    ### Represent as a pitch ###

    class Pitch():
        """A TonalVector's pitch representation,
        which holds relevant details such as letter name, accidental, etc.
        
        Example
        -------

        >>> type(TonalVector((0,0)).pitch)
        <class 'openmusickit.tones.tonal_vector.TonalVector.Pitch'>
        """
        
        def __init__(self, vector: TonalVector):
            self._v = vector


        # letter name
        @property
        def _ln(self) -> str:
            """The letter name (without sharps or flats) of the pitch.
            
            Examples
            --------

            >>> TonalVector((0,0)).pitch._ln
            'C'

            >>> TonalVector((0,1)).pitch._ln
            'C'
            """
            return self._v._diatone.ln.upper()

        # how sharp or flat
        @property
        def _modifier_value(self) -> int:
            """A number representing the distance in halfsteps between the named pitch
            and the natural version of the named pitch.

            >>> TonalVector((0,0)).pitch._modifier_value # C natural
            0
            
            >>> TonalVector((0,1)).pitch._modifier_value # C sharp
            1

            >>> TonalVector((0, 11)).pitch._modifier_value # C flat
            -1

            >>> TonalVector((4,6,1)).pitch._modifier_value # G flat
            -1

            >>> TonalVector((6,0)).pitch._modifier_value # B sharp
            1
            """
            
            modifier = self._v.c - self._v._diatone.c


            if abs(modifier) > 4: # 4 = triple aug or triple dim
                if self._v.c < self._v._diatone.c:
                    d_val_c = self._v._diatone.c - C_LEN
                if self._v.c > self._v._diatone.c:
                    d_val_c = self._v._diatone.c + C_LEN
                modifier = self._v.c - d_val_c

            return modifier
            

        @property
        def _modifier(self) -> Accidental:
            """Returns an Accidental, which contains
            information about how to represent the modifier (sharp, flat, natural).

            >>> TonalVector((0,0)).pitch._modifier
            Accidental(offset=0, v='natural', uni='♮', asc='', ly='')
            
            >>> TonalVector((0,0)).pitch._modifier.v
            'natural'
            """
            return AC[self._modifier_value]

        def _unicode(self, mid_c: int = 0) -> str:
            """Returns a human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            The mid_c arg can be used to set the octave designation for middle C.
            (In OMK, middle C == C0. In MIDI etc., middle C == C4).

            Examples
            --------

            >>> TonalVector((0,1)).pitch._unicode()
            'C♯'

            >>> TonalVector((1,1,0)).pitch._unicode(4)
            'D♭4'
            """
            u_str = self._ln

            if self._modifier_value:
                u_str = "".join([u_str, self._modifier.u])

            if self._v._has_octave:
                u_str = "".join([u_str, str(self._v.o + mid_c)])
            
            return u_str

        @property
        def unicode(self) -> str:
            """A human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            If the pitch has an octave designation, middle C == C0.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode
            'D♭0'
            """
            return self._unicode()

        @property
        def unicode_C4(self) -> str:
            """A human readable representation of the pitch, with Unicode modifiers (♯, ♭).
            If the pitch has an octave designation, middle C == C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.unicode_C4
            'C♯'

            >>> TonalVector((1,1,0)).pitch.unicode_C4
            'D♭4'
            """
            return self._unicode(mid_c=4)

        def _ascii(self, octave_modifier: int=0, show_nat: bool = False):
            """Returns a human readable representation of the pitch, with ascii modifiers (#, b).
            The octave_modifier can be used to set the octave designation for middle C.
            (In OMK, middle C == C0. In MIDI etc., middle C == C4).

            Examples
            --------

            >>> TonalVector((0,1)).pitch._ascii()
            'C#'

            >>> TonalVector((1,1,0)).pitch._ascii(4)
            'Db4'
            """
            astr = self._ln

            if self._modifier_value:
                astr = "".join([astr, self._modifier.a])

            if self._v._has_octave:
                astr = "".join([astr, str(self._v.o + octave_modifier)])
            
            return astr
            
        @property
        def ascii(self):
            """A human readable representation of the pitch, with Ascii modifiers (#, b).
            If the pitch has an octave designation, middle C == C0.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii
            'Db0'
            """
            return self._ascii()

        @property
        def ascii_C4(self):
            """A human readable representation of the pitch, with Ascii modifiers (#, b).
            If the pitch has an octave designation, middle C == C4.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ascii_C4
            'C#'

            >>> TonalVector((1,1,0)).pitch.ascii_C4
            'Db4'
            """
            return self._ascii(octave_modifier=4)

        @property
        def ly(self):
            """The Lilypond representation of the pitch name, 
            without an octave designation.

            Examples
            --------

            >>> TonalVector((0,1)).pitch.ly # C sharp
            'ces'

            >>> TonalVector((6,10,1)).pitch.ly # B flat, with an octave designation
            'bis'
            """

            return "".join([self._ln.lower(), self._modifier.ly])

        @property
        def ly_abs8ve(self):
            """The Lilypond representation of the pitch name,
            with an absolute octave designation. 
            (see: http://lilypond.org/doc/v2.18/Documentation/learning/absolute-pitch-names)

            Examples
            --------

            >>> TonalVector((0,0,1)).pitch.ly_abs8ve # C above middle C
            "c'"

            >>> TonalVector((6,10,-1)).pitch.ly_abs8ve # B flat below middle C
            'bis,'

            >>> TonalVector((3,6,0)).pitch.ly_abs8ve # F sharp in octave of middle c
            'fes'

            >>> TonalVector((3,6)).pitch.ly_abs8ve # F sharp, no octave designation
            'fes'

            >>> TonalVector((1,1,4)).pitch.ly_abs8ve # D flat, 4 octaves above middle c
            "dis''''"

            >>> TonalVector((1,1,-4)).pitch.ly_abs8ve # D flat, 4 octaves below middle c
            'dis,,,,'
            """

            if not self._v._has_octave:
                return self.ly

            if self._v.o < 0:
                ostr = ","
            else:
                ostr = "'"

            return "".join([self.ly, ostr*abs(self._v.o)])


        def ly_rel8ve(self, prev=None):
            """Returns the Lilypond representation of the pitch name,
            with a relative octave designation, based on the previous pitch.

            >>> TonalVector((3,5,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'f'

            >>> TonalVector((4,7,0)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            "g'"

            >>> TonalVector((3,5,-1)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'f,'

            >>> TonalVector((4,7,-1)).pitch.ly_rel8ve(TonalVector((0,0,0)))
            'g'
            """
            if prev == None:
                return self.ly_abs8ve

            if self._v.distance(prev).d <= 3:
                return self.ly

            closer_chroma = prev.nearest_instance(self._v)

            octave_distance = self._v.o - closer_chroma.o

            if octave_distance < 0:
                ostr = ","
            else:
                ostr = "'"

            return "".join([self.ly, ostr*abs(octave_distance)]) 


        @property
        def verbose(self):
            """
            >>> TonalVector((0,0)).pitch.verbose
            'C'
            
            >>> TonalVector((0,1)).pitch.verbose
            'Csharp'

            >>> TonalVector((0,1,1)).pitch.verbose
            'Csharp1'

            """ 
            if self._v.o == None:
                o = ""
            else:
                o = str(self._v.o)

            if self._modifier_value == 0:
                mod_text = ""
            else:
                mod_text = self._modifier.v

            return "".join([self._ln, mod_text, o])

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).pitch
            TonalVector((0, 0, 0)).pitch
            """
            return "".join([self._v.__repr__(), ".pitch"])

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).pitch)
            'C0 | (0, 0, 0)'
            """
            return "".join([self.unicode, " | ", str(tuple(self._v))])

    
    class Interval():

        def __init__(self, vector):
            """
            >>> TonalVector((0, 0)).interval._v
            TonalVector((0, 0))

            >>> TonalVector((1, 2)).interval.quality
            IntervalQuality("major", 0.5)
            
            >>> TonalVector((2, 3)).interval.number
            3
            """
            self._v = vector
            self.quality = iq._get_quality(vector)
            self.number = vector.d + 1
            
            try:
                self.o = vector.o or 0
            except AttributeError:
                self.o = 0
            else:
                if self.o > 0:
                    self.o = "".join(["+", str(self.o)])
                elif self.o == 0:
                    self.o = ""
                else:
                    self.o = str(self.o)

        @property
        def abbr(self):
            """Returns abbreviated quality designation.

            Examples
            --------

            >>> TonalVector((0,0)).interval.abbr
            'per1'

            >>> TonalVector((3, 6, 1)).interval.abbr
            'aug4+1'
            """
            return "".join([self.quality.abbr, str(self.number), self.o])

        def __repr__(self):
            """
            >>> TonalVector((0, 0, 0)).interval
            TonalVector((0, 0, 0)).interval
            """
            return "".join([self._v.__repr__(), ".interval"])
        
        @property
        def unicode(self):
            """
            >>> TonalVector((0,0)).interval.unicode
            'perfect 1'

            >>> TonalVector((3,6)).interval.unicode
            'augmented 4'
            """
            return f"{self.quality.__str__()} {self.number}"

        def __str__(self):
            """
            >>> str(TonalVector((0, 0, 0)).interval)
            'perfect 1 | (0, 0, 0)'
            """
            return "".join([self.unicode, " | ", str(tuple(self._v))])
