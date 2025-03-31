"""
Add and subtract intervals, chromae, notes.

These functions operate on tuples of the form `(d, c, o)`, where
`d` is a required integer representing a diatonic value,
`c` is a required integer representing a chromatic value,
`o` is an optional integer reprenting an octave designation.
"""

# TODO: @tonal_args decorator
#   Input validation on arithmetic functions

import itertools

from .constants import D_LEN, C_LEN, MS


def tonal_sum(x: tuple[int], y: tuple[int]) -> tuple[int]:
    """Returns the value of x augmented by y.

    Examples
    --------

    >>> tonal_sum((0, 0), (2, 3))
    (2, 3)

    >>> tonal_sum((3, 6), (4, 6))
    (0, 0)

    >>> tonal_sum((0, 0, 0), (2, 3))
    (2, 3, 0)

    >>> tonal_sum((3, 6, 0), (4, 6))
    (0, 0, 1)

    >>> tonal_sum((6, 11, 1), (2, 4))
    (1, 3, 2)
    """

    if len(x) < len(y):
        raise TypeError("An octave designation cannot be added to an abstract tonal value.")

    sum = tuple(xval+yval for xval,yval in itertools.zip_longest(x,y, fillvalue=0))

    sum = _tonal_modulo(sum)

    return sum

# @tonal_args
def tonal_diff(x: tuple[int], y: tuple[int]) -> tuple[int]:
    """Returns the value of x diminished by y.

    Examples
    --------

    >>> tonal_diff((2, 3), (2, 3))
    (0, 0)

    >>> tonal_diff((0, 0), (1, 1))
    (6, 11)

    >>> tonal_diff((0, 0, 0), (1, 1))
    (6, 11, -1)

    >>> tonal_diff((0,1),(1,1))
    (6, 0)

    >>> tonal_diff((0,1,0), (6,10, -1))
    (1, 3, 0)

    >>> tonal_diff((0,0,0),(0,10,0))
    (0, 2, 0)

    """

    return tonal_sum(x, _negative_tuple(y))

def _negative_tuple(x: tuple[int]) -> tuple[int]:
    """
    Negates a tonal tuple on (0, 0, (0)).
    (Implies an interval moving downward.)

    Examples
    --------

    >>> _negative_tuple((1, 1, 1))
    (-1, -1, -1)
    """

    return tuple(-m for m in x)


#@tonal_args
def tonal_invert(x, y=(0,0)):
    """Returns the inversion of x on y.

    The inversion is the value which is as far below y
    as x is above y.

    Examples
    --------

    >>> tonal_invert((2,4)) # The inversion of a Major Third is a Minor Sixth
    (5, 8)

    >>> tonal_invert((3,6)) # The inversion of a tritone is a tritone with a different name.
    (4, 6)

    >>> tonal_invert((4,7), (2,4)) # G is a min 3rd up from E. Down a min 3rd from E is C#.
    (0, 1)

    >>> tonal_invert((0,1,0))
    (0, 11, 0)

    >>> tonal_invert((0,1,0)) == tonal_sum((0,0,0), _negative_tuple((0,1,0)))
    True

    """

    x, y = _qualify_octave_as_needed(x, y)

    return tonal_diff(y, tonal_diff(x, y))


def _tonal_modulo(x: tuple[int]) -> tuple[int]:
    """Returns an octave-normalized rendering of x.

    Examples
    --------

    >>> _tonal_modulo((7, 12)) # C + 1 octave, no octave designation
    (0, 0)

    >>> _tonal_modulo((7, 12, 0)) # C + 1 octave
    (0, 0, 1)

    >>> _tonal_modulo((-1, -1)) # B - 1 octave
    (6, 11)

    >>> _tonal_modulo((-1, -1, 0)) # B - 1 octave
    (6, 11, -1)

    >>> _tonal_modulo((-1, 0))
    (6, 0)

    >>> _tonal_modulo((7, 12, 1))
    (0, 0, 2)

    """

    # From (0,0) to (6,11) (inclusive), no modulo is needed.
    if x[0] in range(D_LEN) and x[1] in range(C_LEN):
        return x

    d_val = x[0] % D_LEN # The normalized diatonic value.
    d_oct = x[0] // D_LEN # The additional diatonic octave.
    c_val = x[1] % C_LEN # The normalized chromatic value.
    
    if len(x) == 2:
        return (d_val, c_val)

    if len(x) == 3:
        return (d_val, c_val, (x[2] + d_oct))


def tonal_abs(x: tuple[int]) -> int:
    """Returns the absolute distance in half steps from the origin (Middle C).

    Examples
    --------

    >>> tonal_abs((6,11,-1))
    1

    >>> tonal_abs((0,1,0))
    1
    """

    return abs(tonal_int(x))

def tonal_int(x):
    """Returns the directed (+/-) distance in half steps from the origin (Middle C).

    Examples
    --------

    >>> tonal_int((4,7))
    7

    >>> tonal_int((4,7,2))
    31

    >>> tonal_int((6,11,-1))
    -1

    >>> tonal_int((0,-1,-1))
    -13

    >>> tonal_int((6,0,0))
    12

    >>> tonal_int((0,11,0))
    -1

    >>> tonal_int((0,11))
    -1

    >>> tonal_int((2, 0))
    0

    """

    if len(x) == 2:
        x = _tonal_unmodulo(x)
        return x[1]

    d = x[0]
    c = x[1]
    base_c = MS[d].c

    # Example: Cb --- base=0 c=11  c-base=11   11 - 12 = -1

    if c - base_c > 3:
        c = c - C_LEN

    # Example: B# --- base=11 c=0 c-base=-11        c+C_LEN =12
    if c - base_c < -3:
        c = c + C_LEN

    return c + x[2]*(C_LEN)

        

def tonal_higher_of(x: tuple[int],y: tuple[int]) -> tuple[int]:
    """Returns the higher pitch.

    Examples
    --------
    >>> tonal_higher_of((0,0,0), (0,11,-1)) # C, C-flat
    (0, 0, 0)

    >>> tonal_higher_of((1, 1), (1, 3)) # D-flat, D-sharp | min2, Aug2
    (1, 3)

    >>> tonal_higher_of((0,0,0),(0,10,0)) # C, C-flat
    (0, 0, 0)
    """
    if tonal_int(x) == tonal_int(y): # if same half-steps, larger diatonic
                                     # dim5 > aug4
        if x[0] > y[0]:
            return x
        else:
            return y

    if tonal_int(x) > tonal_int(y):
        return x
    else:
        return y

def tonal_lower_of(x: tuple[int], y: tuple[int]) -> tuple[int]:
    """Returns the lower pitch

    Examples
    --------

    >>> tonal_lower_of((0,0,0), (0,11,-1))
    (0, 11, -1)

    >>> tonal_lower_of((0,1,0),(0,10,0))
    (0, 10, 0)
    """
    x = _tonal_unmodulo(x)
    y = _tonal_unmodulo(y)

    if tonal_int(x) == tonal_int(y):
        if x[0] < y[0]:
            return x
        else:
            return y
    if tonal_int(x) < tonal_int(y):
        return _tonal_modulo(x)
    else:
        return _tonal_modulo(y)

def tonal_larger_of(x: tuple[int], y:tuple[int]) -> tuple[int]:
    """Returns the larger interval.
    
    Examples
    --------

    >>> tonal_larger_of((1, 1), (2,3)) # min2 < min3
    (2, 3)

    """

    if tonal_abs(x) == tonal_abs(y): # if same half-steps, larger diatonic
                                     # dim5 > aug4
        if abs(x[0]) > abs(y[0]):
            return x
        else:
            return y

    if tonal_abs(x) > tonal_abs(y):
        return x
    else:
        return y
    
def tonal_smaller_of(x: tuple[int], y:tuple[int]) -> tuple[int]:
    """Returns the smaller interval.
    
    Examples
    --------

    >>> tonal_smaller_of((1, 1), (2,3)) # min2 < min3
    (1, 1)

    """

    if x == tonal_larger_of(x, y):
        return y
    else:
        return x



def abs_interval(x: tuple[int]) -> tuple[int]:
    """Returns the smaller of: the given interval and its inversion.

    Examples
    --------

    >>> abs_interval((4,7))
    (3, 5)

    >>> abs_interval((6,11,-1))
    (1, 1, 0)

    >>> abs_interval((1,1,0))
    (1, 1, 0)

    >>> abs_interval((6, 0, -1))
    (1, 0, 0)

    >>> abs_interval((0,11,0))
    (0, 1, 0)
    """
    if len(x) == 2:
        y = tonal_invert(x)
        if x[0] == y[0]:
            if _tonal_unmodulo(x)[1] < 0:
                return y
            if _tonal_unmodulo(y)[1] < 0:
                return x

        return tonal_lower_of(x, y)

    if len(x) == 3:
        y = tonal_invert(x)
        if x[2] < 0:
            return y
        if y[2] < 0:
            return x

        if x[0] == y[0] and x[2] == y[2] == 0:
            if _tonal_unmodulo(x)[1] < 0:
                return y
            if _tonal_unmodulo(y)[1] < 0:
                return x

        return tonal_lower_of(x, y)
        


def tonal_abs_diff(x: tuple[int], y: tuple[int]) -> tuple[int]:
    """Returns an tuple representing the smallest difference between two tonal primitives.
    (That is, the abs_interval between them.)

    Examples
    --------

    >>> tonal_abs_diff((0,0),(5,9))
    (2, 3)

    >>> tonal_abs_diff((0,0,0), (6,11,-1))
    (1, 1, 0)

    >>> tonal_abs_diff((6,0,0), (0,0,1))
    (1, 0, 0)

    >>> tonal_abs_diff((0,0,0),(0,11,0))
    (0, 1, 0)

    >>> tonal_abs_diff((0,0,0), (0,11,-1))
    (0, 1, 1)

    >>> tonal_abs_diff((0,0,0), (0,11,0))
    (0, 1, 0)

    >>> tonal_abs_diff((0, 0), (0, 1))
    (0, 1)

    >>> tonal_abs_diff((0, 0), (0,11))
    (0, 1)

    >>> tonal_abs_diff((1, 3), (3, 3))
    (2, 0)

    >>> x, y = (0,0), (4,6)
    >>> tonal_abs_diff(x,y) == tonal_abs_diff(x,tonal_invert(y))
    True

    """
    x,y = _qualify_octave_as_needed(x,y)
    #if len(x) == 3:
    #    return tonal_diff(tonal_greater_of(x,y), tonal_lesser_of(x,y))

    #return tonal_lesser_of(tonal_diff(x,y), tonal_diff(y,x))

    a = abs_interval(tonal_diff(x,y))
    b = abs_interval(tonal_diff(y,x))



    return _tonal_modulo(tonal_lower_of(a, b))

def abs_int_diff(x: tuple[int], y: tuple[int]) -> int:
    """Returns the smallest number of half-steps between two tonal primitives.

    Examples
    --------

    >>> abs_int_diff((0,1,0),(0,11,0))
    2

    >>> abs_int_diff((0,1,0),(6,11,-1))
    2
    """
    x,y = _qualify_octave_as_needed(x,y)

    if len(x) == 3:
        x = tonal_int(x)
        y = tonal_int(y)
        return abs(x-y)

    return tonal_int(tonal_abs_diff(x,y))


def tonal_nearest_instance(x: tuple[int], y: tuple[int]):
    """Returns the location of an octave adjusted y that is closest to x.
    That is, if x and y are more than a tritone apart,
    the octave qualifier of y is adjusted to be within a tritone of x.

    If x is not octave designated, y is returned with no octave designation.
    If y is not octave designeted (but x is),
    y is returned with an octave designation making it closest to x.

    Examples
    --------

    >>> tonal_nearest_instance((0,0,0), (1,2,-1))
    (1, 2, 0)

    >>> tonal_nearest_instance((0,1,1), (6,10, -3))
    (6, 10, 0)

    >>> tonal_nearest_instance((0,0,0), (6,11,3))
    (6, 11, -1)

    >>> tonal_nearest_instance((0,0), (6,11,-1))
    (6, 11)

    >>> tonal_nearest_instance((0, 0, 0), (0, 11, 0))
    (0, 11, 0)
    """
    if len(x) == 2:
        return (y[0], y[1])

    d = y[0]
    c = y[1]
    o = x[2]

    o = [o, o-1, o+1]

    candidates = [(d,c,z) for z in o]
    diff_candidates = {abs_int_diff(x, z):z for z in candidates}

    return diff_candidates[min(diff_candidates.keys())]

def _tonal_unmodulo(x: tuple[int]) -> tuple[int]:
    """Utility function.
    Returns a tuple in which the chromatic value is close to the diatonic value,
    even if that requires a negative value.
    (This makes certain calculations easier 
    when the d and c values wrap around their modulo scale.)


    >>> _tonal_unmodulo((0,10,0))
    (0, -2, 0)

    >>> _tonal_unmodulo((6,0,0))
    (6, 12, 0)

    >>> _tonal_unmodulo((2, 0))
    (2, 0)
    """

    d = x[0]
    c = x[1]
    base_c = MS[d].c
    # Example: Cb --- base=0 c=11  c-base=11   11 - 12 = -1

    if c - base_c > 6:
        c = c - C_LEN

    # Example: B# --- base=11 c=0 c-base=-11        c+C_LEN =12
    if c - base_c < -6:
        c = c + C_LEN

    try:
        return (d, c, x[2])
    except:
        return (d, c)
    
def _qualify_octave_as_needed(x: tuple[int], y: tuple[int]) -> tuple[tuple[int], tuple[int]]:
    """Returns (x,y), with an octave qualifier on both x and y if either had one.

    Examples
    --------
    
    >>> _qualify_octave_as_needed((1, 1, 0), (1, 1))
    ((1, 1, 0), (1, 1, 0))

    >>> _qualify_octave_as_needed((1, 1), (1, 1, 0))
    ((1, 1, 0), (1, 1, 0))

    >>> _qualify_octave_as_needed((1, 1), (1, 1))
    ((1, 1), (1, 1))

    >>> _qualify_octave_as_needed((1, 1, 0), (1, 1, 0))
    ((1, 1, 0), (1, 1, 0))


    """
    if len(x) != len(y) and (len(max(x, y, key=len)) == 3):
        x = list(x)
        y = list(y)
        z = min(x, y, key=len)
        z.append(0)
        x = tuple(x)
        y = tuple(y)
    return x, y

    
if __name__ == "__main__":
    import doctest
    doctest.testmod()