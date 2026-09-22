"""PercussionTone is a plain unpitched value: a relative pitch and a stroke,
each optional, in its own tonal system, printing as its readable form."""

import copy
import pickle

import pytest
from hypothesis import given

from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.systems.wsmn.percussion.percussion_tone import (
    PercussionTone,
    RelativePitch,
    Stroke,
)
from openmusickit.systems.wsmn.percussion.wsmn import WSMN_PERCUSSION
from openmusickit.systems.wsmn.tonal.symbols import M3, C, E
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.systems.wsmn.tonal.wsmn import WSMN
from openmusickit.values.tone.interval import Interval
from openmusickit.values.tone.silent_tone import SilentTone
from openmusickit.values.tone.tone import ANY_TONAL_SYSTEM, Tone
from openmusickit.values.tone.unpitched_tone import UnpitchedTone
from tests.domains import PERCUSSION_TONES
from tests.strategies import percussion_tones

HIT = PercussionTone()
HIGH_OPEN = PercussionTone(relative_pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)


def test_hierarchy():
    assert isinstance(HIT, Tone)
    assert isinstance(HIT, UnpitchedTone)
    assert not isinstance(HIT, Interval)
    assert not isinstance(HIT, SilentTone)


def test_its_own_system_which_transposes_nothing():
    assert HIT.tonal_system is WSMN_PERCUSSION
    assert not WSMN_PERCUSSION.universal
    assert not WSMN_PERCUSSION.compatible_with(WSMN)
    assert WSMN_PERCUSSION.compatible_with(ANY_TONAL_SYSTEM)


def test_no_pitch_and_the_readable_form_through_format():
    assert HIT.pitch is None and HIGH_OPEN.pitch is None
    assert str(HIT) == "hit"
    assert str(HIGH_OPEN) == "high open"
    assert str(PercussionTone(stroke=Stroke.RIM_SHOT)) == "rim shot"
    assert str(PercussionTone(relative_pitch=RelativePitch.LOW_MID)) == "low-mid"
    assert f"{HIGH_OPEN}" == "high open"
    assert format(HIGH_OPEN, "ascii") == "high open"  # no pitch: the spec is ignored, not an error


@pytest.mark.parametrize("tone", PERCUSSION_TONES, ids=str)
def test_repr_round_trips(tone):
    assert eval(repr(tone)) == tone


@given(percussion_tones())
def test_a_plain_value(tone):
    assert tone == PercussionTone(relative_pitch=tone.relative_pitch, stroke=tone.stroke)
    assert hash(tone) == hash(copy.deepcopy(tone))
    assert pickle.loads(pickle.dumps(tone)) == tone
    assert not hasattr(tone, "__dict__")
    with pytest.raises(AttributeError):
        tone.stroke = None


def test_distinct_from_pitched_tones_and_silence():
    assert HIT != SilentTone() and SilentTone() != HIT
    assert HIT != TonalVector((0, 0)) and TonalVector((0, 0)) != HIT
    assert len({HIT, HIGH_OPEN, SilentTone(), TonalVector((0, 0)), PercussionTone()}) == 4


def test_relative_pitch_is_ordered_low_to_high():
    assert list(RelativePitch) == sorted(RelativePitch)
    assert RelativePitch.LOW < RelativePitch.LOW_MID < RelativePitch.MID
    assert RelativePitch.MID < RelativePitch.HIGH_MID < RelativePitch.HIGH
    assert [str(p) for p in RelativePitch] == ["low", "low-mid", "mid", "high-mid", "high"]


def test_stroke_values_are_display_forms():
    assert len(Stroke) == 28
    assert len({s.value for s in Stroke}) == 28
    assert all(s.value == s.value.lower() and "_" not in s.value for s in Stroke)
    assert Stroke("rim shot") is Stroke.RIM_SHOT


def test_a_note_event_may_mix_pitched_and_unpitched_tones():
    note = NoteEvent(tones={C, HIT})
    assert not note.is_rest
    assert note.tones == {C, HIT}
    rest = Rest(None)
    rest.add_tone(HIT)
    assert rest.tones == {HIT} and not rest.is_rest


def test_a_pitched_operation_on_a_percussion_tone_is_loud():
    note = NoteEvent(tones={C, HIT})
    with pytest.raises(TypeError):
        note.transform_tones(TonalVector.transpose, M3)
    assert note.tones == {C, HIT}  # unchanged on failure


def test_a_remap_is_an_ordinary_tone_operation():
    note = NoteEvent(tones={HIT, HIGH_OPEN})
    remap = {HIT: PercussionTone(stroke=Stroke.RIM_SHOT)}
    note.transform_tones(lambda tone: remap.get(tone, tone))
    assert note.tones == {PercussionTone(stroke=Stroke.RIM_SHOT), HIGH_OPEN}
    pitched = NoteEvent(tones={C})
    pitched.transform_tones(TonalVector.transpose, M3)
    assert pitched.tones == {E}
