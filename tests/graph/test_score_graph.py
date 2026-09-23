"""Scores: the work's metadata, naming the heads of its top-level lines and
its Parts with plain CONTAINS edges, and never a timing origin.
See _plans/clef-score-text.md."""

import pytest

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, OmkEdge, TimedEdge
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter
from openmusickit.systems.wsmn.tonal.symbols import A, B, C, D, E, F, G, dom7, maj
from tests.graph.helpers import notes, snapshot


@pytest.fixture
def twinkle():
    """A melody with a two-note second voice branched from its second note,
    a chord line pinned to the melody head, a Voice part with a stint, a
    Piano part with no music yet, and a Score holding both lines and both
    parts."""
    graph = OmkGraph(GraphMeta())
    melody = notes(C, D, E, F)
    voice = notes(A, B, duration=eighth)
    chords = [ChordEvent(chord=C(maj), duration=half), ChordEvent(chord=G(dom7), duration=half)]
    for line in (melody, voice, chords):
        graph.add_line(line)
    graph.add_branch(melody[1], voice[0])
    graph.add_simultaneous(melody[0], chords[0])
    singer, piano = Part(name="Voice"), Part(name="Piano")
    graph.add_stint(singer, Stint(), melody[0])
    score = Score(title="Twinkle, Twinkle, Little Star", lyricist="Jane Taylor")
    graph.add_line_to_score(score, melody[0])
    graph.add_line_to_score(score, chords[0])
    graph.add_part_to_score(score, singer)
    graph.add_part_to_score(score, piano)
    return graph, score, melody, voice, chords, singer, piano


# --- membership ------------------------------------------------------------------


def test_score_lines_and_parts(twinkle):
    graph, score, melody, voice, chords, singer, piano = twinkle
    assert {h.id for h in graph.score_lines(score)} == {melody[0].id, chords[0].id}
    assert {p.id for p in graph.score_parts(score)} == {singer.id, piano.id}


def test_scores_of_a_head_and_a_part(twinkle):
    graph, score, melody, voice, chords, singer, piano = twinkle
    for member in (melody[0], chords[0], singer, piano):
        assert list(graph.scores_of(member)) == [score]
    assert list(graph.scores_of(melody[1])) == []  # mid-line
    assert (
        list(graph.scores_of(voice[0])) == []
    )  # a branched head is in the score through its parent


def test_walk_score_covers_every_line_including_branched_voices(twinkle):
    graph, score, melody, voice, chords, singer, piano = twinkle
    walked = list(graph.walk_score(score))
    assert len(walked) == len(melody) + len(voice) + len(chords)
    assert {e.id for e in walked} == {e.id for e in melody + voice + chords}


def test_the_edges_are_plain_contains_edges(twinkle):
    graph, score, melody, voice, chords, singer, piano = twinkle
    for member in (melody[0], singer):
        edge = graph.get_edge(score, member, EdgeType.CONTAINS)
        assert type(edge) is OmkEdge and not isinstance(edge, TimedEdge)


def test_a_part_with_no_music_is_allowed(twinkle):
    graph, score, melody, voice, chords, singer, piano = twinkle
    assert piano in list(graph.score_parts(score))
    assert list(graph.stints(piano)) == [] and list(graph.groups(piano)) == []


# --- what a member must be ---------------------------------------------------------


def test_a_member_is_a_head_that_is_not_branched():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    score = Score()
    with pytest.raises(GraphError, match="not the head"):
        graph.add_line_to_score(score, d)
    graph.add_branch(c, a)
    with pytest.raises(GraphError, match="branched"):
        graph.add_line_to_score(score, a)
    graph.add_line_to_score(score, c)
    with pytest.raises(GraphError):
        graph.add_line_to_score(score, c)  # once per score
    flute = Part(name="Flute")
    graph.add_part_to_score(score, flute)
    with pytest.raises(GraphError):
        graph.add_part_to_score(score, flute)  # once per score


def test_a_scores_line_cannot_then_be_branched():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    a, b = notes(A, B)
    graph.add_line([c, d])
    graph.add_line([a, b])
    graph.add_line_to_score(Score(), a)
    with pytest.raises(GraphError, match="group or a score"):
        graph.add_branch(c, a)


# --- a Score is not a timing origin -------------------------------------------------


def test_a_score_is_not_a_timing_node():
    graph, plain = OmkGraph(GraphMeta()), OmkGraph(GraphMeta())
    first, second = notes(C, D, E), notes(F, G)
    reference = notes(C, D, E)
    graph.add_line(first)
    graph.add_line(second)
    plain.add_line(reference)
    score = Score()
    graph.add_line_to_score(score, first[0])
    graph.add_line_to_score(score, second[0])
    with pytest.raises(GraphError):
        graph.relative_onset(first[0], second[0])  # two lines, no pin: the score relates nothing
    with pytest.raises(GraphError):
        graph.relative_onset(score, first[0])
    for i in range(3):
        assert graph.relative_onset(first[0], first[i]) == plain.relative_onset(
            reference[0], reference[i]
        )
    assert graph.relative_onset(first[2], first[0]) == -(quarter + quarter)


def test_groups_are_unaffected():
    graph = OmkGraph(GraphMeta())
    rh, lh = notes(C, D), notes(E, F, duration=half)
    graph.add_line(rh)
    graph.add_line(lh)
    hands = LineGroup(name="Piano")
    graph.add_group(hands, [rh[0], lh[0]])
    score = Score()
    graph.add_line_to_score(score, rh[0])
    graph.add_line_to_score(score, lh[0])
    assert list(graph.groups_of(rh[0])) == [hands]
    assert list(graph.scores_of(rh[0])) == [score]
    assert {h.id for h in graph.group_members(hands)} == {rh[0].id, lh[0].id}
    assert graph.relative_onset(rh[1], lh[1]) == quarter  # timed through the group, as before
    assert graph.check_alignment() == []


# --- lifecycle ----------------------------------------------------------------------


def test_removing_the_score_frees_its_members():
    graph = OmkGraph(GraphMeta())
    c, d = notes(C, D)
    graph.add_line([c, d])
    flute = Part(name="Flute")
    graph.add_stint(flute, Stint(), c)
    before = snapshot(graph)
    score = Score(title="Gone")
    graph.add_line_to_score(score, c)
    graph.add_part_to_score(score, flute)
    assert list(graph.scores_of(c)) == [score]
    graph.remove_node(score)
    assert snapshot(graph) == before
    assert list(graph.scores_of(c)) == [] and list(graph.scores_of(flute)) == []


def test_a_graph_may_hold_two_scores():
    graph = OmkGraph(GraphMeta())
    first, second = notes(C, D), notes(E, F)
    graph.add_line(first)
    graph.add_line(second)
    one, two = Score(title="One"), Score(title="Two")
    graph.add_line_to_score(one, first[0])
    graph.add_line_to_score(two, second[0])
    assert list(graph.scores_of(first[0])) == [one]
    assert list(graph.scores_of(second[0])) == [two]
    with pytest.raises(GraphError):
        graph.relative_onset(first[0], second[0])
