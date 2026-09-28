"""Ranks and rows: what shares a column, what comes after what, what goes
above what, on the example fixture and on small graphs built for one rule.
See _plans/graph-visualization.md §2.2."""

import pytest

from openmusickit.graph.edge import EdgeType, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import OmkObject
from openmusickit.objects.part import LineGroup
from openmusickit.objects.score import Score
from openmusickit.systems.wsmn.temporal.symbols import half, quarter, whole
from openmusickit.systems.wsmn.tonal.symbols import A, C, D, E, F, G, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.visualization import GraphRenderer, SequenceDirection, VisualizationConfig
from tests.graph.helpers import notes
from tests.visualization.dot_helpers import column, column_of, edge, edges, end_id, nid, node


def model_of(graph, **config):
    return GraphRenderer(graph, VisualizationConfig(**config)).dot_graph()


def fresh(*lines):
    graph = OmkGraph(GraphMeta())
    for line in lines:
        graph.add_line(line)
    return graph


# --- ranks --------------------------------------------------------------------------------


def test_a_next_chain_of_known_durations_gets_consecutive_ranks():
    line = notes(C, D, E)
    model = model_of(fresh(line))
    ranks = [column_of(model, nid(n)) for n in line]
    assert ranks == [ranks[0], ranks[0] + 1, ranks[0] + 2]


def test_a_zero_duration_clef_precedes_its_note(twinkle):
    model = model_of(twinkle.graph)
    assert column_of(model, nid(twinkle.melody[0])) == column_of(model, nid(twinkle.clef)) + 1


@pytest.mark.parametrize("direction", list(SequenceDirection))
def test_direction_sets_rankdir(twinkle, direction):
    model = model_of(twinkle.graph, direction=direction)
    assert model.attrs["rankdir"] == direction.value


def test_timing_aligns_what_the_pin_implies(twinkle):
    """The chord line is pinned at the first note only; the other chords land
    on the notes their durations put them over."""
    model = model_of(twinkle.graph)
    melody, chords = twinkle.melody, twinkle.chords
    assert column_of(model, nid(chords[0])) == column_of(model, nid(melody[0]))
    assert column_of(model, nid(chords[1])) == column_of(model, nid(melody[4]))
    assert column_of(model, nid(chords[2])) == column_of(model, nid(melody[6]))


def test_a_displaced_pin_aligns_by_timing_and_labels_the_edge():
    melody = notes(C, D, E)
    chords = [ChordEvent(chord=C(maj), duration=whole)]
    graph = fresh(melody, chords)
    graph.add_simultaneous(melody[1], chords[0], displacement=-quarter)
    model = model_of(graph)
    assert column_of(model, nid(chords[0])) == column_of(model, nid(melody[0]))
    pin = edge(model, nid(melody[1]), nid(chords[0]))
    assert pin.attrs["label"] == "-1/4"
    assert pin.attrs["constraint"] == "false"


def test_an_offset_anchored_branch_starts_where_the_parent_ends():
    melody = notes(C, D, duration=half)
    voice = notes(A, duration=half)
    graph = fresh(melody, voice)
    graph.add_branch(melody[0], voice[0], anchor=TimingAnchor.OFFSET)
    model = model_of(graph)
    assert column_of(model, nid(voice[0])) == column_of(model, nid(melody[1]))
    assert edge(model, nid(melody[0]), nid(voice[0])).attrs["label"] == "from offset"


def test_a_branched_eighth_gets_a_column_of_its_own(twinkle):
    model = model_of(twinkle.graph)
    first, second = (column_of(model, nid(n)) for n in twinkle.voice)
    assert first == column_of(model, nid(twinkle.melody[4]))
    assert (
        column_of(model, nid(twinkle.melody[4])) < second < column_of(model, nid(twinkle.melody[5]))
    )


def test_attachments_share_their_events_column(twinkle):
    model = model_of(twinkle.graph)
    for syllable, note_event in zip(twinkle.syllables, twinkle.melody, strict=True):
        assert column_of(model, nid(syllable)) == column_of(model, nid(note_event))
    assert column_of(model, nid(twinkle.staccato)) == column_of(model, nid(twinkle.melody[2]))
    assert column_of(model, nid(twinkle.slur)) == column_of(model, nid(twinkle.melody[4]))
    assert column_of(model, end_id(twinkle.slur)) == column_of(model, nid(twinkle.melody[5]))
    assert column_of(model, nid(twinkle.verse)) == column_of(model, nid(twinkle.syllables[0]))
    assert column_of(model, end_id(twinkle.verse)) == column_of(model, nid(twinkle.syllables[-1]))


def test_a_groups_heads_and_the_group_share_a_rank():
    right, left = notes(C, D), notes(E, F)
    graph = fresh(right, left)
    group = LineGroup(name="Piano")
    graph.add_group(group, [right[0], left[0]])
    model = model_of(graph)
    assert (
        column_of(model, nid(right[0]))
        == column_of(model, nid(left[0]))
        == column_of(model, nid(group))
    )


def test_sync_points_rank_with_their_events_and_the_bar_spans_the_graph(twinkle):
    model = model_of(twinkle.graph)
    p5, p9, p12 = twinkle.points
    assert column_of(model, nid(p5)) == column_of(model, nid(twinkle.melody[0]))
    assert column_of(model, nid(p9)) == column_of(model, nid(twinkle.melody[4]))
    assert (
        column_of(model, nid(p9))
        < column_of(model, nid(p12))
        < column_of(model, end_id(twinkle.reel))
    )
    assert column_of(model, nid(twinkle.reel)) == 0
    assert column_of(model, end_id(twinkle.reel)) == len(model.ranks) - 1


def test_the_bar_is_a_chain_of_unclipped_port_edges(twinkle):
    model = model_of(twinkle.graph)
    sequence = [nid(twinkle.reel), *(nid(p) for p in twinkle.points), end_id(twinkle.reel)]
    for a, b in zip(sequence, sequence[1:], strict=False):
        bar = edge(model, a, b)
        assert (bar.source_port, bar.target_port) == ("bar", "bar")
        assert bar.attrs["tailclip"] == bar.attrs["headclip"] == "false"
        assert "constraint" not in bar.attrs
        assert bar.attrs["arrowhead"] == "none"
        assert bar.attrs["class"] == "omk-edge sync-bar"
    for node_id in sequence:
        assert node(model, node_id).attrs["group"] == nid(twinkle.reel)
    for point in twinkle.points:
        assert edges(model, nid(twinkle.reel), nid(point)) == [] or point is twinkle.points[0]


def test_a_sync_lines_contains_edges_are_not_drawn(twinkle):
    model = model_of(twinkle.graph)
    drawn = {e.attrs.get("class") for e in model.edges if e.source == nid(twinkle.reel)}
    assert drawn == {"omk-edge sync-bar"}


def test_after_an_unknown_duration_ranks_follow_next_and_pins_still_align():
    melody = notes(C, D, E)
    melody[1].duration = None
    other = notes(A, G)
    graph = fresh(melody, other)
    graph.add_simultaneous(melody[2], other[0])
    model = model_of(graph)
    assert column_of(model, nid(melody[2])) == column_of(model, nid(melody[1])) + 1
    assert column_of(model, nid(other[0])) == column_of(model, nid(melody[2]))


def test_the_stint_and_the_part_come_before_the_head(twinkle):
    model = model_of(twinkle.graph)
    head = column_of(model, nid(twinkle.clef))
    assert column_of(model, nid(twinkle.stint)) == head - 1
    assert column_of(model, nid(twinkle.singer)) == head - 2
    assert "constraint" not in edge(model, nid(twinkle.stint), nid(twinkle.clef)).attrs
    assert "constraint" not in edge(model, nid(twinkle.singer), nid(twinkle.stint)).attrs


def test_pins_that_disagree_still_yield_ranks():
    one, two = notes(C, D, E), notes(A, G)
    graph = fresh(one, two)
    graph.add_simultaneous(one[0], two[1])
    graph.add_simultaneous(one[2], two[0])
    model = model_of(graph)
    for event in one + two:
        column_of(model, nid(event))


RELATIONAL = [
    EdgeType.ACCOMPANIES,
    EdgeType.HARMONIZES,
    EdgeType.VARIATION_OF,
    EdgeType.DERIVATIVE_OF,
    EdgeType.REFERENCES,
    EdgeType.IMPLEMENTS,
    EdgeType.REALIZES,
    EdgeType.USER_DEFINED,
]


@pytest.mark.parametrize("edge_type", RELATIONAL, ids=lambda t: t.name)
def test_a_relational_edge_is_free_and_labelled_with_its_type(edge_type):
    one, two = notes(C), notes(D)
    graph = fresh(one, two)
    graph.add_edge(one[0], two[0], edge_type)
    drawn = edge(model_of(graph), nid(one[0]), nid(two[0]))
    assert drawn.attrs["constraint"] == "false"
    assert drawn.attrs["label"] == edge_type.value.replace("_", " ")


def test_the_spine_orders_the_columns(twinkle):
    model = model_of(twinkle.graph)
    spines = [f"_spine_{r}" for r in range(len(model.ranks))]
    for rank, spine in enumerate(spines):
        assert model.ranks[rank][-1] == spine
        assert node(model, spine).attrs["style"] == "invis"
    for a, b in zip(spines, spines[1:], strict=False):
        assert edge(model, a, b).attrs == {"style": "invis"}


# --- the score ---------------------------------------------------------------------------


def test_one_connected_score_is_the_title_block(twinkle):
    model = model_of(twinkle.graph)
    assert model.attrs["label"].startswith("<<TABLE")
    assert "Twinkle, Twinkle, Little Star" in model.attrs["label"]
    assert (model.attrs["labelloc"], model.attrs["labeljust"]) == ("t", "r")
    assert all(n.id != nid(twinkle.score) for n in model.nodes)
    assert all(e.source != nid(twinkle.score) for e in model.edges)


def test_a_score_with_material_outside_it_is_a_legend_above_its_earliest_head(twinkle):
    twinkle.graph.add_line(notes(G, A))
    model = model_of(twinkle.graph)
    assert "label" not in model.attrs
    assert column_of(model, nid(twinkle.score)) == column_of(model, nid(twinkle.clef))
    assert column(model, nid(twinkle.clef)).index(nid(twinkle.score)) < column(
        model, nid(twinkle.clef)
    ).index(nid(twinkle.clef))
    assert node(model, nid(twinkle.score)).attrs["label"].startswith("<<TABLE")
    assert all(e.source != nid(twinkle.score) for e in model.edges)


def test_two_scores_are_two_legends():
    one, two = notes(C, D), notes(E, F)
    graph = fresh(one, two)
    first, second = Score(title="One"), Score(title="Two")
    graph.add_line_to_score(first, one[0])
    graph.add_line_to_score(second, two[0])
    model = model_of(graph)
    assert "label" not in model.attrs
    assert column_of(model, nid(first)) == column_of(model, nid(one[0]))
    assert column_of(model, nid(second)) == column_of(model, nid(two[0]))


# --- spanners ------------------------------------------------------------------------------


def test_a_spanner_is_a_start_marker_and_an_end_marker(twinkle):
    model = model_of(twinkle.graph)
    assert node(model, nid(twinkle.slur)).attrs["label"] == "⌈slur"
    assert node(model, end_id(twinkle.slur)).attrs["label"] == "slur⌉"
    assert node(model, nid(twinkle.verse)).attrs["label"] == "⌊verse 1"
    assert node(model, end_id(twinkle.verse)).attrs["label"] == "verse 1⌋"
    assert edges(model, nid(twinkle.slur), nid(twinkle.melody[5])) == []
    assert (
        edge(model, end_id(twinkle.slur), nid(twinkle.melody[5])).attrs["class"]
        == "omk-edge ends_at"
    )


# --- rows ----------------------------------------------------------------------------------


def test_rows_in_the_first_column(twinkle):
    model = model_of(twinkle.graph)
    p5 = twinkle.points[0]
    assert column(model, nid(twinkle.melody[0])) == [
        nid(twinkle.chords[0]),
        nid(twinkle.melody[0]),
        nid(twinkle.syllables[0]),
        nid(twinkle.verse),
        nid(p5),
    ]


def test_rows_where_the_branch_and_the_slur_begin(twinkle):
    model = model_of(twinkle.graph)
    assert column(model, nid(twinkle.melody[4])) == [
        nid(twinkle.chords[1]),
        nid(twinkle.slur),
        nid(twinkle.melody[4]),
        nid(twinkle.voice[0]),
        nid(twinkle.syllables[4]),
        nid(twinkle.points[1]),
    ]


def test_a_mark_sits_just_above_its_note(twinkle):
    model = model_of(twinkle.graph)
    assert column(model, nid(twinkle.melody[2])) == [
        nid(twinkle.staccato),
        nid(twinkle.melody[2]),
        nid(twinkle.syllables[2]),
    ]


def test_a_higher_branch_goes_above_its_parent():
    melody = notes(C, D)
    voice = [NoteEvent(tones={TonalVector.from_string("G5")}, duration=quarter)]
    graph = fresh(melody, voice)
    graph.add_branch(melody[0], voice[0])
    assert column(model_of(graph), nid(melody[0])) == [nid(voice[0]), nid(melody[0])]


def test_an_unpitched_branch_goes_below_its_parent():
    melody = notes(C, D)
    voice = [Rest(quarter)]
    graph = fresh(melody, voice)
    graph.add_branch(melody[0], voice[0])
    assert column(model_of(graph), nid(melody[0])) == [nid(melody[0]), nid(voice[0])]


def test_another_note_line_pinned_to_a_line_goes_below_it():
    one, two = notes(C, D), notes(E, F)
    graph = fresh(one, two)
    graph.add_simultaneous(one[0], two[0])
    assert column(model_of(graph), nid(one[0])) == [nid(one[0]), nid(two[0])]


def test_the_same_rows_come_out_top_to_bottom(twinkle):
    left_to_right = model_of(twinkle.graph).ranks
    top_to_bottom = model_of(twinkle.graph, direction=SequenceDirection.TOP_TO_BOTTOM).ranks
    assert left_to_right == top_to_bottom


def test_every_chain_member_carries_its_heads_id_as_group(twinkle):
    model = model_of(twinkle.graph)
    for event in twinkle.melody:
        assert node(model, nid(event)).attrs["group"] == nid(twinkle.clef)
    for event in twinkle.voice:
        assert node(model, nid(event)).attrs["group"] == nid(twinkle.voice[0])
    assert "group" not in node(model, nid(twinkle.staccato)).attrs


# --- what is drawn ---------------------------------------------------------------------------


def test_every_node_appears_once_in_the_nodes_and_once_in_the_ranks(twinkle):
    model = model_of(twinkle.graph)
    drawn = [n.id for n in model.nodes]
    assert len(drawn) == len(set(drawn))
    ranked = [i for column_ids in model.ranks for i in column_ids]
    assert sorted(ranked) == sorted(drawn)
    expected = {nid(o) for o in twinkle.graph.nodes() if o is not twinkle.score}
    expected |= {end_id(twinkle.slur), end_id(twinkle.verse), end_id(twinkle.reel)}
    expected |= {f"_spine_{r}" for r in range(len(model.ranks))}
    assert set(drawn) == expected


def test_lyric_next_edges_are_invisible_and_note_next_edges_solid(twinkle):
    model = model_of(twinkle.graph)
    for a, b in zip(twinkle.syllables, twinkle.syllables[1:], strict=False):
        assert edge(model, nid(a), nid(b)).attrs["style"] == "invis"
    for a, b in zip(twinkle.melody, twinkle.melody[1:], strict=False):
        assert edge(model, nid(a), nid(b)).attrs["style"] == "solid"
        assert "constraint" not in edge(model, nid(a), nid(b)).attrs


def test_every_drawn_edge_is_free_unless_it_sequences(twinkle):
    model = model_of(twinkle.graph)
    sequencing = {"omk-edge next", "omk-edge performs", "omk-edge sync-bar"}
    for drawn in model.edges:
        kind = drawn.attrs.get("class")
        if kind is None:  # the spine
            continue
        if kind in sequencing or drawn.source == nid(twinkle.stint):
            assert "constraint" not in drawn.attrs, kind
        else:
            assert drawn.attrs["constraint"] == "false", kind


def test_nodes_and_edges_carry_ids_and_classes(twinkle):
    model = model_of(twinkle.graph)
    first = node(model, nid(twinkle.melody[0]))
    assert first.attrs["id"] == nid(twinkle.melody[0])
    assert first.attrs["class"].split() == ["omk-node", "NoteEvent", "SequentialEvent", "OmkObject"]
    following = edge(model, nid(twinkle.melody[0]), nid(twinkle.melody[1]))
    assert following.attrs["class"] == "omk-edge next"
    assert following.attrs["id"] == str(
        twinkle.graph.get_edge(twinkle.melody[0], twinkle.melody[1], EdgeType.NEXT).id
    )


def test_an_unknown_class_still_appears():
    graph = OmkGraph(GraphMeta())
    thing = OmkObject()
    graph.add_node(thing)
    model = model_of(graph)
    assert node(model, nid(thing)).attrs["label"] == "OmkObject"
    assert column_of(model, nid(thing)) == 0
