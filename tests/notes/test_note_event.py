import pytest

from openmusickit.objects.note.note import NoteEvent, Rest
from openmusickit.values.tone.silent_tone import SilentTone
from openmusickit.values.tone.tone import Tone
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector, TonalDirection
from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Gx, B, M3


def test_rest_is_a_note_event_with_a_silent_tone():
    rest = Rest(None)
    assert isinstance(rest, NoteEvent)
    assert rest.tones == {SilentTone()}
    assert rest.is_rest
    assert repr(rest) == "Rest(duration=None)"


def test_pitched_note_is_not_a_rest():
    note = NoteEvent(tones={C, E, G})
    assert not note.is_rest
    assert repr(note) == (
        "NoteEvent(tones=[TonalVector((0, 0)), TonalVector((2, 4)), TonalVector((4, 7))], duration=None)"
    )


def test_empty_note_event_is_not_a_rest():
    note = NoteEvent(tones=set())
    assert not note.is_rest
    assert repr(note) == "NoteEvent(tones=[], duration=None)"


def test_silent_tone_cannot_coexist_with_other_tones():
    with pytest.raises(ValueError):
        NoteEvent(tones={C, SilentTone()})


def test_add_tone_to_rest_removes_silence():
    rest = Rest(None)
    rest.add_tone(C)
    assert rest.tones == {C}
    assert not rest.is_rest


def test_add_silent_tone_to_pitched_note_is_noop():
    note = NoteEvent(tones={C})
    note.add_tone(SilentTone())
    assert note.tones == {C}


def test_make_rest():
    note = NoteEvent(tones={C, E})
    note.make_rest()
    assert note.is_rest
    assert note.tones == {SilentTone()}


def test_swap_tone():
    note = NoteEvent(tones={C, E})
    note.swap_tone(E, G)
    assert note.tones == {C, G}


def test_transform_transposes_every_tone():
    note = NoteEvent(tones={C, E, G})
    note.transform_tones(TonalVector.transpose, M3)
    assert note.tones == {E, Gx, B}
    note.transform_tones(TonalVector.transpose, M3, TonalDirection.DOWN)
    assert note.tones == {C, E, G}


def test_transform_leaves_rest_alone():
    rest = Rest(None)
    rest.transform_tones(TonalVector.transpose, M3)
    assert rest.tones == {SilentTone()}
    assert rest.is_rest


def test_transform_accepts_any_tone_result():
    """The result need not be the same Tone subclass as the input."""
    class OtherTone(Tone):
        def __eq__(self, other):
            return type(other) is OtherTone
        def __hash__(self):
            return 1

    note = NoteEvent(tones={C})
    note.transform_tones(lambda tv: OtherTone())
    assert note.tones == {OtherTone()}


def test_transform_rejects_non_tone_result():
    note = NoteEvent(tones={C, E})
    with pytest.raises(TypeError, match="must return a Tone"):
        note.transform_tones(str)
    assert note.tones == {C, E}
