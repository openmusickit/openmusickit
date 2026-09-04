from __future__ import annotations

from .graph_adapter import GraphAdapter, RustworkxAdapter
from .edge import EdgeType, OmkEdge
from openmusickit.utils.id import OmkId
from openmusickit.utils.omk_object import OmkObject
from openmusickit.events.event import SequentialObject, MusicalEvent


class GraphMeta:
    """Details about the graph, including title, composer namer, etc."""
    pass

class OmkGraph:
    """A graph representation of music."""

    def __init__(self, meta: GraphMeta, graph_engine: GraphAdapter=RustworkxAdapter):
        self._meta = meta
        self._graph = graph_engine
        self._index = dict()

    # Load and import

    @classmethod
    def load_from_json(cls, js_graph, graph_engine: GraphAdapter=RustworkxAdapter) -> OmkGraph:
        """Returns an OmkGraph built from a JSON serialization."""
        pass

    def import_json_graph(cls, js_graph) -> None:
        """Adds the contents of js_graph to the current graph.
        Do not assume metadata from the source graph is retained."""
        pass


    # Basic Add, Connect, Remove

    def get_node(self, id: OmkId|str) -> OmkObject|None:
        """Returns an OmkObj based on id. Returns None if no such object exists."""
        pass

    def add_node(self, obj: OmkObject) -> None:
        """Adds node to the graph. If the node is already on the graph, does nothing."""
        pass

    def remove_node(self, obj: OmkObject) -> tuple[OmkObject, list[OmkEdge]]:
        """Removes a node and all related edges from the graph.
        Returns the node and edge objects.
        
        This does not automatically remove the object and edges from memory;
        if you retain a reference to the object and edges, they remain accessible
        until they are garbage collected."""
        pass

    def get_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> OmkEdge:
        pass

    def add_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> None:
        pass

    def remove_edge(self, edge: OmkEdge) -> OmkEdge:
        pass


    # Sequential Data

    def get_next(self, current: SequentialObject) -> None:
        pass

    def add_next(self, current: SequentialObject, next: SequentialObject) -> None:
        """Places a sequential object after another SequentialObject.
        
        It makes no difference if the object was already part of the graph."""
        self.add_node(next)
        self.add_edge(current, next, EdgeType.NEXT)

    
    def insert_event(self, event: SequentialObject, prev: SequentialObject, next: SequentialObject) -> None:
        """Insert a SequentialObject between two SequentialObjects.
        
        It makes no difference if the inserted object was already part of the graph."""
        edge = self.get_edge(prev, next, EdgeType.NEXT)
        self.remove_edge(edge)
        self.add_next(prev, event)
        self.add_next(event, next)

    def add_line(self, line: list[SequentialObject]) -> None:
        """Create a new linear subgraph from a list of objects."""
        pass

    def insert_line_from_list(self, line: list[SequentialObject], prev: SequentialObject, next: SequentialObject) -> None:
        """Create a new linear subgraph from a list of objects and insert """