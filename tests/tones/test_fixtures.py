import pytest

@pytest.fixture
def tonal_tuples():
    """List of (d,c) tuples comprising 
    naturals, sharps, flats, double sharps, and double flats."""

    MS = [
        (0, 0),
        (1, 2),
        (2, 4),
        (3, 5), 
        (4, 7), 
        (5, 9),
        (6,11)
    ]

    return [(x[0],(x[1]+m)%12) for m in [0,1,2,-1,-2] for x in MS]

@pytest.fixture
def tonal_oct_tuples(tonal_tuples):
    """List of octave-qualified tonal tuples,
    at Middle C and up & down two octaves."""
    
    return [(x[0], x[1], y) for y in [0,1,2,-1,-2] for x in tonal_tuples]