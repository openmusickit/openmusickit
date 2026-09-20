"""The Tone / Interval class hierarchy: TonalVector and SilentTone are Tones,
TonalVector is also an Interval, and the base-class contract behaves."""

import pytest

from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.wsmn import WSMN
from openmusickit.values.tone.interval import Interval, IntervalRepresentation
from openmusickit.values.tone.silent_tone import SilentTone
from openmusickit.values.tone.tone import ANY_TONAL_SYSTEM, PitchRepresentation, TonalSystem, Tone


def test_tonal_vector_is_tone_and_interval():
    tv = TonalVector((0, 0))
    assert isinstance(tv, Tone)
    assert isinstance(tv, Interval)
    assert isinstance(tv, tuple)
    assert issubclass(TonalVector, Tone)
    assert issubclass(TonalVector, Interval)


def test_silent_tone_is_tone_only():
    st = SilentTone()
    assert isinstance(st, Tone)
    assert not isinstance(st, Interval)
    assert not isinstance(st, TonalVector)


def test_silent_tone_equality_and_hash():
    assert SilentTone() == SilentTone()
    assert hash(SilentTone()) == hash(SilentTone())
    assert SilentTone() in {SilentTone()}
    assert SilentTone() != TonalVector((0, 0))
    assert TonalVector((0, 0)) != SilentTone()


def test_mixed_tones_in_one_set():
    tones = {SilentTone(), TonalVector((0, 0)), TonalVector((0, 0)), SilentTone()}
    assert len(tones) == 2


def test_pitch_contract():
    assert SilentTone().pitch is None
    assert isinstance(TonalVector((0, 0)).pitch, PitchRepresentation)
    assert isinstance(TonalVector((0, 0)).pitch, TonalVector._PitchRepresentation)
    assert isinstance(TonalVector((0, 0)).interval, IntervalRepresentation)
    assert isinstance(TonalVector((0, 0)).interval, TonalVector._IntervalRepresentation)


def test_pitch_and_interval_are_read_only():
    tv = TonalVector((0, 0))
    with pytest.raises(AttributeError):
        tv.pitch = None
    with pytest.raises(AttributeError):
        tv.interval = None


def test_tonal_vector_init_runs_once_per_interned_value():
    tv = TonalVector((3, 5, 2))
    pitch, interval = tv.pitch, tv.interval
    assert TonalVector((3, 5, 2)) is tv
    assert TonalVector(3, 5, 2).pitch is pitch
    assert TonalVector([3, 5, 2]).interval is interval


def test_abandoned_machinery_is_gone():
    for name in ("to_array", "__array__", "abstract_array_len", "qualified_array_len"):
        assert not hasattr(Tone, name)
        assert not hasattr(Interval, name)
    for name in ("abstract_vector_len", "qualified_vector_len"):
        assert not hasattr(TonalVector, name)
    assert not hasattr(Tone, "TONAL_SYSTEM")


def test_tonal_system_is_declared_by_each_subclass():
    assert TonalVector((0, 0)).tonal_system is WSMN
    assert SilentTone().tonal_system is ANY_TONAL_SYSTEM
    assert WSMN.compatible_with(ANY_TONAL_SYSTEM)
    assert not WSMN.compatible_with(TonalSystem("Other", "..."))
