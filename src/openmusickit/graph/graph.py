from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from openmusickit.graph.edges.edge import EdgeType, OmkEdge
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.graph.rx_adapter import RustworkxAdapter
from openmusickit.objects.lyrics.lyrics import LyricSequence, LyricSyllable
from openmusickit.objects.omk_object import OmkObject, SequentialObject, Spanner, TonalObject
from openmusickit.utils.id import OmkId
from openmusickit.values.tone.tone import Tone


class GraphMeta:
    """Details about the graph, including title, composer name, etc."""

    pass


class OmkGraph:
    """A graph representation of music."""

    def __init__(self, meta: GraphMeta, graph_engine: GraphAdapter | None = None):
        self._meta = meta
        self._graph = graph_engine if graph_engine is not None else RustworkxAdapter()

    # Load and import

    @classmethod
    def load_from_json(cls, js_graph, graph_engine: GraphAdapter | None = None) -> OmkGraph:
        """Returns an OmkGraph built from a JSON serialization."""
        raise NotImplementedError

    @classmethod
    def load_from_file(cls, f: Path, graph_engine: GraphAdapter | None = None) -> OmkGraph:
        raise NotImplementedError

    def import_json_graph(self, js_graph) -> None:
        """Adds the contents of js_graph to the current graph.
        Do not assume metadata from the source graph is retained."""
        raise NotImplementedError

    def import_file(self, f: Path) -> None:
        raise NotImplementedError

    def export_to_json(self):
        raise NotImplementedError

    def export_json_to_file(self, f: Path) -> None:
        raise NotImplementedError

    # Basic Add, Connect, Remove

    def get_node(self, id: OmkId | str) -> OmkObject | None:
        """Returns an OmkObj based on id. Returns None if no such object exists."""
        id = str(id)
        return self._graph.get_node(id)

    def add_node(self, obj: OmkObject) -> None:
        """Adds node to the graph. If the node is already on the graph, does nothing."""
        self._graph.add_node(obj)

    def remove_node(self, obj: OmkObject) -> None:
        """Removes a node and all related edges from the graph.

        This does not automatically remove the object and edges from memory;
        if you retain a reference to the object and edges, they remain accessible
        until they are garbage collected.

        Raises an exception if the node does not exist."""
        self._graph.remove_node(obj)

    def get_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> OmkEdge:
        return self._graph.get_edge(from_obj, to_obj, edge_type)

    def get_edges(
        self, from_obj: OmkObject, to_obj: OmkObject
    ) -> tuple[list[OmkEdge], list[OmkEdge]]:
        return self._graph.get_edges(from_obj, to_obj)

    def get_edges_by_type(self, edge_type: EdgeType) -> list[OmkEdge]:
        return [edge for edge in self._graph.edges(edge_type)]

    def add_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> None:
        edge = OmkEdge(_type=edge_type)
        self._graph.add_edge(from_obj, to_obj, edge)

    def remove_edge(self, edge: OmkEdge) -> OmkEdge:
        return self._graph.remove_edge(edge)

    # Sequential Data

    def add_next(self, current: SequentialObject, next: SequentialObject) -> None:
        """Places a SequentialObject after another SequentialObject.

        Current node must be on the graph before adding a next node.
        Next node can be on the graph or not."""
        self.add_node(next)
        self.add_edge(current, next, EdgeType.NEXT)

    def get_next(self, current: SequentialObject) -> SequentialObject | None:
        return self._graph.get_next(current)

    def get_previous(self, current: SequentialObject) -> SequentialObject | None:
        return self._graph.get_previous(current)

    def insert_event(
        self, event: SequentialObject, prev: SequentialObject, next: SequentialObject
    ) -> None:
        """Insert a SequentialObject between two SequentialObjects.

        It makes no difference if the inserted object was already part of the graph."""
        edge = self.get_edge(prev, next, EdgeType.NEXT)
        self.remove_edge(edge)
        self.add_next(prev, event)
        self.add_next(event, next)

    def add_line(self, line: list[SequentialObject]) -> None:
        """Create a new linear subgraph from a list of objects."""
        prev = None
        for obj in line:
            if prev is not None:
                self.add_next(prev, obj)
            else:
                self.add_node(obj)
            prev = obj

    def insert_line_from_list(
        self, line: list[SequentialObject], prev: SequentialObject, next: SequentialObject
    ) -> None:
        """Create a new linear subgraph from a list of objects and insert it between prev and next."""
        edge = self.get_edge(prev, next, EdgeType.NEXT)
        if edge is not None:
            self.remove_edge(edge)
        if not line:
            return
        self.add_next(prev, line[0])
        for i in range(len(line) - 1):
            self.add_next(line[i], line[i + 1])
        self.add_next(line[-1], next)

    def define_span(
        self, start: SequentialObject, end: SequentialObject, spanner: Spanner | None = None
    ) -> Spanner:
        """Defines a span of SequentialObjects from start to end, inclusive."""
        spanner = spanner or Spanner()
        self.add_node(spanner)
        self.add_edge(spanner, start, EdgeType.STARTS_AT)
        self.add_edge(spanner, end, EdgeType.ENDS_AT)
        return spanner

    def transform_tones(
        self,
        start: SequentialObject,
        end: SequentialObject | None,
        operation: Callable[..., Tone],
        *args,
        **kwargs,
    ) -> None:
        """Applies `operation` to the tonal content of every TonalObject from
        `start` to `end` (inclusive) along NEXT edges; `end=None` runs to the end
        of the line. Objects without tonal content are passed over.

        Raises ValueError if the line ends before `end` is reached.

        >>> from openmusickit.objects.note.note import NoteEvent
        >>> from openmusickit.objects.chord.chord_event import ChordEvent
        >>> from openmusickit.objects.context.context_event import KeySignatureEvent
        >>> from openmusickit.systems.wsmn.tonal.key import Key
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Gx, B, maj, M3, Major
        >>> key, note, chord = (KeySignatureEvent(_key=Key.of(C, Major)),
        ...                     NoteEvent(tones={C, E, G}), ChordEvent(chord=C(maj)))
        >>> graph = OmkGraph(GraphMeta())
        >>> graph.add_line([key, note, chord])
        >>> graph.transform_tones(key, chord, TonalVector.transpose, M3)
        >>> key.key.name, note.tones == {E, Gx, B}, str(chord.chord)
        ('E Major', True, 'E')
        """
        obj = start
        while obj is not None:
            if isinstance(obj, TonalObject):
                obj.transform_tones(operation, *args, **kwargs)
            if obj is end:
                return
            obj = self.get_next(obj)

        if end is not None:
            raise ValueError(
                f"{end!r} was not reached: the line starting at {start!r} ended first."
            )

    # Annotations (articulations, memos, analysis)

    def add_articulation(self, articulation: OmkObject, obj: OmkObject) -> None:
        self.add_node(articulation)
        self.add_edge(articulation, obj, EdgeType.MARKS)

    def add_annotation(self, annotation: OmkObject, obj: OmkObject) -> None:
        self.add_node(annotation)
        self.add_edge(annotation, obj, EdgeType.ANNOTATES)

    # Spanners (slurs, crescendos, phrasing)

    def add_spanner(
        self, spanner: OmkObject, start: SequentialObject, end: SequentialObject
    ) -> None:
        self.add_node(spanner)
        self.add_edge(spanner, start, EdgeType.STARTS_AT)
        self.add_edge(spanner, end, EdgeType.ENDS_AT)

    # Lyrics
    def add_lyric_syllable(self, lyric_syllable: LyricSyllable) -> None:
        self.add_node(lyric_syllable)

    def connect_lyric_to_object(self, lyric_syllable: LyricSyllable, obj: OmkObject) -> None:
        self.add_edge(obj, lyric_syllable, EdgeType.LYRIC)

    def add_lyric_sequence(self, lyric_sequence: LyricSequence) -> None:
        """Creates a new linear subgraph from a sequence of lyric syllables."""
        prev = None
        for syllable in lyric_sequence:
            if prev is not None:
                self.add_next(prev, syllable)
            else:
                self.add_node(syllable)
            prev = syllable
        # Do something with lyric sequence metadata once i have an annotation object

    def zip_lyrics_to_objects(
        self, start_syllable: LyricSyllable, start_object: SequentialObject
    ) -> None:
        """Connects a sequence of lyric syllables to a sequence of musical objects in a one-to-one manner."""
        syllable = start_syllable
        obj = start_object
        while syllable is not None and obj is not None:
            self.connect_lyric_to_object(syllable, obj)
            syllable = self.get_next(syllable)
            obj = self.get_next(obj)

    def unlink_lyric_from_object(self, lyric_syllable: LyricSyllable, obj: OmkObject) -> None:
        self.remove_edge(self.get_edge(obj, lyric_syllable, EdgeType.LYRIC))

    def unlink_lyric_sequence(
        self, start_syllable: LyricSyllable, stop_syllable: LyricSyllable | None = None
    ) -> None:
        """Unlink a sequence of lyric syllables from their associated musical objects, stopping at the specified stop syllable if provided.
        If no stop syllable is provided, the sequence will be unlinked until the end."""
        syllable = start_syllable
        while syllable is not None:
            if stop_syllable is not None and syllable == stop_syllable:
                break
            next_syllable = self.get_next(syllable)
            for edge in list(self._graph.incident_edges(syllable, EdgeType.LYRIC)):
                self.remove_edge(edge)
            syllable = next_syllable
