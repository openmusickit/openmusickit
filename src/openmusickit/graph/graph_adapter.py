from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator

from openmusickit.graph.edge import EdgeType, OmkEdge
from openmusickit.objects.omk_object import OmkObject
from openmusickit.utils.id import OmkId


class GraphAdapter(ABC):
    """Abstract base class providing a unified API to any graph engine."""

    @abstractmethod
    def add_node(self, node: OmkObject) -> None:
        """Add a node to the graph."""

    @abstractmethod
    def add_edge(self, source: OmkObject, target: OmkObject, edge: OmkEdge) -> None:
        """Add an edge from source to target to the graph.

        Raises an exception if there is already an edge of the same type between source and target."""

    @abstractmethod
    def remove_node(self, node: OmkObject) -> None:
        """Remove a node (and its incident edges) from the graph."""

    @abstractmethod
    def remove_edge(self, edge: OmkEdge) -> None:
        """Remove an edge from the graph."""

    @abstractmethod
    def get_node(self, node_id: OmkId) -> OmkObject:
        """Return the node with the given OmkId."""

    @abstractmethod
    def get_edge(self, source: OmkObject, target: OmkObject, edge_type: EdgeType) -> OmkEdge:
        """Return the edge of the given type from source to target."""

    @abstractmethod
    def filter_edges(self, filter_function: Callable[[OmkEdge], bool]) -> list[OmkEdge]:
        """Returns a list of all edges for which filter_function(edge) returns True."""

    @abstractmethod
    def filter_nodes(self, filter_function: Callable[[OmkObject], bool]) -> list[OmkObject]:
        """Returns a list of all nodes for which filter_function(node) returns True."""

    @abstractmethod
    def get_edge_endpoints(self, edge: OmkEdge) -> tuple[OmkObject, OmkObject]:
        """Return the source and target nodes of the given edge as a tuple (source, target)."""

    @abstractmethod
    def get_source_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the source node of the given edge."""

    @abstractmethod
    def get_target_of_edge(self, edge: OmkEdge) -> OmkObject:
        """Return the target node of the given edge."""

    # Membership / counts
    @abstractmethod
    def has_node(self, node: OmkObject) -> bool:
        """Return True if node is present in the graph."""

    @abstractmethod
    def has_edge(
        self, source: OmkObject, target: OmkObject, edge_type: EdgeType | None = None
    ) -> bool:
        """Return True if an edge (optionally of the given type) exists from source to target."""

    @abstractmethod
    def num_nodes(self) -> int:
        """Return the total number of nodes in the graph."""

    @abstractmethod
    def num_edges(self) -> int:
        """Return the total number of edges in the graph."""

    # Iteration/query
    @abstractmethod
    def nodes(
        self,
        node_type: type[OmkObject] | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes, optionally filtered by node_type and/or predicate."""

    @abstractmethod
    def edges(
        self,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkEdge], bool] | None = None,
    ) -> Iterator[OmkEdge]:
        """Iterate over edges, optionally filtered by edge_type and/or predicate."""

    @abstractmethod
    def edges_between(
        self,
        source: OmkObject,
        target: OmkObject,
        edge_type: EdgeType | None = None,
    ) -> Iterator[OmkEdge]:
        """Iterate over edges from source to target, optionally filtered by edge_type."""

    # Neighborhood
    @abstractmethod
    def successors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes reachable from node via an outgoing edge, optionally filtered."""

    @abstractmethod
    def predecessors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over nodes that have an outgoing edge to node, optionally filtered."""

    @abstractmethod
    def get_next(self, node: OmkObject) -> OmkObject | None:
        """Return the next node connected by an edge of type NEXT from the given node, if it exists."""

    @abstractmethod
    def get_previous(self, node: OmkObject) -> OmkObject | None:
        """Return the previous node connected by an edge of type NEXT to the given node, if it exists."""

    @abstractmethod
    def neighbors(
        self,
        node: OmkObject,
        node_type: type[OmkObject] | None = None,
        edge_type: EdgeType | None = None,
        predicate: Callable[[OmkObject], bool] | None = None,
    ) -> Iterator[OmkObject]:
        """Iterate over all nodes adjacent to node (predecessors and successors), optionally filtered."""

    @abstractmethod
    def out_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        """Iterate over edges originating from node, optionally filtered by edge_type."""

    @abstractmethod
    def in_edges(self, node: OmkObject, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        """Iterate over edges terminating at node, optionally filtered by edge_type."""

    @abstractmethod
    def incident_edges(
        self, node: OmkObject, edge_type: EdgeType | None = None
    ) -> Iterator[OmkEdge]:
        """Iterate over all edges touching node (incoming and outgoing), optionally filtered by edge_type."""

    # Degree
    @abstractmethod
    def degree(self, node: OmkObject) -> int:
        """Return the total number of edges incident to node."""

    @abstractmethod
    def in_degree(self, node: OmkObject) -> int:
        """Return the number of edges terminating at node."""

    @abstractmethod
    def out_degree(self, node: OmkObject) -> int:
        """Return the number of edges originating from node."""

    # NOTE: subgraph/edge_subgraph/copy/merge previously lived here but were
    # removed pending a redesign that moves derived-graph construction to
    # OmkGraph itself, built from lower-level adapter primitives.
