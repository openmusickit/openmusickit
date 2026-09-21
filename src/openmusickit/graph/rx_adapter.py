from collections.abc import Callable, Iterator
from uuid import UUID

import rustworkx as rx
from bidict import bidict

from openmusickit.errors import GraphError
from openmusickit.graph.edge import EdgeType, OmkEdge
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.objects.omk_object import OmkObject


class RustworkxAdapter(GraphAdapter):
    """Default adapter for OmkGraph.

    Implementation note:
    This adapter uses Rustworkx's PyDiGraph as the underlying graph structure.
    OmkObjects and OmkEdges are registered by the string form of their id with their Rustworkx integer ids in bidirectional indices.
    OmkGraph users supply OmkObjects and OmkEdges (usually directly, but in some cases by their id),
    and the adapter handles the conversion to Rustworkx integer ids internally.
    (Users should not need to interact with Rustworkx integer ids directly.)

    OmkObjects and OmkEdges are the payload for PyDiGraph's nodes and edges, respectively.
    """

    def __init__(self):
        self.graph = rx.PyDiGraph()
        self._node_index = bidict()  # str(id): rxid
        self._edge_index = bidict()  # str(id): rxid

    # ID and registration helpers

    def _register_node(self, node: OmkObject, rxid: int) -> None:
        """Registers a node and its Rustworkx integer id to self._node_index."""

        self._node_index[str(node.id)] = rxid

    def _unregister_node(self, node: OmkObject | UUID | str) -> None:
        del self._node_index[str(node.id if hasattr(node, "_id") else node)]

    def _unregister_node_rxid(self, rxid: int) -> None:
        del self._node_index.inverse[rxid]

    def _rxid(self, item: OmkObject | OmkEdge | UUID | str) -> int:
        """Returns the Rustworkx integer id of the OmkObject or OmkEdge.

        Raises GraphError if the item is not on the graph; no KeyError leaves here."""
        key = str(item.id if hasattr(item, "_id") else item)
        if key in self._node_index:
            return self._node_index[key]
        if key in self._edge_index:
            return self._edge_index[key]
        raise GraphError(f"{item!r} is not on the graph.")

    def _omkid_node(self, rxid: int) -> str:
        return self._node_index.inverse[rxid]

    def _omkid_edge(self, rxid: int) -> str:
        return self._edge_index.inverse[rxid]

    def _get_node_by_rxid(self, rxid: int) -> OmkObject:
        return self.graph.get_node_data(rxid)

    def _register_edge(self, edge: OmkEdge, rxid: int) -> None:
        """Registers an edge and its Rustworkx integer id to self._edge_index."""
        self._edge_index[str(edge.id)] = rxid

    def _unregister_edge(self, edge: OmkEdge | UUID | str) -> None:
        del self._edge_index[str(edge.id if hasattr(edge, "_id") else edge)]

    def _get_edge_by_rxid(self, rxid: int) -> OmkEdge:
        return self.graph.get_edge_data_by_index(rxid)

    # Add and remove operations

    def add_node(self, node: OmkObject) -> None:
        """Add a node to the graph.

        Does nothing if the node (by id) is already present."""
        if str(node.id) in self._node_index:
            return
        rxid = self.graph.add_node(node)
        self._register_node(node, rxid)

    def add_edge(self, source: OmkObject, target: OmkObject, edge: OmkEdge) -> None:
        """Add an edge from source to target to the graph.

        Raises an exception if there is already an edge of the same type between source and target.
        Raises an exception if edge_type is NEXT and source already has an outgoing edge of type NEXT,
        or target already has an incoming one (a line is a chain: one NEXT in, one NEXT out)."""
        if self.has_edge(source, target, edge.type):
            raise GraphError(
                f"An edge of type {edge.type!r} already exists between {source!r} and {target!r}."
            )
        if edge.type == EdgeType.NEXT:
            if any(self.out_edges(source, EdgeType.NEXT)):
                raise GraphError(f"Source {source!r} already has an outgoing edge of type NEXT.")
            if any(self.in_edges(target, EdgeType.NEXT)):
                raise GraphError(f"Target {target!r} already has an incoming edge of type NEXT.")
        rxid = self.graph.add_edge(self._rxid(source), self._rxid(target), edge)
        self._register_edge(edge, rxid)

    def remove_node(self, node: OmkObject) -> None:
        """Remove a node (and its incident edges) from the graph.

        Raises an exception if the node does not exist."""
        rxid = self._rxid(node)
        for edge_rxid in self.graph.incident_edges(rxid, all_edges=True):
            self._unregister_edge(self._get_edge_by_rxid(edge_rxid))
        self.graph.remove_node(rxid)
        self._unregister_node(node)

    def remove_edge(self, edge: OmkEdge) -> None:
        """Remove an edge from the graph."""
        rxid = self._rxid(edge)
        self.graph.remove_edge_from_index(rxid)
        self._unregister_edge(edge)

    # Retrieval operations

    def get_node(self, node_id: UUID | str) -> OmkObject | None:
        """Return the node with the given id, or None if there is no such node."""
        if str(node_id) not in self._node_index:
            return None
        return self.graph.get_node_data(self._rxid(node_id))

    def get_edge(self, source: OmkObject, target: OmkObject, edge_type: EdgeType) -> OmkEdge:
        """Return the edge of the given type from source to target; raises GraphError if there is none."""
        try:
            edges = self.graph.get_all_edge_data(self._rxid(source), self._rxid(target))
        except rx.NoEdgeBetweenNodes:
            edges = []
        for edge in edges:
            if edge.type == edge_type:
                return edge
        raise GraphError(f"No edge of type {edge_type!r} between {source!r} and {target!r}.")

    def filter_edges(self, filter_function: Callable[[OmkEdge], bool]) -> list[OmkEdge]:
        """Returns a list of all edges for which filter_function(edge) returns True."""
        return [self._get_edge_by_rxid(rxid) for rxid in self.graph.filter_edges(filter_function)]

    def filter_nodes(self, filter_function: Callable[[OmkObject], bool]) -> list[OmkObject]:
        """Returns a list of all nodes for which filter_function(node) returns True."""
        return [self._get_node_by_rxid(rxid) for rxid in self.graph.filter_nodes(filter_function)]

    def get_edge_endpoints(self, edge: OmkEdge) -> tuple[OmkObject, OmkObject]:
        """Return the source and target nodes of the given edge as a tuple (source, target)."""
        source_rxid, target_rxid = self.graph.get_edge_endpoints_by_index(self._rxid(edge))
        return self._get_node_by_rxid(source_rxid), self._get_node_by_rxid(target_rxid)

    def get_source_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the source node of the given edge."""
        return self.get_edge_endpoints(edge)[0]

    def get_target_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the target node of the given edge."""
        return self.get_edge_endpoints(edge)[1]

    def has_node(self, node: OmkObject) -> bool:
        """Return True if node is present in the graph."""
        return str(node.id) in self._node_index

    def has_edge(
        self, source: OmkObject, target: OmkObject, edge_type: EdgeType | None = None
    ) -> bool:
        """Return True if an edge (optionally of the given type) exists from source to target."""
        source_rxid = self._rxid(source)
        target_rxid = self._rxid(target)
        if edge_type is None:
            return self.graph.has_edge(source_rxid, target_rxid)
        try:
            edges = self.graph.get_all_edge_data(source_rxid, target_rxid)
        except rx.NoEdgeBetweenNodes:
            return False
        return any(edge.type == edge_type for edge in edges)

    def num_nodes(self) -> int:
        """Return the total number of nodes in the graph."""
        return self.graph.num_nodes()

    def num_edges(self) -> int:
        """Return the total number of edges in the graph."""
        return self.graph.num_edges()

    def nodes(
        self,
        node_type: type[OmkObject] | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes, optionally filtered by node_type and/or predicate."""
        for node in self.graph.nodes():
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
        """Iterate over edges, optionally filtered by edge_type and/or predicate."""
        for edge in self.graph.edges():
            if edge_type is not None and edge.type != edge_type:
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
        """Iterate over edges from source to target, optionally filtered by edge_type."""
        try:
            edges = self.graph.get_all_edge_data(self._rxid(source), self._rxid(target))
        except rx.NoEdgeBetweenNodes:
            return
        for edge in edges:
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def successors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes reachable from node via an outgoing edge, optionally filtered."""
        for _, target_rxid, edge in self.graph.out_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            successor = self._get_node_by_rxid(target_rxid)
            if node_type is not None and not isinstance(successor, node_type):
                continue
            if predicate is not None and not predicate(successor):
                continue
            yield successor

    def predecessors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes that have an outgoing edge to node, optionally filtered."""
        for source_rxid, _, edge in self.graph.in_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            predecessor = self._get_node_by_rxid(source_rxid)
            if node_type is not None and not isinstance(predecessor, node_type):
                continue
            if predicate is not None and not predicate(predecessor):
                continue
            yield predecessor

    def get_next(self, node: OmkObject) -> OmkObject | None:
        """Return the next node connected by an edge of type NEXT from the given node, if it exists."""
        try:
            return self.graph.find_successor_node_by_edge(
                self._rxid(node), lambda edge: edge.type == EdgeType.NEXT
            )
        except rx.NoSuitableNeighbors:
            return None

    def get_previous(self, node: OmkObject) -> OmkObject | None:
        """Return the previous node connected by an edge of type NEXT to the given node, if it exists."""
        try:
            return self.graph.find_predecessor_node_by_edge(
                self._rxid(node), lambda edge: edge.type == EdgeType.NEXT
            )
        except rx.NoSuitableNeighbors:
            return None

    def neighbors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over all nodes adjacent to node (predecessors and successors), optionally filtered."""
        seen: set[str] = set()
        for neighbor in self.predecessors(node, node_type, edge_type, predicate):
            seen.add(str(neighbor.id))
            yield neighbor
        for neighbor in self.successors(node, node_type, edge_type, predicate):
            if str(neighbor.id) in seen:
                continue
            yield neighbor

    def out_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        """Iterate over edges originating from node, optionally filtered by edge_type."""
        for _, _, edge in self.graph.out_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def in_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        """Iterate over edges terminating at node, optionally filtered by edge_type."""
        for _, _, edge in self.graph.in_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def incident_edges(
        self, node: OmkObject, edge_type: EdgeType | None = None
    ) -> Iterator[OmkEdge]:
        """Iterate over all edges touching node (incoming and outgoing), optionally filtered by edge_type."""
        rxid = self._rxid(node)
        for edge_rxid in self.graph.incident_edges(rxid, all_edges=True):
            edge = self._get_edge_by_rxid(edge_rxid)
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def degree(self, node: OmkObject) -> int:
        """Return the total number of edges incident to node."""
        rxid = self._rxid(node)
        return self.graph.in_degree(rxid) + self.graph.out_degree(rxid)

    def in_degree(self, node: OmkObject) -> int:
        """Return the number of edges terminating at node."""
        return self.graph.in_degree(self._rxid(node))

    def out_degree(self, node: OmkObject) -> int:
        """Return the number of edges originating from node."""
        return self.graph.out_degree(self._rxid(node))
