"""The round-trip laws of `_plans/json-serialization.md` §6, over graphs of every
node type, edge kind and value type the vocabularies define (`any_graphs`):

- L1, document → graph → document: a canonical document reads back and writes the same text;
- L2, graph → document → graph: the same ids, endpoints, types, fields and metadata;
- L3, independence: the text depends on the graph's content alone,
  not on the adapter or the order things were added in;
- L4, canonical: the text is its own canonical form.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 graphs each.
"""

from hypothesis import given
from hypothesis import strategies as st

from openmusickit.graph.graph import OmkGraph
from openmusickit.io.omk_json import canonical, dumps, loads
from tests.graph.dict_adapter import DictAdapter
from tests.io.omk_json.identity import assert_same_graph
from tests.strategies import any_graphs


@given(any_graphs())
def test_l1_l2_l4_a_graph_and_its_document_round_trip_exactly(graph):
    """L1, L2 and L4 are checks on one round trip, so they share one generated graph
    (generating it is nearly all of the cost)."""
    text = dumps(graph)
    again = loads(text)
    assert dumps(again) == text  # L1
    assert_same_graph(graph, again)  # L2
    assert graph.is_equivalent(again)
    assert canonical.dumps(canonical.loads(text)) == text  # L4


@given(any_graphs(), st.randoms(use_true_random=False))
def test_l3_the_text_depends_on_the_content_alone(graph, rng):
    nodes = list(graph.nodes())
    edges = [(edge, *graph.edge_endpoints(edge)) for edge in graph.edges()]
    rng.shuffle(nodes)
    rng.shuffle(edges)
    elsewhere = OmkGraph(graph.meta, DictAdapter())
    elsewhere._add_objects(nodes, edges)
    assert dumps(elsewhere) == dumps(graph)
