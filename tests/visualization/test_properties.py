"""Laws of the layout over random lines: ranks follow the line, two events
share a column exactly when their onsets coincide, and the ranks partition
the picture. Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 examples."""

from hypothesis import given
from hypothesis import strategies as st

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.visualization import GraphRenderer
from tests.strategies import lines, metrical_durations
from tests.visualization.dot_helpers import column_of, nid


def model_of(graph):
    return GraphRenderer(graph).dot_graph()


@given(lines())
def test_ranks_increase_along_a_line_and_are_consecutive_when_durations_are_known(line):
    graph = OmkGraph(GraphMeta())
    graph.add_line(line)
    model = model_of(graph)
    ranks = [column_of(model, nid(event)) for event in line]
    assert ranks == sorted(ranks) and len(set(ranks)) == len(ranks)
    if all(event.duration is not None for event in line):
        assert ranks == list(range(ranks[0], ranks[0] + len(line)))


@given(
    lines(min_size=2),
    lines(min_size=2),
    st.data(),
)
def test_two_events_share_a_column_iff_their_onsets_coincide(one, two, data):
    graph = OmkGraph(GraphMeta())
    graph.add_line(one)
    graph.add_line(two)
    at = data.draw(st.integers(0, len(one) - 1))
    other = data.draw(st.integers(0, len(two) - 1))
    anchor = data.draw(st.sampled_from(list(TimingAnchor)))
    displacement = data.draw(st.none() | metrical_durations())
    graph.add_simultaneous(one[at], two[other], anchor=anchor, displacement=displacement)
    model = model_of(graph)
    for x in one:
        for y in two:
            try:
                distance = graph.relative_onset(x, y)
            except GraphError:
                continue  # no timing path: nothing is claimed about their columns
            same = column_of(model, nid(x)) == column_of(model, nid(y))
            assert same == (distance.rational_length == 0), (x, y, distance)


@given(lines(min_size=2), lines(min_size=1), st.data())
def test_ranks_partition_the_picture_and_next_advances(one, two, data):
    graph = OmkGraph(GraphMeta())
    graph.add_line(one)
    graph.add_line(two)
    graph.add_simultaneous(
        one[data.draw(st.integers(0, len(one) - 1))], two[data.draw(st.integers(0, len(two) - 1))]
    )
    model = model_of(graph)
    ranked = [node_id for column in model.ranks for node_id in column]
    assert len(ranked) == len(set(ranked))
    assert set(ranked) == {node.id for node in model.nodes}
    for edge in graph.edges(EdgeType.NEXT):
        source, target = graph.edge_endpoints(edge)
        assert column_of(model, nid(source)) < column_of(model, nid(target))
