from bidict import bidict
import rustworkx as rx

from openmusickit.utils.id import OmkId
from openmusickit.utils.omk_object import OmkObject
from openmusickit.graph.edge import OmkEdge, EdgeType

class GraphAdapter:
    """Abstract base class providing a unified API to any graph engine."""

    def add_node(self, node:OmkObject) -> None:
        raise NotImplementedError

    def add_edge(self, from_node: OmkObject, to_node: OmkObject, edge: OmkEdge) -> None:
        raise NotImplementedError

    def remove_node(self, node) -> None:
        raise NotImplementedError

    def remove_edge(self, edge) -> None:
        raise NotImplementedError

    def get_edge(self, from_node: OmkObject, to_node: OmkObject, edge_type: EdgeType) -> OmkEdge:
        raise NotImplementedError

    def get_edges(self, node_a: OmkObject, node_b: OmkObject)-> tuple[list[OmkEdge]]:
        """Returns all edges between node_a and node_b, in two lists:
            return_tuple[0] --> edges from node_a to node_b
            return_tuple[1] --> edges from node_b to node_a
        """
        raise NotImplementedError

    def filter_edges(self, filter_function) -> list[OmkEdge]:
        """Returns a list of all edges for which filter_function(edge) returns True."""
        raise NotImplementedError


class RustworkxAdapter(GraphAdapter):
    """Default adapter for OmkGraph."""

    def __init__(self):
        self.graph = rx.PyDiGraph()
        self._index = bidict() # OmkId: rxid

    def _register_node(self, node: OmkObject, rxid: int) -> None:
        """Registers a node and its Rustworkx integer id to self._index."""
        self._index[str(OmkObject.id)] = rxid

    def _unregister_node(self, node: OmkObject|OmkId|str) -> None:
        try:
            del self._index[str(omk_obj)]
        except AttributeError:
            del self._index[str(omk_obj._id)]

    def _unregister_rxid(self, rxid: int) -> None:
        del self._index.invert[rxid]

    def _rxid(self, omk_obj: OmkObject|OmkId|str) -> int:
        """Returns the Rustworks integer id of the OmkObject."""
        try:
            return self._index[str(omk_obj)]
        except AttributeError:
            return self._index[str(omk_obj._id)]

    def _omkid(self, rxid: int) -> str:
        return self._index.invert[rxid]

    
        
