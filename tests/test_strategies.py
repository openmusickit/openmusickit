"""Smoke tests: every strategy in `tests.strategies` draws values of the
right shape. A handful of examples each; the properties themselves live
with the code they test (Step 8 of the testing plan).
"""

from fractions import Fraction

from hypothesis import given, settings

from openmusickit.objects.note_event import NoteEvent
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.duration import Duration
from openmusickit.values.tone.tone import Tone
from tests import strategies as omk

FEW = settings(max_examples=10)


@FEW
@given(omk.tonal_vectors())
def test_tonal_vectors(v):
    assert isinstance(v, TonalVector)


@FEW
@given(omk.tonal_vectors(qualified=True), omk.tonal_vectors(qualified=False))
def test_tonal_vectors_by_kind(q, a):
    assert q.has_octave and not a.has_octave


@FEW
@given(omk.metrical_durations())
def test_metrical_durations(d):
    assert isinstance(d, MetricalDuration)
    assert d.rational_length > 0


@FEW
@given(omk.positive_fractions())
def test_positive_fractions(x):
    assert isinstance(x, Fraction)
    assert 0 < x <= 16 and x.denominator <= 64


@FEW
@given(omk.percussion_tones())
def test_percussion_tones(tone):
    assert isinstance(tone, PercussionTone)


@FEW
@given(omk.note_events())
def test_note_events(event):
    assert isinstance(event, NoteEvent)
    assert len(event.tones) <= 3
    assert all(isinstance(t, TonalVector) for t in event.tones)
    assert event.duration is None or isinstance(event.duration, Duration)


@FEW
@given(omk.note_events(unpitched=True))
def test_note_events_with_percussion(event):
    assert all(isinstance(t, Tone) for t in event.tones)


@FEW
@given(omk.lines(min_size=2, max_size=4))
def test_lines(line):
    assert 2 <= len(line) <= 4
    assert all(isinstance(e, NoteEvent) for e in line)
    assert len({e.id for e in line}) == len(line)


@FEW
@given(omk.pitch_spellings())
def test_pitch_spellings(spelling):
    text, expected = spelling
    assert isinstance(text, str) and isinstance(expected, TonalVector)


@FEW
@given(omk.interval_spellings())
def test_interval_spellings(spelling):
    text, expected = spelling
    assert isinstance(text, str) and isinstance(expected, TonalVector)


@FEW
@given(omk.lyric_texts())
def test_lyric_texts(text):
    assert isinstance(text, str)
    assert text == text.strip()
