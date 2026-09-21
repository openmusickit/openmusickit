"""A rule-based state machine over the graph: random sequences of adding
events, appending, branching, pinning and removing, with the same sequence
applied to an `OmkGraph` on `RustworkxAdapter` and one on the dict-backed
reference adapter, and a small model of lines and branches kept beside them.

After every step: the two adapters agree on the snapshot; NEXT degree is at
most one each way and matches the model; every event is at zero onset from
itself; consecutive onsets follow durations; every walk terminates within
the node count; `check_alignment` runs.

The generator never makes a NEXT cycle (it only appends to a tail) and
never branches a head from its own tree, since walkers do not yet stop on
cycles (Part 5, item 1); pins may go anywhere.

Run with `uv run pytest --hypothesis-profile=thorough` for 2,000 runs.
"""

import itertools
import warnings
from uuid import UUID

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.note_event import NoteEvent
from openmusickit.systems.wsmn.temporal.symbols import eighth, quarter
from openmusickit.values.time.duration import ZeroDuration
from tests.graph.dict_adapter import DictAdapter
from tests.graph.helpers import snapshot
from tests.strategies import note_events


class GraphModel(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.rx = OmkGraph(GraphMeta())
        self.ref = OmkGraph(GraphMeta(), graph_engine=DictAdapter())
        self.graphs = (self.rx, self.ref)
        self.events: dict[UUID, NoteEvent] = {}
        self.next: dict[UUID, UUID | None] = {}
        self.prev: dict[UUID, UUID | None] = {}
        self.parent: dict[UUID, UUID | None] = {}  # branch parent of a head
        self.pins: set[tuple[UUID, UUID]] = set()

    # --- the model ---

    def _root(self, event: NoteEvent) -> UUID:
        """The top of the tree of lines and branches `event` hangs from."""
        node = event.id
        while True:
            up = self.prev[node] if self.prev[node] is not None else self.parent[node]
            if up is None:
                return node
            node = up

    def _tails(self) -> list[NoteEvent]:
        return [e for e in self.events.values() if self.next[e.id] is None]

    def _heads(self) -> list[NoteEvent]:
        return [e for e in self.events.values() if self.prev[e.id] is None]

    def _free_heads(self) -> list[NoteEvent]:
        return [e for e in self._heads() if self.parent[e.id] is None]

    def _branch_pairs(self) -> list[tuple[NoteEvent, NoteEvent]]:
        return [
            (parent, head)
            for head in self._free_heads()
            for parent in self.events.values()
            if parent is not head and self._root(parent) != head.id
        ]

    def _next_pairs(self) -> list[tuple[NoteEvent, NoteEvent]]:
        return [(a, self.events[b]) for a in self.events.values() if (b := self.next[a.id])]

    def _branch_edges(self) -> list[tuple[NoteEvent, NoteEvent]]:
        return [
            (self.events[p], head) for head in self.events.values() if (p := self.parent[head.id])
        ]

    def _register(self, event: NoteEvent) -> None:
        self.events[event.id] = event
        self.next[event.id] = self.prev[event.id] = self.parent[event.id] = None

    # --- rules ---

    @rule(event=note_events())
    def add_node(self, event):
        for graph in self.graphs:
            graph.add_node(event)
        self._register(event)

    @precondition(lambda self: self._tails())
    @rule(data=st.data(), event=note_events())
    def append_next(self, data, event):
        tail = data.draw(st.sampled_from(self._tails()))
        for graph in self.graphs:
            graph.add_next(tail, event)
        self._register(event)
        self.next[tail.id], self.prev[event.id] = event.id, tail.id

    @precondition(lambda self: self._branch_pairs())
    @rule(data=st.data(), displacement=st.sampled_from([None, quarter, -eighth]))
    def branch(self, data, displacement):
        parent, head = data.draw(st.sampled_from(self._branch_pairs()))
        for graph in self.graphs:
            graph.add_branch(parent, head, displacement=displacement)
        self.parent[head.id] = parent.id

    @precondition(lambda self: len(self.events) >= 2)
    @rule(data=st.data(), displacement=st.sampled_from([None, quarter, -eighth]))
    def pin(self, data, displacement):
        events = list(self.events.values())
        a = data.draw(st.sampled_from(events))
        b = data.draw(st.sampled_from([e for e in events if e is not a]))
        if (a.id, b.id) in self.pins:
            return
        for graph in self.graphs:
            graph.add_simultaneous(a, b, displacement=displacement)
        self.pins.add((a.id, b.id))

    @precondition(lambda self: self.events)
    @rule(data=st.data())
    def remove_node(self, data):
        event = data.draw(st.sampled_from(list(self.events.values())))
        for graph in self.graphs:
            graph.remove_node(event)
        for table in (self.next, self.prev, self.parent):
            for key, value in table.items():
                if value == event.id:
                    table[key] = None
            del table[event.id]
        self.pins = {pair for pair in self.pins if event.id not in pair}
        del self.events[event.id]

    @precondition(lambda self: self._next_pairs())
    @rule(data=st.data())
    def remove_next(self, data):
        a, b = data.draw(st.sampled_from(self._next_pairs()))
        for graph in self.graphs:
            graph.remove_edge(graph.get_edge(a, b, EdgeType.NEXT))
        self.next[a.id] = self.prev[b.id] = None

    @precondition(lambda self: self._branch_edges())
    @rule(data=st.data())
    def remove_branch(self, data):
        parent, head = data.draw(st.sampled_from(self._branch_edges()))
        for graph in self.graphs:
            graph.remove_edge(graph.get_edge(parent, head, EdgeType.BRANCHES))
        self.parent[head.id] = None

    @precondition(lambda self: self.pins)
    @rule(data=st.data())
    def remove_pin(self, data):
        a_id, b_id = data.draw(st.sampled_from(sorted(self.pins, key=str)))
        a, b = self.events[a_id], self.events[b_id]
        for graph in self.graphs:
            graph.remove_edge(graph.get_edge(a, b, EdgeType.SIMULTANEOUS))
        self.pins.discard((a_id, b_id))

    # --- invariants ---

    @invariant()
    def adapters_agree(self):
        assert snapshot(self.rx) == snapshot(self.ref)
        assert self.rx._graph.num_nodes() == len(self.events)

    @invariant()
    def next_is_one_in_one_out_and_matches_the_model(self):
        for event in self.events.values():
            assert len(list(self.rx._graph.out_edges(event, EdgeType.NEXT))) <= 1
            assert len(list(self.rx._graph.in_edges(event, EdgeType.NEXT))) <= 1
            following = self.rx.get_next(event)
            assert (following.id if following else None) == self.next[event.id]
            previous = self.rx.get_previous(event)
            assert (previous.id if previous else None) == self.prev[event.id]

    @invariant()
    def every_event_is_at_zero_from_itself(self):
        for event in self.events.values():
            assert self.rx.relative_onset(event, event) == ZeroDuration()

    @invariant()
    def consecutive_onsets_follow_durations(self):
        for a, b in self._next_pairs():
            if a.duration is not None:
                assert self.rx.relative_onset(a, b) == a.duration
                assert self.rx.relative_onset(b, a) == -a.duration

    @invariant()
    def walks_terminate_within_the_node_count(self):
        n = len(self.events)
        for head in self._heads():
            assert len(list(itertools.islice(self.rx.walk_line(head), n + 1))) <= n
        for root in self._free_heads():
            assert len(list(itertools.islice(self.rx.walk_span(root), n + 1))) <= n

    @invariant()
    def alignment_check_runs(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=Warning)
            conflicts = self.rx.check_alignment()
        assert all(edge.type is EdgeType.SIMULTANEOUS for edge in conflicts)


TestGraphModel = GraphModel.TestCase
# 25 steps per run keeps the default profile under two seconds; the number
# of runs still comes from the active profile (100, or 2,000 for thorough).
TestGraphModel.settings = settings(stateful_step_count=25)
