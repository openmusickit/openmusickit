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

cb = dim1 = TonalVector((0,11))
c  = P1 = TonalVector((0,0))
cx = aug1 = TonalVector((0,1))

db = m2 = TonalVector((1,1))
d  = M2 = TonalVector((1,2))
dx = aug2 = TonalVector((1,3))

eb = m3 = TonalVector((2,3))
e  = M3 = TonalVector((2,4))
ex = aug2 = TonalVector((2,5))

fb = dim4 = TonalVector((3,4))
f  = P4 = TonalVector((3,5))
fx = aug4 = TonalVector((3,6))

gb = dim5 = TonalVector((4,6))
g  = P5 = TonalVector((4,7))
gx = aug4 = TonalVector((4,8))

ab = m6 = TonalVector((5,8))
a  = M6 = TonalVector((5,9))
ax = aug6 = TonalVector((5,10))

bb = m7 = TonalVector(6,10)
b  = M7 = TonalVector(6,11)
bx = aug7 = TonalVector(6,0)

