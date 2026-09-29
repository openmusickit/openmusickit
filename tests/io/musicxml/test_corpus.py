"""Every real score in `tests/scores/` reads, and what comes out is pinned:
the warnings it raises (by kind), the parts and measures, that every line
of a part is the same length, that the bar grid pins every part at every
bar, and a shape literal (lines, branches, spanners, ...) that a mapping
change must update in the same commit.
"""

from __future__ import annotations

import warnings
from collections import defaultdict
from fractions import Fraction
from functools import cache

import pytest

from openmusickit.errors import OmkWarning
from openmusickit.graph.edge import EdgeType
from openmusickit.io.musicxml import read
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import LineGroup, PercussionPart
from openmusickit.objects.score import Score
from openmusickit.systems.wsmn.scoring import symbols as scoring
from openmusickit.values.time.duration import Measurable
from tests.scores.registry import FIXTURES, ScoreFixture

WITH_MUSICXML = [fixture for fixture in FIXTURES.values() if fixture.musicxml is not None]
LARGE = {
    "tchaikovsky-swan-lake-suite-op20a-no1",
    "mozart-string-quartet-k464-mvt3",
    "moonlight-gaze-big-band",
    "bach-art-of-fugue-bwv1080-contrapunctus-19",
}


def fixtures(slow_for_large: bool = False):
    return [
        pytest.param(
            fixture,
            id=fixture.slug,
            marks=[pytest.mark.slow] if slow_for_large and fixture.slug in LARGE else [],
        )
        for fixture in WITH_MUSICXML
    ]


@cache
def graph_and_warnings(slug: str):
    fixture = FIXTURES[slug]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        graph = read(fixture.musicxml)
    messages = [str(w.message) for w in caught if issubclass(w.category, OmkWarning)]
    assert len(messages) == len(caught), "only OmkWarnings are expected"
    return graph, messages


def score_of(graph) -> Score:
    scores = list(graph.nodes(Score))
    assert len(scores) == 1
    return scores[0]


def parts_by_index(graph, score):
    by_index = defaultdict(list)
    for part in graph.score_parts(score):
        by_index[part.meta["musicxml"]["index"]].append(part)
    return by_index


def lines_of_part(graph, part):
    """The top-level line heads a Part plays: its stints' lines or its group's members."""
    heads = [
        next(graph._graph.successors(stint, edge_type=EdgeType.STARTS_AT))
        for stint in graph.stints(part)
    ]
    for group in graph.groups(part):
        heads.extend(graph.group_members(group))
    return heads


def length_of(graph, head) -> Fraction:
    total = Fraction(0)
    for event in graph.walk_line(head):
        if isinstance(event.duration, Measurable):
            total += event.duration.rational_length
    return total


@pytest.mark.parametrize("fixture", fixtures())
def test_reads_with_only_the_expected_kinds_of_warning(fixture: ScoreFixture):
    _, messages = graph_and_warnings(fixture.slug)
    for message in messages:
        assert any(kind in message for kind in fixture.expected_warnings), message
    for kind in fixture.expected_warnings:
        assert any(kind in message for message in messages), kind


@pytest.mark.parametrize("fixture", fixtures())
def test_the_parts_are_the_part_list(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    by_index = parts_by_index(graph, score_of(graph))
    assert sorted(by_index) == list(range(len(fixture.parts)))
    for index, name in enumerate(fixture.parts):
        parts = by_index[index]
        if len(parts) == 1:
            assert parts[0].name == name
            assert parts[0].meta["musicxml"]["id"] is not None
        else:  # a drum kit: one PercussionPart per instrument of that <score-part>
            assert "unpitched" in fixture.features
            assert all(isinstance(part, PercussionPart) for part in parts)


@pytest.mark.parametrize("fixture", fixtures())
def test_the_first_part_has_the_measures_of_the_file(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    first = parts_by_index(graph, score_of(graph))[0][0]
    head = lines_of_part(graph, first)[0]
    numbered = [
        event
        for event in graph.walk_line(head)
        if isinstance(event, DivisionEvent) and "number" in event.meta.get("musicxml", {})
    ]
    assert len(numbered) == fixture.measures


@pytest.mark.parametrize("fixture", fixtures())
def test_every_line_of_every_part_has_the_length_of_the_score(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    lengths = {
        length_of(graph, head)
        for parts in parts_by_index(graph, score_of(graph)).values()
        for part in parts
        for head in lines_of_part(graph, part)
    }
    assert len(lengths) == 1 and next(iter(lengths)) > 0


@pytest.mark.parametrize("fixture", fixtures())
def test_pins_agree_with_the_durations(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    assert graph.check_alignment() == []


@pytest.mark.parametrize("fixture", fixtures())
def test_a_grid_exists_exactly_for_several_parts(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    score = score_of(graph)
    grids = list(graph.score_sync_lines(score))
    chord_pins = len(list(graph.nodes(ChordEvent)))
    pins = len(list(graph.edges(EdgeType.SIMULTANEOUS)))
    if len(fixture.parts) < 2:
        assert grids == []
        assert pins == chord_pins
        return
    assert len(grids) == 1
    points = graph.sync_points(grids[0])
    assert len(points) == fixture.measures + 1
    assert pins == chord_pins + len(fixture.parts) * len(points)
    assert len(list(graph.synced_events(points[0]))) == len(fixture.parts)


@pytest.mark.parametrize("fixture", fixtures(slow_for_large=True))
def test_the_grid_runs_with_the_music(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    if len(fixture.parts) >= 2:
        assert graph.check_sync_alignment() == []


@pytest.mark.parametrize("fixture", fixtures())
def test_the_shape_is_as_pinned(fixture: ScoreFixture):
    graph, _ = graph_and_warnings(fixture.slug)
    score = score_of(graph)
    heads = list(graph.score_lines(score))
    spanners = list(graph.nodes(MarkSpanner))
    shape = {
        "lines": len(heads),
        "chord_lines": sum(isinstance(head, ChordEvent) for head in heads),
        "parts": len(list(graph.score_parts(score))),
        "groups": len(list(graph.nodes(LineGroup))),
        "branches": len(list(graph.edges(EdgeType.BRANCHES))),
        "notes": len(list(graph.nodes(NoteEvent))),
        "divisions": len(list(graph.nodes(DivisionEvent))),
        "markings": len(list(graph.nodes(Marking))),
        "spanners": len(spanners),
        "ties": sum(spanner.mark is scoring.tie for spanner in spanners),
        "slurs": sum(spanner.mark is scoring.slur for spanner in spanners),
        "lyric_lines": len(list(graph.nodes(LyricSection))),
        "chords": len(list(graph.nodes(ChordEvent))),
        "grid_points": sum(len(graph.sync_points(s)) for s in graph.score_sync_lines(score)),
        "pins": len(list(graph.edges(EdgeType.SIMULTANEOUS))),
    }
    assert shape == dict(fixture.shape)


def test_the_corrected_companions_read_like_their_originals():
    """The edits (syllabic flags; hidden tempi) change no counts the shape pins."""
    for fixture in WITH_MUSICXML:
        if fixture.corrected is None:
            continue
        original, _ = graph_and_warnings(fixture.slug)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            corrected = read(fixture.corrected)
        for kind in (NoteEvent, DivisionEvent, LyricSection, Marking, MarkSpanner):
            assert len(list(corrected.nodes(kind))) == len(list(original.nodes(kind))), kind


def test_the_hymn_companion_hyphenates_as_the_page_does():
    fixture = FIXTURES["croft-o-god-our-help"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph = read(fixture.corrected)
    verse = next(s for s in graph.nodes(LyricSection) if s.section_number == 1)
    text = " ".join(str(s) for s in graph.walk_line(graph.spanner_start(verse)))
    assert text.startswith(
        "O God, our help in a - - ges past, our hope for years to come, our shel - - ter"
    )


def test_the_schubert_companion_has_one_printed_tempo():
    from openmusickit.objects.context_event import TempoEvent

    fixture = FIXTURES["schubert-allegretto-d915"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        graph = read(fixture.corrected)
    figures = [
        t
        for t in graph.nodes(TempoEvent)
        if t.tempo is not None and not t.meta.get("musicxml", {}).get("tempo_hidden")
    ]
    assert len(figures) == 2  # the Allegretto, once per staff line
    assert all(t.term is scoring.allegretto for t in figures)
    words = [t for t in graph.nodes(TempoEvent) if t.tempo is None]
    assert len(words) == 4 and all(t.term is scoring.a_tempo for t in words)
