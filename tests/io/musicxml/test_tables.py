"""The name tables between MusicXML and WSMN: complete over the MusicXML
vocabularies they claim, made of the ready-made WSMN symbols, and exact both
ways where a conversion has an inverse (pitch)."""

import pytest

from openmusickit.io.musicxml import tables
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineShape
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.tonal.chords import ChordType
from openmusickit.systems.wsmn.tonal.key import ModePattern
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import Mark, MarkType
from openmusickit.values.scoring.tempo_term import TempoTerm
from tests.domains import ABSTRACT_VECTORS, QUALIFIED_VECTORS

# --- pitch -------------------------------------------------------------------------


def test_every_qualified_vector_round_trips_through_a_musicxml_pitch():
    for tone in QUALIFIED_VECTORS:
        step, alter, octave = tables.pitch_of_tone(tone)
        assert step in tables.STEPS and -2 <= alter <= 2
        assert tables.tone_from_pitch(step, alter, octave) == tone


def test_every_musicxml_pitch_round_trips_through_a_tone():
    for step in tables.STEPS:
        for alter in range(-2, 3):
            for octave in range(0, 10):
                tone = tables.tone_from_pitch(step, alter, octave)
                assert tone.has_octave
                assert tables.pitch_of_tone(tone) == (step, alter, octave)


def test_middle_c_is_octave_four_and_the_origin():
    assert tables.tone_from_pitch("C", 0, 4) == TonalVector((0, 0, 0))
    assert tables.pitch_of_tone(TonalVector((0, 0, 0))) == ("C", 0, 4)


def test_an_abstract_tone_has_no_pitch():
    for tone in ABSTRACT_VECTORS[:5]:
        with pytest.raises(ValueError):
            tables.pitch_of_tone(tone)


# --- durations ------------------------------------------------------------------------

MUSICXML_NOTE_TYPES = [
    "1024th", "512th", "256th", "128th", "64th", "32nd", "16th", "eighth",
    "quarter", "half", "whole", "breve", "long", "maxima",
]  # fmt: skip


def test_note_types_cover_the_musicxml_vocabulary_in_length_order():
    assert list(tables.NOTE_TYPES) == MUSICXML_NOTE_TYPES
    lengths = [MetricalDuration(*value).rational_length for value in tables.NOTE_TYPES.values()]
    assert lengths == sorted(lengths)
    assert all(later == 2 * earlier for earlier, later in zip(lengths, lengths[1:], strict=False))
    assert tables.NOTE_TYPES["whole"] == (1, 1) and tables.NOTE_TYPES["quarter"] == (1, 4)


# --- attributes -------------------------------------------------------------------------

MUSICXML_BAR_STYLES = [
    "regular", "dotted", "dashed", "heavy", "light-light", "light-heavy",
    "heavy-light", "heavy-heavy", "tick", "short", "none",
]  # fmt: skip


def test_bar_styles_cover_the_musicxml_vocabulary_with_ready_made_shapes(bar_line_symbols):
    assert set(tables.BAR_STYLES) == set(MUSICXML_BAR_STYLES)
    ready_made = {id(shape) for shape in bar_line_symbols.values()}
    for style, shape in tables.BAR_STYLES.items():
        assert isinstance(shape, BarLineShape) and id(shape) in ready_made, style
    assert tables.BAR_STYLES["regular"] is scoring.single_bar
    assert tables.BAR_STYLES["light-heavy"] is scoring.final_bar
    assert tables.BAR_STYLES["none"] is scoring.invisible_bar


def test_clef_signs_cover_every_clef_sign():
    assert set(tables.CLEF_SIGNS.values()) == set(ClefSign)
    assert set(tables.CLEF_SIGNS) == {"G", "F", "C", "percussion", "TAB", "none"}


def test_modes_are_the_mode_patterns_with_a_tonic_degree_each(mode_pattern_symbols):
    assert set(tables.MODES) == set(tables.MODE_TONIC_DEGREE)
    ready_made = {id(pattern) for pattern in mode_pattern_symbols.values()}
    for name, pattern in tables.MODES.items():
        assert isinstance(pattern, ModePattern) and id(pattern) in ready_made, name
    assert tables.MODE_TONIC_DEGREE["major"] == 0 and tables.MODE_TONIC_DEGREE["minor"] == 5
    assert tables.MODE_TONIC_DEGREE["dorian"] == 1 and tables.MODE_TONIC_DEGREE["locrian"] == 6


# --- chord symbols --------------------------------------------------------------------------

MUSICXML_KINDS = [
    "major", "minor", "augmented", "diminished", "dominant", "major-seventh",
    "minor-seventh", "diminished-seventh", "augmented-seventh", "half-diminished",
    "major-minor", "major-sixth", "minor-sixth", "dominant-ninth", "major-ninth",
    "minor-ninth", "dominant-11th", "major-11th", "minor-11th", "dominant-13th",
    "major-13th", "minor-13th", "suspended-second", "suspended-fourth", "Neapolitan",
    "Italian", "French", "German", "pedal", "power", "Tristan", "other", "none",
]  # fmt: skip


def test_kinds_map_every_named_chord_kind_to_a_ready_made_chord_type(chord_type_symbols):
    ready_made = {id(chord_type) for chord_type in chord_type_symbols.values()}
    for kind, chord_type in tables.KINDS.items():
        assert kind in MUSICXML_KINDS, kind
        assert isinstance(chord_type, ChordType) and id(chord_type) in ready_made, kind
    unmapped = set(MUSICXML_KINDS) - set(tables.KINDS)
    assert unmapped == {
        "Neapolitan",
        "Italian",
        "French",
        "German",
        "pedal",
        "Tristan",
        "other",
        "none",
    }
    assert tables.KINDS["dominant"] is scoring_free(chord_type_symbols, "dom7")
    assert tables.KINDS["augmented-seventh"] is scoring_free(chord_type_symbols, "dom7_sharp5")


def scoring_free(symbols: dict, name: str):
    return symbols[name]


# --- marks ------------------------------------------------------------------------------------

MUSICXML_ARTICULATIONS = [
    "accent", "strong-accent", "staccato", "tenuto", "detached-legato", "staccatissimo",
    "spiccato", "scoop", "plop", "doit", "falloff", "breath-mark", "caesura", "stress",
    "unstress", "soft-accent",
]  # fmt: skip
MUSICXML_DYNAMICS = [
    "p", "pp", "ppp", "pppp", "ppppp", "pppppp", "f", "ff", "fff", "ffff", "fffff", "ffffff",
    "mp", "mf", "sf", "sfp", "sfpp", "fp", "rf", "rfz", "sfz", "sffz", "fz", "n", "pf", "sfzp",
]  # fmt: skip
MUSICXML_ORNAMENTS = [
    "trill-mark", "turn", "delayed-turn", "inverted-turn", "delayed-inverted-turn",
    "vertical-turn", "inverted-vertical-turn", "shake", "wavy-line", "mordent",
    "inverted-mordent", "schleifer", "tremolo", "haydn",
]  # fmt: skip

MARK_TABLES = (
    tables.ARTICULATIONS, tables.BREATH_MARKS, tables.ORNAMENTS, tables.TECHNICAL,
    tables.FINGERINGS, tables.STRINGS, tables.PLUCKS, tables.HANDBELLS, tables.HARMON_MUTES,
    tables.HOLES, tables.DYNAMICS, tables.FERMATAS, tables.ARPEGGIOS, tables.WEDGES,
    tables.OCTAVE_SHIFTS, tables.PEDALS, tables.NOTATION_SPANS,
)  # fmt: skip


def test_every_mark_in_a_table_is_a_ready_made_mark(mark_symbols):
    ready_made = {id(mark) for mark in mark_symbols.values()}
    for table in MARK_TABLES:
        for key, mark in table.items():
            assert isinstance(mark, Mark) and id(mark) in ready_made, (key, mark)


def test_the_element_tables_cover_their_musicxml_vocabularies():
    assert set(tables.ARTICULATIONS) == set(MUSICXML_ARTICULATIONS)
    assert set(tables.DYNAMICS) == set(MUSICXML_DYNAMICS)
    assert set(tables.ORNAMENTS) == set(MUSICXML_ORNAMENTS)
    assert set(tables.FINGERINGS) == {str(i) for i in range(6)}
    assert set(tables.STRINGS) == {str(i) for i in range(1, 7)}
    assert set(tables.PLUCKS) == {"p", "i", "m", "a", "c"}
    assert tables.PER_TONE_TECHNICAL <= set(tables.TECHNICAL) | {
        "fingering", "string", "fret", "pluck", "hole",
    }  # fmt: skip


def test_the_tables_agree_with_the_marks_kinds():
    for mark in tables.ARTICULATIONS.values():
        assert mark.kind in (MarkType.ARTICULATION, MarkType.BREATH), mark.name
    for mark in tables.DYNAMICS.values():
        assert mark.kind is MarkType.DYNAMIC, mark.name
    for mark in tables.ORNAMENTS.values():
        assert mark.kind is MarkType.ORNAMENT, mark.name
    for mark in (*tables.FINGERINGS.values(), *tables.STRINGS.values(), *tables.PLUCKS.values()):
        assert mark.kind is MarkType.FINGERING, mark.name
    for mark in tables.FERMATAS.values():
        assert mark.kind is MarkType.PHRASING, mark.name
    for mark in tables.OCTAVE_SHIFTS.values():
        assert mark.kind is MarkType.TRANSPOSITION, mark.name


def test_marks_without_an_element_are_reachable_by_their_words(mark_symbols):
    """The marks no MusicXML element names (navigation words, expression
    words, most technique text) are reached through `WORDS` by name or
    alias; the count is pinned so a new mark or table entry is noticed."""
    by_element = {id(mark) for table in MARK_TABLES for mark in table.values()}
    by_element |= {id(scoring.tie), id(scoring.non_arpeggio), id(scoring.laissez_vibrer)}
    words_only = {mark.name for mark in mark_symbols.values() if id(mark) not in by_element}
    assert len(words_only) == 95
    for name in words_only:
        assert tables.WORDS[name.lower()].name == name


def test_words_and_tempo_terms_are_keyed_by_name_and_alias_in_lower_case():
    assert tables.WORDS["p"] is scoring.piano
    assert tables.WORDS["pizz."] is scoring.pizzicato
    assert tables.WORDS["d.s. al coda"] is scoring.dal_segno_al_coda
    assert tables.WORDS["8va"] is scoring.ottava_alta
    assert tables.TEMPO_TERMS["allegro"] is scoring.allegro
    assert tables.TEMPO_TERMS["tempo i"] is scoring.tempo_primo
    assert tables.TEMPO_TERMS["a tempo"] is scoring.a_tempo
    assert all(isinstance(term, TempoTerm) for term in tables.TEMPO_TERMS.values())
    assert all(key == key.lower() for key in (*tables.WORDS, *tables.TEMPO_TERMS))


@pytest.mark.parametrize(
    ("text", "gradual"),
    [
        ("rit.", True),
        ("Rit.", True),
        ("poco rit.", True),
        ("poco a poco accel.", True),
        ("molto rallentando", True),
        ("calando", True),
        ("stringendo", True),
        ("Più mosso", True),
        ("a tempo", False),
        ("Allegro", False),
        ("cresc.", False),
        ("dolce", False),
    ],
)
def test_gradual_tempo_words(text, gradual):
    assert tables.is_gradual_tempo(text) is gradual


def test_normalize_words_trims_folds_case_and_collapses_spaces():
    assert tables.normalize_words("  Poco   RIT. \n") == "poco rit."
