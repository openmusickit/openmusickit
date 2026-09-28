"""Labels: what a node says, and the blocks the layout places.
Most of the simple cases are doctests in `labels`; these cover the rest."""

import pytest

from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import ClefEvent, MeterEvent, ModalContextEvent, TempoEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable, parse_lyrics
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.temporal.symbols import eighth, four_four, half, quarter
from openmusickit.systems.wsmn.tonal.key import Key
from openmusickit.systems.wsmn.tonal.symbols import P5, C, Cx, E, G, Major, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration
from openmusickit.visualization.dot import is_html_label
from openmusickit.visualization.labels import (
    clef_glyph,
    clock_label,
    default_label,
    duration_glyph,
    escape,
    rest_glyph,
    sync_block,
    title_block,
    tone_label,
)


def test_a_note_with_a_sharp_and_an_octave():
    label = default_label(NoteEvent(tones={TonalVector.from_string("C#4")}, duration=quarter))
    assert is_html_label(label)
    assert 'C♯<SUP><FONT POINT-SIZE="6">4</FONT></SUP>' in label
    assert '<FONT POINT-SIZE="14">♩</FONT>' in label


def test_an_unqualified_pitch_has_no_superscript():
    assert tone_label(Cx) == "C♯"
    assert "SUP" not in default_label(NoteEvent(tones={E}, duration=half))


def test_tones_are_sorted_lowest_first():
    label = default_label(NoteEvent(tones={G, C, E}, duration=None))
    assert label.index("C") < label.index("E") < label.index("G")


def test_a_rest_shows_the_rest_glyph():
    assert rest_glyph(quarter) == "𝄽"
    assert default_label(Rest(quarter)) == '<<FONT POINT-SIZE="14">𝄽</FONT>>'
    assert default_label(Rest(None)) == "rest"


def test_a_chord_and_a_syllable():
    assert (
        default_label(ChordEvent(chord=C(maj), duration=half))
        == '<C <FONT POINT-SIZE="14">𝅗𝅥</FONT>>'
    )
    syllable = parse_lyrics("Twin-kle")[0]
    assert default_label(syllable) == str(syllable) == "Twin -"


def test_clef_glyphs():
    assert clef_glyph(scoring.treble_clef) == "𝄞"
    assert clef_glyph(scoring.bass_clef) == "𝄢"
    assert clef_glyph(scoring.alto_clef) == "𝄡"
    assert clef_glyph(scoring.percussion_clef) == "𝄥"
    assert clef_glyph(scoring.bass_clef_8vb) == "𝄢<SUB>8</SUB>"
    assert clef_glyph(scoring.no_clef) is None
    assert default_label(ClefEvent(clef=scoring.treble_clef)) == '<<FONT POINT-SIZE="16">𝄞</FONT>>'
    assert default_label(ClefEvent()) == "clef"


def test_context_events():
    assert default_label(MeterEvent(meter=four_four)) == "4/4"
    assert default_label(MeterEvent()) == "meter"
    assert default_label(TempoEvent(term=scoring.allegro)) == "allegro"
    assert default_label(TempoEvent()) == "tempo"
    key = Key(tonic=C, signature=None, mode=Major)
    assert default_label(ModalContextEvent(modal_context=key)) == "key C Major"
    assert default_label(ModalContextEvent()) == "key"


def test_divisions_marks_spanners_and_structure():
    assert default_label(DivisionEvent(shape=scoring.double_bar)) == "thin thin"
    assert default_label(DivisionEvent()) == "division"
    assert default_label(Marking(mark=scoring.staccato)) == "staccato"
    assert default_label(MarkSpanner(mark=scoring.slur)) == "slur"
    assert default_label(LyricSection(section_type="verse", section_number=2)) == "verse 2"
    assert default_label(LyricSection(section_name="Bridge")) == "Bridge"
    assert default_label(LyricSection()) == "section"
    assert default_label(Stint()) == "stint"
    assert default_label(Stint(transposition=P5)) == "stint perfect 5"
    assert default_label(Part(name="Oboe")) == "Oboe"
    assert default_label(LineGroup()) == "group"
    assert default_label(Score(title="Op. 1")) == "Op. 1"
    assert default_label(Score()) == "score"
    assert default_label(SyncLine(temporal_system=CLOCK_TIME)) == "sync line"
    assert default_label(SyncPoint(offset=ClockDuration.from_seconds(5))) == "00:00:05.0000"
    assert default_label(SyncPoint(offset=quarter, name="cue")) == "cue"
    assert default_label(OmkObject()) == "OmkObject"


def test_clock_label_rounds_to_tenths_of_a_millisecond():
    assert clock_label(ClockDuration(1_234_567)) == "00:00:01.2346"
    assert clock_label(ClockDuration.from_seconds(-5)) == "-00:00:05.0000"


def test_duration_glyphs_cover_the_table():
    assert duration_glyph(quarter) == "♩"
    assert duration_glyph(eighth) == "♪"
    assert duration_glyph(ClockDuration.from_seconds(1)) is None


def test_html_text_is_escaped():
    assert escape("Tom & Jerry <3") == "Tom &amp; Jerry &lt;3"
    block = sync_block(
        "0", "Tom & Jerry", "<cue>", bar_color="#b0b0b0", bar_width=4, horizontal=True
    )
    assert "Tom &amp; Jerry" in block and "&lt;cue&gt;" in block
    title = title_block(Score(title="R&B"), "#303030")
    assert "R&amp;B" in title


def test_sync_blocks_have_the_same_skeleton_in_both_orientations():
    across = sync_block(
        "00:00:05.0000", None, None, bar_color="#abcdef", bar_width=3, horizontal=True
    )
    down = sync_block(
        "00:00:05.0000", None, None, bar_color="#abcdef", bar_width=3, horizontal=False
    )
    assert is_html_label(across) and is_html_label(down)
    assert 'PORT="bar" COLSPAN="2" HEIGHT="3" BGCOLOR="#abcdef"' in across
    assert 'PORT="bar" ROWSPAN="3" WIDTH="3" BGCOLOR="#abcdef"' in down
    assert across.count("<TR>") == 4 and down.count("<TR>") == 3
    head = sync_block(
        "Reel 1", None, None, bar_color="#abcdef", bar_width=3, horizontal=True, dot=False
    )
    assert "●" not in head and "Reel 1" in head
    empty = sync_block("", None, None, bar_color="#abcdef", bar_width=3, horizontal=True, dot=False)
    assert "FONT" not in empty


def test_the_title_block_lists_every_set_field():
    score = Score(
        title="Sonata",
        subtitle="in C",
        composer="A. Composer",
        lyricist="A. Poet",
        arranger="A. Arranger",
        opus="Op. 3",
        dedication="for B",
    )
    block = title_block(score, "#303030")
    for text in (
        "<B>Sonata</B>",
        "in C",
        "music: A. Composer",
        "lyrics: A. Poet",
        "arranged: A. Arranger",
        "Op. 3",
        "for B",
    ):
        assert text in block
    assert title_block(Score(), "#303030").count("<TR>") == 1


@pytest.mark.parametrize("syllable", parse_lyrics("Al-le-lu-ia"))
def test_every_syllable_label_is_plain_text(syllable):
    assert isinstance(syllable, LyricSyllable)
    assert not is_html_label(default_label(syllable))
