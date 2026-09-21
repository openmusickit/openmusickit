"""A dict-backed `GraphAdapter`: the reference implementation the contract
tests run beside `RustworkxAdapter`, and the model the graph state machine
compares against. It lives in `tests/`, not `src/`: a test oracle, not a
backend.

Everything is keyed by `str(id)`. The two contract rules (`GraphError` on a
second edge of the same type between two nodes; NEXT is one in and one out)
are enforced in `add_edge`; an unknown node or edge is a `GraphError`
everywhere except `get_node`, which answers `None`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from uuid import UUID

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, OmkEdge
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.objects.omk_object import OmkObject


def _key(item: OmkObject | OmkEdge | UUID | str) -> str:
    return str(item.id) if isinstance(item, OmkObject | OmkEdge) else str(item)


class DictAdapter(GraphAdapter):
    """Nodes, edges and endpoints in three dicts, plus out and in adjacency
    lists of edge ids in insertion order."""

    def __init__(self):
        self.nodes_by_id: dict[str, OmkObject] = {}
        self.edges_by_id: dict[str, OmkEdge] = {}
        self.endpoints: dict[str, tuple[str, str]] = {}
        self.out: dict[str, list[str]] = {}
        self.incoming: dict[str, list[str]] = {}

    # --- lookups that enforce membership ---

    def _node_key(self, node: OmkObject | UUID | str) -> str:
        key = _key(node)
        if key not in self.nodes_by_id:
            raise GraphError(f"{node!r} is not on the graph.")
        return key

    def _edge_key(self, edge: OmkEdge) -> str:
        key = _key(edge)
        if key not in self.edges_by_id:
            raise GraphError(f"{edge!r} is not on the graph.")
        return key

    def _matches(self, edge: OmkEdge, edge_type: EdgeType | None) -> bool:
        return edge_type is None or edge.type == edge_type

    # --- add and remove ---

    def add_node(self, node: OmkObject) -> None:
        key = _key(node)
        if key in self.nodes_by_id:
            return
        self.nodes_by_id[key] = node
        self.out[key] = []
        self.incoming[key] = []

    def add_edge(self, source: OmkObject, target: OmkObject, edge: OmkEdge) -> None:
        source_key, target_key = self._node_key(source), self._node_key(target)
        if self.has_edge(source, target, edge.type):
            raise GraphError(
                f"An edge of type {edge.type!r} already exists between {source!r} and {target!r}."
            )
        if edge.type == EdgeType.NEXT:
            if any(self.out_edges(source, EdgeType.NEXT)):
                raise GraphError(f"Source {source!r} already has an outgoing edge of type NEXT.")
            if any(self.in_edges(target, EdgeType.NEXT)):
                raise GraphError(f"Target {target!r} already has an incoming edge of type NEXT.")
        key = _key(edge)
        self.edges_by_id[key] = edge
        self.endpoints[key] = (source_key, target_key)
        self.out[source_key].append(key)
        self.incoming[target_key].append(key)

    def remove_node(self, node: OmkObject) -> None:
        key = self._node_key(node)
        for edge_key in list(self.out[key]) + list(self.incoming[key]):
            if edge_key in self.edges_by_id:
                self.remove_edge(self.edges_by_id[edge_key])
        del self.nodes_by_id[key], self.out[key], self.incoming[key]

    def remove_edge(self, edge: OmkEdge) -> None:
        key = self._edge_key(edge)
        source_key, target_key = self.endpoints.pop(key)
        self.out[source_key].remove(key)
        self.incoming[target_key].remove(key)
        del self.edges_by_id[key]

    # --- retrieval ---

    def get_node(self, node_id: UUID | str) -> OmkObject | None:
        return self.nodes_by_id.get(_key(node_id))

    def get_edge(self, source: OmkObject, target: OmkObject, edge_type: EdgeType) -> OmkEdge:
        for edge in self.edges_between(source, target, edge_type):
            return edge
        raise GraphError(f"No edge of type {edge_type!r} between {source!r} and {target!r}.")

    def filter_edges(self, filter_function: Callable[[OmkEdge], bool]) -> list[OmkEdge]:
        return [edge for edge in self.edges_by_id.values() if filter_function(edge)]

    def filter_nodes(self, filter_function: Callable[[OmkObject], bool]) -> list[OmkObject]:
        return [node for node in self.nodes_by_id.values() if filter_function(node)]

    def get_edge_endpoints(self, edge: OmkEdge) -> tuple[OmkObject, OmkObject]:
        source_key, target_key = self.endpoints[self._edge_key(edge)]
        return self.nodes_by_id[source_key], self.nodes_by_id[target_key]

    def get_source_of_edge(self, edge: OmkEdge) -> OmkObject:
        return self.get_edge_endpoints(edge)[0]

    def get_target_of_edge(self, edge: OmkEdge) -> OmkObject:
        return self.get_edge_endpoints(edge)[1]

    # --- membership and counts ---

    def has_node(self, node: OmkObject) -> bool:
        return _key(node) in self.nodes_by_id

    def has_edge(
        self, source: OmkObject, target: OmkObject, edge_type: EdgeType | None = None
    ) -> bool:
        return any(True for _ in self.edges_between(source, target, edge_type))

    def num_nodes(self) -> int:
        return len(self.nodes_by_id)

    def num_edges(self) -> int:
        return len(self.edges_by_id)

    # --- iteration ---

    def nodes(
        self,
        node_type: type[OmkObject] | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        for node in list(self.nodes_by_id.values()):
            if node_type is not None and not isinstance(node, node_type):
                continue
            if predicate is not None and not predicate(node):
                continue
            yield node

    def edges(
        self,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkEdge], bool] | None = None,
    ) -> Iterator[OmkEdge]:
        for edge in list(self.edges_by_id.values()):
            if not self._matches(edge, edge_type):
                continue
            if predicate is not None and not predicate(edge):
                continue
            yield edge

    def edges_between(
        self,
        source: OmkObject,
        target: OmkObject,
        edge_type: EdgeType | None = None,
    ) -> Iterator[OmkEdge]:
        source_key, target_key = self._node_key(source), self._node_key(target)
        for edge_key in list(self.out[source_key]):
            if self.endpoints[edge_key][1] != target_key:
                continue
            edge = self.edges_by_id[edge_key]
            if self._matches(edge, edge_type):
                yield edge

    # --- neighbourhood ---

    def _across(
        self,
        edges: Iterator[OmkEdge],
        end: int,
        node_type: type[OmkObject] | None,
        predicate: Callable[[OmkObject], bool] | None,
    ) -> Iterator[OmkObject]:
        for edge in edges:
            neighbour = self.get_edge_endpoints(edge)[end]
            if node_type is not None and not isinstance(neighbour, node_type):
                continue
            if predicate is not None and not predicate(neighbour):
                continue
            yield neighbour

    def successors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        return self._across(self.out_edges(node, edge_type), 1, node_type, predicate)

    def predecessors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        return self._across(self.in_edges(node, edge_type), 0, node_type, predicate)

    def get_next(self, node: OmkObject) -> OmkObject | None:
        return next(self.successors(node, edge_type=EdgeType.NEXT), None)

    def get_previous(self, node: OmkObject) -> OmkObject | None:
        return next(self.predecessors(node, edge_type=EdgeType.NEXT), None)

    def neighbors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        seen: set[str] = set()
        for neighbour in self.predecessors(node, node_type, edge_type, predicate):
            seen.add(_key(neighbour))
            yield neighbour
        for neighbour in self.successors(node, node_type, edge_type, predicate):
            if _key(neighbour) not in seen:
                yield neighbour

    def out_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        for edge_key in list(self.out[self._node_key(node)]):
            edge = self.edges_by_id[edge_key]
            if self._matches(edge, edge_type):
                yield edge

    def in_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        for edge_key in list(self.incoming[self._node_key(node)]):
            edge = self.edges_by_id[edge_key]
            if self._matches(edge, edge_type):
                yield edge

    def incident_edges(
        self, node: OmkObject, edge_type: EdgeType | None = None
    ) -> Iterator[OmkEdge]:
        yield from self.in_edges(node, edge_type)
        yield from self.out_edges(node, edge_type)

    # --- degree ---

    def degree(self, node: OmkObject) -> int:
        return self.in_degree(node) + self.out_degree(node)

    def in_degree(self, node: OmkObject) -> int:
        return len(self.incoming[self._node_key(node)])

    def out_degree(self, node: OmkObject) -> int:
        return len(self.out[self._node_key(node)])
