# Graph equivalence: `is_equivalent`, `correspondence`, `diff`

## Context

Roundtrip testing needs to ask whether two `OmkGraph`s hold the same music
when their objects are different objects with different ids.
Examples: a graph built twice, a graph after export/import,
or a graph copied onto another adapter.
Today the only comparison is `tests/graph/helpers.py:snapshot`.
It keys on ids, so it only works when both graphs hold the *same* objects.

"Same music" means a graph isomorphism:
a one-to-one pairing of nodes where
- paired nodes are `==`, and
- every ordered pair of nodes has the same edges in both graphs, compared with `==`.

`OmkObject.__eq__` and `OmkEdge.__eq__` already leave out `_id` and `meta`,
and they compare the exact class, so `Next` ≠ `OmkEdge(type=NEXT)`
and `Contains` ≠ a Score's plain CONTAINS edge.
The equivalence adds nothing to them.

Decisions confirmed with the developer:
- All `meta` is ignored: object, edge and `GraphMeta`.
  This follows `__eq__`.
  A test that cares checks `a.meta == b.meta`,
  or checks per-node meta through `correspondence`.
- The API is `is_equivalent`, `correspondence` and `diff`.
  It is not `__eq__`.
- The diff is a content-level multiset difference.
  There is no subgraph-embedding search.

## Why not just `rustworkx.is_isomorphic` (measured)

VF2 with `==` matchers is instant on isomorphic graphs (a 1000-note line plus marks: 4 ms).
It is exponential when it has to *refute* a symmetric graph,
and refuting is exactly the case where a roundtrip test fails:
- 10 identical isolated notes plus one differing node: 1.9 s. 12 notes: did not finish.
- 10 identical lines × 20 identical notes, with one note changed: 0.9 s.

Rustworkx's own multigraph handling is correct:
swapped parallel edges match, `{S,E}` vs `{S,S}` does not, and self-loops are compared.
We still bundle parallel edges ourselves, because colour refinement needs it anyway.

**Approach: colour refinement (1-dimensional Weisfeiler–Leman) first, then VF2 on the refined colours.**
Refinement refutes soundly and in near-linear time:
if the colour histograms differ, the graphs are not isomorphic.
It handles every pathological case above.
VF2 then runs with integer colours as labels.
It returns a mapping, which is a certificate, whenever the graphs are equivalent.
The residual risk is highly regular graphs that refinement cannot split and VF2 must refute,
for example two 3-cycles vs one 6-cycle of identical notes.
Cycles force the chain once a start is chosen, so this is O(n²), not exponential.
The docstring will state the worst case honestly.

The comparison reads only the public `OmkGraph` API
(`nodes()`, `edges()`, `edge_endpoints()`).
So it works across adapters, e.g. `RustworkxAdapter` vs the test `DictAdapter`.
Rustworkx is used as an algorithm library on a snapshot, not through the adapter.

## Implementation

### New module `src/openmusickit/graph/equivalence.py`

It is separate from `graph.py` (1,800 lines) because it is a self-contained algorithm.

- `_Snapshot` (private): the graph's nodes as a list,
  plus `bundles: dict[tuple[int, int], dict[EdgeType, OmkEdge]]`,
  which holds the edges of each ordered node pair keyed by type.
  The adapter contract allows at most one edge per type per pair,
  so dict `==` compares two bundles exactly.
  Built from `graph.nodes()`, `graph.edges()` and `graph.edge_endpoints(edge)`.
- `_classes(items) -> list[int]` (private): partitions items by `==` into class ids.
  It buckets by `type(item)` first, then scans that type's representatives with `==`.
  This is needed because OmkObjects are unhashable, and `==` is an equivalence relation.
  Durations across temporal systems compare `False`, not raise (checked).
  It is used on the nodes of both graphs together, on bundles, and on single edges (for the diff).
- `_refine(a, b)`: runs colour refinement over both snapshots with shared colour numbering.
  - Round 0 colour is the node's content class.
  - Round k+1 colour is (own colour, sorted out-signature, sorted in-signature).
    Each signature entry is (bundle class, neighbour colour).
    Tuples are relabelled to ints through a dict shared by both graphs.
  - It stops when the class count stops growing.
  - It returns the final colours, or `None` as soon as the per-graph histograms differ.
- `correspondence(a, b) -> dict[UUID, UUID] | None`:
  1. Cheap exits: node and edge counts.
  2. Run `_refine`.
  3. Build two `rx.PyDiGraph`s with node payload = colour and edge payload = bundle class.
  4. Take `next(rx.vf2_mapping(ga, gb, operator.eq, operator.eq, id_order=False), None)`.
  5. Map the indices back to node ids.
- `GraphDiff`: a frozen dataclass relative to `a` (read "a → b").
  - `removed_nodes` / `added_nodes` are `tuple[OmkObject, ...]`.
  - `removed_edges` / `added_edges` are `tuple[tuple[OmkObject, OmkEdge, OmkObject], ...]` (source, edge, target).
  - `rearranged: bool` is True when every multiset matches but the graphs are still not equivalent.
    That means the same things wired differently among equal-content nodes, which the diff cannot place.
  - A `__str__` gives `-`/`+` lines, for readable `assert a.is_equivalent(b), a.diff(b)` failures.
- `diff(a, b) -> GraphDiff`:
  - Nodes: take the multiset difference by content class.
    Report actual objects from the graph that has the surplus.
    Which of several equal nodes gets reported is arbitrary, and the docstring says so.
  - Edges: the key is (source content class, edge class, target content class), per single edge.
  - `rearranged` is `not any(...) and correspondence(a, b) is None`.

### `OmkGraph` methods (`src/openmusickit/graph/graph.py`)

These are thin wrappers, placed in a new `# Comparison` section after `edge_endpoints` / `nodes`.
Each gets a one-line docstring and a short doctest (two notes built twice → `True`; a changed tone → `False` and a readable diff):
- `is_equivalent(self, other: OmkGraph) -> bool`
- `correspondence(self, other: OmkGraph) -> dict[UUID, UUID] | None`
  (the node id in `self` → the equal node id in `other`)
- `diff(self, other: OmkGraph) -> GraphDiff`

`graph.py` imports from `equivalence`.
`equivalence.py` imports `OmkGraph` only under `TYPE_CHECKING`, to avoid a cycle.

### Exports and docs

- `src/openmusickit/graph/__init__.py`: import the module, add `equivalence` and `GraphDiff` to `__all__`,
  and add one sentence to the package docstring.
  (`tests/test_namespace.py` checks that exports resolve.)
- `docs/_quarto.yml`: add `graph.equivalence` to the graph reference section.
- `CHANGELOG.md`: add a line, if it has an unreleased section in use.

## Tests: `tests/graph/test_equivalence.py`

The helper in `tests/graph/helpers.py` is `fork_graph(graph, engine=None) -> OmkGraph`.
It rebuilds a graph with fresh-id copies of every node and edge,
using `copy.deepcopy` + a new `_id`, like `graph._fork`,
and adds through `graph._graph.add_edge`, which the tests already reach into.

Examples:
- Equivalent graphs:
  - A graph with every structure (lines, branch, pin, group, stint, spanner, lyrics, sync line)
    is equivalent to its fork, and to its fork on `DictAdapter` (cross-adapter).
  - The correspondence pairs equal nodes.
  - Meta differences (object, edge, `GraphMeta`) don't matter.
  - An empty graph is equivalent to an empty graph.
- One-change negatives, each asserting the exact diff:
  - a tone changed;
  - a duration changed;
  - a marking dropped;
  - an extra pin;
  - `Contains` vs plain CONTAINS;
  - displacement, anchor or `origin` differs;
  - an edge reversed;
  - a staccato moved between different notes.
- Parallel edges: a spanner over one note (STARTS_AT + ENDS_AT to the same node).
- A self-loop cycle.
- `rearranged`: a staccato moved between two equal notes in positions that differ structurally.
- The measured pathologies must refute and finish:
  - 13 identical isolated notes plus an odd one;
  - 20 lines × 20 identical notes with one changed.
- A `slow`-marked scale check: a fork of a 2,000-event line with marks, and the same with one change.

Hypothesis properties, using `tests/strategies.py` (`lines`, `note_events`):
- `g.is_equivalent(fork_graph(g))` holds on both adapters.
- `correspondence` is a genuine isomorphism, checked independently:
  it is a bijection, paired nodes are `==`, and the edge bundles of every mapped pair are `==`.
- Symmetry: `a.is_equivalent(b) == b.is_equivalent(a)`.
- `diff(a, b)` mirrors `diff(b, a)`.
- The diff with a fork is empty.
- Changing one node's content in a fork gives not-equivalent and a non-empty diff.

State machine (`tests/graph/test_graph_state_machine.py`):
add one invariant, `self.rx.is_equivalent(self.ref)`.
It runs the cross-adapter path on every step at almost no cost.

## Execution

1. Run the heavy set as a baseline: `uv run pytest --hypothesis-profile=thorough -m ""`.
2. Commit 1: the `equivalence` module with `correspondence` / `is_equivalent`, the OmkGraph methods, exports, and tests.
   `Claude: OmkGraph.is_equivalent and correspondence; tests`
3. Commit 2: `GraphDiff` and `diff`, with tests.
   `Claude: OmkGraph.diff and GraphDiff; tests`
4. Run the heavy set again. Copy this plan to `_plans/graph-equivalence.md`.

## Verification

- `uv run pytest` (fast set, doctests included).
- `uv run pytest tests/graph/test_equivalence.py -m ""` (includes the slow scale check).
- `uv run pytest -q -o addopts="" tests --cov=openmusickit --cov-report=term-missing`
  to confirm `equivalence.py` is covered.
- By hand: `uv run python -c` builds a graph and its fork, then prints `a.diff(b)` after changing one note.
  This eyeballs the `__str__` output.

## Deviation during execution

Measured after the first cut: an *equivalent* pair of 2,000-note lines of identical notes took 7 s,
because refinement needs about n/2 rounds to settle a run of identical notes.
`_correspondence` now starts with a short VF2 search on content colours alone,
capped at 10 states per node.
A pairing it finds is proof, and it found one at once in every case measured (0.06 s for that pair).
Only when it gives up does refinement run, followed by the unbounded search.
Refuting a mark moved within that line still takes about 1 s (refinement).
The work went in as one commit rather than two: the diff shares the labelling code.
CHANGELOG.md was left alone because it has no section in use.
