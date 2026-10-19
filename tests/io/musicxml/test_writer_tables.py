"""The reader's tables backwards, exhaustively: every symbol the reader can
make from MusicXML is written by the writer as something the reader makes
back into that same symbol. Marks (ready-made and minted), spanners, chord
kinds, clefs, bar lines, keys and modes, brackets, note values, meters and
tempos each go through `write` and `read` and are compared one by one.
"""

from __future__ import annotations

import io
import warnings

import pytest

from openmusickit.errors import OmkWarning
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.musicxml import read, tables, write
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import ClefEvent, MeterEvent, TempoEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.objects.part import Part, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bracket_shape import BracketShape
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.temporal import symbols as temporal
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.time_signature import TimeSignature
from openmusickit.systems.wsmn.tonal.chords import Chord
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import AttachmentMode, Mark, MarkType
from openmusickit.values.time.clock_time import Tempo
from openmusickit.values.time.duration import GraceDuration, TemporalRatio
from tests.domains import distinct, symbols_of
from tests.io.musicxml.documents import doc, main_line, notes_of, read_bytes
from tests.strategies import DURATION_SYMBOLS

C4, E4, G4 = TonalVector((0, 0, 0)), TonalVector((2, 4, 0)), TonalVector((4, 7, 0))
C, D, G, B_FLAT = (TonalVector(t) for t in ((0, 0), (1, 2), (4, 7), (6, 10)))


def scored(line: list[SequentialEvent]) -> OmkGraph:
    """One Part over `line` in a Score."""
    graph = OmkGraph(GraphMeta())
    graph.add_line(line)
    score, part = Score(), Part(name="P")
    graph.add_line_to_score(score, line[0])
    graph.add_part_to_score(score, part)
    graph.add_stint(part, Stint(), line[0])
    return graph


def bars_of(events: list[SequentialEvent]) -> list[SequentialEvent]:
    """`events` one to a bar, with no meter: each division ends its bar."""
    line: list[SequentialEvent] = [MeterEvent(meter=temporal.four_four)]
    for event in events:
        line += [event, DivisionEvent()]
    return line


def back(graph: OmkGraph) -> OmkGraph:
    """`graph` written and read again."""
    out = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        write(graph, out)
        return read(io.BytesIO(out.getvalue()))


def whole(tone: TonalVector = C4) -> NoteEvent:
    return NoteEvent(tones={tone}, duration=temporal.whole)


def marks_on(graph: OmkGraph, event: SequentialEvent) -> list[Mark]:
    return [m.mark for m in graph._graph.predecessors(event, Marking, EdgeType.MARKS)]


# --- marks ----------------------------------------------------------------------------------

TABLES = (
    tables.ARTICULATIONS, tables.BREATH_MARKS, tables.ORNAMENTS, tables.TECHNICAL,
    tables.FINGERINGS, tables.STRINGS, tables.PLUCKS, tables.HANDBELLS, tables.HARMON_MUTES,
    tables.HOLES, tables.FERMATAS, tables.ARPEGGIOS, tables.DYNAMICS,
)  # fmt: skip
TABLE_MARKS = list(
    {
        id(mark): mark
        for table in TABLES
        for mark in table.values()
        if mark.attachment_mode is not AttachmentMode.SPAN
    }.values()
) + [scoring.non_arpeggio, scoring.laissez_vibrer]


def test_every_mark_in_the_tables_is_written_back_as_itself():
    notes = [whole() for _ in TABLE_MARKS]
    graph = scored(bars_of(notes))
    for note_event, mark in zip(notes, TABLE_MARKS, strict=True):
        graph.add_articulation(Marking(mark=mark), note_event)
    again = back(graph)
    written = notes_of(again, main_line(again))
    assert [marks_on(again, n) for n in written] == [[mark] for mark in TABLE_MARKS]


MINTED = [
    (Mark(name="zing", kind=MarkType.ARTICULATION), {}),
    (Mark(name="zang", kind=MarkType.ORNAMENT), {}),
    (Mark(name="zong", kind=MarkType.TECHNIQUE), {}),
    (Mark(name="arrow", kind=MarkType.TECHNIQUE), {}),
    (Mark(name="fret 3", kind=MarkType.FINGERING), {}),
    (Mark(name="string 7", kind=MarkType.FINGERING), {}),
    (Mark(name="pluck x", kind=MarkType.FINGERING), {}),
    (Mark(name="fingering 1-2", kind=MarkType.FINGERING), {"fingering": "1-2"}),
    (Mark(name="fermata (wide)", kind=MarkType.PHRASING), {}),
    (Mark(name="sfffz", kind=MarkType.DYNAMIC), {}),
    (Mark(name="calando", kind=MarkType.EXPRESSION), {"element": "other-dynamics"}),
    (Mark(name="con fuoco e brio", kind=MarkType.EXPRESSION), {"element": "words"}),
    (Mark(name="B", kind=MarkType.REHEARSAL), {}),
    (Mark(name="snap", kind=MarkType.OTHER), {"element": "other-notation"}),
]


def test_every_kind_of_mark_the_reader_mints_is_written_back_as_itself():
    notes = [whole() for _ in MINTED]
    graph = scored(bars_of(notes))
    for note_event, (mark, meta) in zip(notes, MINTED, strict=True):
        marking = Marking(mark=mark)
        marking.meta["musicxml"] = dict(meta)
        graph.add_articulation(marking, note_event)
    again = back(graph)
    written = notes_of(again, main_line(again))
    assert [marks_on(again, n) for n in written] == [[mark] for mark, _ in MINTED]


def test_marks_on_bar_lines_are_written_in_the_bar_line():
    first, second = DivisionEvent(), DivisionEvent(shape=scoring.final_bar)
    graph = scored([MeterEvent(meter=temporal.four_four), whole(), first, whole(), second])
    for mark, division in ((scoring.segno, first), (scoring.short_fermata, second)):
        graph.add_articulation(Marking(mark=mark), division)
    again = back(graph)
    divisions = [e for e in again.walk_line(main_line(again)) if isinstance(e, DivisionEvent)]
    assert [marks_on(again, d) for d in divisions] == [[scoring.segno], [scoring.short_fermata]]


# --- spanners -------------------------------------------------------------------------------

SPANS = [
    *tables.WEDGES.values(),
    *tables.PEDALS.values(),
    *tables.OCTAVE_SHIFTS.values(),
    *tables.NOTATION_SPANS.values(),
    scoring.wavy_line,
    scoring.una_corda,
    scoring.cresc,
    Mark(name="poco a poco", kind=MarkType.EXPRESSION, attachment_mode=AttachmentMode.SPAN),
    Mark(
        name="octave shift up 22", kind=MarkType.TRANSPOSITION, attachment_mode=AttachmentMode.SPAN
    ),
]


@pytest.mark.parametrize("mark", SPANS, ids=lambda mark: mark.name)
@pytest.mark.parametrize("closed", [True, False], ids=["closed", "open"])
def test_every_kind_of_spanner_is_written_back_as_itself(mark, closed):
    notes = [whole(tone) for tone in (C4, E4, G4)]
    graph = scored(bars_of(notes))
    graph.add_spanner(MarkSpanner(mark=mark), notes[0], notes[1] if closed else None)
    again = back(graph)
    (spanner,) = again.nodes(MarkSpanner)
    written = notes_of(again, main_line(again))
    assert spanner.mark == mark
    assert again.spanner_start(spanner) is written[0]
    assert again.spanner_end(spanner) is (written[1] if closed else None)


def test_a_bracket_line_with_no_words_is_written_back_as_itself():
    notes = [whole(), whole()]
    graph = scored(bars_of(notes))
    spanner = MarkSpanner(
        mark=Mark(name="bracket", kind=MarkType.OTHER, attachment_mode=AttachmentMode.SPAN)
    )
    spanner.meta["musicxml"] = {"element": "bracket"}
    graph.add_spanner(spanner, notes[0], notes[1])
    again = back(graph)
    (back_spanner,) = again.nodes(MarkSpanner)
    assert (
        back_spanner.mark == spanner.mark and back_spanner.meta["musicxml"]["element"] == "bracket"
    )


# --- chord symbols --------------------------------------------------------------------------


def chords_written_back(chords: list) -> list:
    notes = [whole() for _ in chords]
    graph = scored(bars_of(notes))
    events = [ChordEvent(chord=chord) for chord in chords]
    graph.add_line(events)
    graph.add_line_to_score(next(graph.nodes(Score)), events[0])
    for note_event, event in zip(notes, events, strict=True):
        graph.add_simultaneous(note_event, event)
    again = back(graph)
    (head,) = (h for h in again.score_lines(next(again.nodes(Score))) if isinstance(h, ChordEvent))
    return [event.chord for event in again.walk_line(head)]


def test_every_chord_kind_is_written_back_as_itself():
    chords = [root(kind) for kind in tables.KINDS.values() for root in (C, B_FLAT)]
    assert chords_written_back(chords) == chords


def test_inversions_and_slash_chords_are_written_back_as_themselves():
    chords = [
        C(tables.KINDS["major"]).inversion(G),
        D(tables.KINDS["minor-seventh"]).inversion(1),
        Chord(C, list(C(tables.KINDS["major"])), bass=B_FLAT),
    ]
    assert chords_written_back(chords) == chords


def test_chords_with_added_altered_and_missing_degrees_are_written_back_as_themselves():
    major, dominant = list(C(tables.KINDS["major"])), list(G(tables.KINDS["dominant"]))
    chords = [
        Chord(C, [*major, D]),  # add 9
        Chord(G, [dominant[0], dominant[1], TonalVector((1, 1)), dominant[3]]),  # 7♭5
        Chord(C, [major[0], major[1]]),  # no fifth
        Chord(C, [major[0], TonalVector((3, 5)), major[2]]),  # a sus4 spelled as an altered third
    ]
    assert chords_written_back(chords) == chords


# --- attributes, bar lines, brackets --------------------------------------------------------

CLEFS = (
    [StaffClef(ClefSign.G, line) for line in (1, 2)]
    + [StaffClef(ClefSign.G, 2, octave_change=change) for change in (-1, 1, -2)]
    + [StaffClef(ClefSign.F, line) for line in (3, 4, 5)]
    + [StaffClef(ClefSign.F, 4, octave_change=-1)]
    + [StaffClef(ClefSign.C, line) for line in (1, 2, 3, 4, 5)]
    + [StaffClef(sign) for sign in (ClefSign.PERCUSSION, ClefSign.TAB, ClefSign.NONE)]
)


def test_every_clef_is_written_back_as_itself():
    line: list[SequentialEvent] = [MeterEvent(meter=temporal.four_four)]
    for clef in CLEFS:
        line += [ClefEvent(clef=clef), whole(), DivisionEvent()]
    again = back(scored(line))
    assert [e.clef for e in again.walk_line(main_line(again)) if isinstance(e, ClefEvent)] == CLEFS


SHAPES = [
    *tables.BAR_STYLES.values(),
    scoring.start_repeat,
    scoring.end_repeat,
    scoring.double_repeat,
]


def test_every_bar_line_shape_is_written_back_as_itself():
    line: list[SequentialEvent] = [MeterEvent(meter=temporal.four_four)]
    for shape in SHAPES:
        line += [whole(), DivisionEvent(shape=shape)]
    line += [whole(), DivisionEvent()]
    again = back(scored(line))
    shapes = [e.shape for e in again.walk_line(main_line(again)) if isinstance(e, DivisionEvent)]
    assert shapes == [*SHAPES, None]


def test_a_start_repeat_at_the_head_is_written_back_as_itself():
    graph = scored([MeterEvent(meter=temporal.four_four), DivisionEvent(shape=scoring.start_repeat),
                    whole(), DivisionEvent(shape=scoring.end_repeat)])  # fmt: skip
    again = back(graph)
    assert again.is_equivalent(graph)


def test_every_key_and_mode_is_written_back_as_itself():
    for fifths in range(-7, 8):
        for mode in [None, *tables.MODES]:
            mode_xml = f"<mode>{mode}</mode>" if mode else ""
            attributes = f"<key><fifths>{fifths}</fifths>{mode_xml}</key>"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OmkWarning)
                graph = read_bytes(doc("<note><rest/><duration>16</duration><voice>1</voice></note>",
                                       attributes=attributes))  # fmt: skip
            assert back(graph).is_equivalent(graph), (fifths, mode)


SHAPES_OF_BRACKETS = [None] + [
    BracketShape(symbol=symbol, bar_lines=bar_lines)
    for symbol in tables.GROUP_SYMBOLS.values()
    for bar_lines in tables.GROUP_BARLINES.values()
]


@pytest.mark.parametrize("shape", SHAPES_OF_BRACKETS, ids=repr)
def test_every_bracket_is_written_back_as_itself(shape):
    graph = OmkGraph(GraphMeta())
    score = Score()
    parts = []
    for name in ("Upper", "Lower"):
        line = bars_of([whole()])
        graph.add_line(line)
        part = Part(name=name)
        graph.add_line_to_score(score, line[0])
        graph.add_part_to_score(score, part)
        graph.add_stint(part, Stint(), line[0])
        parts.append(part)
    graph.add_stack(parts)
    graph.add_stack_group(StackGroup(name="Pair", abbreviation="Pr.", shape=shape), *parts)
    again = back(graph)
    (group,) = again.nodes(StackGroup)
    assert (group.name, group.abbreviation, group.shape) == ("Pair", "Pr.", shape)


# --- durations, meters, tempos --------------------------------------------------------------

PLAIN_VALUES = [
    MetricalDuration(numerator, denominator, dots)
    for numerator, denominator in tables.NOTE_TYPES.values()
    for dots in range(4)
    if (numerator, denominator) != (1, 1024) or dots == 0
]


def spelling(duration) -> tuple:
    ratio = getattr(duration, "ratio", None)
    return (duration.numerator, duration.denominator, duration.dots, ratio and ratio.multiplier)


@pytest.mark.parametrize("values", [PLAIN_VALUES, DURATION_SYMBOLS], ids=["note types", "symbols"])
def test_every_note_value_is_written_back_with_its_spelling(values):
    notes = [NoteEvent(tones={C4}, duration=value) for value in values]
    line: list[SequentialEvent] = []
    for note_event in notes:
        line += [note_event, DivisionEvent()]
    again = back(scored(line))
    written = notes_of(again, main_line(again))
    assert [spelling(n.duration) for n in written] == [spelling(v) for v in values]


def test_every_rest_value_is_written_back_with_its_length():
    rests = [Rest(value) for value in DURATION_SYMBOLS]
    line: list[SequentialEvent] = []
    for rest in rests:
        line += [rest, DivisionEvent()]
    again = back(scored(line))
    assert [n.duration.rational_length for n in notes_of(again, main_line(again))] == [
        value.rational_length for value in DURATION_SYMBOLS
    ]


def test_every_grace_note_is_written_back_as_itself():
    graces = list(distinct(symbols_of(temporal, GraceDuration)).values())
    events = [e for grace in graces for e in (NoteEvent(tones={E4}, duration=grace), whole())]
    again = back(scored([MeterEvent(meter=temporal.four_four), *events, DivisionEvent()]))
    written = [
        n.duration
        for n in notes_of(again, main_line(again))
        if isinstance(n.duration, GraceDuration)
    ]
    assert [(g.nominal, g.on_beat) for g in written] == [(g.nominal, g.on_beat) for g in graces]


METERS = list(distinct(symbols_of(temporal, TimeSignature)).values())


def test_every_time_signature_is_written_back_with_its_spelling():
    line: list[SequentialEvent] = []
    for meter in METERS:
        bar = MetricalDuration.from_length(meter.rational_length)
        line += [MeterEvent(meter=meter), Rest(bar), DivisionEvent()]  # a bar's rest in each
    again = back(scored(line))
    written = [e.meter for e in again.walk_line(main_line(again)) if isinstance(e, MeterEvent)]
    assert [(m.rational_length, m.presentation) for m in written] == [
        (m.rational_length, m.presentation) for m in METERS
    ]


TEMPOS = [
    TempoEvent(tempo=Tempo(60, temporal.quarter)),
    TempoEvent(tempo=Tempo(72, temporal.dotted_quarter)),
    TempoEvent(tempo=Tempo(40, temporal.half)),
    TempoEvent(tempo=TemporalRatio(temporal.quarter, temporal.dotted_quarter)),  # a modulation
    TempoEvent(term=scoring.andante),
    TempoEvent(tempo=Tempo(132, temporal.quarter), term=scoring.allegro),
]


def test_every_kind_of_tempo_is_written_back_as_itself():
    line: list[SequentialEvent] = [MeterEvent(meter=temporal.four_four)]
    for tempo in TEMPOS:
        line += [tempo, whole(), DivisionEvent()]
    again = back(scored(line))
    written = [e for e in again.walk_line(main_line(again)) if isinstance(e, TempoEvent)]
    assert [(t.tempo, t.term) for t in written] == [(t.tempo, t.term) for t in TEMPOS]


def test_a_hidden_metronome_beside_printed_words_stays_hidden():
    tempo = TempoEvent(tempo=Tempo(96, temporal.quarter), term=scoring.a_tempo)
    tempo.meta["musicxml"] = {"tempo_hidden": True}
    again = back(scored([MeterEvent(meter=temporal.four_four), tempo, whole(), DivisionEvent()]))
    (written,) = again.nodes(TempoEvent)
    assert (written.tempo, written.term) == (tempo.tempo, tempo.term)
    assert written.meta["musicxml"].get("tempo_hidden") and not written.meta["musicxml"].get(
        "term_hidden"
    )


def test_a_transposition_of_every_kind_is_written_back_as_itself():
    for interval in [(1, 2, 0), (2, 3, 0), (4, 7, 0), (5, 9, 0), (5, 9, 1), (0, 0, 1), (0, 0, -1),
                     (6, 11, -1), (3, 6, 0), (1, 1, 0)]:  # fmt: skip
        transposition = TonalVector(interval)
        graph = scored(bars_of([whole(tone) for tone in (C4, E4, G4)]))
        (stint,) = graph.stints(next(graph.nodes(Part)))
        stint.transposition = transposition
        again = back(graph)
        assert again.is_equivalent(graph), interval
        (back_stint,) = again.stints(next(again.nodes(Part)))
        assert back_stint.transposition == transposition
