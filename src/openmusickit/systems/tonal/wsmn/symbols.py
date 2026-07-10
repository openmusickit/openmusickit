"""Ready-to-go pitch and interval designations.

Examples
--------

>>> C
TonalVector((0, 0))

>>> Db
TonalVector((1, 1))

>>> P5
TonalVector((4, 7))

>>> m7
TonalVector((6, 10))
"""

from .tonal_vector import TonalVector

Cb = d1 = TonalVector((0,11))
C  = P1 = TonalVector((0,0))
Cx = a1 = TonalVector((0,1))

Db = m2 = TonalVector((1,1))
D  = M2 = TonalVector((1,2))
Dx = a2 = TonalVector((1,3))

Eb = m3 = TonalVector((2,3))
E  = M3 = TonalVector((2,4))
Ex = a2 = TonalVector((2,5))

Fb = d4 = TonalVector((3,4))
F  = P4 = TonalVector((3,5))
Fx = a4 = TonalVector((3,6))

Gb = d5 = TonalVector((4,6))
G  = P5 = TonalVector((4,7))
Gx = a4 = TonalVector((4,8))

Ab = m6 = TonalVector((5,8))
A  = M6 = TonalVector((5,9))
Ax = a6 = TonalVector((5,10))

Bb = m7 = TonalVector(6,10)
B  = M7 = TonalVector(6,11)
Bx = a7 = TonalVector(6,0)

