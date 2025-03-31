import functools
import math

from .constants import D_LEN, C_LEN, MS, AC



q_vals = {
- 4.5 : 'quad_diminished-from_maj_min',
- 4.0 : 'quad_diminished-from_perfect',
- 3.5 : 'trpl_diminished-from_maj_min',
- 3.0 : 'trpl_diminished-from_perfect',
- 2.5 : 'dbl_dimished-from_maj_min',
- 2   : 'dbl_diminished-from_perfect',
- 1.5 : 'diminished-from_maj_min',
- 1   : 'diminished-from_perfect',
- 0.5 : 'minor',
  0   : 'perfect',
  0.5 : 'major',
  1   : 'augmented-from_perfect',
  1.5 : 'augmented-from_maj_min',
  2   : 'dbl_augmented-from_perfect',
  2.5 : 'dbl_augmented-from_maj_min',
  3.0 : 'trpl_augmented-from_perfect',
  3.5 : 'trpl_augmented-from_maj_min',
  4.0 : 'quad_augmented-from_perfect',
  4.5 : 'quad_augmented-from_maj_min'
}

qualities = dict()

class IntervalQuality():
    """
    >>> len(qualities)
    19

    >>> qualities[0]
    IntervalQuality("perfect", 0)
    """


    def __new__(cls, name, rel_number):
        
        try:
            return _get_quality(name)
        except:
            pass

        try:
            return _get_quality(rel_number)
        except:
            return super().__new__(cls)

    def __init__(self, name, rel_number):
        self.name = name
        self.__rel_number = rel_number
        qualities[rel_number] = self

    @property
    def chromatic_modifier(self):
        """
        >>> _get_quality("major").chromatic_modifier
        0

        >>> _get_quality("minor").chromatic_modifier
        -1

        >>> _get_quality("diminished-from_maj_min").chromatic_modifier
        -2
        """
        return math.floor(self.__rel_number)

    # Arithmetic operations

    def augment(self, halfsteps=1):
        aug_number = self.__rel_number + halfsteps
        return qualities[aug_number]

    def diminish(self, halfsteps=1):
        return self.augment(-halfsteps)

    def __add__(self, halfsteps):
        return self.augment(halfsteps)

    def __sub__(self, halfsteps):
        return self.__add__(-halfsteps)


    # String representations

    @property
    def abbr(self):
        return " ".join([wrd[:3] for wrd in str(self).split()])

    def __str__(self):
        return " ".join(self.name.split("-")[0].split("_"))

    def __repr__(self):
        return "".join(['IntervalQuality("', self.name, '", ', str(self.__rel_number), ")"])

# Instantiate the Interval Qualities
for number, name in q_vals.items():
    IntervalQuality(name, number)


###########

@functools.singledispatch
def _get_quality(q, d=None):
    """
    >>> _get_quality(['x','y'], 2)
    Traceback (most recent call last):
    TypeError: The quality identifier supplied is not a supported type.

    """
    raise TypeError("The quality identifier supplied is not a supported type.")

@_get_quality.register(int)
@_get_quality.register(float)
def _(q, d=None):
    """
    >>> _get_quality(0)
    IntervalQuality("perfect", 0)
    """
    return qualities[q]

@_get_quality.register(tuple)
def _(v, _=None):
    """
    >>> _get_quality((0,0))
    IntervalQuality("perfect", 0)

    >>> _get_quality((0,11))
    IntervalQuality("diminished-from_perfect", -1)
    """
    d, c = v[0], v[1]
    d_val = MS[d]
    modifier = c - d_val.c
    base_q_val = d_val.q.value

    # correct for octave break cases
    if abs(modifier) > 4: # 4 = triple aug or triple dim
        if c < d_val.c:
            d_val_c = d_val.c - C_LEN
        if c > d_val.c:
            d_val_c = d_val.c + C_LEN
        modifier = c - d_val_c



    if modifier < 0:
        base_q_val = -base_q_val

    return _get_quality(base_q_val + modifier)



@_get_quality.register(str)
def _(q, d=None):
    """
    >>> _get_quality("M")
    IntervalQuality("major", 0.5)

    >>> _get_quality("maj")
    IntervalQuality("major", 0.5)

    >>> _get_quality("major")
    IntervalQuality("major", 0.5)

    >>> _get_quality("m")
    IntervalQuality("minor", -0.5)

    >>> _get_quality("min")
    IntervalQuality("minor", -0.5)

    >>> _get_quality("aug", 2)
    IntervalQuality("augmented-from_maj_min", 1.5)

    >>> _get_quality("double diminished", 4)
    IntervalQuality("dbl_diminished-from_perfect", -2)

    >>> _get_quality("perfect")
    IntervalQuality("perfect", 0)

    >>> _get_quality("P")
    IntervalQuality("perfect", 0)

    >>> _get_quality("d", 1)
    IntervalQuality("diminished-from_maj_min", -1.5)
    """

    for rel_number, quality in qualities.items():
        if quality.name.lower() == q.lower():
            return quality

    for rel_number, quality in qualities.items():
        if (len(q) == 1 and q == "M") or q.lower() == "maj":
            return _get_quality("major")
        if (len(q) == 1 and q == "m") or q.lower() == "min":
            return _get_quality("minor")

        if q.lower() == "p" or q.lower() == "per":
            return _get_quality("perfect")

        if q.lower() in ["a","d"] or any(qstr in q.lower() for qstr in ['dim', 'aug', 'dbl']):
            return _get_quality_x(q, d)

def _get_quality_x(q, d): # x= extended
    q = q.lower()
    base_quality = MS[d].q.value
    
    if q == 'a' or 'aug' in q:
        q_add = 1 # quality addend

    if q == 'd' or 'dim' in q:
        q_add = -1

    if 'dbl' in q or 'double' in q:
        q_add = q_add * 2

    if base_quality == 0:
        q_val = q_add

    if base_quality == 0.5:
        if q_add < 0:
            base_quality = -base_quality
        q_val = base_quality + q_add

    return _get_quality(q_val)

    
if __name__ == "__main__":
    import doctest
    doctest.testmod()