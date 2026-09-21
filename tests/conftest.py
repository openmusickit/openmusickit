"""Shared fixtures.

The `*_symbols` fixtures collect every ready-made object of one kind from the
relevant `symbols` module, by name, so a test can iterate over the whole set
(all pitch classes, all chord types, all modes, all note values, ...). A
module often binds several names to one object (`quarter is crotchet`);
`tests.domains.distinct` keeps one name per object when a law should be
checked once per value. `tests/test_fixtures.py` pins the size of every
fixture so an empty one fails loudly.

Hypothesis runs under the `default` profile (100 examples, no deadline,
since graph tests allocate); `uv run pytest --hypothesis-profile=thorough`
runs 2,000 examples per property. Tests marked `slow` are skipped by
default (`-m "not slow"` in `addopts`); `uv run pytest -m slow` runs them.
"""

import pytest
from hypothesis import settings

from openmusickit.systems.wsmn.scoring import symbols as scoring_symbols
from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.tonal import symbols as tonal_symbols
from openmusickit.systems.wsmn.tonal.chords import ChordType
from openmusickit.systems.wsmn.tonal.interval_quality import QUALITIES
from openmusickit.systems.wsmn.tonal.key import Key, ModePattern
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import Mark
from openmusickit.values.time.duration import GraceDuration
from tests.domains import TONAL_OCT_TUPLES, TONAL_TUPLES, symbols_of

settings.register_profile("default", max_examples=100, deadline=None)
settings.register_profile("thorough", max_examples=2000, deadline=None)
settings.load_profile("default")


# --- tonal arithmetic tuples -------------------------------------------------


@pytest.fixture
def tonal_tuples():
    """List of (d,c) tuples comprising
    naturals, sharps, flats, double sharps, and double flats."""
    return list(TONAL_TUPLES)


@pytest.fixture
def tonal_oct_tuples():
    """List of octave-qualified tonal tuples,
    at Middle C and up & down two octaves."""
    return list(TONAL_OCT_TUPLES)


# --- tonal symbols -----------------------------------------------------------


@pytest.fixture
def pitch_symbols():
    """All the TonalVectors defined in `tonal.symbols`, by name. Pitch names
    (`C`, `Eb`, `Fx`, ...) and interval names (`P5`, `m3`, ...) are aliases of
    the same objects, so both spellings are present."""
    return symbols_of(tonal_symbols, TonalVector)


@pytest.fixture
def chord_type_symbols():
    """All the ChordType symbols (`maj`, `min7`, `dom7_flat9`, ...) in `tonal.symbols`, by name."""
    return symbols_of(tonal_symbols, ChordType)


@pytest.fixture
def mode_pattern_symbols():
    """All the ModePattern symbols (`Major`, `Dorian`, ...) in `tonal.symbols`, by name."""
    return symbols_of(tonal_symbols, ModePattern)


@pytest.fixture
def key_symbols():
    """All the Key symbols (`NoKey`, ...) in `tonal.symbols`, by name."""
    return symbols_of(tonal_symbols, Key)


@pytest.fixture
def interval_qualities():
    """The nineteen IntervalQuality values, from `QUALITIES`, in relative-number order."""
    return list(QUALITIES.values())


# --- temporal symbols --------------------------------------------------------


@pytest.fixture
def duration_symbols():
    """All the MetricalDuration symbols (`quarter`, `dotted_half`, `eighth_in_triplet`, ...)
    in `temporal.symbols`, by name. GraceDurations are a different type and
    live in `grace_duration_symbols`."""
    return symbols_of(temporal_symbols, MetricalDuration)


@pytest.fixture
def grace_duration_symbols():
    """All the GraceDuration symbols (`grace_eighth`, `appoggiatura_quarter`, ...)
    in `temporal.symbols`, by name."""
    return symbols_of(temporal_symbols, GraceDuration)


@pytest.fixture
def tuplet_ratio_factories():
    """The six TemporalRatio factory functions in `temporal.symbols`, by name:
    the general `tuplet(nominal, contextual, base)` and the five named
    `triplet(base)` .. `septuplet(base)`."""
    return {
        name: getattr(temporal_symbols, name)
        for name in ["tuplet", "triplet", "duplet", "quintuplet", "sextuplet", "septuplet"]
    }


@pytest.fixture
def tuplet_ratio_symbols(tuplet_ratio_factories):
    """Six TemporalRatios built on the quarter: one from each factory.

    `temporal.symbols` defines no TemporalRatio constants, only the factory
    functions (a ratio needs a base value), so this fixture builds the ratios
    rather than collecting them. The general `tuplet` contributes the
    7-in-the-time-of-6 septuplet, which no named factory makes."""
    ratios = {
        name: factory(temporal_symbols.quarter)
        for name, factory in tuplet_ratio_factories.items()
        if name != "tuplet"
    }
    ratios["tuplet_7_6"] = tuplet_ratio_factories["tuplet"](7, 6, temporal_symbols.quarter)
    return ratios


@pytest.fixture
def time_signature_symbols():
    """All the TimeSignature symbols (`four_four`, `six_eight`, `seven_eight_2_2_3`, ...)
    in `temporal.symbols`, by name."""
    return symbols_of(temporal_symbols, TimeSignature)


# --- scoring symbols ---------------------------------------------------------


@pytest.fixture
def mark_symbols():
    """All the Mark symbols (`staccato`, `slur`, `piano`, ...) in `scoring.symbols`, by name."""
    return symbols_of(scoring_symbols, Mark)
