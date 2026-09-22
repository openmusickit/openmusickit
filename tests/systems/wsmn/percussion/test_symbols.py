"""The ready-made percussion tones and palettes: every palette is a
ToneCollection of distinct PercussionTones with `hit` first, ordered low to
high; the tone symbols are distinct except for the one documented alias."""

import pytest

from openmusickit.systems.wsmn.percussion import symbols
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone, Stroke
from openmusickit.values.tone.tone_collection import ToneCollection
from tests.domains import distinct


def test_every_palette_is_a_named_collection_of_distinct_tones_starting_with_hit(palette_symbols):
    for name, palette in palette_symbols.items():
        assert isinstance(palette, ToneCollection), name
        assert palette.name, name
        assert palette.root is None
        assert palette[0] == symbols.hit, name
        assert all(isinstance(t, PercussionTone) for t in palette), name
        assert len(set(palette)) == len(palette), name


def test_palettes_are_ordered_low_to_high(palette_symbols):
    for name, palette in palette_symbols.items():
        pitches = [t.relative_pitch for t in palette if t.relative_pitch is not None]
        assert pitches == sorted(pitches), name


def test_tone_symbols_are_distinct_but_for_the_open_alias(percussion_tone_symbols):
    assert percussion_tone_symbols["open_hat"] is percussion_tone_symbols["open_hand"]
    kept = distinct(percussion_tone_symbols)
    assert len(kept) == len(percussion_tone_symbols) - 1
    assert len(set(kept.values())) == len(kept)


def test_hand_drum_pairs_are_in_the_hand_drum_palette():
    for tone in (symbols.low_open, symbols.high_slap, symbols.high_bass, symbols.low_mute):
        assert tone in symbols.hand_drums
    assert symbols.rim_shot not in symbols.hand_drums
    assert symbols.rim_shot in symbols.snare_drums and symbols.rim_shot in symbols.toms


@pytest.mark.parametrize(
    ("palette", "size"),
    [
        (symbols.hand_drums, 40),
        (symbols.snare_drums, 8),
        (symbols.bass_drums, 12),
        (symbols.toms, 36),
        (symbols.hi_hats, 8),
        (symbols.cymbals, 5),
        (symbols.blocks, 6),
        (symbols.body, 5),
        (symbols.single_hit, 1),
    ],
    ids=lambda x: x.name if isinstance(x, ToneCollection) else str(x),
)
def test_palette_sizes(palette, size):
    assert len(palette) == size


def test_a_palette_transforms_like_any_tone_collection():
    """A remap over a palette is an ordinary Tone -> Tone operation."""
    remap = {symbols.closed: symbols.open_hat}
    remapped = symbols.hi_hats.transform(lambda t: remap.get(t, t))
    assert symbols.closed not in remapped
    assert list(remapped).count(symbols.open_hat) == 2
    assert symbols.hi_hats.name == remapped.name == "hi-hat"


def test_every_stroke_appears_in_some_palette(palette_symbols):
    used = {t.stroke for palette in palette_symbols.values() for t in palette}
    assert used >= set(Stroke)
