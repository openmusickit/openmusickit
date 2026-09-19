"""Shared fixtures.

The `*_symbols` fixtures collect every ready-made object of one kind from the
relevant `symbols` module, by name, so a test can iterate over the whole set
(all pitch classes, all chord types, all modes, all note values, ...).
"""

import pytest

from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.tonal import symbols as tonal_symbols
from openmusickit.systems.wsmn.tonal.chords import ChordType
from openmusickit.systems.wsmn.tonal.key import Key, ModePattern
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.duration import TemporalRatio


def _symbols_of(module, kind) -> dict:
    """Every public module attribute of type `kind`, by name."""
    return {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("_") and type(value) is kind
    }


# --- tonal arithmetic tuples -------------------------------------------------


@pytest.fixture
def tonal_tuples():
    """List of (d,c) tuples comprising
    naturals, sharps, flats, double sharps, and double flats."""
    major_scale = [(0, 0), (1, 2), (2, 4), (3, 5), (4, 7), (5, 9), (6, 11)]
    return [(x[0], (x[1] + m) % 12) for m in [0, 1, 2, -1, -2] for x in major_scale]


@pytest.fixture
def tonal_oct_tuples(tonal_tuples):
    """List of octave-qualified tonal tuples,
    at Middle C and up & down two octaves."""
    return [(x[0], x[1], y) for y in [0, 1, 2, -1, -2] for x in tonal_tuples]


# --- tonal symbols -----------------------------------------------------------


@pytest.fixture
def pitch_symbols():
    """All the TonalVectors defined in `tonal.symbols`, by name. Pitch names
    (`C`, `Eb`, `Fx`, ...) and interval names (`P5`, `m3`, ...) are aliases of
    the same objects, so both spellings are present."""
    return _symbols_of(tonal_symbols, TonalVector)


@pytest.fixture
def chord_type_symbols():
    """All the ChordType symbols (`maj`, `min7`, `dom7_flat9`, ...) in `tonal.symbols`, by name."""
    return _symbols_of(tonal_symbols, ChordType)


@pytest.fixture
def mode_pattern_symbols():
    """All the ModePattern symbols (`Major`, `Dorian`, ...) in `tonal.symbols`, by name."""
    return _symbols_of(tonal_symbols, ModePattern)


@pytest.fixture
def key_symbols():
    """All the Key symbols (`NoKey`, ...) in `tonal.symbols`, by name."""
    return _symbols_of(tonal_symbols, Key)


# --- temporal symbols --------------------------------------------------------


@pytest.fixture
def duration_symbols():
    """All the MetricalDuration symbols (`quarter`, `dotted_half`, `eighth_in_triplet`, ...)
    in `temporal.symbols`, by name."""
    return _symbols_of(temporal_symbols, MetricalDuration)


@pytest.fixture
def tuplet_ratio_symbols():
    """All the TemporalRatio symbols in `temporal.symbols`, by name."""
    return _symbols_of(temporal_symbols, TemporalRatio)


@pytest.fixture
def time_signature_symbols():
    """All the TimeSignature symbols (`four_four`, `six_eight`, `seven_eight_2_2_3`, ...)
    in `temporal.symbols`, by name."""
    return _symbols_of(temporal_symbols, TimeSignature)
