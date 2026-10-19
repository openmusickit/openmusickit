"""The MusicXML reader, rule by rule (`_plans/musicxml.md` §5 and §9.2):
one small document per rule, read from memory,
with the shape of the graph and the exact warnings asserted.
"""

import io
import zipfile
from fractions import Fraction

import pytest

from openmusickit.errors import MusicXmlError
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.musicxml import read
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import (
    ClefEvent,
    ContextEvent,
    MeterEvent,
    ModalContextEvent,
    TempoEvent,
)
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import LineGroup, Part, PercussionPart, StackGroup
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.percussion.symbols import hit
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.systems.wsmn.scoring.bracket_shape import (
    BracketShape,
    BracketSymbol,
    GroupBarLines,
)
from openmusickit.systems.wsmn.scoring.staff_clef import ClefSign, StaffClef
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.temporal.symbols import (
    dotted_half,
    eighth,
    eighth_in_triplet,
    half,
    quarter,
    tuplet,
    whole,
)
from openmusickit.systems.wsmn.tonal.key import Key, KeySignature
from openmusickit.systems.wsmn.tonal.symbols import D
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.scoring.mark import MarkType
from openmusickit.values.time.clock_time import Tempo
from openmusickit.values.time.duration import GraceDuration
from tests.io.musicxml.documents import (
    DEFAULT_ATTRIBUTES,
    branches,
    direction,
    doc,
    events_of,
    kinds_of,
    lines_of_part,
    lyric,
    main_line,
    mark_names_on,
    markings_on,
    measure,
    names_of,
    note,
    notes_of,
    onset_of,
    onsets_of,
    parts_of,
    read_bytes,
    read_with_warnings,
    rest,
    score_of,
    spanners_named,
    stint_of,
    tuplet_of,
    xml_meta_of,
)

Q = 4  # divisions per quarter in the default document
BAR = 4 * Q
BACKUP = f"<backup><duration>{BAR}</duration></backup>"
CONTEXTS = ["ModalContextEvent", "MeterEvent", "ClefEvent"]

TWO_STAVES = (
    "<key><fifths>0</fifths></key>"
    "<time><beats>4</beats><beat-type>4</beat-type></time>"
    "<staves>2</staves>"
    '<clef number="1"><sign>G</sign><line>2</line></clef>'
    '<clef number="2"><sign>F</sign><line>4</line></clef>'
)


def q(step: str, octave: int = 4, **kwargs) -> str:
    return note(step, octave, Q, "quarter", **kwargs)


def h(step: str, octave: int = 4, **kwargs) -> str:
    return note(step, octave, 2 * Q, "half", **kwargs)


def w(step: str, octave: int = 4, **kwargs) -> str:
    return note(step, octave, 4 * Q, "whole", **kwargs)


def right_barline(inner: str) -> str:
    return f'<barline location="right">{inner}</barline>'


def left_barline(inner: str) -> str:
    return f'<barline location="left">{inner}</barline>'


# --- voices --------------------------------------------------------------------------


def test_a_one_bar_second_voice_is_a_branch_under_the_event_at_its_onset():
    bar_one = q("C") + q("D") + q("E") + q("F") + BACKUP + h("A", 3, voice=2) + h("B", 3, voice=2)
    graph, warned = read_with_warnings(bar_one, q("G") + h("A") + q("B"))
    assert warned == []
    head = main_line(graph)
    assert names_of(notes_of(graph, head)) == ["C4", "D4", "E4", "F4", "G4", "A4", "B4"]
    ((parent, branch),) = branches(graph, head)
    assert names_of([parent]) == ["C4"]
    assert names_of(notes_of(graph, branch)) == ["A3", "B3"]
    assert kinds_of(events_of(graph, branch)) == ["NoteEvent", "NoteEvent"]
    assert graph.get_edge(parent, branch, EdgeType.BRANCHES).displacement is None
    assert xml_meta_of(branch) == {"staff": 1, "voice": "2"}
    assert list(graph.score_lines(score_of(graph))) == [head]  # a branch is not a score line


def test_a_voice_number_reused_in_two_bars_gives_two_branches():
    plain = h("C") + h("D")
    second = BACKUP + h("A", 3, voice=2) + h("B", 3, voice=2)
    graph, warned = read_with_warnings(plain + second, plain, plain, plain, plain + second)
    assert warned == []
    head = main_line(graph)
    found = branches(graph, head)
    assert [names_of(notes_of(graph, branch)) for _, branch in found] == [
        ["A3", "B3"],
        ["A3", "B3"],
    ]
    assert [onset_of(graph, head, parent) for parent, _ in found] == [Fraction(0), Fraction(4)]


def test_a_forward_inside_a_second_voice_splits_the_run_into_two_branches():
    body = (
        q("C") + q("D") + q("E") + q("F") + BACKUP
        + q("A", 3, voice=2)
        + f"<forward><duration>{Q}</duration></forward>"
        + q("B", 3, voice=2) + q("C", 3, voice=2)
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    found = branches(graph, main_line(graph))
    assert [(names_of([p]), names_of(notes_of(graph, b))) for p, b in found] == [
        (["C4"], ["A3"]),
        (["E4"], ["B3", "C3"]),
    ]


def test_a_run_starting_mid_event_is_branched_with_a_displacement():
    body = (
        h("C") + h("D") + f"<backup><duration>{3 * Q}</duration></backup>"
        + q("A", 3, voice=2) + q("B", 3, voice=2) + q("C", 3, voice=2)
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    head = main_line(graph)
    ((parent, branch),) = branches(graph, head)
    assert names_of([parent]) == ["C4"]
    assert graph.get_edge(parent, branch, EdgeType.BRANCHES).displacement == quarter
    assert onset_of(graph, head, branch) == Fraction(1, 4)


def test_the_main_voice_of_staff_two_is_the_lowest_voice_number_there():
    body = (
        h("C", staff=1) + h("D", staff=1) + BACKUP
        + h("C", 3, voice=5, staff=2) + h("G", 2, voice=5, staff=2) + BACKUP
        + h("C", 2, voice=6, staff=2) + h("C", 2, voice=6, staff=2)
    )  # fmt: skip
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)
    assert warned == []
    lower = main_line(graph, staff=2)
    assert xml_meta_of(lower) == {"staff": 2, "voice": "5"}
    assert names_of(notes_of(graph, lower)) == ["C3", "G2"]
    ((parent, branch),) = branches(graph, lower)
    assert names_of([parent]) == ["C3"]
    assert xml_meta_of(branch) == {"staff": 2, "voice": "6"}


def test_a_forward_in_the_main_voice_is_unspecified_content():
    body = q("C") + f"<forward><duration>{Q}</duration></forward>" + q("E") + q("F")
    graph, warned = read_with_warnings(body)
    assert warned == []
    notes = notes_of(graph, main_line(graph))
    assert names_of(notes) == ["C4", "", "E4", "F4"]
    gap = notes[1]
    assert gap.tones == set() and not gap.is_rest
    assert gap.duration == quarter
    assert xml_meta_of(gap)["forward"] is True


# --- staves --------------------------------------------------------------------------


def test_two_staves_are_a_line_group_the_part_performs():
    body = (
        q("C", staff=1) + q("D", staff=1) + h("E", staff=1) + BACKUP
        + h("C", 3, voice=2, staff=2) + h("G", 2, voice=2, staff=2)
    )  # fmt: skip
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)
    assert warned == []
    (part,) = parts_of(graph)
    (group,) = graph.groups(part)
    assert group.name == "P1"
    members = list(graph.group_members(group))
    assert {xml_meta_of(m)["staff"] for m in members} == {1, 2}
    assert list(graph.stints(part)) == []
    assert names_of(notes_of(graph, main_line(graph, staff=1))) == ["C4", "D4", "E4"]
    assert names_of(notes_of(graph, main_line(graph, staff=2))) == ["C3", "G2"]
    assert {h.id for h in graph.score_lines(score_of(graph))} == {m.id for m in members}


def test_a_key_with_a_staff_number_lands_only_on_that_staff():
    attributes = TWO_STAVES.replace(
        "<key><fifths>0</fifths></key>",
        '<key number="2"><fifths>-3</fifths><mode>minor</mode></key>',
    )
    body = w("C", staff=1) + BACKUP + w("C", 3, voice=2, staff=2)
    graph, warned = read_with_warnings(body, attributes=attributes)
    assert warned == []
    assert kinds_of(events_of(graph, main_line(graph, staff=1))) == [
        "MeterEvent", "ClefEvent", "NoteEvent", "DivisionEvent",
    ]  # fmt: skip
    lower = events_of(graph, main_line(graph, staff=2))
    assert kinds_of(lower) == [
        "ModalContextEvent",
        "MeterEvent",
        "ClefEvent",
        "NoteEvent",
        "DivisionEvent",
    ]
    assert lower[0].modal_context.name == "C Minor"


def test_staves_written_after_key_still_gives_staff_two_its_contexts():
    body = w("C", staff=1) + BACKUP + w("C", 3, voice=2, staff=2)
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)  # <staves> after <key>, <time>
    assert warned == []
    for staff in (1, 2):
        events = events_of(graph, main_line(graph, staff=staff))
        assert kinds_of(events[:3]) == CONTEXTS
        assert events[0].modal_context.name == "no sharps or flats"
        assert events[1].meter.rational_length == Fraction(1)


# --- notes ---------------------------------------------------------------------------


def test_a_chord_merges_into_one_note_event():
    graph, warned = read_with_warnings(h("C") + h("E", chord=True) + h("G", chord=True) + h("D"))
    assert warned == []
    notes = notes_of(graph, main_line(graph))
    assert names_of(notes) == ["C4+E4+G4", "D4"]
    assert notes[0].duration == half
    assert branches(graph, main_line(graph)) == []


def test_a_partial_chord_tie_splits_the_chord_and_ties_the_branched_tone():
    body = (
        q("C") + q("E", chord=True, tie="start") + q("D") + q("E", chord=True, tie="stop") + h("G")
    )
    graph, warned = read_with_warnings(body)
    assert warned == []
    head = main_line(graph)
    assert names_of(notes_of(graph, head)) == ["C4", "D4", "G4"]  # the lowest tone stays
    found = branches(graph, head)
    assert [(names_of([p]), names_of(notes_of(graph, b))) for p, b in found] == [
        (["C4"], ["E4"]),
        (["D4"], ["E4"]),
    ]
    for parent, branch in found:
        assert graph.get_edge(parent, branch, EdgeType.BRANCHES).displacement is None
        assert branch.duration == quarter
    (tie,) = spanners_named(graph, "tie")
    assert graph.spanner_start(tie) is found[0][1]
    assert graph.spanner_end(tie) is found[1][1]


def test_the_larger_class_of_tones_stays_on_the_main_line():
    body = (
        q("C") + q("E", chord=True) + q("G", chord=True, tie="start")
        + q("D") + q("F", chord=True) + q("G", chord=True, tie="stop") + h("A")
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    head = main_line(graph)
    assert names_of(notes_of(graph, head)) == ["C4+E4", "D4+F4", "A4"]
    assert [names_of(notes_of(graph, b)) for _, b in branches(graph, head)] == [["G4"], ["G4"]]


def test_a_tie_across_a_bar_line_spans_the_division():
    graph, warned = read_with_warnings(h("C") + h("D", tie="start"), h("D", tie="stop") + h("E"))
    assert warned == []
    (tie,) = spanners_named(graph, "tie")
    start, end = graph.spanner_start(tie), graph.spanner_end(tie)
    assert names_of([start, end]) == ["D4", "D4"]
    assert kinds_of(graph.walk_span(start, end)) == ["NoteEvent", "DivisionEvent", "NoteEvent"]
    assert all(isinstance(n.duration, MetricalDuration) for n in notes_of(graph, main_line(graph)))


def test_a_tie_is_matched_by_pitch_across_voices():
    bar_two = h("D", voice=2, tie="stop") + h("E", voice=2) + BACKUP + w("C", 3, voice=1)
    graph, warned = read_with_warnings(h("C") + h("D", tie="start"), bar_two)
    assert warned == []
    (tie,) = spanners_named(graph, "tie")
    assert names_of([graph.spanner_start(tie), graph.spanner_end(tie)]) == ["D4", "D4"]
    assert onset_of(graph, main_line(graph), graph.spanner_end(tie)) == Fraction(1)


def test_a_grace_note_takes_no_time():
    body = note("D", 5, 0, "eighth", grace=True) + q("C", 5) + q("D", 5) + h("E", 5)
    graph, warned = read_with_warnings(body)
    assert warned == []
    head = main_line(graph)
    grace, principal = notes_of(graph, head)[:2]
    assert names_of([grace, principal]) == ["D5", "C5"]
    assert grace.duration == GraceDuration(eighth, on_beat=True)
    assert onset_of(graph, head, grace) == onset_of(graph, head, principal) == Fraction(0)
    assert onsets_of(graph, head)[-1] == Fraction(1)


def test_a_grace_with_a_slash_is_off_the_beat():
    body = note("D", 5, 0, "sixteenth", grace="slash") + w("C", 5)
    graph, warned = read_with_warnings(body)
    assert warned == []
    grace = notes_of(graph, main_line(graph))[0]
    assert grace.duration == GraceDuration(MetricalDuration(1, 16), on_beat=False)


def test_a_triplet_is_the_ready_made_duration():
    triplet_eighth = note("C", 4, 4, "eighth", time_modification=tuplet_of(3, 2))
    body = triplet_eighth * 3 + note("E", 4, 24, "half") + note("F", 4, 12, "quarter")
    graph, warned = read_with_warnings(body, divisions=12)
    assert warned == []
    notes = notes_of(graph, main_line(graph))
    assert [n.duration for n in notes[:3]] == [eighth_in_triplet] * 3
    assert onsets_of(graph, main_line(graph))[-1] == Fraction(1)


def test_a_nested_tuplet_is_one_ratio_from_normal_type():
    outer = note("C", 4, 24, "quarter", time_modification=tuplet_of(3, 2))
    inner = note("D", 4, 8, "eighth", time_modification=tuplet_of(9, 4, "eighth"))
    body = outer * 2 + inner * 3 + note("E", 4, 72, "half")
    graph, warned = read_with_warnings(body, divisions=36)
    assert warned == []
    notes = notes_of(graph, main_line(graph))
    assert notes[2].duration == MetricalDuration(1, 8, ratio=tuplet(9, 4, eighth))
    assert notes[2].duration.rational_length == Fraction(1, 18)
    assert onsets_of(graph, main_line(graph))[-1] == Fraction(1)


def test_a_whole_measure_rest_without_a_type_takes_the_bar():
    attributes = DEFAULT_ATTRIBUTES.replace("<beats>4</beats>", "<beats>3</beats>")
    graph, warned = read_with_warnings(rest(3 * Q, whole_measure=True), attributes=attributes)
    assert warned == []
    (silence,) = notes_of(graph, main_line(graph))
    assert silence.is_rest and silence.duration == dotted_half
    assert onsets_of(graph, main_line(graph))[-1] == Fraction(3, 4)


def test_a_hidden_rest_is_kept_with_hidden_in_meta():
    body = h("C") + rest(2 * Q, "half", attrs='print-object="no"')
    graph, warned = read_with_warnings(body)
    assert warned == []
    hidden = notes_of(graph, main_line(graph))[1]
    assert hidden.is_rest and xml_meta_of(hidden) == {"hidden": True}


def test_a_slash_notehead_note_has_no_tones_and_keeps_its_written_pitch():
    body = h("B", notehead="slash") + h("B", 4, notehead="normal")
    graph, warned = read_with_warnings(body)
    assert warned == []
    slash, normal = notes_of(graph, main_line(graph))
    assert slash.tones == set() and not slash.is_rest
    assert xml_meta_of(slash) == {"slash_pitch": [["B", "0", "4"]]}
    assert names_of([normal]) == ["B4"] and xml_meta_of(normal) == {"notehead": "normal"}


def test_a_note_whose_duration_disagrees_with_its_type_warns_and_keeps_the_type():
    body = note("C", 4, 3 * Q, "half") + q("D")
    graph, warned = read_with_warnings(body)
    assert warned == [
        "part 'P1', measure 1: a half with 0 dot(s) is notated as 1/2 whole notes "
        "but its <duration> says 3/4; the notated value is used"
    ]
    notes = notes_of(graph, main_line(graph))
    assert notes[0].duration == half
    assert names_of(notes) == ["C4", "", "D4"]  # the cursor gap is unspecified content
    assert xml_meta_of(notes[1]) == {"forward": True}


def test_a_rest_whose_duration_disagrees_with_its_type_uses_the_duration():
    attributes = DEFAULT_ATTRIBUTES.replace("<beats>4</beats>", "<beats>3</beats>")
    graph, warned = read_with_warnings(
        rest(3 * Q, "whole"), q("C") + q("D") + q("E"), attributes=attributes
    )
    assert warned == [
        "part 'P1': 1 rests whose <type> and <duration> disagree (the <duration> is used)"
    ]
    (silence,) = notes_of(graph, main_line(graph))[:1]
    assert silence.duration == dotted_half


# --- structure -----------------------------------------------------------------------


def test_a_pickup_measure_is_a_short_first_bar():
    graph, warned = read_with_warnings(
        measure(q("G"), number="0", implicit="yes"), q("C") + q("D") + h("E")
    )
    assert warned == []
    head = main_line(graph)
    events = events_of(graph, head)
    assert kinds_of(events) == CONTEXTS + ["NoteEvent", "DivisionEvent"] + ["NoteEvent"] * 3 + [
        "DivisionEvent"
    ]
    assert onsets_of(graph, head)[3:] == [
        Fraction(0), Fraction(1, 4), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(5, 4),
    ]  # fmt: skip
    divisions = [e for e in events if isinstance(e, DivisionEvent)]
    assert [xml_meta_of(d) for d in divisions] == [
        {"number": "0", "implicit": True},
        {"number": "2"},
    ]


def test_a_split_measure_is_two_divisions():
    graph, warned = read_with_warnings(
        w("C"), h("D"), measure(h("E"), number="X2", implicit="yes"), w("F")
    )
    assert warned == []
    head = main_line(graph)
    onsets = onsets_of(graph, head)
    divisions = [
        (o, e)
        for o, e in zip(onsets, events_of(graph, head), strict=True)
        if isinstance(e, DivisionEvent)
    ]
    assert [o for o, _ in divisions] == [Fraction(1), Fraction(3, 2), Fraction(2), Fraction(3)]
    assert [xml_meta_of(d)["number"] for _, d in divisions] == ["1", "2", "X2", "4"]


@pytest.mark.parametrize(
    ("style", "shape"),
    [
        ("regular", scoring.single_bar),
        ("light-light", scoring.double_bar),
        ("light-heavy", scoring.final_bar),
        ("heavy-light", scoring.reverse_final_bar),
        ("none", scoring.invisible_bar),
    ],
)
def test_a_bar_style_is_the_matching_bar_line_shape(style, shape):
    body = h("C") + h("D") + right_barline(f"<bar-style>{style}</bar-style>")
    graph, warned = read_with_warnings(body, h("E") + h("F"))
    assert warned == []
    styled, plain = (e for e in events_of(graph, main_line(graph)) if isinstance(e, DivisionEvent))
    assert styled.shape == shape
    assert plain.shape is None  # no <barline>: the writer knows not to emit one


def test_a_backward_repeat_is_an_end_repeat():
    body = (
        h("C")
        + h("D")
        + right_barline('<bar-style>light-heavy</bar-style><repeat direction="backward"/>')
    )
    graph, warned = read_with_warnings(body)
    assert warned == []
    (division,) = (e for e in events_of(graph, main_line(graph)) if isinstance(e, DivisionEvent))
    assert division.shape == scoring.end_repeat


def test_adjacent_backward_and_forward_repeats_merge_into_one_double_repeat():
    first = h("C") + h("D") + right_barline('<repeat direction="backward"/>')
    second = left_barline('<repeat direction="forward"/>') + h("E") + h("F")
    graph, warned = read_with_warnings(first, second)
    assert warned == []
    between, last = (e for e in events_of(graph, main_line(graph)) if isinstance(e, DivisionEvent))
    assert between.shape == scoring.double_repeat
    assert xml_meta_of(between) == {"number": "1", "left": True}
    assert last.shape is None


def test_a_forward_repeat_on_the_first_measure_is_a_division_at_the_head():
    body = left_barline('<repeat direction="forward"/>') + h("C") + h("D")
    graph, warned = read_with_warnings(body)
    assert warned == []
    events = events_of(graph, main_line(graph))
    assert kinds_of(events) == CONTEXTS + [
        "DivisionEvent",
        "NoteEvent",
        "NoteEvent",
        "DivisionEvent",
    ]
    assert events[3].shape == scoring.start_repeat
    assert xml_meta_of(events[3]) == {"left": True}
    assert onsets_of(graph, main_line(graph))[3] == Fraction(0)


def test_an_ending_is_a_navigation_spanner_over_its_measure():
    first = h("C") + h("D")
    second = (
        left_barline('<ending number="1" type="start"/>')
        + h("E") + h("F")
        + right_barline('<ending number="1" type="stop"/><repeat direction="backward"/>')
    )  # fmt: skip
    graph, warned = read_with_warnings(first, second, h("G") + h("A"))
    assert warned == [
        "part 'P1': 1 <ending> brackets recorded as navigation spans (control flow is not modelled)"
    ]
    (ending,) = spanners_named(graph, "ending 1")
    assert ending.mark.kind is MarkType.NAVIGATION
    assert names_of([graph.spanner_start(ending), graph.spanner_end(ending)]) == ["E4", "F4"]
    assert xml_meta_of(ending) == {"ending": {"number": "1", "type": "stop", "text": None}}


def test_a_measure_repeat_bar_is_unspecified_content_marked_simile():
    repeated = (
        '<attributes><measure-style><measure-repeat type="start">1</measure-repeat></measure-style></attributes>'
        + h("C") + h("D")
    )  # fmt: skip
    after = (
        '<attributes><measure-style><measure-repeat type="stop"/></measure-style></attributes>'
        + h("E")
        + h("F")
    )
    graph, warned = read_with_warnings(h("C") + h("D"), repeated, after)
    assert warned == [
        "part 'P1': 1 measure-repeat (%) bars recorded as unspecified content with a simile mark "
        "(control flow is not modelled)"
    ]
    notes = notes_of(graph, main_line(graph))
    assert names_of(notes) == ["C4", "D4", "", "E4", "F4"]
    percent = notes[2]
    assert percent.duration == whole
    assert mark_names_on(graph, percent) == ["simile"]
    assert xml_meta_of(percent) == {"measure_repeat": {"slashes": None, "measures": "1"}}


def test_a_multiple_rest_count_goes_on_the_division():
    first = (
        "<attributes><measure-style><multiple-rest>2</multiple-rest></measure-style></attributes>"
        + rest(BAR, whole_measure=True)
    )
    graph, warned = read_with_warnings(first, rest(BAR, whole_measure=True), w("C"))
    assert warned == []
    events = events_of(graph, main_line(graph))
    assert names_of([e for e in events if isinstance(e, NoteEvent)]) == ["rest", "rest", "C4"]
    divisions = [e for e in events if isinstance(e, DivisionEvent)]
    assert [xml_meta_of(d) for d in divisions] == [
        {"number": "1", "multiple_rest": 2},
        {"number": "2"},
        {"number": "3"},
    ]


# --- contexts ------------------------------------------------------------------------


def test_context_events_are_on_both_staff_lines_and_on_no_branch():
    body = (
        h("C", staff=1) + h("D", staff=1) + BACKUP
        + h("A", 3, voice=2, staff=1) + h("B", 3, voice=2, staff=1) + BACKUP
        + w("C", 3, voice=5, staff=2)
    )  # fmt: skip
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)
    assert warned == []
    upper, lower = main_line(graph, staff=1), main_line(graph, staff=2)
    assert kinds_of(events_of(graph, upper)[:3]) == CONTEXTS
    assert kinds_of(events_of(graph, lower)[:3]) == CONTEXTS
    assert events_of(graph, upper)[2].clef == StaffClef(ClefSign.G, 2)
    assert events_of(graph, lower)[2].clef == StaffClef(ClefSign.F, 4)
    ((_, branch),) = branches(graph, upper)
    assert not any(isinstance(e, ContextEvent) for e in events_of(graph, branch))
    assert len(list(graph.nodes(ContextEvent))) == 6


def test_a_key_with_a_mode_is_a_named_key():
    attributes = DEFAULT_ATTRIBUTES.replace(
        "<fifths>0</fifths>", "<fifths>-3</fifths><mode>minor</mode>"
    )
    graph, warned = read_with_warnings(w("C"), attributes=attributes)
    assert warned == []
    (key,) = graph.nodes(ModalContextEvent)
    assert key.modal_context.name == "C Minor"
    assert format(key.modal_context.tonic) == "C"


def test_a_key_without_a_mode_is_a_bare_signature():
    attributes = DEFAULT_ATTRIBUTES.replace("<fifths>0</fifths>", "<fifths>2</fifths>")
    graph, warned = read_with_warnings(w("D"), attributes=attributes)
    assert warned == []
    (key,) = graph.nodes(ModalContextEvent)
    expected = Key.from_signature(KeySignature.from_alts(2))
    assert key.modal_context == expected
    assert key.modal_context.name == expected.name
    assert key.modal_context.tonic is None


def test_cut_time_keeps_its_symbol_in_meta():
    attributes = DEFAULT_ATTRIBUTES.replace(
        "<time><beats>4</beats><beat-type>4</beat-type></time>",
        '<time symbol="cut"><beats>2</beats><beat-type>2</beat-type></time>',
    )
    graph, warned = read_with_warnings(w("C"), attributes=attributes)
    assert warned == []
    (meter,) = graph.nodes(MeterEvent)
    assert meter.meter.rational_length == Fraction(1)
    assert meter.meter.presentation == ("2", "2")
    assert xml_meta_of(meter) == {"symbol": "cut"}


def test_a_clef_change_mid_measure_lands_at_its_onset():
    body = h("C") + "<attributes><clef><sign>F</sign><line>4</line></clef></attributes>" + h("D", 3)
    graph, warned = read_with_warnings(body)
    assert warned == []
    head = main_line(graph)
    clefs = [
        (o, e)
        for o, e in zip(onsets_of(graph, head), events_of(graph, head), strict=True)
        if isinstance(e, ClefEvent)
    ]
    assert [(o, e.clef) for o, e in clefs] == [
        (Fraction(0), StaffClef(ClefSign.G, 2)),
        (Fraction(1, 2), StaffClef(ClefSign.F, 4)),
    ]
    assert kinds_of(events_of(graph, head)[3:]) == [
        "NoteEvent",
        "ClefEvent",
        "NoteEvent",
        "DivisionEvent",
    ]


# --- directions ----------------------------------------------------------------------


def test_a_dynamic_marks_the_note_at_its_position():
    body = q("C") + direction("<dynamics><p/></dynamics>") + q("D") + h("E")
    graph, warned = read_with_warnings(body)
    assert warned == []
    c, d, e = notes_of(graph, main_line(graph))
    assert [mark_names_on(graph, n) for n in (c, d, e)] == [[], ["piano"], []]
    (marking,) = markings_on(graph, d)
    assert marking.mark is scoring.piano and xml_meta_of(marking) == {}


def test_a_direction_inside_a_note_attaches_with_an_offset():
    body = h("C") + direction("<dynamics><f/></dynamics>", offset=Q) + h("D")
    graph, warned = read_with_warnings(body)
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    assert markings_on(graph, c) == []
    (marking,) = markings_on(graph, d)
    assert marking.mark is scoring.forte
    assert xml_meta_of(marking) == {"offset": Fraction(1, 4)}


def test_a_wedge_spans_from_the_note_at_its_start_to_the_note_ending_at_its_stop():
    body = (
        q("C") + direction('<wedge type="crescendo"/>') + q("D") + q("E")
        + direction('<wedge type="stop"/>') + q("F")
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    (hairpin,) = list(graph.nodes(MarkSpanner))
    assert hairpin.mark is scoring.crescendo
    assert names_of([graph.spanner_start(hairpin), graph.spanner_end(hairpin)]) == ["D4", "E4"]


def test_a_pedal_with_no_stop_is_an_open_spanner():
    body = h("C") + direction('<pedal type="start"/>') + h("D")
    graph, warned = read_with_warnings(body, w("E"))
    assert warned == ["part 'P1': 1 pedal left open (no stop in the file)"]
    (pedal,) = spanners_named(graph, "sustain pedal")
    assert names_of([graph.spanner_start(pedal)]) == ["D4"]
    assert graph.spanner_end(pedal) is None


def test_a_pedal_change_ends_one_span_and_starts_another():
    body = (
        direction('<pedal type="start"/>') + h("C")
        + direction('<pedal type="change"/>') + h("D")
        + direction('<pedal type="stop"/>')
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    pedals = spanners_named(graph, "sustain pedal")
    spans = sorted(
        (names_of([graph.spanner_start(p)]) + names_of([graph.spanner_end(p)]), xml_meta_of(p))
        for p in pedals
    )
    assert spans == [(["C4", "C4"], {}), (["D4", "D4"], {"change": True})]


def test_words_and_metronome_in_one_direction_make_one_tempo_event():
    tempo = direction(
        "<words>Allegro</words>",
        "<metronome><beat-unit>quarter</beat-unit><per-minute>120</per-minute></metronome>",
    )
    graph, warned = read_with_warnings(tempo + w("C"))
    assert warned == []
    (event,) = graph.nodes(TempoEvent)
    assert event.term is scoring.allegro
    assert event.tempo == Tempo(120, quarter)
    assert kinds_of(events_of(graph, main_line(graph))) == CONTEXTS + [
        "TempoEvent",
        "NoteEvent",
        "DivisionEvent",
    ]


def test_a_tempo_direction_makes_one_tempo_event_per_staff_line():
    tempo = direction("<words>Allegro</words>")
    body = tempo + w("C", staff=1) + BACKUP + w("C", 3, voice=2, staff=2)
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)
    assert warned == []
    events = list(graph.nodes(TempoEvent))
    assert len(events) == 2 and all(e.term is scoring.allegro for e in events)
    for staff in (1, 2):
        assert "TempoEvent" in kinds_of(events_of(graph, main_line(graph, staff=staff)))


def test_a_gradual_tempo_word_is_an_expression_marking_with_a_warning():
    graph, warned = read_with_warnings(h("C") + direction("<words>rit.</words>") + h("D"))
    assert warned == [
        "part 'P1': 1 gradual tempo word 'rit.' recorded at a point (its span has no end)"
    ]
    _, d = notes_of(graph, main_line(graph))
    (marking,) = markings_on(graph, d)
    assert marking.mark.name == "rit." and marking.mark.kind is MarkType.EXPRESSION
    assert xml_meta_of(marking) == {"gradual_tempo": True}
    assert list(graph.nodes(TempoEvent)) == []


def test_words_naming_a_ready_made_mark_use_it():
    graph, warned = read_with_warnings(direction("<words>dolce</words>") + w("C"))
    assert warned == []
    (marking,) = graph.nodes(Marking)
    assert marking.mark is scoring.dolce
    assert xml_meta_of(marking) == {"element": "words"}  # the writer writes words back
    graph, warned = read_with_warnings(direction("<words>dim.</words>") + w("C"))
    (marking,) = graph.nodes(Marking)
    assert marking.mark is scoring.decresc  # by its alias, whose text is kept
    assert xml_meta_of(marking) == {"element": "words", "text": "dim."}


def test_una_corda_is_an_open_spanner():
    graph, warned = read_with_warnings(h("C") + direction("<words>una corda</words>") + h("D"))
    assert warned == []  # an una corda with no tre corde is expected to stay open
    (soft,) = list(graph.nodes(MarkSpanner))
    assert soft.mark is scoring.una_corda
    assert names_of([graph.spanner_start(soft)]) == ["D4"]
    assert graph.spanner_end(soft) is None


def test_a_comma_is_a_breath_mark_on_the_preceding_note():
    graph, warned = read_with_warnings(h("C") + direction("<words>,</words>") + h("D"))
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    assert mark_names_on(graph, c) == ["breath mark"]
    assert mark_names_on(graph, d) == []
    (marking,) = markings_on(graph, c)
    assert marking.mark is scoring.breath_mark


def test_cresc_with_dashes_is_a_text_crescendo_spanner():
    body = (
        direction("<words>cresc.</words>", '<dashes type="start"/>') + h("C") + h("D")
        + direction('<dashes type="stop"/>')
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    (span,) = list(graph.nodes(MarkSpanner))
    assert span.mark.name == "cresc." and span.mark.kind is MarkType.DYNAMIC
    assert names_of([graph.spanner_start(span), graph.spanner_end(span)]) == ["C4", "D4"]
    assert list(graph.nodes(Marking)) == []  # the words are the span, not a marking too


def test_a_rehearsal_mark_is_a_rehearsal_marking():
    graph, warned = read_with_warnings(direction("<rehearsal>A</rehearsal>") + w("C"))
    assert warned == []
    (marking,) = graph.nodes(Marking)
    assert marking.mark.name == "A" and marking.mark.kind is MarkType.REHEARSAL
    assert names_of([next(graph._graph.successors(marking, NoteEvent, EdgeType.MARKS))]) == ["C4"]


def test_a_segno_at_a_bar_line_marks_the_division():
    graph, warned = read_with_warnings(w("C") + direction("<segno/>"), w("D"))
    assert warned == []
    first_division = next(
        e for e in events_of(graph, main_line(graph)) if isinstance(e, DivisionEvent)
    )
    assert mark_names_on(graph, first_division) == ["segno"]
    assert all(markings_on(graph, n) == [] for n in notes_of(graph, main_line(graph)))


def test_a_sound_tempo_alone_goes_to_meta():
    graph, warned = read_with_warnings('<sound tempo="120"/>' + h("C") + h("D"))
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    assert xml_meta_of(c) == {"sound_tempo": "120"} and xml_meta_of(d) == {}
    assert list(graph.nodes(TempoEvent)) == []


def test_an_octave_shift_is_an_ottava_spanner():
    body = (
        direction('<octave-shift type="down" size="8"/>') + q("C", 5) + q("D", 5)
        + direction('<octave-shift type="stop"/>') + h("E")
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    (ottava,) = list(graph.nodes(MarkSpanner))
    assert ottava.mark is scoring.ottava_alta
    assert names_of([graph.spanner_start(ottava), graph.spanner_end(ottava)]) == ["C5", "D5"]
    assert names_of(notes_of(graph, main_line(graph))) == [
        "C5",
        "D5",
        "E4",
    ]  # pitches are sounding already


# --- lyrics --------------------------------------------------------------------------


def syllables_on(graph: OmkGraph, note_event: NoteEvent) -> list[LyricSyllable]:
    return list(graph._graph.successors(note_event, LyricSyllable, EdgeType.LYRIC))


def test_two_verses_are_two_syllable_lines_joined_to_every_note():
    body = (
        q("C", extra=lyric("Al", "begin") + lyric("Sing", "single", 2))
        + q("D", extra=lyric("le", "middle") + lyric("to", "single", 2))
        + q("E", extra=lyric("lu", "middle") + lyric("Je", "begin", 2))
        + q("F", extra=lyric("ia", "end") + lyric("sus", "end", 2))
    )
    graph, warned = read_with_warnings(body)
    assert warned == []
    sections = sorted(graph.nodes(LyricSection), key=lambda s: s.section_number)
    assert [(s.section_type, s.section_number) for s in sections] == [("verse", 1), ("verse", 2)]
    verses = [list(graph.walk_line(graph.spanner_start(s))) for s in sections]
    assert [[syl.text for syl in verse] for verse in verses] == [
        ["Al", "le", "lu", "ia"],
        ["Sing", "to", "Je", "sus"],
    ]
    for note_event, first, second in zip(notes_of(graph, main_line(graph)), *verses, strict=True):
        assert {s.id for s in syllables_on(graph, note_event)} == {first.id, second.id}


def test_syllabic_begin_and_end_make_one_word():
    body = h("C", extra=lyric("Je", "begin")) + h("D", extra=lyric("sus", "end"))
    graph, warned = read_with_warnings(body)
    assert warned == []
    (section,) = graph.nodes(LyricSection)
    first, second = graph.walk_line(graph.spanner_start(section))
    assert first.word is second.word
    assert (first.index, second.index) == (0, 1)
    assert [str(first), str(second)] == ["Je -", "- sus"]


def test_a_melisma_leaves_the_held_note_without_a_syllable():
    body = h("C", extra=lyric("Ah", "single", extra="<extend/>")) + h("D")
    graph, warned = read_with_warnings(body)
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    (syllable,) = syllables_on(graph, c)
    assert syllable.text == "Ah" and xml_meta_of(syllable) == {"extend": "start"}
    assert syllables_on(graph, d) == []


def test_an_elision_puts_two_syllables_on_one_note():
    elided = (
        '<lyric number="1"><syllabic>single</syllabic><text>the</text>'
        "<elision> </elision><syllabic>single</syllabic><text>a</text></lyric>"
    )
    graph, warned = read_with_warnings(h("C", extra=elided) + h("D", extra=lyric("men", "single")))
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    assert sorted(s.text for s in syllables_on(graph, c)) == ["a", "the"]
    assert [s.text for s in syllables_on(graph, d)] == ["men"]
    (section,) = graph.nodes(LyricSection)
    assert [s.text for s in graph.walk_line(graph.spanner_start(section))] == ["the", "a", "men"]


def test_wrong_syllabic_flags_keep_the_text_in_order():
    body = (
        q("C", extra=lyric("Al", "single")) + q("D", extra=lyric("le", "end"))
        + q("E", extra=lyric("lu", "end")) + q("F", extra=lyric("ia", "end"))
    )  # fmt: skip
    graph, warned = read_with_warnings(body)
    assert warned == []
    (section,) = graph.nodes(LyricSection)
    syllables = list(graph.walk_line(graph.spanner_start(section)))
    assert [s.text for s in syllables] == ["Al", "le", "lu", "ia"]
    for note_event, syllable in zip(notes_of(graph, main_line(graph)), syllables, strict=True):
        assert syllables_on(graph, note_event) == [syllable]


def test_a_verse_number_with_text_takes_its_trailing_integer():
    body = h("C", extra=lyric("Sing", "single", number="part1verse1")) + h(
        "D", extra=lyric("on", "single", number="part1verse1")
    )
    graph, warned = read_with_warnings(body)
    assert warned == []
    (section,) = graph.nodes(LyricSection)
    assert section.section_number == 1
    assert xml_meta_of(section) == {"number": "part1verse1"}


def test_a_blank_syllable_is_skipped():
    body = h("C", extra=lyric("Ah", "single")) + h("D", extra=lyric(" "))
    graph, warned = read_with_warnings(body)
    assert warned == []
    c, d = notes_of(graph, main_line(graph))
    assert [s.text for s in graph.nodes(LyricSyllable)] == ["Ah"]
    assert len(syllables_on(graph, c)) == 1 and syllables_on(graph, d) == []


# --- harmony -------------------------------------------------------------------------


def harmony(root: str, kind: str, extra: str = "", offset: int | None = None) -> str:
    offset_xml = f"<offset>{offset}</offset>" if offset is not None else ""
    return (
        f"<harmony><root><root-step>{root}</root-step></root>"
        f"<kind>{kind}</kind>{extra}{offset_xml}</harmony>"
    )


def chord_line(graph: OmkGraph) -> list[ChordEvent]:
    (head,) = (line for line in graph.score_lines(score_of(graph)) if isinstance(line, ChordEvent))
    return list(graph.walk_line(head))


def pin_of(graph: OmkGraph, chord: ChordEvent):
    (edge,) = graph._graph.in_edges(chord, EdgeType.SIMULTANEOUS)
    return graph.edge_endpoints(edge)[0], edge.displacement


def test_a_harmony_is_a_chord_event_pinned_to_the_note_at_its_onset():
    body = harmony("C", "major") + h("C") + harmony("G", "dominant") + h("D")
    graph, warned = read_with_warnings(body)
    assert warned == []
    chords = chord_line(graph)
    assert [str(c.chord) for c in chords] == ["C", "G7"]
    assert all(c.duration is None for c in chords)
    assert [names_of([pin_of(graph, c)[0]]) for c in chords] == [["C4"], ["D4"]]
    assert all(pin_of(graph, c)[1] is None for c in chords)
    assert xml_meta_of(chords[0]) == {"kind": "major"}
    assert len(list(graph.score_lines(score_of(graph)))) == 2
    assert list(graph.score_sync_lines(score_of(graph))) == []


def test_a_bass_makes_a_slash_chord():
    body = harmony("C", "major", "<bass><bass-step>G</bass-step></bass>") + w("C")
    graph, warned = read_with_warnings(body)
    assert warned == []
    (chord,) = chord_line(graph)
    assert str(chord.chord) == "C/G"


def test_a_degree_adds_a_tone_and_names_the_type():
    degree = "<degree><degree-value>9</degree-value><degree-alter>0</degree-alter><degree-type>add</degree-type></degree>"
    graph, warned = read_with_warnings(harmony("C", "major", degree) + w("C"))
    assert warned == []
    (chord,) = chord_line(graph)
    assert chord.chord.name == "major (add 9)"
    assert D in chord.chord
    assert [format(t) for t in chord.chord] == ["C", "E", "G", "D"]


def test_no_chord_is_skipped_with_a_warning():
    body = harmony("C", "major") + h("C") + harmony("G", "none") + h("D")
    graph, warned = read_with_warnings(body)
    assert warned == ["part 'P1': 1 chord symbols with no chord (N.C.) skipped"]
    assert [str(c.chord) for c in chord_line(graph)] == ["C"]


def test_a_harmony_offset_is_the_pins_displacement():
    graph, warned = read_with_warnings(harmony("C", "major", offset=Q) + w("C"))
    assert warned == []
    (chord,) = chord_line(graph)
    anchor, displacement = pin_of(graph, chord)
    assert names_of([anchor]) == ["C4"]
    assert displacement == quarter
    assert onset_of(graph, main_line(graph), chord) == Fraction(1, 4)


# --- unpitched -----------------------------------------------------------------------

KIT_INSTRUMENTS = {
    "P1": (
        '<score-instrument id="P1-I36"><instrument-name>Bass Drum</instrument-name></score-instrument>'
        '<score-instrument id="P1-I38"><instrument-name>Snare</instrument-name></score-instrument>'
    )
}
KIT_ATTRIBUTES = (
    "<time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>percussion</sign></clef>"
)


def stroke(
    step: str, octave: int, instrument: str, duration: int = Q, type_name: str = "quarter"
) -> str:
    return (
        f"<note><unpitched><display-step>{step}</display-step><display-octave>{octave}</display-octave>"
        f'</unpitched><duration>{duration}</duration><instrument id="{instrument}"/>'
        f"<voice>1</voice><type>{type_name}</type></note>"
    )


def kit_lines(graph: OmkGraph) -> dict[str, list]:
    return {
        part.name: events_of(graph, lines_of_part(graph, part)[0])
        for part in graph.nodes(PercussionPart)
    }


def test_a_drum_kit_is_a_group_with_one_line_per_instrument():
    body = (
        stroke("F", 4, "P1-I36")
        + stroke("C", 5, "P1-I38")
        + stroke("F", 4, "P1-I36", 2 * Q, "half")
    )
    graph, warned = read_with_warnings(
        body, attributes=KIT_ATTRIBUTES, part_list_extra=KIT_INSTRUMENTS
    )
    assert warned == []
    parts = sorted(graph.nodes(PercussionPart), key=lambda p: p.name)
    assert [p.name for p in parts] == ["Bass Drum", "Snare"]
    assert [xml_meta_of(p)["instrument"] for p in parts] == ["P1-I36", "P1-I38"]
    assert list(graph.nodes(Part, lambda p: not isinstance(p, PercussionPart))) == []
    (group,) = graph.nodes(LineGroup)
    assert group.name == "P1" and len(list(graph.group_members(group))) == 2
    lines = kit_lines(graph)
    bass = [e for e in lines["Bass Drum"] if isinstance(e, NoteEvent)]
    assert [e.tones for e in bass] == [{hit}, set(), {hit}]
    assert xml_meta_of(bass[0]) == {"voice": "1", "display": ["F", "4"], "instrument": "P1-I36"}
    assert xml_meta_of(bass[1]) == {"forward": True}
    snare = [e for e in lines["Snare"] if isinstance(e, NoteEvent)]
    assert [e.tones for e in snare] == [set(), {hit}, set()]
    assert xml_meta_of(snare[1]) == {"voice": "1", "display": ["C", "5"], "instrument": "P1-I38"}


def test_a_rest_in_a_kit_staff_produces_nothing():
    body = stroke("F", 4, "P1-I36") + rest(Q, "quarter") + stroke("F", 4, "P1-I36", 2 * Q, "half")
    graph, warned = read_with_warnings(
        body, attributes=KIT_ATTRIBUTES, part_list_extra=KIT_INSTRUMENTS
    )
    assert warned == []
    assert not any(e.is_rest for e in graph.nodes(NoteEvent))
    bass = [e for e in kit_lines(graph)["Bass Drum"] if isinstance(e, NoteEvent)]
    assert names_of(bass) == ["hit", "", "hit"] and xml_meta_of(bass[1]) == {"forward": True}


def test_kit_lines_have_every_division_before_their_first_stroke():
    graph, warned = read_with_warnings(
        stroke("F", 4, "P1-I36", BAR, "whole"),
        stroke("F", 4, "P1-I36", BAR, "whole"),
        stroke("C", 5, "P1-I38", BAR, "whole"),
        attributes=KIT_ATTRIBUTES,
        part_list_extra=KIT_INSTRUMENTS,
    )
    assert warned == []
    snare = kit_lines(graph)["Snare"]
    assert kinds_of(snare) == [
        "MeterEvent", "ClefEvent", "NoteEvent", "DivisionEvent", "NoteEvent", "DivisionEvent",
        "NoteEvent", "DivisionEvent",
    ]  # fmt: skip
    assert [xml_meta_of(e) for e in snare if isinstance(e, DivisionEvent)] == [
        {"number": "1"}, {"number": "2"}, {"number": "3"},
    ]  # fmt: skip


# --- transposition -------------------------------------------------------------------


def test_a_transposing_part_stores_sounding_pitch_and_the_interval():
    attributes = (
        DEFAULT_ATTRIBUTES
        + "<transpose><diatonic>-2</diatonic><chromatic>-3</chromatic></transpose>"
    )
    graph, warned = read_with_warnings(q("C", 5) + q("D", 5) + h("E", 5), attributes=attributes)
    assert warned == []
    assert names_of(notes_of(graph, main_line(graph))) == ["A4", "B4", "C♯5"]
    (part,) = parts_of(graph)
    stint = stint_of(graph, part)
    assert stint.transposition == TonalVector((2, 3, 0))  # written = sounding + a minor third
    sounding = next(iter(notes_of(graph, main_line(graph))[0].tones))
    assert format(sounding + stint.transposition) == "C5"


# --- grid ----------------------------------------------------------------------------


def test_two_parts_get_a_bar_grid():
    graph, warned = read_with_warnings(
        {
            "P1": [q("C") + q("D") + h("E"), h("F") + h("G")],
            "P2": [h("C", 3) + h("D", 3), h("E", 3) + h("F", 3)],
        }
    )
    assert warned == []
    score = score_of(graph)
    (grid,) = graph.score_sync_lines(score)
    assert isinstance(grid, SyncLine) and grid.name == "bars"
    points = graph.sync_points(grid)
    assert [p.offset.rational_length for p in points] == [Fraction(0), Fraction(1), Fraction(2)]
    heads = [main_line(graph, part_index=i) for i in range(2)]
    assert {e.id for e in graph.synced_events(points[0])} == {h.id for h in heads}
    second = list(graph.synced_events(points[1]))
    assert kinds_of(second) == ["DivisionEvent", "DivisionEvent"]
    assert {
        onset_of(graph, head, division)
        for head in heads
        for division in second
        if division in events_of(graph, head)
    } == {Fraction(1)}
    assert len(list(graph.edges(EdgeType.SIMULTANEOUS))) == 2 * 3
    assert graph.check_sync_alignment() == []


def test_a_pickup_puts_the_second_grid_point_at_its_length():
    pickup = measure(q("G"), number="0", implicit="yes")
    graph, warned = read_with_warnings({"P1": [pickup, w("C")], "P2": [pickup, w("E")]})
    assert warned == []
    (grid,) = graph.score_sync_lines(score_of(graph))
    assert [p.offset.rational_length for p in graph.sync_points(grid)] == [
        Fraction(0), Fraction(1, 4), Fraction(5, 4),
    ]  # fmt: skip
    assert graph.check_sync_alignment() == []


def test_one_part_gets_no_grid():
    graph, warned = read_with_warnings(w("C"), w("D"))
    assert warned == []
    assert list(graph.score_sync_lines(score_of(graph))) == []
    assert list(graph.nodes(SyncLine)) == []
    assert list(graph.edges(EdgeType.SIMULTANEOUS)) == []


def test_a_lead_sheet_pins_only_its_chords():
    graph, warned = read_with_warnings(
        harmony("C", "major") + w("C"), harmony("F", "major") + w("F")
    )
    assert warned == []
    assert list(graph.nodes(SyncLine)) == []
    pins = list(graph.edges(EdgeType.SIMULTANEOUS))
    assert len(pins) == 2
    assert all(isinstance(graph.edge_endpoints(pin)[1], ChordEvent) for pin in pins)


def test_parts_of_unequal_measure_length_warn_and_are_padded():
    graph, warned = read_with_warnings({"P1": [w("C")], "P2": [h("E", 3)]})
    assert warned == [
        "measure 1: parts ['P2'] are shorter than the longest part (1 whole notes); "
        "their lines are padded with unspecified content"
    ]
    second = notes_of(graph, main_line(graph, part_index=1))
    assert names_of(second) == ["E3", ""] and xml_meta_of(second[1]) == {"forward": True}
    assert graph.check_sync_alignment() == []


# --- score header --------------------------------------------------------------------


def test_score_fields_come_from_work_and_identification():
    header = (
        "<work><work-number>Op. 1</work-number><work-title>Title</work-title></work>"
        "<movement-number>2</movement-number><movement-title>Movement</movement-title>"
        '<identification><creator type="composer">Someone</creator>'
        '<creator type="lyricist">Another</creator><rights>(c) 2026</rights>'
        "<encoding><software>Test</software></encoding><source>a test</source></identification>"
    )
    graph, warned = read_with_warnings(w("C"), header=header)
    assert warned == []
    score = score_of(graph)
    assert (score.title, score.opus, score.composer, score.lyricist, score.copyright) == (
        "Title", "Op. 1", "Someone", "Another", "(c) 2026",
    )  # fmt: skip
    assert xml_meta_of(score) == {
        "movement_title": "Movement",
        "movement_number": "2",
        "encoding": [["software", "Test"]],
        "source": "a test",
    }


def test_movement_title_is_the_title_when_there_is_no_work_title():
    graph, warned = read_with_warnings(w("C"), header="<movement-title>Movement</movement-title>")
    assert warned == []
    score = score_of(graph)
    assert score.title == "Movement" and score.composer is None
    assert xml_meta_of(score) == {}


def test_a_score_with_no_header_is_all_none():
    graph, warned = read_with_warnings(w("C"))
    assert warned == []
    score = score_of(graph)
    assert (score.title, score.composer, score.lyricist, score.copyright, score.opus) == (None,) * 5


def test_a_blank_part_name_is_an_empty_string():
    graph, warned = read_with_warnings(w("C"), part_names={"P1": ""})
    assert warned == []
    (part,) = parts_of(graph)
    assert part.name == "" and xml_meta_of(part)["id"] == "P1"


def test_part_abbreviation_goes_to_meta_and_the_order_to_the_stack():
    graph, warned = read_with_warnings(
        [w("C")],
        [w("E", 3)],
        parts=("P1", "P2"),
        part_names=("Flute", "Cello"),
        part_list_extra={"P2": "<part-abbreviation>Vc.</part-abbreviation>"},
    )
    assert warned == []
    flute, cello = parts_of(graph)
    assert (flute.name, cello.name) == ("Flute", "Cello")
    assert xml_meta_of(flute) == {"id": "P1"}
    assert xml_meta_of(cello) == {"id": "P2", "abbreviation": "Vc."}
    assert graph.stacked_above(flute) is None and graph.stacked_below(flute) is cello


# --- part order and part groups --------------------------------------------------------


def score_part(part_id: str) -> str:
    return f'<score-part id="{part_id}"><part-name>{part_id}</part-name></score-part>'


def group_start(number: int, *details: str) -> str:
    return f'<part-group type="start" number="{number}">{"".join(details)}</part-group>'


def group_stop(number: int) -> str:
    return f'<part-group type="stop" number="{number}"/>'


def four_parts(part_list: str):
    return read_with_warnings(
        [w("C")], [w("D")], [w("E")], [w("F")], parts=("P1", "P2", "P3", "P4"), part_list=part_list
    )


def test_parts_are_stacked_in_part_list_order_whatever_their_ids():
    graph, warned = read_with_warnings([w("C")], [w("D")], [w("E")], parts=("P3", "P1", "P2"))
    assert warned == []
    top = parts_of(graph)[0]
    assert graph.stacked_above(top) is None
    assert [xml_meta_of(part)["id"] for part in graph.walk_stack(top)] == ["P3", "P1", "P2"]


def test_nested_part_groups_are_nested_stack_groups_with_their_shapes():
    part_list = (
        score_part("P1")
        + group_start(
            1,
            "<group-name>Strings</group-name>",
            "<group-abbreviation>Str.</group-abbreviation>",
            "<group-symbol>bracket</group-symbol>",
            "<group-barline>Mensurstrich</group-barline>",
        )
        + group_start(2, "<group-symbol>brace</group-symbol>", "<group-barline>yes</group-barline>")
        + score_part("P2")
        + score_part("P3")
        + group_stop(2)
        + score_part("P4")
        + group_stop(1)
    )
    graph, warned = four_parts(part_list)
    assert warned == []
    p1, p2, p3, p4 = parts_of(graph)
    strings, violins = sorted(graph.nodes(StackGroup), key=lambda g: g.name is None)
    assert (strings.name, strings.abbreviation) == ("Strings", "Str.")
    assert strings.shape == BracketShape(
        symbol=BracketSymbol.BRACKET, bar_lines=GroupBarLines.MENSURSTRICH
    )
    assert list(graph.stack_group_members(strings)) == [p2, p3, p4]
    assert (violins.name, violins.shape) == (None, scoring.brace_joined)
    assert list(graph.stack_group_members(violins)) == [p2, p3]
    assert list(graph.stack_groups_of(p1)) == []


def test_a_part_group_with_no_symbol_or_bar_line_has_no_shape():
    part_list = group_start(1) + "".join(score_part(p) for p in ("P1", "P2", "P3", "P4"))
    graph, warned = four_parts(part_list + group_stop(1))
    assert warned == []
    (group,) = graph.nodes(StackGroup)
    assert group.shape is None and list(graph.stack_group_members(group)) == parts_of(graph)


def test_unclosed_and_empty_part_groups_warn_and_are_dropped():
    part_list = (
        group_start(1, "<group-symbol>bracket</group-symbol>")
        + score_part("P1")
        + score_part("P2")
        + group_stop(1)
        + group_start(2)
        + group_stop(2)
        + group_start(3)
        + score_part("P3")
        + score_part("P4")
    )
    graph, warned = four_parts(part_list)
    assert warned == [
        "part group 3 starts and never stops; dropped",
        "part group 2 holds no part; dropped",
    ]
    (group,) = graph.nodes(StackGroup)
    assert list(graph.stack_group_members(group)) == parts_of(graph)[:2]


def test_group_time_and_unknown_group_values_warn():
    part_list = (
        group_start(
            1,
            "<group-symbol>curly</group-symbol>",
            "<group-barline>sometimes</group-barline>",
            "<group-time/>",
        )
        + "".join(score_part(p) for p in ("P1", "P2", "P3", "P4"))
        + group_stop(1)
    )
    graph, warned = four_parts(part_list)
    assert warned == [
        "part group 1: <group-time> is not kept",
        "part group 1: unknown group-symbol 'curly'; none kept",
        "part group 1: unknown group-barline 'sometimes'; none kept",
    ]
    (group,) = graph.nodes(StackGroup)
    assert group.shape == BracketShape()


def test_a_part_s_staves_are_stacked_in_staff_order():
    body = (
        h("C", 3, voice=2, staff=2) + h("G", 2, voice=2, staff=2) + BACKUP
        + q("C", staff=1) + q("D", staff=1) + h("E", staff=1)
    )  # fmt: skip
    graph, warned = read_with_warnings(body, attributes=TWO_STAVES)
    assert warned == []
    upper, lower = main_line(graph, staff=1), main_line(graph, staff=2)
    assert list(graph.walk_stack(upper)) == [upper, lower]
    assert graph.stacked_above(upper) is None


def test_a_drum_kit_is_stacked_by_its_group_and_its_lines_are_not():
    graph, warned = read_with_warnings(
        [
            stroke("F", 4, "P1-I36")
            + stroke("C", 5, "P1-I38")
            + stroke("F", 4, "P1-I36", 2 * Q, "half")
        ],
        [w("C")],
        parts=("P1", "P2"),
        attributes={"P1": KIT_ATTRIBUTES, "P2": DEFAULT_ATTRIBUTES},
        part_list_extra=KIT_INSTRUMENTS,
    )
    assert warned == []
    (kit,) = graph.nodes(LineGroup)
    (pitched,) = parts_of(graph)
    assert list(graph.walk_stack(kit)) == [kit, pitched]
    for head in graph.group_members(kit):
        assert graph.stacked_above(head) is None and graph.stacked_below(head) is None


# --- container -----------------------------------------------------------------------

CONTAINER_XML = (
    '<?xml version="1.0" encoding="UTF-8"?><container><rootfiles>'
    '<rootfile full-path="score.xml" media-type="application/vnd.recordare.musicxml+xml"/>'
    "</rootfiles></container>"
)


def test_an_mxl_reads_the_same_as_its_xml():
    data = doc(q("C") + q("D") + h("E"), w("F"))
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("META-INF/container.xml", CONTAINER_XML)
        zipped.writestr("score.xml", data)
    compressed = read(io.BytesIO(archive.getvalue()))
    plain = read_bytes(data)
    assert compressed.is_equivalent(plain), compressed.diff(plain)
    assert names_of(notes_of(compressed, main_line(compressed))) == ["C4", "D4", "E4", "F4"]


def test_a_timewise_score_is_refused():
    with pytest.raises(MusicXmlError, match="score-timewise"):
        read_bytes(b'<score-timewise version="4.0"><part-list/></score-timewise>')


def test_a_file_that_is_not_xml_is_refused():
    with pytest.raises(MusicXmlError, match="Not well-formed XML"):
        read_bytes(b"this is not a score")


def test_an_unknown_notation_is_minted_and_counted():
    body = (
        q("C", extra="<notations><other-notation>wiggle</other-notation></notations>")
        + q("D")
        + h("E")
    )
    graph, warned = read_with_warnings(body)
    assert warned == ["part 'P1': 1 minted mark 'wiggle' from <other-notation>"]
    c = notes_of(graph, main_line(graph))[0]
    (marking,) = markings_on(graph, c)
    assert marking.mark.name == "wiggle" and marking.mark.kind is MarkType.OTHER
    assert xml_meta_of(marking) == {"element": "other-notation"}


# --- OmkGraph.from_file and import_file ----------------------------------------------


def test_from_file_and_import_file_read_a_musicxml_path(tmp_path):
    path = tmp_path / "two.musicxml"
    path.write_bytes(doc(q("C") + q("D") + h("E")))
    graph = OmkGraph.from_file(path)
    assert [type(s) for s in graph.nodes(Score)] == [Score]
    assert names_of(notes_of(graph, main_line(graph))) == ["C4", "D4", "E4"]
    other = OmkGraph(GraphMeta())
    other.import_file(path)
    assert other.is_equivalent(graph)


def test_import_file_twice_gives_two_scores_on_one_graph(tmp_path):
    path = tmp_path / "two.xml"
    path.write_bytes(doc(w("C"), header="<work><work-title>Twice</work-title></work>"))
    graph = OmkGraph(GraphMeta())
    graph.import_file(path)
    graph.import_file(path)
    scores = list(graph.nodes(Score))
    assert [s.title for s in scores] == ["Twice", "Twice"]
    assert scores[0] is not scores[1]
    assert len(list(graph.nodes(NoteEvent))) == 2
    assert {len(list(graph.score_lines(s))) for s in scores} == {1}
