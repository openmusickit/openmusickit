"""Ready-to-go pitch and interval designations.

Examples
--------

>>> c
TonalVector((0, 0))

>>> db
TonalVector((1, 1))

>>> P5
TonalVector((4, 7))

>>> m7
TonalVector((6, 10))
"""

from .tonal_vector import TonalVector

cb = TonalVector((0,11))
c  = TonalVector((0,0))
cx = TonalVector((0,1))