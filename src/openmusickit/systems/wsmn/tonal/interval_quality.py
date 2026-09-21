"""The quality of a WSMN interval: perfect, major, minor, augmented, diminished, and so on.

There are nineteen qualities, held in `QUALITIES` and keyed by a *relative
number*: 0 for perfect, +0.5/-0.5 for major/minor, and each augmentation or
diminution a further 1 away from there. Whether a quality is reached from
perfect or from major/minor is part of its identity (an augmented 4th and an
augmented 3rd are one half-step above different things), which is why the
numbers are spaced by halves.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

from openmusickit.systems.wsmn.tonal.constants import C_LEN, DIATONES


@dataclass(frozen=True, slots=True)
class IntervalQuality:
    """One of the nineteen interval qualities; see `QUALITIES`.

    >>> QUALITIES[0]
    IntervalQuality("perfect", 0)
    >>> QUALITIES[0.5] + 1
    IntervalQuality("augmented-from_maj_min", 1.5)
    """

    name: str
    rel_number: float

    @property
    def chromatic_modifier(self) -> int:
        """Half-steps above the diatonic base of the interval.

        >>> QUALITIES[0.5].chromatic_modifier  # major
        0
        >>> QUALITIES[-0.5].chromatic_modifier  # minor
        -1
        >>> QUALITIES[-1.5].chromatic_modifier  # diminished, from major/minor
        -2
        """
        return math.floor(self.rel_number)

    # Arithmetic operations

    def augment(self, halfsteps: int = 1) -> IntervalQuality:
        """The quality `halfsteps` half-steps wider, in the same family.

        >>> QUALITIES[0].augment()
        IntervalQuality("augmented-from_perfect", 1)
        >>> QUALITIES[0.5].augment(2)
        IntervalQuality("dbl_augmented-from_maj_min", 2.5)
        """
        return QUALITIES[self.rel_number + halfsteps]

    def diminish(self, halfsteps: int = 1) -> IntervalQuality:
        """The quality `halfsteps` half-steps narrower, in the same family.

        >>> QUALITIES[0.5].diminish(), QUALITIES[0].diminish()
        (IntervalQuality("minor", -0.5), IntervalQuality("diminished-from_perfect", -1))
        """
        return self.augment(-halfsteps)

    def __add__(self, halfsteps: int) -> IntervalQuality:
        """`augment`, as an operator.

        >>> QUALITIES[-0.5] + 1
        IntervalQuality("major", 0.5)
        """
        return self.augment(halfsteps)

    def __sub__(self, halfsteps: int) -> IntervalQuality:
        """`diminish`, as an operator.

        >>> QUALITIES[0.5] - 2
        IntervalQuality("diminished-from_maj_min", -1.5)
        """
        return self.augment(-halfsteps)

    # String representations

    @property
    def abbr(self) -> str:
        """The first three letters of each word of the name, as `TonalVector.from_string` accepts them.

        >>> QUALITIES[0].abbr, QUALITIES[2.5].abbr
        ('per', 'dbl aug')
        """
        return " ".join([wrd[:3] for wrd in str(self).split()])

    def __str__(self) -> str:
        """The name in words, without the family suffix.

        >>> str(QUALITIES[-3])
        'trpl diminished'
        """
        return " ".join(self.name.split("-")[0].split("_"))

    def __repr__(self) -> str:
        return f'{type(self).__name__}("{self.name}", {self.rel_number})'


QUALITIES: dict[float, IntervalQuality] = {
    rel_number: IntervalQuality(name, rel_number)
    for rel_number, name in {
        -4.5: "quad_diminished-from_maj_min",
        -4.0: "quad_diminished-from_perfect",
        -3.5: "trpl_diminished-from_maj_min",
        -3.0: "trpl_diminished-from_perfect",
        -2.5: "dbl_diminished-from_maj_min",
        -2: "dbl_diminished-from_perfect",
        -1.5: "diminished-from_maj_min",
        -1: "diminished-from_perfect",
        -0.5: "minor",
        0: "perfect",
        0.5: "major",
        1: "augmented-from_perfect",
        1.5: "augmented-from_maj_min",
        2: "dbl_augmented-from_perfect",
        2.5: "dbl_augmented-from_maj_min",
        3.0: "trpl_augmented-from_perfect",
        3.5: "trpl_augmented-from_maj_min",
        4.0: "quad_augmented-from_perfect",
        4.5: "quad_augmented-from_maj_min",
    }.items()
}
"""The nineteen qualities, keyed by relative number.

>>> len(QUALITIES)
19
"""


# --- lookup by number or (d, c) tuple ---


@functools.singledispatch
def _get_quality(q, d=None) -> IntervalQuality:
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
    return QUALITIES[q]


@_get_quality.register(tuple)
def _(v, _=None):
    """
    >>> _get_quality((0,0))
    IntervalQuality("perfect", 0)

    >>> _get_quality((0,11))
    IntervalQuality("diminished-from_perfect", -1)
    """
    d, c = v[0], v[1]
    d_val = DIATONES[d]
    modifier = c - d_val.chromatic
    base_q_val = d_val.quality_type.value

    # correct for octave break cases
    if abs(modifier) > 4:  # 4 = triple aug or triple dim
        if c < d_val.chromatic:
            d_val_c = d_val.chromatic - C_LEN
        if c > d_val.chromatic:
            d_val_c = d_val.chromatic + C_LEN
        modifier = c - d_val_c

    return _get_quality(base_q_val + modifier)
