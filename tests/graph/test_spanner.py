"""Spanners: STARTS_AT and ENDS_AT, and the open spanner that has only a start."""

import pytest

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.lyrics import LyricSyllable
from openmusickit.objects.marking import MarkSpanner
from openmusickit.objects.part import Part, Stint
from openmusickit.systems.wsmn.scoring.symbols import slur, sustain_pedal, una_corda
from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F
from tests.graph.helpers import notes


@pytest.fixture
def line():
    graph = OmkGraph(GraphMeta())
    events = notes(C, D, E, F)
    graph.add_line(events)
    return graph, events


def test_a_closed_spanner_has_both_ends(line):
    graph, (c, d, e, f) = line
    arc = MarkSpanner(mark=slur)
    graph.add_spanner(arc, c, e)
    assert graph.spanner_start(arc) is c and graph.spanner_end(arc) is e


def test_an_open_spanner_has_a_start_and_no_end(line):
    graph, (c, d, e, f) = line
    pedal = MarkSpanner(mark=sustain_pedal)
    graph.add_spanner(pedal, d)
    assert graph.spanner_start(pedal) is d
    assert graph.spanner_end(pedal) is None
    assert [edge.type for edge in graph.edges(EdgeType.STARTS_AT)] == [EdgeType.STARTS_AT]
    assert list(graph.edges(EdgeType.ENDS_AT)) == []


def test_a_spanner_with_no_start_is_an_error(line):
    graph, _ = line
    soft = MarkSpanner(mark=una_corda)
    graph.add_node(soft)
    with pytest.raises(GraphError):
        graph.spanner_start(soft)


def test_an_open_spanner_can_be_undone(line):
    graph, (c, d, e, f) = line
    pedal = MarkSpanner(mark=sustain_pedal)
    graph.add_spanner(pedal, d)
    graph.remove_node(pedal)
    assert list(graph.edges()) == [edge for edge in graph.edges(EdgeType.NEXT)]


def test_materialize_copies_an_open_spanner_that_starts_inside_the_stint(line):
    graph, (c, d, e, f) = line
    pedal = MarkSpanner(mark=sustain_pedal)
    graph.add_spanner(pedal, d)
    stint = Stint()
    graph.add_stint(Part(name="Oboe"), stint, c, e)
    head = graph.materialize(stint)
    copied = [n for n in graph.nodes(MarkSpanner) if n is not pedal]
    assert len(copied) == 1
    copied_start = graph.spanner_start(copied[0])
    assert copied_start is not d and copied_start == d
    assert graph.spanner_end(copied[0]) is None
    assert graph.get_previous(head) is None


def test_an_open_binding_span_binds_to_the_end_of_the_line(line):
    """A slur with no end is a melisma to the end of the line: the syllable
    begun on its first note is sung through every note after."""
    graph, (c, d, e, f) = line
    graph.add_spanner(MarkSpanner(mark=slur), d)
    syllables = graph.add_lyrics("A-men, a-men")
    graph.zip_lyrics_to_objects(syllables[0], c)
    sung = [
        [str(s) for s in graph._graph.successors(note, LyricSyllable, EdgeType.LYRIC)]
        for note in (c, d, e, f)
    ]
    assert sung == [["A -"], ["- men,"], [], []]
