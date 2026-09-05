from abc import ABC, abstractmethod
from typing import Callable, Iterable, Iterator, Optional

from openmusickit.utils.id import OmkId
from openmusickit.utils.omk_object import OmkObject
from openmusickit.graph.edge import OmkEdge, EdgeType
from openmusickit.graph.graph import OmkGraph

class GraphAdapter(ABC):
    """Abstract base class providing a unified API to any graph engine."""

    @abstractmethod
    def add_node(self, node: OmkObject) -> None:
        """Add a node to the graph."""
        raise NotImplementedError

    @abstractmethod
    def add_edge(self, source: OmkObject, target: OmkObject, edge: OmkEdge) -> None:
        """Add an edge from source to target to the graph."""
        raise NotImplementedError

    @abstractmethod
    def remove_node(self, node: OmkObject) -> None:
        """Remove a node (and its incident edges) from the graph."""
        raise NotImplementedError

    @abstractmethod
    def remove_edge(self, edge: OmkEdge) -> None:
        """Remove an edge from the graph."""
        raise NotImplementedError

    @abstractmethod
    def get_node(self, node_id: OmkId) -> OmkObject:
        """Return the node with the given OmkId."""
        raise NotImplementedError

    @abstractmethod
    def get_edge(self, source: OmkObject, target: OmkObject, edge_type: EdgeType) -> OmkEdge:
        """Return the edge of the given type from source to target."""
        raise NotImplementedError

    @abstractmethod
    def get_edges(self, source: OmkObject, target: OmkObject)-> tuple[list[OmkEdge]]:
        """Returns all edges between source and target, in two lists:
            return_tuple[0] --> edges from source to target
            return_tuple[1] --> edges from target to source
        """
        raise NotImplementedError

    @abstractmethod
    def filter_edges(self, filter_function: Callable[[OmkEdge], bool]) -> list[OmkEdge]:
        """Returns a list of all edges for which filter_function(edge) returns True."""
        raise NotImplementedError

    @abstractmethod
    def filter_nodes(self, filter_function: Callable[[OmkObject], bool]) -> list[OmkObject]:
        """Returns a list of all nodes for which filter_function(node) returns True."""
        raise NotImplementedError


 # Membership / counts
    @abstractmethod
    def has_node(self, node: OmkObject) -> bool:
        """Return True if node is present in the graph."""
        raise NotImplementedError

    @abstractmethod
    def has_edge(self, source: OmkObject, target: OmkObject, edge_type: Optional[EdgeType] = None) -> bool:
        """Return True if an edge (optionally of the given type) exists from source to target."""
        raise NotImplementedError

    @abstractmethod
    def num_nodes(self) -> int:
        """Return the total number of nodes in the graph."""
        raise NotImplementedError

    @abstractmethod
    def num_edges(self) -> int:
        """Return the total number of edges in the graph."""
        raise NotImplementedError

    # Iteration/query
    @abstractmethod
    def nodes(
        self,
        node_type: Optional[type[OmkObject]] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes, optionally filtered by node_type and/or predicate."""
        raise NotImplementedError

    @abstractmethod
    def edges(
        self,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkEdge], bool]] = None,
    ) -> Iterator[OmkEdge]:
        """Iterate over edges, optionally filtered by edge_type and/or predicate."""
        raise NotImplementedError

    @abstractmethod
    def edges_between(
        self,
        source: OmkObject,
        target: OmkObject,
        edge_type: Optional[EdgeType] = None,
    ) -> Iterator[OmkEdge]:
        """Iterate over edges from source to target, optionally filtered by edge_type."""
        raise NotImplementedError

    # Neighborhood
    @abstractmethod
    def successors(
        self,
        node: OmkObject,
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes reachable from node via an outgoing edge, optionally filtered."""
        raise NotImplementedError

    @abstractmethod
    def predecessors(
        self,
        node: OmkObject,
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes that have an outgoing edge to node, optionally filtered."""
        raise NotImplementedError

    @abstractmethod
    def neighbors(
        self,
        node: OmkObject,
        node_type: Optional[type[OmkObject]] = None,
        edge_type: Optional[EdgeType] = None,
        predicate: Optional[Callable[[OmkObject], bool]] = None,
    ) -> Iterator[OmkObject]:
        """Iterate over all nodes adjacent to node (predecessors and successors), optionally filtered."""
        raise NotImplementedError

    @abstractmethod
    def out_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
        """Iterate over edges originating from node, optionally filtered by edge_type."""
        raise NotImplementedError

    @abstractmethod
    def in_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
        """Iterate over edges terminating at node, optionally filtered by edge_type."""
        raise NotImplementedError

    @abstractmethod
    def incident_edges(self, node: OmkObject, edge_type: Optional[EdgeType] = None) -> Iterator[OmkEdge]:
        """Iterate over all edges touching node (incoming and outgoing), optionally filtered by edge_type."""
        raise NotImplementedError

    # Degree
    @abstractmethod
    def degree(self, node: OmkObject) -> int:
        """Return the total number of edges incident to node."""
        raise NotImplementedError

    @abstractmethod
    def in_degree(self, node: OmkObject) -> int:
        """Return the number of edges terminating at node."""
        raise NotImplementedError

    @abstractmethod
    def out_degree(self, node: OmkObject) -> int:
        """Return the number of edges originating from node."""
        raise NotImplementedError

    # Derived graphs
    @abstractmethod
    def subgraph(self, nodes: Iterable[OmkObject]) -> OmkGraph:
        """Return a new graph containing only the given nodes and the edges between them."""
        raise NotImplementedError

    @abstractmethod
    def edge_subgraph(self, edges: Iterable[OmkEdge]) -> OmkGraph:
        """Return a new graph containing only the given edges and their endpoint nodes."""
        raise NotImplementedError

    @abstractmethod
    def copy(self) -> OmkGraph:
        """Return a copy of this graph."""
        raise NotImplementedError

    @abstractmethod
    def merge(self, other: OmkGraph) -> OmkGraph:
        """Return a new graph combining this graph's nodes/edges with those of other."""
        raise NotImplementedError









    
        
