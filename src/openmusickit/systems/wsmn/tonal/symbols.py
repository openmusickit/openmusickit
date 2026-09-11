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
from .chords import ChordType, Quality

Cbb = dd1 = TonalVector((0,10))
Cb = d1 = TonalVector((0,11))
C  = P1 = TonalVector((0,0))
Cx = a1 = TonalVector((0,1))
Cxx = aa1 = TonalVector((0,2))

Dbb = d2 = TonalVector((1,10))
Db = m2 = TonalVector((1,11))
D  = M2 = TonalVector((1,2))
Dx = a2 = TonalVector((1,3))
Dxx = aa2 = TonalVector((1,4))

Ebb = d3 = TonalVector((2,2))
Eb = m3 = TonalVector((2,3))
E  = M3 = TonalVector((2,4))
Ex = a3 = TonalVector((2,5))
Exx = aa3 = TonalVector((2,6))

Fbb = dd4 = TonalVector((3,3))
Fb = d4 = TonalVector((3,4))
F  = P4 = TonalVector((3,5))
Fx = a4 = TonalVector((3,6))
Fxx = aa4 = TonalVector((3,7))

Gbb = dd5 = TonalVector((4,5))
Gb = d5 = TonalVector((4,6))
G  = P5 = TonalVector((4,7))
Gx = a5 = TonalVector((4,8))
Gxx = aa5 = TonalVector((4,9))

Abb = d6 = TonalVector((5,7))
Ab = m6 = TonalVector((5,8))
A  = M6 = TonalVector((5,9))
Ax = a6 = TonalVector((5,10))
Axx = aa6 = TonalVector((5,11))

Bbb = d7 = TonalVector((6,9))
Bb = m7 = TonalVector((6,10))
B  = M7 = TonalVector((6,11))
Bx = a7 = TonalVector((6,0))
Bxx = aa7 = TonalVector((6,1))


# Chord symbols
# Basic triads and open chords

maj = ChordType(
    tones=[C, E, G],
    name="major",
    quality=Quality.MAJ,
)

min = ChordType(
    tones=[C, Eb, G],
    name="minor",
    quality=Quality.MIN,
)

dim = ChordType(
    tones=[C, Eb, Gb],
    name="diminished",
    quality=Quality.DIM,
)

aug = ChordType(
    tones=[C, E, Gx],
    name="augmented",
    quality=Quality.AUG,
)

sus2 = ChordType(
    tones=[C, D, G],
    name="suspended 2",
    quality=Quality.SUS,
)

sus4 = ChordType(
    tones=[C, F, G],
    name="suspended 4",
    quality=Quality.SUS,
)

pow5 = ChordType(
    tones=[C, G],
    name="power chord",
    quality=Quality.POW,
)


# Sixth chords

maj6 = ChordType(
    tones=[C, E, G, A],
    name="major 6",
    quality=Quality.MAJ,
)

min6 = ChordType(
    tones=[C, Eb, G, A],
    name="minor 6",
    quality=Quality.MIN,
)

maj6_9 = ChordType(
    tones=[C, E, G, A, D],
    name="major 6/9",
    quality=Quality.MAJ,
)

min6_9 = ChordType(
    tones=[C, Eb, G, A, D],
    name="minor 6/9",
    quality=Quality.MIN,
)


# Seventh chords

maj7 = ChordType(
    tones=[C, E, G, B],
    name="major 7",
    quality=Quality.MAJ,
)

min7 = ChordType(
    tones=[C, Eb, G, Bb],
    name="minor 7",
    quality=Quality.MIN,
)

dom7 = ChordType(
    tones=[C, E, G, Bb],
    name="dominant 7",
    quality=Quality.DOM,
)

hdim7 = ChordType(
    tones=[C, Eb, Gb, Bb],
    name="half-diminished 7",
    quality=Quality.HDM,
)

dim7 = ChordType(
    tones=[C, Eb, Gb, Bbb],
    name="diminished 7",
    quality=Quality.DIM,
)

min_maj7 = ChordType(
    tones=[C, Eb, G, B],
    name="minor-major 7",
    quality=Quality.MIN,
)

aug_maj7 = ChordType(
    tones=[C, E, Gx, B],
    name="augmented major 7",
    quality=Quality.AUG,
)


# Added-tone chords

add2 = ChordType(
    tones=[C, D, E, G],
    name="add 2",
    quality=Quality.MAJ,
)

add9 = ChordType(
    tones=[C, E, G, D],
    name="add 9",
    quality=Quality.MAJ,
)

min_add9 = ChordType(
    tones=[C, Eb, G, D],
    name="minor add 9",
    quality=Quality.MIN,
)

add4 = ChordType(
    tones=[C, E, F, G],
    name="add 4",
    quality=Quality.MAJ,
)

add11 = ChordType(
    tones=[C, E, G, F],
    name="add 11",
    quality=Quality.MAJ,
)

min_add11 = ChordType(
    tones=[C, Eb, G, F],
    name="minor add 11",
    quality=Quality.MIN,
)

add_sharp11 = ChordType(
    tones=[C, E, G, Fx],
    name="add sharp 11",
    quality=Quality.MAJ,
)


# Ninth chords

maj9 = ChordType(
    tones=[C, E, G, B, D],
    name="major 9",
    quality=Quality.MAJ,
)

min9 = ChordType(
    tones=[C, Eb, G, Bb, D],
    name="minor 9",
    quality=Quality.MIN,
)

dom9 = ChordType(
    tones=[C, E, G, Bb, D],
    name="dominant 9",
    quality=Quality.DOM,
)

min_maj9 = ChordType(
    tones=[C, Eb, G, B, D],
    name="minor-major 9",
    quality=Quality.MIN,
)


# Eleventh chords

maj11 = ChordType(
    tones=[C, E, G, B, D, F],
    name="major 11",
    quality=Quality.MAJ,
)

min11 = ChordType(
    tones=[C, Eb, G, Bb, D, F],
    name="minor 11",
    quality=Quality.MIN,
)

dom11 = ChordType(
    tones=[C, E, G, Bb, D, F],
    name="dominant 11",
    quality=Quality.DOM,
)

maj9_sharp11 = ChordType(
    tones=[C, E, G, B, D, Fx],
    name="major 9 sharp 11",
    quality=Quality.MAJ,
)

dom9_sharp11 = ChordType(
    tones=[C, E, G, Bb, D, Fx],
    name="dominant 9 sharp 11",
    quality=Quality.DOM,
)


# Thirteenth chords

maj13 = ChordType(
    tones=[C, E, G, B, D, F, A],
    name="major 13",
    quality=Quality.MAJ,
)

min13 = ChordType(
    tones=[C, Eb, G, Bb, D, F, A],
    name="minor 13",
    quality=Quality.MIN,
)

dom13 = ChordType(
    tones=[C, E, G, Bb, D, F, A],
    name="dominant 13",
    quality=Quality.DOM,
)

maj13_sharp11 = ChordType(
    tones=[C, E, G, B, D, Fx, A],
    name="major 13 sharp 11",
    quality=Quality.MAJ,
)

dom13_sharp11 = ChordType(
    tones=[C, E, G, Bb, D, Fx, A],
    name="dominant 13 sharp 11",
    quality=Quality.DOM,
)


# Suspended seventh and extended chords

dom7_sus2 = ChordType(
    tones=[C, D, G, Bb],
    name="dominant 7 suspended 2",
    quality=Quality.SUS,
)

dom7_sus4 = ChordType(
    tones=[C, F, G, Bb],
    name="dominant 7 suspended 4",
    quality=Quality.SUS,
)

dom9_sus4 = ChordType(
    tones=[C, F, G, Bb, D],
    name="dominant 9 suspended 4",
    quality=Quality.SUS,
)

dom13_sus4 = ChordType(
    tones=[C, F, G, Bb, D, A],
    name="dominant 13 suspended 4",
    quality=Quality.SUS,
)


# Dominant chords with altered fifths

dom7_flat5 = ChordType(
    tones=[C, E, Gb, Bb],
    name="dominant 7 flat 5",
    quality=Quality.DOM,
)

dom7_sharp5 = ChordType(
    tones=[C, E, Gx, Bb],
    name="dominant 7 sharp 5",
    quality=Quality.DOM,
)

dom9_flat5 = ChordType(
    tones=[C, E, Gb, Bb, D],
    name="dominant 9 flat 5",
    quality=Quality.DOM,
)

dom9_sharp5 = ChordType(
    tones=[C, E, Gx, Bb, D],
    name="dominant 9 sharp 5",
    quality=Quality.DOM,
)


# Dominant chords with altered ninths

dom7_flat9 = ChordType(
    tones=[C, E, G, Bb, Db],
    name="dominant 7 flat 9",
    quality=Quality.DOM,
)

dom7_sharp9 = ChordType(
    tones=[C, E, G, Bb, Dx],
    name="dominant 7 sharp 9",
    quality=Quality.DOM,
)

dom7_flat9_flat5 = ChordType(
    tones=[C, E, Gb, Bb, Db],
    name="dominant 7 flat 9 flat 5",
    quality=Quality.DOM,
)

dom7_flat9_sharp5 = ChordType(
    tones=[C, E, Gx, Bb, Db],
    name="dominant 7 flat 9 sharp 5",
    quality=Quality.DOM,
)

dom7_sharp9_flat5 = ChordType(
    tones=[C, E, Gb, Bb, Dx],
    name="dominant 7 sharp 9 flat 5",
    quality=Quality.DOM,
)

dom7_sharp9_sharp5 = ChordType(
    tones=[C, E, Gx, Bb, Dx],
    name="dominant 7 sharp 9 sharp 5",
    quality=Quality.DOM,
)

dom7_flat9_sharp9 = ChordType(
    tones=[C, E, G, Bb, Db, Dx],
    name="dominant 7 flat 9 sharp 9",
    quality=Quality.DOM,
)


# Dominant sharp-eleventh chords

dom7_sharp11 = ChordType(
    tones=[C, E, G, Bb, Fx],
    name="dominant 7 sharp 11",
    quality=Quality.DOM,
)

dom7_flat9_sharp11 = ChordType(
    tones=[C, E, G, Bb, Db, Fx],
    name="dominant 7 flat 9 sharp 11",
    quality=Quality.DOM,
)

dom7_sharp9_sharp11 = ChordType(
    tones=[C, E, G, Bb, Dx, Fx],
    name="dominant 7 sharp 9 sharp 11",
    quality=Quality.DOM,
)


# Dominant flat-thirteenth chords

dom7_flat13 = ChordType(
    tones=[C, E, G, Bb, Ab],
    name="dominant 7 flat 13",
    quality=Quality.DOM,
)

dom7_flat9_flat13 = ChordType(
    tones=[C, E, G, Bb, Db, Ab],
    name="dominant 7 flat 9 flat 13",
    quality=Quality.DOM,
)

dom7_sharp9_flat13 = ChordType(
    tones=[C, E, G, Bb, Dx, Ab],
    name="dominant 7 sharp 9 flat 13",
    quality=Quality.DOM,
)

dom7_sharp11_flat13 = ChordType(
    tones=[C, E, G, Bb, Fx, Ab],
    name="dominant 7 sharp 11 flat 13",
    quality=Quality.DOM,
)


# Common fully altered dominant voicings/types

dom7_flat9_sharp9_flat5 = ChordType(
    tones=[C, E, Gb, Bb, Db, Dx],
    name="dominant 7 flat 9 sharp 9 flat 5",
    quality=Quality.DOM,
)

dom7_flat9_sharp9_sharp5 = ChordType(
    tones=[C, E, Gx, Bb, Db, Dx],
    name="dominant 7 flat 9 sharp 9 sharp 5",
    quality=Quality.DOM,
)

dom7_flat9_sharp9_sharp11 = ChordType(
    tones=[C, E, G, Bb, Db, Dx, Fx],
    name="dominant 7 flat 9 sharp 9 sharp 11",
    quality=Quality.DOM,
)

dom7_flat9_sharp9_flat13 = ChordType(
    tones=[C, E, G, Bb, Db, Dx, Ab],
    name="dominant 7 flat 9 sharp 9 flat 13",
    quality=Quality.DOM,
)

dom7_alt = ChordType(
    tones=[C, E, Bb, Db, Dx, Gb, Ab],
    name="altered dominant 7",
    quality=Quality.DOM,
)


# Altered major chords

maj7_flat5 = ChordType(
    tones=[C, E, Gb, B],
    name="major 7 flat 5",
    quality=Quality.MAJ,
)

maj7_sharp5 = ChordType(
    tones=[C, E, Gx, B],
    name="major 7 sharp 5",
    quality=Quality.MAJ,
)

maj7_sharp11 = ChordType(
    tones=[C, E, G, B, Fx],
    name="major 7 sharp 11",
    quality=Quality.MAJ,
)


# Altered minor chords

min7_flat5 = ChordType(
    tones=[C, Eb, Gb, Bb],
    name="minor 7 flat 5",
    quality=Quality.HDM,
)

min7_sharp5 = ChordType(
    tones=[C, Eb, Gx, Bb],
    name="minor 7 sharp 5",
    quality=Quality.MIN,
)

min9_flat5 = ChordType(
    tones=[C, Eb, Gb, Bb, D],
    name="minor 9 flat 5",
    quality=Quality.HDM,
)

min11_flat5 = ChordType(
    tones=[C, Eb, Gb, Bb, D, F],
    name="minor 11 flat 5",
    quality=Quality.HDM,
)


# Diminished-family extensions occasionally encountered in jazz charts

dim_maj7 = ChordType(
    tones=[C, Eb, Gb, B],
    name="diminished major 7",
    quality=Quality.DIM,
)

dim9 = ChordType(
    tones=[C, Eb, Gb, Bbb, D],
    name="diminished 9",
    quality=Quality.DIM,
)

hdim9 = ChordType(
    tones=[C, Eb, Gb, Bb, D],
    name="half-diminished 9",
    quality=Quality.HDM,
)

hdim11 = ChordType(
    tones=[C, Eb, Gb, Bb, D, F],
    name="half-diminished 11",
    quality=Quality.HDM,
)
