"""The MusicXML writer (`_plans/musicxml.md` §6).

First, the reader's rules in reverse: for one small document per rule,
what the reader builds is written and read back as the same music
(`is_equivalent`), and writing it warns about nothing.
Then the writer's own rules, on graphs built by hand:
what it refuses, the bar lines a meter places, notes cut at bar lines,
transposition, part order and brackets, chord lines,
and the warnings for what it leaves out.
"""

from __future__ import annotations

import io
import warnings
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest

from openmusickit.errors import OmkWarning, UnexportableError
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.musicxml import read, write
from openmusickit.io.musicxml.writer import document
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import MeterEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.objects.part import Part, StackGroup, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.temporal.metrical_duration import TiedDuration
from openmusickit.systems.wsmn.temporal.symbols import (
    eighth,
    four_four,
    half,
    quarter,
    three_four,
    two_four,
    whole,
)
from openmusickit.systems.wsmn.temporal.wsmn import WSMN_TEMPORAL
from openmusickit.systems.wsmn.tonal.symbols import C, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.clock_time import ClockDuration
from openmusickit.values.time.duration import ZeroDuration
from tests.io.musicxml.documents import (
    DEFAULT_ATTRIBUTES,
    direction,
    doc,
    lyric,
    main_line,
    measure,
    names_of,
    note,
    notes_of,
    read_bytes,
    rest,
    tuplet_of,
)
from tests.io.musicxml.test_reader import (
    BACKUP,
    BAR,
    KIT_ATTRIBUTES,
    KIT_INSTRUMENTS,
    TWO_STAVES,
    Q,
    h,
    harmony,
    left_barline,
    q,
    right_barline,
    stroke,
    w,
)

C4, D4, E4, F4, G4 = (
    TonalVector(v) for v in ((0, 0, 0), (1, 2, 0), (2, 4, 0), (3, 5, 0), (4, 7, 0))
)

PERCENT = (
    '<attributes><measure-style><measure-repeat type="start">1</measure-repeat>'
    "</measure-style></attributes>"
)
PERCENT_STOP = (
    '<attributes><measure-style><measure-repeat type="stop"/></measure-style></attributes>'
)
MULTIPLE_REST = (
    "<attributes><measure-style><multiple-rest>2</multiple-rest></measure-style></attributes>"
)
ELISION = (
    '<lyric number="1"><syllabic>single</syllabic><text>the</text>'
    "<elision> </elision><syllabic>single</syllabic><text>a</text></lyric>"
)
DEGREE = (
    "<degree><degree-value>9</degree-value><degree-alter>0</degree-alter>"
    "<degree-type>add</degree-type></degree>"
)
TRANSPOSE = "<transpose><diatonic>-2</diatonic><chromatic>-3</chromatic></transpose>"
MINOR_KEY = (
    "<key><fifths>-3</fifths><mode>minor</mode></key>"
    "<time><beats>4</beats><beat-type>4</beat-type></time>"
)
NOTATIONS = "<notations><articulations><staccato/><accent/></articulations><fermata/></notations>"


def triplet(step: str) -> str:
    """An eighth of an eighth-note triplet, at six divisions per quarter."""
    return note(step, 4, 2, "eighth", time_modification=tuplet_of(3, 2))


def fingered(step: str, finger: int, chord: bool = False) -> str:
    fingering = f"<notations><technical><fingering>{finger}</fingering></technical></notations>"
    return h(step, chord=chord, extra=fingering)


# One document per reader rule (the reader tests' documents), as `doc` arguments.
DOCUMENTS: dict[str, tuple[tuple, dict]] = {
    "second voice": (
        (q("C") + q("D") + q("E") + q("F") + BACKUP + h("A", 3, voice=2) + h("B", 3, voice=2),),
        {},
    ),
    "voice reused": (
        (
            q("C") + q("D") + h("E") + BACKUP + h("A", 3, voice=2) + h("B", 3, voice=2),
            w("F"),
            w("G") + BACKUP + w("A", 3, voice=2),
        ),
        {},
    ),
    "run from mid-event": (
        (
            h("C")
            + h("D")
            + BACKUP
            + f"<forward><duration>{Q}</duration><voice>2</voice></forward>"
            + q("A", 3, voice=2)
            + h("B", 3, voice=2),
        ),
        {},
    ),  # fmt: skip
    "forward in the main voice": (
        (q("C") + f"<forward><duration>{2 * Q}</duration></forward>" + q("D"),),
        {},
    ),
    "two staves": (
        (h("C", staff=1) + h("D", staff=1) + BACKUP + w("C", 3, staff=2, voice=5),),
        {"attributes": TWO_STAVES},
    ),
    "chord": ((h("C") + h("E", chord=True) + h("G", chord=True) + h("D"),), {}),
    "partial chord tie": (
        (
            q("C")
            + q("E", chord=True, tie="start")
            + q("D")
            + q("E", chord=True, tie="stop")
            + h("G"),
        ),
        {},
    ),
    "larger class stays": (
        (
            q("C")
            + q("E", chord=True)
            + q("G", chord=True, tie="start")
            + q("D")
            + q("F", chord=True)
            + q("G", chord=True, tie="stop")
            + h("A"),
        ),
        {},
    ),  # fmt: skip
    "fingering per tone": ((fingered("C", 1) + fingered("G", 5, chord=True) + h("D"),), {}),
    "tie across a bar line": ((h("C") + h("D", tie="start"), h("D", tie="stop") + h("E")), {}),
    "graces": (
        (q("C", grace=True) + q("D") + q("E", grace="slash") + q("F") + h("G"),),
        {},
    ),
    "triplets": (
        (
            triplet("C")
            + triplet("D")
            + triplet("E")
            + note("F", 4, 6, "quarter")
            + note("G", 4, 12, "half"),
        ),
        {"divisions": 6},
    ),  # fmt: skip
    "whole-measure rest": ((rest(BAR, whole_measure=True),), {}),
    "hidden rest": ((h("C") + rest(2 * Q, "half", attrs='print-object="no"'),), {}),
    "slash notes": (
        (q("B", notehead="slash") + q("B", notehead="slash") + h("B", notehead="slash"),),
        {},
    ),
    "pickup": ((measure(q("G"), number="0", implicit="yes"), q("C") + q("D") + h("E")), {}),
    "split measure": ((w("C"), h("D"), measure(h("E"), number="X2", implicit="yes"), w("F")), {}),
    "bar styles": (
        (
            h("C") + h("D") + right_barline("<bar-style>light-light</bar-style>"),
            h("E") + h("F") + right_barline("<bar-style>light-heavy</bar-style>"),
        ),
        {},
    ),
    "repeats": (
        (
            left_barline('<repeat direction="forward"/>')
            + w("C")
            + right_barline('<repeat direction="backward"/>'),
            left_barline('<repeat direction="forward"/>')
            + w("E")
            + right_barline('<bar-style>light-heavy</bar-style><repeat direction="backward"/>'),
        ),
        {},
    ),  # fmt: skip
    "endings": (
        (
            w("C"),
            left_barline('<ending number="1" type="start"/>')
            + w("E")
            + right_barline('<ending number="1" type="stop"/><repeat direction="backward"/>'),
            left_barline('<ending number="2" type="start">2.</ending>')
            + w("G")
            + right_barline('<ending number="2" type="discontinue"/>'),
        ),
        {},
    ),  # fmt: skip
    "measure repeat": ((w("C"), PERCENT + w("C"), w("C"), PERCENT_STOP + w("E")), {}),
    "multiple rest": (
        (MULTIPLE_REST + rest(BAR, whole_measure=True), rest(BAR, whole_measure=True), w("C")),
        {},
    ),
    "key with a mode": ((w("C"),), {"attributes": MINOR_KEY}),
    "cut time": (
        (w("C"),),
        {"attributes": '<time symbol="cut"><beats>2</beats><beat-type>2</beat-type></time>'},
    ),
    "additive meter": (
        (h("C") + q("D") + h("E"),),
        {"attributes": "<time><beats>3+2</beats><beat-type>4</beat-type></time>"},
    ),
    "clef change mid-measure": (
        (
            h("C")
            + "<attributes><clef><sign>F</sign><line>4</line></clef></attributes>"
            + h("D", 3),
            w("E", 3),
        ),
        {},
    ),  # fmt: skip
    "dynamic": ((q("C") + direction("<dynamics><p/></dynamics>") + q("D") + h("E"),), {}),
    "direction inside a note": (
        (h("C") + direction("<dynamics><f/></dynamics>", offset=Q) + h("D"),),
        {},
    ),
    "wedge": (
        (
            q("C")
            + direction('<wedge type="crescendo"/>')
            + q("D")
            + q("E")
            + direction('<wedge type="stop"/>')
            + q("F"),
        ),
        {},
    ),  # fmt: skip
    "open pedal": ((h("C") + direction('<pedal type="start"/>') + h("D"), w("E")), {}),
    "pedal change": (
        (
            direction('<pedal type="start"/>')
            + h("C")
            + direction('<pedal type="change"/>')
            + h("D")
            + direction('<pedal type="stop"/>'),
        ),
        {},
    ),  # fmt: skip
    "tempo": (
        (
            direction(
                "<words>Allegro</words>",
                "<metronome><beat-unit>quarter</beat-unit><per-minute>120</per-minute></metronome>",
            )
            + w("C"),
        ),
        {},
    ),
    "gradual tempo": ((h("C") + direction("<words>poco rit.</words>") + h("D"),), {}),
    "ready-made words": ((direction("<words>dolce</words>") + w("C"),), {}),
    "una corda": (
        (
            direction("<words>una corda</words>") + w("C"),
            w("E") + direction("<words>tre corde</words>"),
        ),
        {},
    ),
    "breath comma": ((h("C") + direction("<words>,</words>") + h("D"),), {}),
    "cresc with dashes": (
        (
            direction("<words>cresc.</words>", '<dashes type="start"/>')
            + h("C")
            + h("D")
            + direction('<dashes type="stop"/>'),
            w("E"),
        ),
        {},
    ),  # fmt: skip
    "rehearsal": ((direction("<rehearsal>A</rehearsal>") + w("C"),), {}),
    "segno on a bar line": ((w("C") + right_barline("<segno/>"), w("D")), {}),
    "octave shift": (
        (
            direction('<octave-shift type="down" size="8"/>')
            + h("C", 6)
            + h("D", 6)
            + direction('<octave-shift type="stop" size="8"/>'),
        ),
        {},
    ),  # fmt: skip
    "notations and a slur": (
        (
            q("C", extra=NOTATIONS)
            + q("D", extra='<notations><slur type="start" number="1"/></notations>')
            + q("E")
            + q(
                "F",
                extra='<notations><slur type="stop" number="1"/><ornaments><trill-mark/></ornaments></notations>',
            ),
        ),
        {},
    ),  # fmt: skip
    "two verses": (
        (
            q("C", extra=lyric("Al", "begin") + lyric("Sing", "single", 2))
            + q("D", extra=lyric("le", "middle") + lyric("to", "single", 2))
            + q("E", extra=lyric("lu", "middle") + lyric("Je", "begin", 2))
            + q("F", extra=lyric("ia", "end") + lyric("sus", "end", 2)),
        ),
        {},
    ),
    "melisma": ((h("C", extra=lyric("Ah", "single", extra="<extend/>")) + h("D"),), {}),
    "elision": ((h("C", extra=ELISION) + h("D", extra=lyric("men", "single")),), {}),
    "named verse": (
        (
            h("C", extra=lyric("Sing", "single", number="part1verse1"))
            + h("D", extra=lyric("on", "single", number="part1verse1")),
        ),
        {},
    ),
    "harmony": ((harmony("C", "major") + h("C") + harmony("G", "dominant") + h("D"),), {}),
    "slash chord": ((harmony("C", "major", "<bass><bass-step>G</bass-step></bass>") + w("C"),), {}),
    "degree": ((harmony("C", "major", DEGREE) + w("C"),), {}),
    "harmony offset": ((harmony("C", "major", offset=Q) + w("C"),), {}),
    "drum kit": (
        (
            stroke("F", 4, "P1-I36")
            + stroke("C", 5, "P1-I38")
            + stroke("F", 4, "P1-I36", 2 * Q, "half"),
            stroke("C", 5, "P1-I38", BAR, "whole"),
        ),
        {"attributes": KIT_ATTRIBUTES, "part_list_extra": KIT_INSTRUMENTS},
    ),
    "transposition": (
        (q("C", 5) + q("D", 5) + h("E", 5),),
        {"attributes": DEFAULT_ATTRIBUTES + TRANSPOSE},
    ),
    "two parts": (([w("C")], [w("E")]), {"parts": ("P1", "P2")}),
    "two parts with a pickup": (
        (
            [measure(q("G"), number="0", implicit="yes"), w("C")],
            [measure(q("B"), number="0", implicit="yes"), w("E")],
        ),
        {"parts": ("P1", "P2")},
    ),
}


def round_trip(graph: OmkGraph, **options) -> tuple[OmkGraph, list[str]]:
    """The graph read back from writing `graph`, and what writing it warned."""
    out = io.BytesIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        write(graph, out, **options)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        again = read(io.BytesIO(out.getvalue()))
    return again, [str(w.message) for w in caught]


def written(graph: OmkGraph, **options) -> tuple[ET.Element, list[str]]:
    """The document the writer makes of `graph`, and what it warned."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        root = document(graph, **options)
    return root, [str(w.message) for w in caught]


@pytest.mark.parametrize("name", list(DOCUMENTS))
def test_each_reader_rule_writes_back_as_the_same_music(name):
    args, kwargs = DOCUMENTS[name]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        graph = read_bytes(doc(*args, **kwargs))
    again, warned = round_trip(graph)
    assert warned == []
    assert graph.is_equivalent(again), graph.diff(again)


# --- the writer's own rules, on graphs built by hand ----------------------------------------


def scored(*lines: list[SequentialEvent], names: tuple[str, ...] = ()) -> tuple[OmkGraph, Score]:
    """A graph holding a Score of one single-staff Part per line, stacked in order."""
    graph = OmkGraph(GraphMeta())
    score = Score(title="Test")
    parts = []
    for index, line in enumerate(lines):
        graph.add_line(line)
        part = Part(name=names[index] if names else f"Part {index + 1}")
        graph.add_line_to_score(score, line[0])
        graph.add_part_to_score(score, part)
        graph.add_stint(part, Stint(), line[0])
        parts.append(part)
    graph.add_stack(parts)
    return graph, score


def notes(*tones_and_durations) -> list[NoteEvent]:
    return [NoteEvent(tones={tone}, duration=duration) for tone, duration in tones_and_durations]


def main_line_of(graph: OmkGraph, index: int = 0) -> SequentialEvent:
    return main_line(graph, index)


def test_no_score_several_scores_and_no_parts_are_refused():
    graph = OmkGraph(GraphMeta())
    with pytest.raises(UnexportableError, match="no Score"):
        document(graph)
    graph.add_node(Score(title="One"))
    with pytest.raises(UnexportableError, match="has no parts"):
        document(graph)
    graph.add_node(Score(title="Two"))
    with pytest.raises(UnexportableError, match="2 Scores"):
        document(graph)
    with pytest.raises(UnexportableError, match="not on the graph"):
        document(graph, score=Score(title="Elsewhere"))


def test_the_score_to_write_can_be_chosen():
    graph, score = scored([MeterEvent(meter=four_four), *notes((C4, whole)), DivisionEvent()])
    graph.add_node(Score(title="An empty sketch"))
    again, warned = round_trip(graph, score=score)
    assert warned == []
    assert next(again.nodes(Score)).title == "Test"


def test_score_fields_are_the_header():
    graph, score = scored([MeterEvent(meter=four_four), *notes((C4, whole))])
    score.composer, score.lyricist, score.arranger = "Croft", "Watts", "Someone"
    score.copyright, score.opus = "Public domain\nAll yours", "Op. 1"
    again, _ = round_trip(graph)
    back = next(again.nodes(Score))
    assert (back.title, back.composer, back.lyricist, back.arranger) == (
        "Test", "Croft", "Watts", "Someone",
    )  # fmt: skip
    assert (back.copyright, back.opus) == ("Public domain\nAll yours", "Op. 1")


def test_a_meter_places_the_bar_lines_of_a_line_with_none_and_warns():
    graph, _ = scored(
        [MeterEvent(meter=two_four), *notes((C4, half), (D4, quarter), (E4, quarter))]
    )
    again, warned = round_trip(graph)
    assert warned == ["part 'Part 1' has no bar lines; its meter places them"]
    kinds = [type(e).__name__ for e in again.walk_line(main_line_of(again))]
    assert kinds == [
        "MeterEvent",
        "NoteEvent",
        "DivisionEvent",
        "NoteEvent",
        "NoteEvent",
        "DivisionEvent",
    ]


def test_bar_lines_left_where_the_meter_would_not_put_them_are_kept():
    pickup, end = DivisionEvent(), DivisionEvent(shape=scoring.final_bar)
    line = [MeterEvent(meter=two_four), *notes((G4, quarter)), pickup,
            *notes((C4, half), (D4, half), (E4, quarter)), end]  # fmt: skip
    graph, _ = scored(line)
    again, warned = round_trip(graph)
    assert warned == []
    divisions = [e for e in again.walk_line(main_line_of(again)) if isinstance(e, DivisionEvent)]
    assert len(divisions) == 4 and divisions[-1].shape == scoring.final_bar
    onsets = again.onsets(main_line_of(again))
    assert [onsets[d.id].rational_length for d in divisions] == [
        Fraction(1, 4), Fraction(3, 4), Fraction(5, 4), Fraction(3, 2),
    ]  # fmt: skip


def test_a_note_across_a_bar_line_is_split_and_tied():
    graph, _ = scored([MeterEvent(meter=three_four), *notes((C4, half), (D4, half), (E4, half))])
    again, warned = round_trip(graph)
    assert "1 notes split at bar lines and tied (part 'Part 1')" in warned
    head = main_line_of(again)
    assert names_of(notes_of(again, head)) == ["C4", "D4", "D4", "E4"]
    (tie,) = (s for s in again.nodes(MarkSpanner) if s.mark is scoring.tie)
    assert names_of([again.spanner_start(tie), again.spanner_end(tie)]) == ["D4", "D4"]


def test_a_tied_duration_is_written_as_tied_notes():
    graph, _ = scored([MeterEvent(meter=four_four),
                       NoteEvent(tones={C4}, duration=TiedDuration([half, eighth])),
                       *notes((D4, eighth), (E4, quarter))])  # fmt: skip
    again, _ = round_trip(graph)
    head = main_line_of(again)
    assert [n.duration for n in notes_of(again, head)] == [half, eighth, eighth, quarter]
    assert sum(s.mark is scoring.tie for s in again.nodes(MarkSpanner)) == 1


def test_an_event_of_unknown_or_clock_duration_ends_what_is_written():
    for duration in (None, ClockDuration.from_seconds(1)):
        line = [MeterEvent(meter=four_four), *notes((C4, half)),
                NoteEvent(tones={D4}, duration=duration), *notes((E4, half))]  # fmt: skip
        graph, _ = scored(line)
        again, warned = round_trip(graph)
        assert any("which MusicXML cannot place" in m for m in warned)
        assert names_of(notes_of(again, main_line_of(again))) == ["C4"]


def test_unspecified_content_is_written_as_a_rest_with_a_warning():
    graph, _ = scored([MeterEvent(meter=two_four), NoteEvent(tones=set(), duration=half),
                       DivisionEvent()])  # fmt: skip
    again, warned = round_trip(graph)
    assert warned == ["1 events of unspecified content written as rests (part 'Part 1')"]
    assert names_of(notes_of(again, main_line_of(again))) == ["rest"]


def test_a_transposing_stint_writes_written_pitch_and_transpose():
    graph, score = scored([MeterEvent(meter=four_four), *notes((C4, whole)), DivisionEvent()])
    (stint,) = graph.stints(next(graph.score_parts(score)))
    stint.transposition = TonalVector((1, 2, 0))  # a clarinet in B♭: written a tone up
    root, warned = written(graph)
    assert warned == []
    assert ET.tostring(root.find(".//transpose"), encoding="unicode") == (
        "<transpose><diatonic>-1</diatonic><chromatic>-2</chromatic></transpose>"
    )
    assert root.find(".//note/pitch/step").text == "D"
    again, _ = round_trip(graph)
    (part,) = again.score_parts(next(again.nodes(Score)))
    assert next(again.stints(part)).transposition == TonalVector((1, 2, 0))
    assert names_of(notes_of(again, main_line_of(again))) == ["C4"]


def test_parts_are_written_in_stack_order_and_brackets_are_part_groups():
    lines = [
        [MeterEvent(meter=four_four), *notes((tone, whole)), DivisionEvent()]
        for tone in (C4, E4, G4)
    ]
    graph, score = scored(*lines, names=("Zither", "Viola", "Cello"))
    named = {part.name: part for part in graph.score_parts(score)}
    viola, cello = named["Viola"], named["Cello"]
    graph.add_stack_group(StackGroup(name="Strings", shape=scoring.bracket), viola, cello)
    root, warned = written(graph)
    assert warned == []
    assert [p.findtext("part-name") for p in root.iter("score-part")] == [
        "Zither",
        "Viola",
        "Cello",
    ]
    assert [
        (g.get("type"), g.findtext("group-name"), g.findtext("group-symbol"))
        for g in root.iter("part-group")
    ] == [
        ("start", "Strings", "bracket"),
        ("stop", None, None),
    ]


def test_parts_in_separate_stacks_are_written_stack_by_stack_with_a_warning():
    lines = [
        [MeterEvent(meter=four_four), *notes((tone, whole)), DivisionEvent()] for tone in (C4, E4)
    ]
    graph, score = scored(*lines, names=("Oboe", "Flute"))
    for part in graph.score_parts(score):
        graph.remove_from_stack(part)
    root, warned = written(graph)
    assert warned == [
        "the parts are not one stack; they are written stack by stack: ['Flute']; ['Oboe']"
    ]
    assert [p.findtext("part-name") for p in root.iter("score-part")] == ["Flute", "Oboe"]


def test_a_chord_line_pinned_to_a_part_is_its_harmony_and_omit_leaves_it_out():
    line = [MeterEvent(meter=four_four), *notes((C4, half), (G4, half)), DivisionEvent()]
    graph, score = scored(line)
    chords = [ChordEvent(chord=C(maj)), ChordEvent(chord=TonalVector((4, 7))(maj))]
    graph.add_line(chords)
    graph.add_line_to_score(score, chords[0])
    graph.add_simultaneous(line[1], chords[0])
    graph.add_simultaneous(line[2], chords[1])
    root, warned = written(graph)
    assert warned == []
    assert [h.findtext("root/root-step") for h in root.iter("harmony")] == ["C", "G"]
    again, _ = round_trip(graph)
    assert again.is_equivalent(graph)
    root, warned = written(graph, omit=[ChordEvent])
    assert list(root.iter("harmony")) == [] and warned == []


def test_omitted_marks_and_their_spanners_are_left_out():
    line = [MeterEvent(meter=four_four), *notes((C4, half), (G4, half)), DivisionEvent()]
    graph, _ = scored(line)
    graph.add_articulation(Marking(mark=scoring.staccato), line[1])
    graph.add_spanner(MarkSpanner(mark=scoring.slur), line[1], line[2])
    root, _ = written(graph, omit=[Marking, MarkSpanner])
    assert list(root.iter("notations")) == []
    root, _ = written(graph)
    assert [e.tag for e in root.iter() if e.tag in ("staccato", "slur")] == [
        "slur",
        "staccato",
        "slur",
    ]


def test_a_line_no_part_performs_is_left_out_with_a_warning():
    graph, score = scored([MeterEvent(meter=four_four), *notes((C4, whole)), DivisionEvent()])
    stray = notes((E4, whole))
    graph.add_line(stray)
    graph.add_line_to_score(score, stray[0])
    _, warned = written(graph)
    assert len(warned) == 1 and "is performed by no part; it is left out" in warned[0]


def test_a_part_with_no_music_is_an_empty_staff():
    graph, score = scored([MeterEvent(meter=two_four), *notes((C4, half)), DivisionEvent()])
    tacet = Part(name="Tacet")
    graph.add_part_to_score(score, tacet)
    graph.add_stacked(next(p for p in graph.score_parts(score) if p is not tacet), tacet)
    again, warned = round_trip(graph)
    assert warned == ["Part(name='Tacet') performs nothing; it is written as an empty staff"]
    tacet = next(p for p in again.score_parts(next(again.nodes(Score))) if p.name == "Tacet")
    start = again.spanner_start(next(again.stints(tacet)))
    assert names_of(notes_of(again, start)) == ["rest"]


def test_a_bar_grid_that_disagrees_with_the_durations_warns():
    lines = [
        [MeterEvent(meter=two_four), *notes((tone, half)), DivisionEvent()] for tone in (C4, E4)
    ]
    graph, score = scored(*lines)
    grid = SyncLine(temporal_system=WSMN_TEMPORAL, name="bars")
    graph.add_sync_line_to_score(score, grid)
    for line in lines:
        graph.sync_event(line[0], grid, ZeroDuration())
    graph.sync_event(lines[0][-1], grid, half)
    graph.sync_event(lines[1][-1], grid, whole)  # the second part's bar line is a bar late
    _, warned = written(graph)
    assert warned == [
        "part 'Part 2': the event at 1/2 whole notes is pinned at 1 on 'bars'; "
        "the part's durations are written"
    ]


def test_export_file_dispatches_on_the_suffix(tmp_path):
    graph, _ = scored([MeterEvent(meter=four_four), *notes((C4, whole)), DivisionEvent()])
    graph.export_file(tmp_path / "out.musicxml")
    assert (tmp_path / "out.musicxml").read_bytes().startswith(b"<?xml")
    graph.export_file(tmp_path / "out.mxl")
    assert (tmp_path / "out.mxl").read_bytes()[:2] == b"PK"
    with pytest.raises(ValueError, match="No writer for '.txt'"):
        graph.export_file(tmp_path / "out.txt")
    with pytest.raises(NotImplementedError):
        graph.export_file(tmp_path / "out.json")


def test_what_musicxml_cannot_carry_is_left_out_with_a_warning():
    line = [MeterEvent(meter=two_four), NoteEvent(tones={C}, duration=half), DivisionEvent()]
    graph, score = scored(line)
    graph.add_annotation(Marking(mark=scoring.staccato), line[1])
    again, warned = round_trip(graph)
    assert sorted(warned) == [
        "1 annotations, which MusicXML cannot carry, left out (part 'Part 1')",
        "1 tones MusicXML cannot carry (no octave, or not WSMN), left out (part 'Part 1')",
    ]
    assert names_of(notes_of(again, main_line_of(again))) == ["rest"]


def test_a_part_performing_part_of_a_line_writes_that_part():
    line = [MeterEvent(meter=two_four), *notes((C4, half)), DivisionEvent(), *notes((D4, half)),
            DivisionEvent()]  # fmt: skip
    graph, score = scored(line)
    viola = Part(name="Viola")
    graph.add_part_to_score(score, viola)
    graph.add_stint(viola, Stint(), line[0], line[2])  # the first bar only
    graph.add_stacked(next(p for p in graph.score_parts(score) if p is not viola), viola)
    again, warned = round_trip(graph)
    assert warned == [
        "Part(name='Viola') performs part of a line; that part is written",
        "part 'Viola' ends 1/2 whole notes before part 'Part 1'; its last measures are left empty",
    ]
    viola_again = next(p for p in again.score_parts(next(again.nodes(Score))) if p.name == "Viola")
    start = again.spanner_start(next(again.stints(viola_again)))
    assert names_of(notes_of(again, start)) == ["C4", ""]


def test_a_subtitle_and_a_dedication_are_credits():
    graph, score = scored([MeterEvent(meter=two_four), *notes((C4, half)), DivisionEvent()])
    score.subtitle, score.dedication = "for strings", "To M."
    root, _ = written(graph)
    assert [
        (c.findtext("credit-type"), c.findtext("credit-words")) for c in root.iter("credit")
    ] == [
        ("subtitle", "for strings"),
        ("dedication", "To M."),
    ]


def test_a_hidden_staff_of_a_group_is_numbered():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        graph = read_bytes(
            doc(
                h("C", staff=1) + h("D", staff=1) + BACKUP + w("C", 3, staff=2, voice=5),
                attributes=TWO_STAVES + '<staff-details number="2" print-object="no"/>',
            )
        )
    root, warned = written(graph)
    assert warned == []
    (details,) = root.iter("staff-details")
    assert details.attrib == {"print-object": "no", "number": "2"}


def test_chord_symbols_after_a_pinned_one_follow_its_duration():
    line = [MeterEvent(meter=four_four), *notes((C4, half), (G4, half)), DivisionEvent()]
    graph, score = scored(line)
    chords = [ChordEvent(chord=C(maj), duration=half), ChordEvent(chord=TonalVector((4, 7))(maj))]
    graph.add_line(chords)
    graph.add_line_to_score(score, chords[0])
    graph.add_simultaneous(line[1], chords[0])  # only the first is pinned
    root, warned = written(graph)
    assert warned == ["1 chord-symbol durations not written (a <harmony> has none)"]
    assert [h.findtext("root/root-step") for h in root.iter("harmony")] == ["C", "G"]
    orphan = ChordEvent(chord=C(maj))
    graph.add_line([orphan])
    graph.add_line_to_score(score, orphan)
    _, warned = written(graph)
    assert any("is pinned to nothing written; it is left out" in m for m in warned)
