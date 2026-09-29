"""Whether two graphs hold the same music, whatever the ids of their objects.

Two graphs are equivalent when their nodes pair off one to one, 
each with an equal node (`==`, which leaves out the id and `meta`), 
so that every ordered pair of nodes has equal edges in both graphs.
That is a graph isomorphism respecting content; the pairing is the `correspondence`. 
`GraphMeta` is not compared: it describes the container, not the music.

The comparison reads only the public `OmkGraph` API,
so the two graphs may sit on different adapters.

How it is found: 
equal nodes are given one colour, and a pairing is searched for (VF2, from rustworkx) among nodes of equal colour.
A short search nearly always finds one at once when there is one; a pairing found is proof.
When the short search gives up, each round of colour refinement
(one-dimensional Weisfeiler-Leman) recolours every node by its colour
and the colours and edges around it, with one palette across both graphs. 
If the graphs ever differ in how many nodes have a colour, they are not equivalent;
otherwise the search runs to the end among nodes of equal final colour.
Refinement is what keeps a *failed* comparison fast: 
on its own VF2 has to try every arrangement of symmetric material
(a run of identical notes, a set of identical fragments) before it can say no. 
What remains slow is only material that refinement cannot tell apart,
every node surrounded exactly as every other of its colour is,
and still not arranged the same way (two cycles of three identical notes against one of six).

`diff` says what one graph has that the other lacks, counted by content:
a multiset difference of nodes, and of edges taken with the content of their ends.
It never searches, so it is always cheap.
"""

from __future__ import annotations

import operator
from collections import Counter
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import rustworkx as rx

from openmusickit.graph.edge import OmkEdge
from openmusickit.objects.omk_object import OmkObject

if TYPE_CHECKING:
    from openmusickit.graph.graph import OmkGraph


@dataclass(frozen=True, slots=True)
class GraphDiff:
    """What changes from one graph to another, counted by content
    (see `OmkGraph.diff`).

    Where several equal nodes are in surplus, which of them is reported is
    arbitrary; an edge is reported with its source and target. `rearranged`
    is True when the counts all agree but the graphs are still not
    equivalent: the same things, wired differently among nodes of equal
    content, which a count cannot place.
    """

    removed_nodes: tuple[OmkObject, ...] = ()
    added_nodes: tuple[OmkObject, ...] = ()
    removed_edges: tuple[tuple[OmkObject, OmkEdge, OmkObject], ...] = ()
    added_edges: tuple[tuple[OmkObject, OmkEdge, OmkObject], ...] = ()
    rearranged: bool = False

    def __str__(self) -> str:
        lines = [f"- {node!r}" for node in self.removed_nodes]
        lines += [f"+ {node!r}" for node in self.added_nodes]
        lines += [f"- {s!r} --{e!r}--> {t!r}" for s, e, t in self.removed_edges]
        lines += [f"+ {s!r} --{e!r}--> {t!r}" for s, e, t in self.added_edges]
        if self.rearranged:
            lines.append("the same nodes and edges, arranged differently")
        return "\n".join(lines) if lines else "no differences"


class _Labelled:
    """A graph's nodes and edges, with the content class of each (shared with
    the graph it is being compared with), and its edges bundled by ordered
    pair of nodes: the bundle's label stands for the multiset of its edges'
    classes."""

    def __init__(self, graph: OmkGraph):
        self.nodes: list[OmkObject] = list(graph.nodes())
        position = {node.id: index for index, node in enumerate(self.nodes)}
        self.edges: list[tuple[int, OmkEdge, int]] = []
        for edge in graph.edges():
            source, target = graph.edge_endpoints(edge)
            self.edges.append((position[source.id], edge, position[target.id]))
        self.node_classes: list[int] = []
        self.edge_classes: list[int] = []
        self.bundles: dict[tuple[int, int], int] = {}


def _label(first: OmkGraph, second: OmkGraph) -> tuple[_Labelled, _Labelled]:
    """Both graphs, labelled with one set of classes."""
    a, b = _Labelled(first), _Labelled(second)
    node_classes = _classes(a.nodes + b.nodes)
    a.node_classes, b.node_classes = node_classes[: len(a.nodes)], node_classes[len(a.nodes) :]
    edge_classes = _classes([edge for _, edge, _ in a.edges + b.edges])
    a.edge_classes, b.edge_classes = edge_classes[: len(a.edges)], edge_classes[len(a.edges) :]
    bundle_labels: dict[tuple[int, ...], int] = {}
    for graph in (a, b):
        bundles: dict[tuple[int, int], list[int]] = {}
        for (source, _, target), edge_class in zip(graph.edges, graph.edge_classes, strict=True):
            bundles.setdefault((source, target), []).append(edge_class)
        for pair, classes in bundles.items():
            graph.bundles[pair] = _relabel(bundle_labels, tuple(sorted(classes)))
    return a, b


def _classes(items: Sequence[OmkObject | OmkEdge]) -> list[int]:
    """The class of each item under `==`, numbered in order of first appearance.

    Objects and edges are mutable and so unhashable: each item is compared
    with one representative of every class so far of its own type (dataclass
    equality is never true across types)."""
    representatives: dict[type, list[tuple[OmkObject | OmkEdge, int]]] = {}
    classes: list[int] = []
    count = 0
    for item in items:
        candidates = representatives.setdefault(type(item), [])
        for representative, item_class in candidates:
            if representative == item:
                classes.append(item_class)
                break
        else:
            candidates.append((item, count))
            classes.append(count)
            count += 1
    return classes


def _relabel(palette: dict[Hashable, int], signature: Hashable) -> int:
    """The number `palette` gives `signature`, a new one if it has none yet."""
    return palette.setdefault(signature, len(palette))


def _refine(a: _Labelled, b: _Labelled) -> tuple[list[int], list[int]] | None:
    """The stable colouring of both graphs, or None if at some round they do
    not have the same number of nodes of each colour (and so cannot be
    equivalent).

    Refinement only ever splits a colour, so the rounds stop when a round
    makes no more colours than the one before."""
    neighbourhoods = [_neighbourhoods(graph) for graph in (a, b)]
    colours = (a.node_classes, b.node_classes)
    count = len(set(colours[0]))
    while True:
        if Counter(colours[0]) != Counter(colours[1]):
            return None
        palette: dict[Hashable, int] = {}
        refined = (
            _recolour(colours[0], neighbourhoods[0], palette),
            _recolour(colours[1], neighbourhoods[1], palette),
        )
        if len(palette) == count:
            return colours
        count = len(palette)
        colours = refined


def _neighbourhoods(graph: _Labelled) -> list[tuple[list[tuple[int, int]], list[tuple[int, int]]]]:
    """For each node, its outgoing and its incoming bundles, as (bundle
    label, node at the other end)."""
    around: list[tuple[list[tuple[int, int]], list[tuple[int, int]]]] = [
        ([], []) for _ in graph.nodes
    ]
    for (source, target), label in graph.bundles.items():
        around[source][0].append((label, target))
        around[target][1].append((label, source))
    return around


def _recolour(
    colours: list[int],
    neighbourhoods: list[tuple[list[tuple[int, int]], list[tuple[int, int]]]],
    palette: dict[Hashable, int],
) -> list[int]:
    """One round of refinement: each node's colour, with the colours at the
    far ends of its bundles and the bundles' labels, becomes a new colour."""
    recoloured = []
    for colour, (outgoing, incoming) in zip(colours, neighbourhoods, strict=True):
        signature = (
            colour,
            tuple(sorted((label, colours[other]) for label, other in outgoing)),
            tuple(sorted((label, colours[other]) for label, other in incoming)),
        )
        recoloured.append(_relabel(palette, signature))
    return recoloured


_QUICK_SEARCH_STATES_PER_NODE = 10


def _correspondence(a: _Labelled, b: _Labelled) -> dict[UUID, UUID] | None:
    """The pairing, if there is one. A short search on content alone comes
    first: equivalent graphs are nearly always paired by it at once, and it
    spares them refinement, which needs a round per step along a run of
    identical notes. Only when it gives up (or there is no pairing) is the
    colouring refined and the search run to the end."""
    if len(a.nodes) != len(b.nodes) or len(a.edges) != len(b.edges):
        return None
    if Counter(a.node_classes) != Counter(b.node_classes):
        return None
    quick = _search(
        a, b, (a.node_classes, b.node_classes), _QUICK_SEARCH_STATES_PER_NODE * len(a.nodes)
    )
    if quick is not None:
        return quick
    colours = _refine(a, b)
    if colours is None:
        return None
    return _search(a, b, colours, call_limit=None)


def _search(
    a: _Labelled, b: _Labelled, colours: tuple[list[int], list[int]], call_limit: int | None
) -> dict[UUID, UUID] | None:
    """A pairing of nodes of equal colour that carries every bundle onto an
    equal one (VF2), or None if there is none or `call_limit` states were
    visited without finding one."""
    first, second = _digraph(a, colours[0]), _digraph(b, colours[1])
    mappings = rx.vf2_mapping(
        first, second, operator.eq, operator.eq, id_order=False, call_limit=call_limit
    )
    mapping = next(iter(mappings), None)
    if mapping is None:
        return None
    return {a.nodes[i].id: b.nodes[j].id for i, j in mapping.items()}


def _digraph(graph: _Labelled, colours: list[int]) -> rx.PyDiGraph:
    """A rustworkx graph of colours, one edge per bundle carrying its label;
    node index i is `graph.nodes[i]`."""
    digraph = rx.PyDiGraph()
    digraph.add_nodes_from(colours)
    digraph.add_edges_from([(s, t, label) for (s, t), label in graph.bundles.items()])
    return digraph


def correspondence(first: OmkGraph, second: OmkGraph) -> dict[UUID, UUID] | None:
    """The id of each node of `first` paired with the id of its equal in
    `second`, or None if the graphs are not equivalent (see `OmkGraph.correspondence`)."""
    return _correspondence(*_label(first, second))


def diff(first: OmkGraph, second: OmkGraph) -> GraphDiff:
    """What changes from `first` to `second`, by content (see `OmkGraph.diff`)."""
    a, b = _label(first, second)
    edge_keys = [
        [
            (graph.node_classes[s], edge_class, graph.node_classes[t])
            for (s, _, t), edge_class in zip(graph.edges, graph.edge_classes, strict=True)
        ]
        for graph in (a, b)
    ]
    edges = [
        [(graph.nodes[s], edge, graph.nodes[t]) for s, edge, t in graph.edges] for graph in (a, b)
    ]
    found = GraphDiff(
        removed_nodes=_surplus(a.nodes, a.node_classes, b.node_classes),
        added_nodes=_surplus(b.nodes, b.node_classes, a.node_classes),
        removed_edges=_surplus(edges[0], edge_keys[0], edge_keys[1]),
        added_edges=_surplus(edges[1], edge_keys[1], edge_keys[0]),
    )
    if any((found.removed_nodes, found.added_nodes, found.removed_edges, found.added_edges)):
        return found
    return GraphDiff(rearranged=_correspondence(a, b) is None)


def _surplus[T](
    items: Sequence[T], keys: Sequence[Hashable], other_keys: Sequence[Hashable]
) -> tuple[T, ...]:
    """The items whose key occurs more often in `keys` than in `other_keys`:
    as many of each as the excess, the first ones found."""
    excess = Counter(keys) - Counter(other_keys)
    surplus = []
    for item, key in zip(items, keys, strict=True):
        if excess[key] > 0:
            surplus.append(item)
            excess[key] -= 1
    return tuple(surplus)
