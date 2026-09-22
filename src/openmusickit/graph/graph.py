from __future__ import annotations

import copy
import warnings
from collections import deque
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from uuid import UUID, uuid4

from openmusickit.errors import GraphError, OmkWarning
from openmusickit.graph.edge import (
    Branch,
    EdgeType,
    Next,
    OmkEdge,
    Simultaneous,
    TimedEdge,
    TimingAnchor,
)
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.graph.rx_adapter import RustworkxAdapter
from openmusickit.objects.lyrics import LyricSection, LyricSyllable, parse_lyrics
from openmusickit.objects.marking import Marked, Marking
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject, SequentialEvent, Spanner, TonalObject
from openmusickit.objects.part import Part, Stint
from openmusickit.values.time.duration import Duration, ZeroDuration
from openmusickit.values.tone.tone import Tone


class GraphMeta:
    """Details about the graph, including title, composer name, etc."""

    pass


class OmkGraph:
    """A graph representation of music: objects (see `objects`) as nodes,
    related by typed edges (see `graph.edge`). See the `graph` package
    docstring for lines, branches, pins, parts and stints.

    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
    >>> graph = OmkGraph(GraphMeta())
    >>> c, d, e = (NoteEvent(tones={t}, duration=quarter) for t in (C, D, E))
    >>> graph.add_line([c, d, e])
    >>> [format(next(iter(n.tones))) for n in graph.walk_line(c)]
    ['C', 'D', 'E']
    >>> graph.relative_onset(c, e)
    MetricalDuration(1, 2)
    """

    def __init__(self, meta: GraphMeta, graph_engine: GraphAdapter | None = None):
        self._meta = meta
        self._graph = graph_engine if graph_engine is not None else RustworkxAdapter()

    # Load and import

    @classmethod
    def from_json(cls, js_graph, graph_engine: GraphAdapter | None = None) -> OmkGraph:
        """Returns an OmkGraph built from a JSON serialization."""
        raise NotImplementedError

    @classmethod
    def from_file(cls, f: Path, graph_engine: GraphAdapter | None = None) -> OmkGraph:
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

    def get_node(self, node_id: UUID | str) -> OmkObject | None:
        """Returns an OmkObj based on id. Returns None if no such object exists.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C
        >>> graph = OmkGraph(GraphMeta())
        >>> note = NoteEvent(tones={C})
        >>> graph.add_node(note)
        >>> graph.get_node(note.id) is note, graph.get_node(str(note.id)) is note
        (True, True)
        """
        return self._graph.get_node(str(node_id))

    def add_node(self, obj: OmkObject) -> None:
        """Adds node to the graph. If the node is already on the graph, does nothing.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C
        >>> graph = OmkGraph(GraphMeta())
        >>> note = NoteEvent(tones={C})
        >>> graph.add_node(note)
        >>> graph.add_node(note)  # a second add is a no-op
        >>> graph.get_node(note.id) is note
        True
        """
        self._graph.add_node(obj)

    def remove_node(self, obj: OmkObject) -> None:
        """Removes a node and all related edges from the graph.

        This does not automatically remove the object and edges from memory;
        if you retain a reference to the object and edges, they remain accessible
        until they are garbage collected.

        Removing an event from the middle of a line takes its NEXT edges with it:

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.remove_node(d)
        >>> graph.get_next(c) is None, list(graph.edges())
        (True, [])

        Raises an exception if the node does not exist."""
        self._graph.remove_node(obj)

    def get_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> OmkEdge:
        """Returns the edge of `edge_type` from `from_obj` to `to_obj`.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> graph.get_edge(c, d, EdgeType.NEXT).type
        <EdgeType.NEXT: 'next'>
        >>> graph.get_edge(c, d, EdgeType.MARKS)
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: No edge of type <EdgeType.MARKS: 'marks'> between ...

        Raises
        ------
        GraphError
            if there is no such edge.
        """
        return self._graph.get_edge(from_obj, to_obj, edge_type)

    def edges_between(
        self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType | None = None
    ) -> Iterator[OmkEdge]:
        """Iterates over the edges from from_obj to to_obj, optionally filtered by edge_type.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> [edge.type for edge in graph.edges_between(c, d)]
        [<EdgeType.NEXT: 'next'>]
        >>> list(graph.edges_between(d, c))  # edges are directed
        []
        """
        return self._graph.edges_between(from_obj, to_obj, edge_type)

    def edges(self, edge_type: EdgeType | None = None) -> Iterator[OmkEdge]:
        """Iterates over all edges, optionally filtered by edge_type.

        >>> from openmusickit.objects.marking import Marking
        >>> from openmusickit.systems.wsmn.scoring.symbols import staccato
        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.add_articulation(Marking(mark=staccato), c)
        >>> sorted(edge.type.name for edge in graph.edges())
        ['MARKS', 'NEXT', 'NEXT']
        >>> [edge.type.name for edge in graph.edges(EdgeType.MARKS)]
        ['MARKS']
        """
        return self._graph.edges(edge_type)

    def add_edge(self, from_obj: OmkObject, to_obj: OmkObject, edge_type: EdgeType) -> None:
        """Adds a plain edge of `edge_type`; the semantic methods (`add_next`,
        `add_branch`, `add_articulation`, ...) build on this and are usually
        what a caller wants.

        >>> from openmusickit.objects.marking import Marking
        >>> from openmusickit.systems.wsmn.scoring.symbols import staccato
        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> dot = Marking(mark=staccato)
        >>> graph.add_line([c, d])
        >>> graph.add_node(dot)
        >>> graph.add_edge(dot, c, EdgeType.MARKS)
        >>> graph.get_edge(dot, c, EdgeType.MARKS).type
        <EdgeType.MARKS: 'marks'>
        >>> graph.add_edge(dot, c, EdgeType.MARKS)  # one edge of a type between two nodes
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: An edge of type <EdgeType.MARKS: 'marks'> already exists ...

        Raises
        ------
        GraphError
            if an edge of that type already exists between the two nodes,
            or if a NEXT edge would give a node a second NEXT in or out.
        """
        edge = OmkEdge(type=edge_type)
        self._graph.add_edge(from_obj, to_obj, edge)

    def remove_edge(self, edge: OmkEdge) -> OmkEdge:
        """Removes an edge, found with `get_edge` or by iterating `edges`,
        and returns it, so an undo has what it removed (its type,
        displacement and metadata) to hand.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> removed = graph.remove_edge(graph.get_edge(c, d, EdgeType.NEXT))
        >>> removed, graph.get_next(c) is None, graph.get_previous(d) is None
        (Next(next, origin=asserted), True, True)
        """
        self._graph.remove_edge(edge)
        return edge

    # Sequential Data

    def add_next(self, current: SequentialEvent, following: SequentialEvent) -> None:
        """Places a SequentialEvent after another SequentialEvent.

        Current node must be on the graph before adding a next node.
        Next node can be on the graph or not.

        A line is a chain: an event has at most one NEXT out and one NEXT in.
        Music that runs alongside a line goes on a line of its own, joined to
        this one by `add_branch` or `add_simultaneous`.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> graph.add_next(c, e)
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: Source NoteEvent(...) already has an outgoing edge of type NEXT.
        >>> graph.add_next(e, d)
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: Target NoteEvent(...) already has an incoming edge of type NEXT.
        """
        self.add_node(following)
        self._graph.add_edge(current, following, Next())

    def get_next(self, current: SequentialEvent) -> SequentialEvent | None:
        """The event that follows `current` in its line, or None at the end of the line.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.get_next(c) is d, graph.get_next(e) is None
        (True, True)
        """
        return self._graph.get_next(current)

    def get_previous(self, current: SequentialEvent) -> SequentialEvent | None:
        """The event before `current` in its line, or None at the head of the line.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.get_previous(d) is c, graph.get_previous(c) is None
        (True, True)
        """
        return self._graph.get_previous(current)

    def insert_event(
        self, event: SequentialEvent, prev: SequentialEvent, following: SequentialEvent
    ) -> None:
        """Insert a SequentialEvent between two SequentialEvents.

        It makes no difference if the inserted object was already part of the graph.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, e])
        >>> graph.insert_event(d, c, e)
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(c)]
        ['C', 'D', 'E']
        """
        edge = self.get_edge(prev, following, EdgeType.NEXT)
        self.remove_edge(edge)
        self.add_next(prev, event)
        self.add_next(event, following)

    def add_line(self, line: list[SequentialEvent]) -> None:
        """Create a new linear subgraph from a list of objects.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(c)]
        ['C', 'D', 'E']
        >>> graph.get_previous(c) is None, graph.get_next(e) is None
        (True, True)
        """
        prev = None
        for obj in line:
            if prev is not None:
                self.add_next(prev, obj)
            else:
                self.add_node(obj)
            prev = obj

    def insert_line_from_list(
        self, line: list[SequentialEvent], prev: SequentialEvent, following: SequentialEvent
    ) -> None:
        """Create a new linear subgraph from a list of objects and insert it between prev and next.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e, f = (NoteEvent(tones={t}) for t in (C, D, E, F))
        >>> graph.add_line([c, f])
        >>> graph.insert_line_from_list([d, e], c, f)
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(c)]
        ['C', 'D', 'E', 'F']
        """
        self.remove_edge(self.get_edge(prev, following, EdgeType.NEXT))
        if not line:
            self.add_next(prev, following)
            return
        self.add_next(prev, line[0])
        self.add_line(line)
        self.add_next(line[-1], following)

    def walk_line(
        self, start: SequentialEvent, end: SequentialEvent | None = None
    ) -> Iterator[SequentialEvent]:
        """Yields the events from `start` to `end` (inclusive) along NEXT edges;
        `end=None` runs to the end of the line. Never leaves the line, and
        yields each event once: a cyclic line (a gamelan cycle, whose last
        event is followed by its first) comes out as one pass from `start`.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(d)]
        ['D', 'E']
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(c, d)]
        ['C', 'D']
        >>> list(graph.walk_line(e, c))
        Traceback (most recent call last):
        ...
        ValueError: NoteEvent(...) was not reached: the line starting at NoteEvent(...) ended first.
        >>> graph.add_next(e, c)  # close the cycle
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(d)]
        ['D', 'E', 'C']

        Raises ValueError if the line ends, or comes back round to an event
        already yielded, before `end` is reached.
        """
        seen: set[UUID] = set()
        for obj in self._follow_next(start):
            if obj.id in seen:
                break
            seen.add(obj.id)
            yield obj
            if obj is end:
                return
        if end is not None:
            raise ValueError(
                f"{end!r} was not reached: the line starting at {start!r} ended first."
            )

    def _follow_next(self, start: SequentialEvent) -> Iterator[SequentialEvent]:
        """Yields `start` and then each NEXT successor for as long as there is
        one. On a cyclic line this never stops: `walk_line` bounds it to one
        pass over the events, and a walker that means to go round (a
        realization playing a cycle continuously, or a counted number of
        times) bounds it its own way.
        """
        obj: SequentialEvent | None = start
        while obj is not None:
            yield obj
            obj = self.get_next(obj)

    def walk_span(
        self, start: SequentialEvent, end: SequentialEvent | None = None
    ) -> Iterator[SequentialEvent]:
        """Yields the events from `start` to `end` (inclusive) along NEXT edges,
        and, after each, the whole of every line branched from it: everything
        the performer of this line does over that stretch. Pinned lines
        (`add_simultaneous`) are never entered. Each event is yielded once,
        however the lines cycle or branch back into each other.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, A, B
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e, a, b = (NoteEvent(tones={t}) for t in (C, D, E, A, B))
        >>> graph.add_line([c, d, e])
        >>> graph.add_line([a, b])
        >>> graph.add_branch(d, a)                  # a second voice under d-e
        >>> [format(next(iter(n.tones))) for n in graph.walk_span(c)]
        ['C', 'D', 'A', 'B', 'E']
        >>> [format(next(iter(n.tones))) for n in graph.walk_line(c)]
        ['C', 'D', 'E']
        """
        yield from self._walk_span(start, end, set())

    def _walk_span(
        self, start: SequentialEvent, end: SequentialEvent | None, seen: set[UUID]
    ) -> Iterator[SequentialEvent]:
        """`walk_span` with the events already yielded, shared down the
        recursion, so a head branched from its own tree is entered once."""
        for event in self.walk_line(start, end):
            if event.id in seen:
                return
            seen.add(event.id)
            yield event
            for head in self.branches_from(event):
                yield from self._walk_span(head, None, seen)

    def transform_tones(
        self,
        start: SequentialEvent,
        end: SequentialEvent | None,
        operation: Callable[..., Tone],
        *args,
        **kwargs,
    ) -> None:
        """Applies `operation` to the tonal content of every TonalObject from
        `start` to `end` (inclusive), over the span (`walk_span`): along NEXT
        edges and into every line branched from them, never into a pinned
        line. `end=None` runs to the end of the line. Objects without tonal
        content are passed over.

        Raises ValueError if the line ends before `end` is reached.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.objects.chord_event import ChordEvent
        >>> from openmusickit.objects.context_event import ModalContextEvent
        >>> from openmusickit.systems.wsmn.tonal.key import Key
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, E, G, Gx, B, maj, M3, Major
        >>> key, note, chord = (ModalContextEvent(modal_context=Key.of(C, Major)),
        ...                     NoteEvent(tones={C, E, G}), ChordEvent(chord=C(maj)))
        >>> graph = OmkGraph(GraphMeta())
        >>> graph.add_line([key, note, chord])
        >>> graph.transform_tones(key, chord, TonalVector.transpose, M3)
        >>> key.modal_context.name, note.tones == {E, Gx, B}, str(chord.chord)
        ('E Major', True, 'E')
        """
        for obj in self.walk_span(start, end):
            if isinstance(obj, TonalObject):
                obj.transform_tones(operation, *args, **kwargs)

    # Compound lines: branches (same performer), pins (independent lines), timing

    def add_branch(
        self,
        parent: SequentialEvent,
        head: SequentialEvent,
        anchor: TimingAnchor = TimingAnchor.ONSET,
        displacement: Duration | None = None,
    ) -> None:
        """Hangs the line starting at `head` off `parent`: the same performer
        does both. The child starts at the `anchor` of `parent` (its onset by
        default; its offset for a voice that begins after this event) plus the
        signed `displacement`.

        A whole-piece layer (the pianist's left hand, the drummer's feet) is a
        line branched head-from-head; a one-measure second voice is a short
        line branched from the event it starts under. Either way it just ends
        when it ends; there is no join.

        `parent` must be on the graph; `head` may or may not be. `head` must be
        the head of a line (no NEXT in), not already branched, and not the
        start of a Stint (whoever performs the parent performs the branch).

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, half
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, A, B
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}, duration=half) for t in (C, D, E))
        >>> a, b = (NoteEvent(tones={t}, duration=quarter) for t in (A, B))
        >>> graph.add_line([c, d, e])
        >>> graph.add_line([a, b])
        >>> graph.add_branch(c, a, anchor=TimingAnchor.OFFSET)   # a-b fills the time of d
        >>> graph.relative_onset(c, b)
        MetricalDuration(1, 2, dots=1)
        >>> graph.relative_onset(b, e)
        MetricalDuration(1, 4)
        >>> graph.add_branch(d, b)
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: NoteEvent(...) is not the head of a line.
        """
        self.add_node(head)
        if self.get_previous(head) is not None:
            raise GraphError(f"{head!r} is not the head of a line.")
        if any(self._graph.in_edges(head, EdgeType.BRANCHES)):
            raise GraphError(f"{head!r} is already branched from another line.")
        if any(self._graph.predecessors(head, Stint, EdgeType.STARTS_AT)):
            raise GraphError(
                f"A Stint starts at {head!r}; a branched line is performed by "
                "whoever performs its parent."
            )
        self._graph.add_edge(parent, head, Branch(anchor=anchor, displacement=displacement))

    def branches_from(self, event: SequentialEvent) -> Iterator[SequentialEvent]:
        """The heads of the lines branched from `event`.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, A
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, a = (NoteEvent(tones={t}) for t in (C, D, A))
        >>> graph.add_line([c, d])
        >>> graph.add_branch(d, a)
        >>> list(graph.branches_from(d)) == [a], list(graph.branches_from(c))
        (True, [])
        """
        return self._graph.successors(event, SequentialEvent, EdgeType.BRANCHES)

    def add_simultaneous(
        self,
        event: SequentialEvent,
        other: SequentialEvent,
        anchor: TimingAnchor = TimingAnchor.ONSET,
        displacement: Duration | None = None,
    ) -> None:
        """Pins `other` to `event`: it starts at the `anchor` of `event` plus
        the signed `displacement`. The two lines stay independent; nothing is
        said about who performs either, and span walks never cross a pin.

        This is how incomplete music is joined without a score origin: a
        three-bar chord line pinned to bar 1 of a melody, a countermelody
        pinned under a held note with a displacement.

        `event` must be on the graph; `other` may or may not be.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.objects.chord_event import ChordEvent
        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, whole
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F, maj
        >>> graph = OmkGraph(GraphMeta())
        >>> melody = [NoteEvent(tones={t}, duration=quarter) for t in (C, D, E, F)]
        >>> chords = [ChordEvent(chord=C(maj), duration=whole), ChordEvent(chord=F(maj), duration=whole)]
        >>> graph.add_line(melody)
        >>> graph.add_line(chords)
        >>> graph.add_simultaneous(melody[1], chords[0], displacement=-quarter)  # chords start with the melody
        >>> graph.relative_onset(melody[0], chords[1])
        MetricalDuration(1, 1)
        >>> [n is melody[0] for n in graph.walk_span(chords[0])]     # pins are not entered
        [False, False]
        """
        self.add_node(other)
        self._graph.add_edge(event, other, Simultaneous(anchor=anchor, displacement=displacement))

    def relative_onset(self, reference: SequentialEvent, event: SequentialEvent) -> Duration:
        """How long after the onset of `reference` the onset of `event` falls
        (negative if before), found by following NEXT edges through event
        durations and branches and pins through their anchors.

        There is no score origin; a position only ever means "relative to".
        An event with `duration=None` is opaque: nothing is known about what
        follows it or hangs from its offset. Where pins disagree with the
        lines' own durations, the first path found wins; see `check_alignment`.

        Raises GraphError if no timing path connects the two events.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, half
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}, duration=quarter) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.relative_onset(c, e), graph.relative_onset(e, c), graph.relative_onset(c, c)
        (MetricalDuration(1, 2), MetricalDuration(-1, 2), ZeroDuration())
        >>> d.duration = None
        >>> graph.relative_onset(c, e)
        Traceback (most recent call last):
        ...
        openmusickit.errors.GraphError: No timing path connects NoteEvent(...) to NoteEvent(...).
        """
        offset = self._relative_onset(reference, event, ignoring=None)
        if offset is None:
            raise GraphError(f"No timing path connects {reference!r} to {event!r}.")
        return offset

    def _relative_onset(
        self, reference: SequentialEvent, event: SequentialEvent, ignoring: OmkEdge | None
    ) -> Duration | None:
        """Breadth-first search of the timing graph from `reference`, skipping
        the edge `ignoring`; None if `event` is not reached."""
        offsets: dict[UUID, Duration] = {reference.id: ZeroDuration()}
        queue: deque[SequentialEvent] = deque([reference])
        while queue:
            node = queue.popleft()
            if node is event:
                return offsets[node.id]
            for neighbour, delta in self._timing_neighbours(node, ignoring):
                if neighbour.id in offsets:
                    continue
                offsets[neighbour.id] = offsets[node.id] + delta
                queue.append(neighbour)
        return None

    def _timing_neighbours(
        self, node: SequentialEvent, ignoring: OmkEdge | None
    ) -> Iterator[tuple[SequentialEvent, Duration]]:
        """Every event whose onset is a known distance from the onset of
        `node`, with that distance: the next and previous events in the line,
        and the far ends of branches and pins in either direction."""
        following = self.get_next(node)
        if following is not None and node.duration is not None:
            yield following, node.duration
        previous = self.get_previous(node)
        if previous is not None and previous.duration is not None:
            yield previous, -previous.duration
        for edge_type in (EdgeType.BRANCHES, EdgeType.SIMULTANEOUS):
            for edge in self._graph.out_edges(node, edge_type):
                delta = self._timed_delta(edge, node)
                if edge is not ignoring and delta is not None:
                    yield self._graph.get_target_of_edge(edge), delta
            for edge in self._graph.in_edges(node, edge_type):
                source = self._graph.get_source_of_edge(edge)
                delta = self._timed_delta(edge, source)
                if edge is not ignoring and delta is not None:
                    yield source, -delta

    @staticmethod
    def _timed_delta(edge: TimedEdge, source: SequentialEvent) -> Duration | None:
        """How long after the onset of `source` the target of `edge` starts;
        None if the edge hangs from the offset of an event of unknown duration."""
        delta = edge.displacement if edge.displacement is not None else ZeroDuration()
        if edge.anchor is TimingAnchor.OFFSET:
            if source.duration is None:
                return None
            delta = source.duration + delta
        return delta

    def check_alignment(self) -> list[Simultaneous]:
        """Checks every pin against the rest of the timing graph.

        Branches alone keep timing a tree, always consistent. Pins make it a
        graph: two pins between the same lines can disagree with the lines'
        own durations. That is a musical fact to report, not an error: each
        pin whose claim differs from the offset found by another path is
        returned, with an `OmkWarning`. A pin with no other path is unchecked.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, whole
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, A, B
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}, duration=quarter) for t in (C, D, E))
        >>> a, b = (NoteEvent(tones={t}, duration=whole) for t in (A, B))
        >>> graph.add_line([c, d, e])
        >>> graph.add_line([a, b])
        >>> graph.add_simultaneous(c, a)
        >>> graph.add_simultaneous(e, b)         # but b is a whole after a, e only a half after c
        >>> import warnings
        >>> with warnings.catch_warnings(record=True) as caught:
        ...     warnings.simplefilter("always")
        ...     conflicts = graph.check_alignment()
        >>> len(conflicts), str(caught[1].message)
        (2, 'NoteEvent(tones=[TonalVector((6, 11))], duration=MetricalDuration(1, 1)) is pinned ZeroDuration() after NoteEvent(tones=[TonalVector((2, 4))], duration=MetricalDuration(1, 4)), but lies MetricalDuration(1, 2) after it by another path.')
        """
        conflicts: list[Simultaneous] = []
        for edge in self._graph.edges(EdgeType.SIMULTANEOUS):
            source, target = self._graph.get_edge_endpoints(edge)
            claimed = self._timed_delta(edge, source)
            if claimed is None:
                continue
            found = self._relative_onset(source, target, ignoring=edge)
            if found is None or found == claimed:
                continue
            warnings.warn(
                f"{target!r} is pinned {claimed!r} after {source!r}, "
                f"but lies {found!r} after it by another path.",
                OmkWarning,
                stacklevel=2,
            )
            conflicts.append(edge)
        return conflicts

    # Parts and stints (who performs what)

    def add_stint(
        self, part: Part, stint: Stint, start: SequentialEvent, end: SequentialEvent | None = None
    ) -> None:
        """Records that `part` performs the line from `start` to `end`
        (inclusive), or to the end of the line, however long it grows, if
        `end` is None. Everything branched from those events is covered too.

        `start` must not be a branched head: a branched line is performed by
        whoever performs its parent.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, P5
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> flute, oboe = Part(name="Flute"), Part(name="Oboe")
        >>> graph.add_stint(flute, Stint(), c)
        >>> graph.add_stint(oboe, Stint(transposition=P5), c, d)     # doubling, a fifth up, for two notes
        >>> [len(list(graph.walk_stint(s))) for s in graph.stints(oboe)]
        [2]
        """
        self.add_node(part)
        self.add_node(stint)
        if any(self._graph.in_edges(start, EdgeType.BRANCHES)):
            raise GraphError(
                f"{start!r} is a branched head; it is performed by whoever performs its parent."
            )
        self.add_edge(part, stint, EdgeType.PERFORMS)
        self.add_edge(stint, start, EdgeType.STARTS_AT)
        if end is not None:
            self.add_edge(stint, end, EdgeType.ENDS_AT)

    def stints(self, part: Part) -> Iterator[Stint]:
        """The stints `part` performs, in no particular order.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> flute, stint = Part(name="Flute"), Stint()
        >>> graph.add_stint(flute, stint, c)
        >>> list(graph.stints(flute)) == [stint]
        True
        """
        return self._graph.successors(part, Stint, EdgeType.PERFORMS)

    def walk_stint(self, stint: Stint) -> Iterator[SequentialEvent]:
        """The events `stint` covers (`walk_span` from its start to its end).
        The events are yielded as they are; `stint.transposition` is the
        consumer's to apply.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> stint = Stint()
        >>> graph.add_stint(Part(name="Oboe"), stint, c, d)
        >>> [format(next(iter(n.tones))) for n in graph.walk_stint(stint)]
        ['C', 'D']
        """
        start, end = self._stint_bounds(stint)
        return self.walk_span(start, end)

    def _stint_bounds(self, stint: Stint) -> tuple[SequentialEvent, SequentialEvent | None]:
        start = next(self._graph.successors(stint, SequentialEvent, EdgeType.STARTS_AT))
        end = next(self._graph.successors(stint, SequentialEvent, EdgeType.ENDS_AT), None)
        return start, end

    def materialize(self, stint: Stint) -> SequentialEvent:
        """Forks a doubled line: copies everything that defines the music
        `stint` covers into a new line, points the stint at the copy, and
        returns the copy's head. The copy starts exact, so the two parts can
        now diverge; the original events, and any other stint over them, are
        untouched.

        Copied: the events (`walk_span`, so branches come along), and every
        mark, spanner, annotation and lyric attached to them, with all the
        edges among those things. Not copied: relationships to other lines
        (pins to events outside the span), other Parts' stints, and any
        spanner (a slur, a lyric section) that reaches beyond the covered
        events -- such a spanner is left out with an `OmkWarning`, since the
        copy has no event for its other end.

        >>> from openmusickit.objects.marking import Marking, MarkSpanner
        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.scoring.symbols import slur, staccato
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, P5
        >>> from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> graph.add_articulation(Marking(mark=staccato), c)
        >>> graph.add_spanner(MarkSpanner(mark=slur), c, d)
        >>> flute, oboe = Part(name="Flute"), Part(name="Oboe")
        >>> graph.add_stint(flute, Stint(), c)
        >>> oboe_stint = Stint()
        >>> graph.add_stint(oboe, oboe_stint, c, d)
        >>> head = graph.materialize(oboe_stint)
        >>> head == c, head is c, graph.get_previous(head) is None
        (True, False, True)
        >>> sorted(type(n).__name__ for n in graph._graph.predecessors(head))
        ['MarkSpanner', 'Marking', 'Stint']
        >>> graph.transform_tones(head, None, TonalVector.transpose, P5)
        >>> [format(next(iter(n.tones))) for n in graph.walk_stint(oboe_stint)]
        ['G', 'A']
        >>> [format(next(iter(n.tones))) for n in graph.walk_span(c)]
        ['C', 'D', 'E']
        """
        start, end = self._stint_bounds(stint)
        originals = self._covered_content(list(self.walk_span(start, end)))

        # one memo across the whole copy, so what the originals share (the Word
        # behind a run of syllables) the copies share too
        memo: dict[int, object] = {}
        copies = {original.id: _fork(original, memo) for original in originals}
        for copied in copies.values():
            self.add_node(copied)
        for original in originals:
            for edge in self._graph.out_edges(original):
                target = self._graph.get_target_of_edge(edge)
                if target.id in copies:
                    self._graph.add_edge(copies[original.id], copies[target.id], _fork(edge, memo))

        for edge_type in (EdgeType.STARTS_AT, EdgeType.ENDS_AT):
            for edge in list(self._graph.out_edges(stint, edge_type)):
                self.remove_edge(edge)
        self.add_edge(stint, copies[start.id], EdgeType.STARTS_AT)
        if end is not None:
            self.add_edge(stint, copies[end.id], EdgeType.ENDS_AT)
        return copies[start.id]

    def _covered_content(self, events: list[SequentialEvent]) -> list[OmkObject]:
        """`events` plus everything attached to them that defines the music
        there: marks, annotations, spanners, lyric syllables, and in turn
        whatever is attached to those (a lyric section over the syllables).
        Stints are not content, and a spanner with an end outside the set is
        dropped with a warning."""
        content: dict[UUID, OmkObject] = {event.id: event for event in events}
        queue = deque(events)
        while queue:
            node = queue.popleft()
            for attacher in self._attachers(node):
                if attacher.id not in content and not isinstance(attacher, Stint):
                    content[attacher.id] = attacher
                    queue.append(attacher)
        for node in list(content.values()):
            if isinstance(node, Spanner) and not all(
                endpoint.id in content
                for edge_type in (EdgeType.STARTS_AT, EdgeType.ENDS_AT)
                for endpoint in self._graph.successors(node, edge_type=edge_type)
            ):
                warnings.warn(
                    f"{node!r} was not copied: it reaches beyond the events the stint covers.",
                    OmkWarning,
                    stacklevel=3,
                )
                del content[node.id]
        return list(content.values())

    def _attachers(self, node: OmkObject) -> Iterator[OmkObject]:
        """The things attached to `node`: what marks, annotates or spans it,
        and the syllables it sings."""
        for edge_type in (EdgeType.MARKS, EdgeType.ANNOTATES, EdgeType.STARTS_AT, EdgeType.ENDS_AT):
            yield from self._graph.predecessors(node, edge_type=edge_type)
        yield from self._graph.successors(node, edge_type=EdgeType.LYRIC)

    # Annotations (articulations, memos, analysis)

    def add_articulation(self, articulation: Marking, obj: OmkObject) -> None:
        """Places a mark on one event, with a MARKS edge from the mark to the event.

        >>> from openmusickit.objects.marking import Marking
        >>> from openmusickit.systems.wsmn.scoring.symbols import staccato
        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> dot = Marking(mark=staccato)
        >>> graph.add_articulation(dot, c)
        >>> graph.get_edge(dot, c, EdgeType.MARKS).type
        <EdgeType.MARKS: 'marks'>
        """
        self.add_node(articulation)
        self.add_edge(articulation, obj, EdgeType.MARKS)

    def add_annotation(self, annotation: OmkObject, obj: OmkObject) -> None:
        """Attaches any object to another as an annotation (a memo, an
        analysis figure), with an ANNOTATES edge from the annotation to the object.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d])
        >>> memo = OmkObject()
        >>> graph.add_annotation(memo, c)
        >>> graph.get_edge(memo, c, EdgeType.ANNOTATES).type
        <EdgeType.ANNOTATES: 'annotates'>
        """
        self.add_node(annotation)
        self.add_edge(annotation, obj, EdgeType.ANNOTATES)

    # Spanners (slurs, crescendos, phrasing)

    def add_spanner(self, spanner: Spanner, start: SequentialEvent, end: SequentialEvent) -> None:
        """Places a spanner over the events from `start` to `end`, with
        STARTS_AT and ENDS_AT edges from the spanner to them.

        >>> from openmusickit.objects.marking import MarkSpanner
        >>> from openmusickit.systems.wsmn.scoring.symbols import slur
        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> arc = MarkSpanner(mark=slur)
        >>> graph.add_spanner(arc, c, d)
        >>> graph.get_edge(arc, c, EdgeType.STARTS_AT).type, graph.get_edge(arc, d, EdgeType.ENDS_AT).type
        (<EdgeType.STARTS_AT: 'starts_at'>, <EdgeType.ENDS_AT: 'ends_at'>)
        """
        self.add_node(spanner)
        self.add_edge(spanner, start, EdgeType.STARTS_AT)
        self.add_edge(spanner, end, EdgeType.ENDS_AT)

    # Lyrics

    def add_lyrics(
        self,
        lyrics: str | Iterable[LyricSyllable],
        section: LyricSection | None = None,
        after: LyricSyllable | None = None,
    ) -> list[LyricSyllable]:
        """Adds a line of lyric syllables, joined by NEXT edges.

        A string is parsed with `parse_lyrics`. `section`, if given, is added
        as a Spanner over the first and last syllable. `after` appends the
        line to an existing one. Returns the syllables in order, ready for
        `zip_lyrics_to_objects`.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F
        >>> graph = OmkGraph(GraphMeta())
        >>> notes = [NoteEvent(tones={tone}) for tone in (C, D, E, F)]
        >>> graph.add_line(notes)
        >>> verse = LyricSection(section_type="verse", section_number=1, language="la")
        >>> syllables = graph.add_lyrics("Al-le-lu-ia", section=verse)
        >>> graph.zip_lyrics_to_objects(syllables[0], notes[0])
        >>> " ".join(str(s) for s in syllables)
        'Al - - le - - lu - - ia'
        >>> graph.get_next(syllables[0]) is syllables[1], graph.get_next(syllables[-1])
        (True, None)
        >>> graph.get_edge(verse, syllables[0], EdgeType.STARTS_AT).type
        <EdgeType.STARTS_AT: 'starts_at'>
        >>> graph.get_edge(verse, syllables[-1], EdgeType.ENDS_AT).type
        <EdgeType.ENDS_AT: 'ends_at'>
        >>> graph.get_edge(notes[2], syllables[2], EdgeType.LYRIC).type
        <EdgeType.LYRIC: 'lyric'>

        Appending continues the line:

        >>> more = graph.add_lyrics("A-men", after=syllables[-1])
        >>> graph.get_next(syllables[-1]) is more[0]
        True
        """
        syllables = parse_lyrics(lyrics) if isinstance(lyrics, str) else list(lyrics)
        if not syllables:
            if section is not None:
                raise ValueError("A LyricSection needs at least one syllable to span.")
            return syllables
        if after is not None:
            self.add_next(after, syllables[0])
        self.add_line(syllables)
        if section is not None:
            self.add_spanner(section, syllables[0], syllables[-1])
        return syllables

    def connect_lyric_to_object(self, lyric_syllable: LyricSyllable, obj: OmkObject) -> None:
        """Records that `obj` *begins* `lyric_syllable`: a LYRIC edge marks a
        syllable's onset. The notes that go on sustaining it (a melisma) get
        no edge of their own; a sung note without one continues the previous
        syllable, and a rest ends it.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> a, men = graph.add_lyrics("A-men")
        >>> graph.connect_lyric_to_object(men, d)
        >>> graph.get_edge(d, men, EdgeType.LYRIC).type
        <EdgeType.LYRIC: 'lyric'>
        """
        self.add_node(lyric_syllable)
        self.add_edge(obj, lyric_syllable, EdgeType.LYRIC)

    def zip_lyrics_to_objects(
        self, start_syllable: LyricSyllable, start_object: SequentialEvent
    ) -> None:
        """Attaches a line of syllables to a line of events, one syllable per
        syllable onset, until either line runs out.

        Walking the events from `start_object`, a syllable begins on every
        event except: a rest; anything of zero duration (a context event or
        a division, which have nothing to sing, and a grace note, sung on
        the syllable of the note it decorates; to put a syllable on one, use
        `connect_lyric_to_object`); and an event that
        lies under a binding `MarkSpanner` (`mark.binds`: a slur or a tie)
        without starting it -- those continue the syllable begun on the
        span's first note. An event that ends one binding span and starts
        another is inside the first, so it continues rather than begins.

        >>> from openmusickit.objects.marking import MarkSpanner
        >>> from openmusickit.objects.note_event import Rest
        >>> from openmusickit.systems.wsmn.scoring.symbols import slur, crescendo
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E, F, G
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e, rest, f, g = (NoteEvent(tones={C}), NoteEvent(tones={D}),
        ...                        NoteEvent(tones={E}), Rest(None),
        ...                        NoteEvent(tones={F}), NoteEvent(tones={G}))
        >>> graph.add_line([c, d, e, rest, f, g])
        >>> graph.add_spanner(MarkSpanner(mark=slur), d, e)          # d-e is a melisma
        >>> graph.add_spanner(MarkSpanner(mark=crescendo), f, g)     # a hairpin binds nothing
        >>> syllables = graph.add_lyrics("Al-le-lu-ia")
        >>> graph.zip_lyrics_to_objects(syllables[0], c)
        >>> for note in (c, d, e, rest, f, g):
        ...     sung = [str(s) for s in graph._graph.successors(note, LyricSyllable, EdgeType.LYRIC)]
        ...     print(note, sung)
        NoteEvent(tones=[TonalVector((0, 0))], duration=None) ['Al -']
        NoteEvent(tones=[TonalVector((1, 2))], duration=None) ['- le -']
        NoteEvent(tones=[TonalVector((2, 4))], duration=None) []
        Rest(duration=None) []
        NoteEvent(tones=[TonalVector((3, 5))], duration=None) ['- lu -']
        NoteEvent(tones=[TonalVector((4, 7))], duration=None) ['- ia']
        """
        syllable = start_syllable
        obj = start_object
        bound_until: SequentialEvent | None = None  # last event of the binding span we are under
        while syllable is not None and obj is not None:
            if bound_until is not None:
                if obj is bound_until:
                    bound_until = None
            elif self._begins_syllable(obj):
                self.connect_lyric_to_object(syllable, obj)
                syllable = self.get_next(syllable)
                bound_until = self._binding_span_end(obj)
            obj = self.get_next(obj)

    def _begins_syllable(self, obj: SequentialEvent) -> bool:
        """Whether a syllable can begin on `obj`, ignoring any span it is under."""
        if isinstance(obj.duration, ZeroDuration):
            return False
        if isinstance(obj, NoteEvent) and obj.is_rest:
            return False
        return True

    def _binding_span_end(self, obj: SequentialEvent) -> SequentialEvent | None:
        """The last event of a binding MarkSpanner (slur, tie) that starts at
        `obj`, or None if no such span starts here."""
        for spanner in self._graph.predecessors(
            obj, Marked, EdgeType.STARTS_AT, predicate=lambda node: node.mark.binds
        ):
            for end in self._graph.successors(spanner, edge_type=EdgeType.ENDS_AT):
                if end is not obj:
                    return end
        return None

    def unlink_lyric_from_object(self, lyric_syllable: LyricSyllable, obj: OmkObject) -> None:
        """The inverse of `connect_lyric_to_object`: removes the LYRIC edge from `obj` to the syllable.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> a, men = graph.add_lyrics("A-men")
        >>> graph.connect_lyric_to_object(men, d)
        >>> graph.unlink_lyric_from_object(men, d)
        >>> list(graph.edges_between(d, men))
        []
        """
        self.remove_edge(self.get_edge(obj, lyric_syllable, EdgeType.LYRIC))

    def unlink_lyric_sequence(
        self, start_syllable: LyricSyllable, stop_syllable: LyricSyllable | None = None
    ) -> None:
        """Unlink a sequence of lyric syllables from their associated musical objects,
        stopping at the specified stop syllable if provided.
        If no stop syllable is provided, the sequence will be unlinked until the end.
        The syllables stay on the graph, in their NEXT line.

        >>> from openmusickit.objects.note_event import NoteEvent
        >>> from openmusickit.systems.wsmn.tonal.symbols import C, D, E
        >>> graph = OmkGraph(GraphMeta())
        >>> c, d, e = (NoteEvent(tones={t}) for t in (C, D, E))
        >>> graph.add_line([c, d, e])
        >>> a, men = graph.add_lyrics("A-men")
        >>> graph.zip_lyrics_to_objects(a, c)
        >>> len(list(graph.edges(EdgeType.LYRIC)))
        2
        >>> graph.unlink_lyric_sequence(a, stop_syllable=men)  # only "A" is unlinked
        >>> len(list(graph.edges(EdgeType.LYRIC)))
        1
        >>> graph.unlink_lyric_sequence(a)
        >>> list(graph.edges(EdgeType.LYRIC)), graph.get_next(a) is men
        ([], True)
        """
        syllable = start_syllable
        while syllable is not None:
            if syllable is stop_syllable:
                break
            next_syllable = self.get_next(syllable)
            for edge in list(self._graph.incident_edges(syllable, EdgeType.LYRIC)):
                self.remove_edge(edge)
            syllable = next_syllable


def _fork[T: (OmkObject, OmkEdge)](original: T, memo: dict[int, object]) -> T:
    """A copy of an object or edge with an id of its own: the same musical
    content, a new place in the score. `memo` is deepcopy's, shared across one
    fork so that values the originals share stay shared among the copies."""
    forked = copy.deepcopy(original, memo)
    forked._id = uuid4()  # deepcopy keeps the id, and the id is the one thing a fork must not share
    return forked
