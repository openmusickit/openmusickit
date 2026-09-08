from typing import Callable, Iterable, Iterator, Optional

from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.graph.edge import OmkEdge, EdgeType
from openmusickit.utils.id import OmkId
from openmusickit.objects.omk_object import OmkObject
from bidict import bidict
import rustworkx as rx

class RustworkxAdapter(GraphAdapter):
    """Default adapter for OmkGraph.
    
    Implementation note:
    This adapter uses Rustworkx's PyDiGraph as the underlying graph structure.
    OmkObjects and OmkEdges are registered by the string value of their OmkId with their Rustworkx integer ids in bidirectional indices.
    OmkGraph users supply OmkObjects and OmkEdges (usually directly, but in some cases by their OmkId),
    and the adapter handles the conversion to Rustworkx integer ids internally.
    (Users should not need to interact with Rustworkx integer ids directly.)

    OmkObjects and OmkEdges are the payload for PyDiGraph's nodes and edges, respectively.
    """

    def __init__(self):
        self.graph = rx.PyDiGraph()
        self._node_index = bidict() # OmkId: rxid
        self._edge_index = bidict() # OmkId: rxid


    # ID and registration helpers

    def _register_node(self, node: OmkObject, rxid: int) -> None:
        """Registers a node and its Rustworkx integer id to self._node_index."""

        self._node_index[str(node._id)] = rxid

    def _unregister_node(self, node: OmkObject|OmkId|str) -> None:
        del self._node_index[str(node._id if hasattr(node, "_id") else node)]

    def _unregister_node_rxid(self, rxid: int) -> None:
        del self._node_index.inverse[rxid]

    def _rxid(self, node: OmkObject|OmkEdge|OmkId|str) -> int:
        """Returns the Rustworks integer id of the OmkObject or OmkEdge."""
        try: # it's a node
            return self._node_index[str(node._id if hasattr(node, "_id") else node)]
        except KeyError: # it's an edge
            return self._edge_index[str(node._id if hasattr(node, "_id") else node)]

    def _omkid_node(self, rxid: int) -> str:
        return self._node_index.inverse[rxid]

    def _omkid_edge(self, rxid: int) -> str:
        return self._edge_index.inverse[rxid]

    def _get_node_by_rxid(self, rxid: int) -> OmkObject:
        return self.graph.get_node_data(rxid)

    def _register_edge(self, edge: OmkEdge, rxid: int) -> None:
        """Registers an edge and its Rustworkx integer id to self._edge_index."""
        self._edge_index[str(edge._id)] = rxid

    def _unregister_edge(self, edge: OmkEdge|OmkId|str) -> None:
        del self._edge_index[str(edge._id if hasattr(edge, "_id") else edge)]

    def _get_edge_by_rxid(self, rxid: int) -> OmkEdge:
        return self.graph.get_edge_data_by_index(rxid)


    # Add and remove operations

    def add_node(self, node: OmkObject) -> None:
        """Add a node to the graph.

        Does nothing if the node (by OmkId) is already present."""
        if str(node._id) in self._node_index:
            return
        rxid = self.graph.add_node(node)
        self._register_node(node, rxid)

    def add_edge(self, source: OmkObject, target: OmkObject, edge: OmkEdge) -> None:
        """Add an edge from source to target to the graph.
        
        Raises an exception if there is already an edge of the same type between source and target.
        Raises an exception if edge_type is NEXT and source already has an outgoing edge of type NEXT."""
        if self.has_edge(source, target, edge.type):
            raise ValueError(f"An edge of type {edge.type!r} already exists between {source!r} and {target!r}.")
        if edge.type == EdgeType.NEXT and self.has_edge(source, target, EdgeType.NEXT):
            raise ValueError(f"Source {source!r} already has an outgoing edge of type NEXT.")
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

    def get_node(self, node_id: OmkId|str) -> OmkObject:
        """Return the node with the given OmkId."""
        return self.graph.get_node_data(self._rxid(node_id))
    
    def get_edge(self, source: OmkObject, target: OmkObject, edge_type: EdgeType) -> OmkEdge:
        """Return the edge of the given type from source to target."""
        for edge in self.graph.get_all_edge_data(self._rxid(source), self._rxid(target)):
            if edge.type == edge_type:
                return edge
        raise rx.NoEdgeBetweenNodes(
            f"No edge of type {edge_type!r} between {source!r} and {target!r}."
        )

    def get_edges(self, source: OmkObject, target: OmkObject)-> tuple[list[OmkEdge]]:
        """Returns all edges between source and target, in two lists:
            return_tuple[0] --> edges from source to target
            return_tuple[1] --> edges from target to source
        """
        source_rxid = self._rxid(source)
        target_rxid = self._rxid(target)
        try:
            forward = self.graph.get_all_edge_data(source_rxid, target_rxid)
        except rx.NoEdgeBetweenNodes:
            forward = []
        try:
            backward = self.graph.get_all_edge_data(target_rxid, source_rxid)
        except rx.NoEdgeBetweenNodes:
            backward = []
        return (forward, backward)

    def filter_edges(self, filter_function: Callable[[OmkEdge], bool]) -> list[OmkEdge]:
        """Returns a list of all edges for which filter_function(edge) returns True."""
        return [self._get_edge_by_rxid(rxid) for rxid in self.graph.filter_edges(filter_function)]

    def filter_nodes(self, filter_function: Callable[[OmkObject], bool]) -> list[OmkObject]:
        """Returns a list of all nodes for which filter_function(node) returns True."""
        return [self._get_node_by_rxid(rxid) for rxid in self.graph.filter_nodes(filter_function)]

    def get_edge_endpoints(self, edge: OmkEdge) -> tuple[OmkObject, OmkObject]:
        """Return the source and target nodes of the given edge as a tuple (source, target)."""
        return self.graph.get_edge_endpoints_by_index(self._rxid(edge))

    def get_source_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the source node of the given edge."""
        return self.graph.get_edge_endpoints_by_index(self._rxid(edge))[0]

    def get_target_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the target node of the given edge."""
        return self.graph.get_edge_endpoints_by_index(self._rxid(edge))[1]

    def has_node(self, node: OmkObject) -> bool:
        """Return True if node is present in the graph."""
        return str(node._id) in self._node_index

    def has_edge(self, source: OmkObject, target: OmkObject, edge_type: Optional[EdgeType] = None) -> bool:
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
        node_type: Optional[type[OmkObject]] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
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
        predicate: Optional[Callable[[OmkEdge], bool]] = None,
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
        edge_type: Optional[EdgeType] = None,
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
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
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
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
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

    def get_next(self, node: OmkObject) -> Optional[OmkObject]:
        """Return the next node connected by an edge of type NEXT from the given node, if it exists."""
        return self.graph.find_successor_node_by_edge(self._rxid(node), EdgeType.NEXT)

    def get_previous(self, node: OmkObject) -> Optional[OmkObject]:
        """Return the previous node connected by an edge of type NEXT to the given node, if it exists."""
        return self.graph.find_predecessor_node_by_edge(self._rxid(node), EdgeType.NEXT)

    
    def neighbors(
        self,
        node: OmkObject,
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
    ) -> Iterator[OmkObject]:
        """Iterate over all nodes adjacent to node (predecessors and successors), optionally filtered."""
        seen: set[str] = set()
        for neighbor in self.predecessors(node, node_type, edge_type, predicate):
            seen.add(str(neighbor._id))
            yield neighbor
        for neighbor in self.successors(node, node_type, edge_type, predicate):
            if str(neighbor._id) in seen:
                continue
            yield neighbor

    def out_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
        """Iterate over edges originating from node, optionally filtered by edge_type."""
        for _, _, edge in self.graph.out_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def in_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
        """Iterate over edges terminating at node, optionally filtered by edge_type."""
        for _, _, edge in self.graph.in_edges(self._rxid(node)):
            if edge_type is not None and edge.type != edge_type:
                continue
            yield edge

    def incident_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
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

    # NOTE: subgraph/edge_subgraph/copy/merge previously lived here but were
    # removed pending a redesign that moves derived-graph construction to
    # OmkGraph itself, built from lower-level adapter primitives.


