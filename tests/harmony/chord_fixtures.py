import pytest

from openmusickit.systems.wsmn.tonal import symbols
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.chords import ChordType


@pytest.fixture
def pitch_symbols():
    """All the pitch-class TonalVectors defined in `symbols` (naturals,
    sharps, flats, double sharps, double flats), by name."""
    return {
        name: value
        for name, value in vars(symbols).items()
        if isinstance(value, TonalVector)
    }


@pytest.fixture
def chord_type_symbols():
    """All the ChordType symbols (`maj`, `min7`, `dom7_flat9`, etc.) defined
    in `symbols`, by name."""
    return {
        name: value
        for name, value in vars(symbols).items()
        if isinstance(value, ChordType)
    }
