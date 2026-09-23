"""Guards on the shared fixtures: each is non-empty and its size is pinned.

A symbol fixture that silently came back empty (as `tuplet_ratio_symbols`
once did) would make every exhaustive test built on it pass over zero cases.
The literals here are the counts as of 2026-09-21; when a symbol is added,
update the literal in the same commit.
"""

from tests.domains import (
    ABSTRACT_VECTORS,
    ALL_VECTORS,
    PERCUSSION_TONES,
    QUALIFIED_VECTORS,
    TONAL_OCT_TUPLES,
    TONAL_TUPLES,
    distinct,
)


def test_tonal_tuple_domains():
    assert len(TONAL_TUPLES) == 35
    assert len(set(TONAL_TUPLES)) == 35
    assert len(TONAL_OCT_TUPLES) == 175
    assert len(set(TONAL_OCT_TUPLES)) == 175


def test_tonal_vector_domains():
    assert len(ABSTRACT_VECTORS) == 35
    assert len(QUALIFIED_VECTORS) == 175
    assert len(ALL_VECTORS) == 210
    assert len(set(ALL_VECTORS)) == 210


def test_percussion_tone_domain():
    """Six relative pitches (five and none) by twenty-nine strokes (twenty-eight and none)."""
    assert len(PERCUSSION_TONES) == 6 * 29
    assert len(set(PERCUSSION_TONES)) == 6 * 29


def test_tonal_tuple_fixtures(tonal_tuples, tonal_oct_tuples):
    assert tonal_tuples == TONAL_TUPLES
    assert tonal_oct_tuples == TONAL_OCT_TUPLES


def test_pitch_symbols(pitch_symbols):
    """35 pitch classes, each bound to a pitch name and an interval name."""
    assert len(pitch_symbols) == 70
    assert len(distinct(pitch_symbols)) == 35


def test_chord_type_symbols(chord_type_symbols):
    assert len(chord_type_symbols) == 78
    assert len(distinct(chord_type_symbols)) == 77


def test_mode_pattern_symbols(mode_pattern_symbols):
    assert len(mode_pattern_symbols) == 9
    assert len(distinct(mode_pattern_symbols)) == 9


def test_key_symbols(key_symbols):
    assert list(key_symbols) == ["NoKey"]


def test_interval_qualities(interval_qualities):
    assert len(interval_qualities) == 19
    assert len({q.rel_number for q in interval_qualities}) == 19


def test_duration_symbols(duration_symbols):
    """39 note values under 68 names (British and American spellings)."""
    assert len(duration_symbols) == 68
    assert len(distinct(duration_symbols)) == 39


def test_grace_duration_symbols(grace_duration_symbols):
    assert len(grace_duration_symbols) == 7
    assert len(distinct(grace_duration_symbols)) == 5


def test_tuplet_ratio_factories(tuplet_ratio_factories):
    assert len(tuplet_ratio_factories) == 6
    assert all(callable(f) for f in tuplet_ratio_factories.values())


def test_tuplet_ratio_symbols(tuplet_ratio_symbols):
    assert len(tuplet_ratio_symbols) == 6
    assert len(distinct(tuplet_ratio_symbols)) == 6


def test_time_signature_symbols(time_signature_symbols):
    assert len(time_signature_symbols) == 35
    assert len(distinct(time_signature_symbols)) == 29


def test_mark_symbols(mark_symbols):
    assert len(mark_symbols) == 238
    assert len(distinct(mark_symbols)) == 238


def test_bar_line_symbols(bar_line_symbols):
    assert len(bar_line_symbols) == 14
    assert len(distinct(bar_line_symbols)) == 14


def test_tempo_term_symbols(tempo_term_symbols):
    assert len(tempo_term_symbols) == 25
    assert len(distinct(tempo_term_symbols)) == 25


def test_percussion_tone_symbols(percussion_tone_symbols):
    """43 names for 42 tones (`open_hat` and `open_hand` are one)."""
    assert len(percussion_tone_symbols) == 43
    assert len(distinct(percussion_tone_symbols)) == 42


def test_palette_symbols(palette_symbols):
    assert len(palette_symbols) == 16
    assert len(distinct(palette_symbols)) == 16
