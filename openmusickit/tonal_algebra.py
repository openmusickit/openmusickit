# AUTOGENERATED! DO NOT EDIT! File to edit: 00_core.ipynb (unless otherwise specified).

__all__ = ['D_LEN', 'C_LEN', 'tonal_sum']

# Cell

import itertools

D_LEN = 7  # "Diatonic Length" - The number of tones in a diatonic scale.
C_LEN = 12 # "Chromatic Length" - The number of tones in a chromatic scale.

# Cell

def tonal_sum(x, y):
    """Returns the value of x + y.

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