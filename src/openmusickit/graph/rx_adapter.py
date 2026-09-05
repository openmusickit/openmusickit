from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.utils.id import OmkId
from openmusickit.utils.omk_object import OmkObject
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

    def _register_node(self, node: OmkObject, rxid: int) -> None:
        """Registers a node and its Rustworkx integer id to self._node_index."""

        self._node_index[str(node._id)] = rxid

    def _unregister_node(self, node: OmkObject|OmkId|str) -> None:
        del self._node_index[str(node._id if hasattr(node, "_id") else node)]

    def _unregister_rxid(self, rxid: int) -> None:
        del self._node_index.invert[rxid]

    def _rxid(self, node: OmkObject|OmkId|str) -> int:
        """Returns the Rustworks integer id of the OmkObject."""
        return self._node_index[str(node._id if hasattr(node, "_id") else node)]

    def _omkid(self, rxid: int) -> str:
        return self._node_index.invert[rxid]

    def _get_node_by_rxid(self, rxid: int) -> OmkObject:
        return self.graph.get_node_data(rxid)

    def add_node(self, node):
        raise NotImplementedError

    def add_edge(self, source, target, edge):
        raise NotImplementedError

    def remove_node(self, node):
        raise NotImplementedError

    def remove_edge(self, edge):
        raise NotImplementedError

    def get_node(self, node_id: OmkId|str) -> OmkObject:
        return self.graph.get_node_data(self._rxid(node_id))
    
    def get_edge(self, source, target, edge_type):
        raise NotImplementedError

    def get_edges(self, source, target):
        raise NotImplementedError

    def filter_edges(self, filter_function):
        raise NotImplementedError

    def filter_nodes(self, filter_function):
        raise NotImplementedError

    def has_node(self, node):
        raise NotImplementedError

    def has_edge(self, source, target, edge_type = None):
        raise NotImplementedError

    def num_nodes(self):
        raise NotImplementedError

    def num_edges(self):
        raise NotImplementedError

    def nodes(self, node_type = None, predicate = None):
        raise NotImplementedError

    def edges(self, edge_type = None, predicate = None):
        raise NotImplementedError

    def edges_between(self, source, target, edge_type = None):
        raise NotImplementedError

    def successors(self, node, node_type = None, edge_type = None, predicate = None):
        raise NotImplementedError

    def predecessors(self, node, node_type = None, edge_type = None, predicate = None):
        raise NotImplementedError

    def neighbors(self, node, node_type = None, edge_type = None, predicate = None):
        raise NotImplementedError

    def out_edges(self, node, edge_type = None):
        raise NotImplementedError

    def in_edges(self, node, edge_type = None):
        raise NotImplementedError

    def incident_edges(self, node, edge_type = None):
        raise NotImplementedError

    def degree(self, node):
        raise NotImplementedError

    def in_degree(self, node):
        raise NotImplementedError

    def out_degree(self, node):
        raise NotImplementedError

    def subgraph(self, nodes):
        raise NotImplementedError

    def edge_subgraph(self, edges):
        raise NotImplementedError

    def copy(self):
        raise NotImplementedError

    def merge(self, other):
        raise NotImplementedError


