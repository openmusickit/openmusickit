"""From an `OmkGraph` to a `DotGraph`: the one place that knows what OMK's
edges mean for placement.

Two axes. The **rank** is a node's column along the sequence axis: the order
of onsets, as a timing walk (`OmkGraph.onsets`) finds them, so everything
that starts at one instant shares a column, whether a pin says so or the
durations imply it. Nodes the walk cannot reach are ranked by NEXT alone.
The **row** is a node's position across the sequence axis: every NEXT chain
is a row, an attached node (a mark, a part, a marker) is a satellite of a
row, and the conventions below say which row goes above which.

Both are computed here and handed to Graphviz explicitly: every rank is a
`rank=same` subgraph whose nodes are chained by invisible edges in row order,
and an invisible spine of one node per rank fixes the order of the columns.
Graphviz then only assigns coordinates and routes the edges.

The conventions are the tables and small predicates at the top of this
module; the machinery below reads them and should not need to change when
one does.
"""

from __future__ import annotations

import heapq
from collections import defaultdict
from fractions import Fraction

from openmusickit.graph.edge import EdgeType, OmkEdge, TimedEdge, TimingAnchor
from openmusickit.graph.graph import OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.omk_object import OmkObject, SequentialEvent, Spanner
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.values.time.clock_time import ClockDuration
from openmusickit.values.time.duration import Measurable
from openmusickit.visualization import labels
from openmusickit.visualization.config import DARK, LIGHT, VisualizationConfig
from openmusickit.visualization.dot import DotEdge, DotGraph, DotNode

# --- Conventions -------------------------------------------------------------------------
# What aligns, what is a sequence, what is drawn, and what goes above what.

ABOVE = -1
BELOW = 1

# The target of one of these shares its source's column (a syllable under its
# note, a mark over it); a spanner's STARTS_AT and ENDS_AT do the same for its
# start and end markers, except a Stint's STARTS_AT, which is a sequence edge.
ALIGNING_TYPES = frozenset({EdgeType.LYRIC, EdgeType.MARKS, EdgeType.ANNOTATES})

# The target of one of these is at least one column after its source.
SEQUENCE_TYPES = frozenset({EdgeType.NEXT, EdgeType.PERFORMS})

# Their CONTAINS edges are not drawn: the title block and the sync bar say the same thing.
UNDRAWN_CONTAINERS = (Score, SyncLine)

# NEXT between two of these is not drawn: the row says it.
INVISIBLE_NEXT = (LyricSyllable,)

# How far from its line an attached row sits: a branched line right beside its
# parent, then the lyrics sung to it, then the lines pinned to it.
BRANCH_DISTANCE = 1
LYRIC_DISTANCE = 2
PIN_DISTANCE = 3

# How far from its line a satellite sits, farther first when above (a part
# above its stint above a mark above the notes).
SATELLITE_DISTANCE: dict[type, int] = {
    Marking: 1,
    MarkSpanner: 2,
    LyricSection: 2,
    LineGroup: 3,
    Stint: 3,
    Part: 4,
    Score: 5,
}


def satellite_side(node: OmkObject) -> int:
    """Which side of its line an attached node sits on."""
    return BELOW if isinstance(node, LyricSection) else ABOVE


def satellite_distance(node: OmkObject) -> int:
    for cls in type(node).__mro__:
        if cls in SATELLITE_DISTANCE:
            return SATELLITE_DISTANCE[cls]
    return 1


def pinned_row_side(pinned_head: OmkObject, anchor_head: OmkObject) -> int:
    """Where a line pinned to another goes: a chord line above, anything else below."""
    if isinstance(pinned_head, ChordEvent) and not isinstance(anchor_head, ChordEvent):
        return ABOVE
    return BELOW


def highest_tone(event: OmkObject) -> object | None:
    if not isinstance(event, NoteEvent) or not event.tones:
        return None
    try:
        return max(event.tones)  # type: ignore[type-var]
    except (TypeError, AttributeError, ValueError):
        return None


def branch_side(head: OmkObject, parent: OmkObject) -> int:
    """Where a branched line goes: above its parent's line when its head sounds
    higher than the parent event, below otherwise or when in doubt."""
    high, low = highest_tone(head), highest_tone(parent)
    if high is None or low is None:
        return BELOW
    try:
        return ABOVE if high > low else BELOW  # type: ignore[operator]
    except (TypeError, AttributeError, ValueError):
        return BELOW


# --- machinery ----------------------------------------------------------------------------


def build(graph: OmkGraph, config: VisualizationConfig) -> DotGraph:
    """The DOT model of `graph` under `config`."""
    return _Layout(graph, config).build()


class _Groups:
    """Union-find over node ids, refusing to merge two members of one chain
    (a chain is a sequence; its members never share a column)."""

    def __init__(self):
        self._parent: dict[str, str] = {}
        self._chains: dict[str, set[str]] = {}

    def add(self, node_id: str, chain: str | None = None) -> None:
        if node_id not in self._parent:
            self._parent[node_id] = node_id
            self._chains[node_id] = {chain} if chain is not None else set()

    def find(self, node_id: str) -> str:
        root = node_id
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[node_id] != root:
            self._parent[node_id], node_id = root, self._parent[node_id]
        return root

    def union(self, a: str, b: str) -> bool:
        """Merges the groups of `a` and `b`; False if that would put two
        members of one chain together, in which case nothing changes."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return True
        if self._chains[ra] & self._chains[rb]:
            return False
        self._parent[rb] = ra
        self._chains[ra] |= self._chains.pop(rb)
        return True

    def members(self) -> list[str]:
        return list(self._parent)


def _ordered(
    vertices: list[str], successors: dict[str, set[str]]
) -> tuple[list[str], dict[str, set[str]]]:
    """A topological order of `vertices` (ties by their given order) and, for
    each vertex, the predecessors that were kept. A cycle is broken by
    freeing the earliest waiting vertex of its remaining predecessors."""
    index = {vertex: i for i, vertex in enumerate(vertices)}
    kept: dict[str, set[str]] = {vertex: set() for vertex in vertices}
    for source, targets in successors.items():
        for target in targets:
            if source != target:
                kept[target].add(source)
    waiting = {vertex: len(kept[vertex]) for vertex in vertices}
    ready = [(index[vertex], vertex) for vertex in vertices if waiting[vertex] == 0]
    heapq.heapify(ready)
    order: list[str] = []
    remaining = set(vertices)
    while remaining:
        if not ready:
            vertex = min(remaining, key=index.__getitem__)
            kept[vertex] = {source for source in kept[vertex] if source not in remaining}
            waiting[vertex] = 0
            ready = [(index[vertex], vertex)]
        _, vertex = heapq.heappop(ready)
        if vertex not in remaining:
            continue
        order.append(vertex)
        remaining.discard(vertex)
        for target in successors.get(vertex, ()):
            if target in remaining and target != vertex:
                waiting[target] -= 1
                if waiting[target] == 0:
                    heapq.heappush(ready, (index[target], target))
    return order, kept


def _timed_label(edge: OmkEdge) -> str | None:
    """The displacement of a timed edge as text, for a pin or branch that is not a co-start."""
    if not isinstance(edge, TimedEdge):
        return None
    parts = []
    if edge.anchor is TimingAnchor.OFFSET:
        parts.append("from offset")
    displacement = edge.displacement
    if displacement is not None:
        if isinstance(displacement, ClockDuration):
            parts.append(str(displacement))
        elif isinstance(displacement, Measurable):
            value = displacement.rational_length
            if value != 0:
                parts.append(f"+{value}" if value > 0 else str(value))
        else:
            parts.append(repr(displacement))
    return " ".join(parts) or None


def _end_id(node_id: str) -> str:
    return f"{node_id}-end"


def _spine_id(rank: int) -> str:
    return f"_spine_{rank}"


class _Layout:
    def __init__(self, graph: OmkGraph, config: VisualizationConfig):
        self.graph = graph
        self.config = config
        self.objects: dict[str, OmkObject] = {}
        self.edges: list[tuple[OmkEdge, str, str]] = []
        self.chains: dict[str, list[str]] = {}
        self.chain_of: dict[str, str] = {}
        self.position: dict[str, int] = {}
        self.sync_lines: dict[str, list[str]] = {}
        self.sync_line_of: dict[str, str] = {}
        self.end_ids: dict[str, str] = {}
        self.groups = _Groups()
        self.component: dict[str, int] = {}
        self.onset: dict[str, Fraction] = {}
        self.rank: dict[str, int] = {}
        self.title: Score | None = None
        self.satellite: dict[str, tuple[str | None, int, int]] = {}
        self.row_index: dict[str, int] = {}

    def build(self) -> DotGraph:
        self._collect()
        self._find_chains()
        self._find_sync_lines()
        self._find_spanner_ends()
        self._align()
        self._rank()
        self._place_scores()
        self._order_rows()
        return self._emit()

    # --- what is there -------------------------------------------------------------

    def _collect(self) -> None:
        self.objects = {str(node.id): node for node in self.graph.nodes()}
        for edge in self.graph.edges():
            source, target = self.graph.edge_endpoints(edge)
            self.edges.append((edge, str(source.id), str(target.id)))

    def _find_chains(self) -> None:
        for node_id, obj in self.objects.items():
            if not isinstance(obj, SequentialEvent) or self.graph.get_previous(obj) is not None:
                continue
            members: list[str] = []
            current: SequentialEvent | None = obj
            while current is not None:
                members.append(str(current.id))
                current = self.graph.get_next(current)
            self.chains[node_id] = members
            for position, member in enumerate(members):
                self.chain_of[member] = node_id
                self.position[member] = position

    def _find_sync_lines(self) -> None:
        for node_id, obj in self.objects.items():
            if not isinstance(obj, SyncLine):
                continue
            points = sorted(self.graph.sync_points(obj), key=lambda p: p.offset.rational_length)
            self.sync_lines[node_id] = [str(point.id) for point in points]
            for point in points:
                self.sync_line_of[str(point.id)] = node_id

    def _find_spanner_ends(self) -> None:
        for edge, source, _ in self.edges:
            if edge.type is EdgeType.ENDS_AT and isinstance(self.objects[source], Spanner):
                self.end_ids[source] = _end_id(source)

    # --- ranks -----------------------------------------------------------------------

    def _references(self) -> list[str]:
        """Where timing walks start: chain heads, then origins and instants, then any event."""
        heads = list(self.chains)
        origins = [
            node_id
            for node_id, obj in self.objects.items()
            if isinstance(obj, LineGroup | SyncLine | SyncPoint)
        ]
        events = [
            node_id
            for node_id, obj in self.objects.items()
            if isinstance(obj, SequentialEvent) and node_id not in self.chains
        ]
        return heads + origins + events

    def _walk_onsets(self) -> None:
        components = 0
        for reference in self._references():
            if reference in self.component:
                continue
            for node_uuid, duration in self.graph.onsets(self.objects[reference]).items():
                node_id = str(node_uuid)
                if node_id in self.component:
                    continue
                self.component[node_id] = components
                if isinstance(duration, Measurable):
                    self.onset[node_id] = duration.rational_length
            components += 1

    def _representatives(self, members: list[str]) -> list[str]:
        """The nodes of an onset class that stand for it: every node outside a
        chain, and the last member of each chain (a clef before a note at the
        same instant precedes the note; the note is the instant)."""
        last_of_chain: dict[str, str] = {}
        loose: list[str] = []
        for member in members:
            chain = self.chain_of.get(member)
            if chain is None:
                loose.append(member)
            elif (
                chain not in last_of_chain
                or self.position[member] > self.position[last_of_chain[chain]]
            ):
                last_of_chain[chain] = member
        return loose + list(last_of_chain.values())

    def _classes(self) -> dict[int, list[tuple[Fraction, list[str]]]]:
        """Per timing component, its onset classes in onset order, each with its representatives."""
        grouped: dict[tuple[int, Fraction], list[str]] = defaultdict(list)
        for node_id, onset in self.onset.items():
            grouped[(self.component[node_id], onset)].append(node_id)
        per_component: dict[int, list[tuple[Fraction, list[str]]]] = defaultdict(list)
        for (component, onset), members in grouped.items():
            per_component[component].append((onset, self._representatives(members)))
        for classes in per_component.values():
            classes.sort(key=lambda item: item[0])
        return per_component

    def _align(self) -> None:
        for node_id in self.objects:
            self.groups.add(node_id, self.chain_of.get(node_id))
        for end_id in self.end_ids.values():
            self.groups.add(end_id)
        for line_id in self.sync_lines:
            self.groups.add(_end_id(line_id))
        self._walk_onsets()
        self.classes = self._classes()
        for classes in self.classes.values():
            for _, representatives in classes:
                for other in representatives[1:]:
                    self.groups.union(representatives[0], other)
        for edge, source, target in self.edges:
            if edge.type in ALIGNING_TYPES:
                self.groups.union(source, target)
            elif edge.type is EdgeType.STARTS_AT and not isinstance(self.objects[source], Stint):
                self.groups.union(source, target)
            elif edge.type is EdgeType.ENDS_AT and source in self.end_ids:
                self.groups.union(self.end_ids[source], target)

    def _is_sequence(self, edge: OmkEdge, source: str) -> bool:
        if edge.type in SEQUENCE_TYPES:
            return True
        return edge.type is EdgeType.STARTS_AT and isinstance(self.objects[source], Stint)

    def _rank(self) -> None:
        successors: dict[str, set[str]] = defaultdict(set)

        def link(a: str, b: str) -> None:
            ra, rb = self.groups.find(a), self.groups.find(b)
            if ra != rb:
                successors[ra].add(rb)

        for edge, source, target in self.edges:
            if self._is_sequence(edge, source):
                link(source, target)
        for classes in self.classes.values():
            for (_, earlier), (_, later) in zip(classes, classes[1:], strict=False):
                link(earlier[0], later[0])
        for line_id, points in self.sync_lines.items():
            sequence = [line_id, *points, _end_id(line_id)]
            for a, b in zip(sequence, sequence[1:], strict=False):
                link(a, b)
        roots: list[str] = []
        seen: set[str] = set()
        for node_id in self.groups.members():
            root = self.groups.find(node_id)
            if root not in seen:
                seen.add(root)
                roots.append(root)
        order, kept = _ordered(roots, successors)
        rank_of_root: dict[str, int] = {}
        for root in order:
            rank_of_root[root] = max((rank_of_root[p] + 1 for p in kept[root]), default=0)
        for node_id in self.groups.members():
            self.rank[node_id] = rank_of_root[self.groups.find(node_id)]
        last = max(self.rank.values(), default=0)
        for line_id in self.sync_lines:
            self.rank[_end_id(line_id)] = last

    # --- scores ----------------------------------------------------------------------

    def _connected_to(self, node_id: str) -> bool:
        """Whether every node is connected to `node_id`, by edges of any type either way."""
        adjacent: dict[str, set[str]] = defaultdict(set)
        for _, source, target in self.edges:
            adjacent[source].add(target)
            adjacent[target].add(source)
        seen = {node_id}
        frontier = [node_id]
        while frontier:
            current = frontier.pop()
            for neighbour in adjacent[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    frontier.append(neighbour)
        return seen >= set(self.objects)

    def _place_scores(self) -> None:
        scores = [node_id for node_id, obj in self.objects.items() if isinstance(obj, Score)]
        if len(scores) == 1 and self._connected_to(scores[0]):
            self.title = self.objects[scores[0]]  # type: ignore[assignment]
            return
        for score_id in scores:
            heads = [str(head.id) for head in self.graph.score_lines(self.objects[score_id])]  # type: ignore[arg-type]
            heads = [head for head in heads if head in self.rank]
            if not heads:
                continue
            earliest = min(
                heads, key=lambda head: (self.rank[head], list(self.objects).index(head))
            )
            self.rank[score_id] = self.rank[earliest]
            self.satellite[score_id] = (
                self.chain_of.get(earliest),
                ABOVE,
                satellite_distance(self.objects[score_id]),
            )

    # --- rows ------------------------------------------------------------------------

    def _row_of(self, node_id: str) -> str | None:
        if node_id in self.chain_of:
            return self.chain_of[node_id]
        if node_id in self.sync_line_of:
            return self.sync_line_of[node_id]
        if node_id in self.sync_lines:
            return node_id
        if node_id in self.satellite:
            return self.satellite[node_id][0]
        return None

    def _order_rows(self) -> None:
        above: list[tuple[str, str]] = []
        attached: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
        group_lines: dict[str, list[str]] = defaultdict(list)

        def put_above(upper: str | None, lower: str | None) -> None:
            if upper is not None and lower is not None and upper != lower:
                above.append((upper, lower))

        def attach(anchor: str | None, row: str | None, side: int, distance: int) -> None:
            if anchor is not None and row is not None and anchor != row:
                attached[(anchor, side)].append((distance, row))

        for edge, source, target in self.edges:
            s_obj, t_obj = self.objects[source], self.objects[target]
            s_row, t_row = self.chain_of.get(source), self.chain_of.get(target)
            if edge.type is EdgeType.SIMULTANEOUS:
                if (
                    isinstance(s_obj, SyncPoint)
                    or isinstance(t_obj, SyncPoint)
                    or not (s_row and t_row)
                ):
                    continue
                side = pinned_row_side(self.objects[t_row], self.objects[s_row])
                attach(s_row, t_row, side, PIN_DISTANCE)
            elif edge.type is EdgeType.BRANCHES:
                attach(s_row, t_row, branch_side(t_obj, s_obj), BRANCH_DISTANCE)
            elif edge.type is EdgeType.LYRIC:
                attach(s_row, t_row, BELOW, LYRIC_DISTANCE)
            elif edge.type is EdgeType.CONTAINS and isinstance(s_obj, LineGroup):
                if t_row is not None:
                    group_lines[source].append(t_row)
            elif edge.type in (EdgeType.MARKS, EdgeType.ANNOTATES):
                self.satellite[source] = (self._row_of(target), ABOVE, satellite_distance(s_obj))
            elif edge.type is EdgeType.STARTS_AT and isinstance(s_obj, Spanner):
                self.satellite[source] = (
                    self._row_of(target),
                    satellite_side(s_obj),
                    satellite_distance(s_obj),
                )
            elif edge.type is EdgeType.ENDS_AT and source in self.end_ids:
                self.satellite[self.end_ids[source]] = (
                    self._row_of(target),
                    satellite_side(s_obj),
                    satellite_distance(s_obj),
                )
        for (anchor, side), rows in attached.items():
            ordered = [anchor]
            for _, row in sorted(rows, key=lambda item: item[0]):
                if row not in ordered:
                    ordered.append(row)
            if side is ABOVE:
                ordered.reverse()
            for upper, lower in zip(ordered, ordered[1:], strict=False):
                put_above(upper, lower)
        for group_id, lines in group_lines.items():
            for upper, lower in zip(lines, lines[1:], strict=False):
                put_above(upper, lower)
            self.satellite[group_id] = (lines[0], ABOVE, satellite_distance(self.objects[group_id]))
        for edge, source, target in self.edges:  # parts last: their host may itself be a satellite
            if edge.type is EdgeType.PERFORMS:
                self.satellite[source] = (
                    self._row_of(target),
                    ABOVE,
                    satellite_distance(self.objects[source]),
                )

        rows = list(self.chains)
        successors: dict[str, set[str]] = defaultdict(set)
        for upper, lower in above:
            if upper in self.chains and lower in self.chains:
                successors[upper].add(lower)
        order, _ = _ordered(rows, successors)
        self.row_index = {row: i for i, row in enumerate(order)}
        for line_id in self.sync_lines:
            self.row_index[line_id] = len(self.row_index)

    def _sort_key(self, node_id: str) -> tuple[int, int, int]:
        free = len(self.row_index) + 1
        if node_id in self.chain_of or node_id in self.sync_line_of or node_id in self.sync_lines:
            return (self.row_index[self._row_of(node_id)], 0, 0)  # type: ignore[index]
        if node_id.endswith("-end") and node_id[:-4] in self.sync_lines:
            return (self.row_index[node_id[:-4]], 0, 0)
        if node_id in self.satellite:
            row, side, distance = self.satellite[node_id]
            if row is None or row not in self.row_index:
                return (free, 0, 0)
            return (self.row_index[row], side, side * distance)
        return (free, 0, 0)

    # --- emission --------------------------------------------------------------------

    def _emitted_ids(self) -> list[str]:
        ids = [node_id for node_id in self.objects if self.objects[node_id] is not self.title]
        ids += list(self.end_ids.values())
        ids += [_end_id(line_id) for line_id in self.sync_lines]
        return ids

    def _classes_of(self, obj: OmkObject) -> str:
        names = [cls.__name__ for cls in type(obj).__mro__ if issubclass(cls, OmkObject)]
        return "omk-node " + " ".join(names)

    def _sync_block(self, obj: SyncLine | SyncPoint | None) -> str:
        bar = self.config.sync_bar
        kwargs = {
            "bar_color": bar.color or LIGHT,
            "bar_width": bar.pen_width or 4,
            "horizontal": self.config.direction.horizontal,
        }
        if obj is None:
            return labels.sync_block("", None, None, dot=False, **kwargs)
        if isinstance(obj, SyncLine):
            return labels.sync_block(obj.name or "", None, None, dot=False, **kwargs)
        return labels.sync_block(
            labels.duration_label(obj.offset), obj.name, obj.description, **kwargs
        )

    def _label(self, node_id: str) -> str:
        obj = self.objects.get(node_id)
        if obj is None:
            if node_id[:-4] in self.sync_lines:
                return self._sync_block(None)
            spanner = self.objects[node_id[:-4]]
            side = "below" if satellite_side(spanner) is BELOW else "above"
            return labels.spanner_markers(self.config.label(spanner), side)[1]
        if isinstance(obj, SyncLine | SyncPoint):
            return self._sync_block(obj)
        if isinstance(obj, Score):
            return labels.title_block(obj, DARK)
        text = self.config.label(obj)
        if isinstance(obj, Spanner) and not isinstance(obj, Stint):
            side = "below" if satellite_side(obj) is BELOW else "above"
            return labels.spanner_markers(text, side)[0]
        return text

    def _node(self, node_id: str) -> DotNode:
        obj = self.objects.get(node_id)
        styled = obj if obj is not None else self.objects.get(node_id[:-4])
        attrs = {"label": self._label(node_id)}
        if styled is not None and node_id[:-4] not in self.sync_lines:
            attrs.update(self.config.node_style(styled).attributes())
        else:
            attrs["shape"] = "plain"
        attrs["id"] = node_id
        if obj is not None:
            attrs["class"] = self._classes_of(obj)
        elif node_id[:-4] in self.sync_lines:
            attrs["class"] = "omk-node sync-bar-end"
        else:
            attrs["class"] = self._classes_of(styled) + " spanner-end"  # type: ignore[arg-type]
        group = self._group_of(node_id)
        if group is not None:
            attrs["group"] = group
        return DotNode(node_id, attrs)

    def _group_of(self, node_id: str) -> str | None:
        if node_id in self.chain_of:
            return self.chain_of[node_id]
        if node_id in self.sync_line_of:
            return self.sync_line_of[node_id]
        if node_id in self.sync_lines:
            return node_id
        if node_id.endswith("-end") and node_id[:-4] in self.sync_lines:
            return node_id[:-4]
        return None

    def _edge(self, edge: OmkEdge, source: str, target: str) -> DotEdge | None:
        s_obj, t_obj = self.objects[source], self.objects[target]
        if edge.type is EdgeType.CONTAINS and isinstance(s_obj, UNDRAWN_CONTAINERS):
            return None
        style = self.config.edge_style(edge.type)
        attrs: dict[str, str] = {}
        if (
            edge.type is EdgeType.NEXT
            and isinstance(s_obj, INVISIBLE_NEXT)
            and isinstance(t_obj, INVISIBLE_NEXT)
        ):
            attrs["style"] = "invis"
        else:
            attrs.update(style.attributes())
        label = _timed_label(edge)
        if label is None and style.show_type:
            label = edge.type.value.replace("_", " ")
        if label is not None:
            attrs["label"] = label
        if not self._is_sequence(edge, source):
            attrs["constraint"] = "false"
        attrs["id"] = str(edge.id)
        attrs["class"] = f"omk-edge {edge.type.value}"
        if edge.type is EdgeType.ENDS_AT and source in self.end_ids:
            source = self.end_ids[source]
        return DotEdge(source, target, attrs)

    def _emit(self) -> DotGraph:
        config = self.config
        dot = DotGraph()
        dot.attrs = {
            "rankdir": config.direction.value,
            "bgcolor": "transparent",
            "splines": config.splines,
            "nodesep": f"{config.node_sep:g}",
            "ranksep": f"{config.rank_sep:g}",
            "fontname": config.font_name,
        }
        if self.title is not None:
            dot.attrs["labelloc"] = "t"
            dot.attrs["labeljust"] = "r"
            dot.attrs["label"] = labels.title_block(self.title, DARK)
        dot.node_defaults = {
            "fontname": config.font_name,
            "fontsize": "10",
            "margin": "0.05,0.02",
            "width": "0",
            "height": "0",
            "color": DARK,
            "fontcolor": DARK,
        }
        dot.edge_defaults = {"color": LIGHT, "style": "dotted", "arrowsize": "0.6"}

        emitted = self._emitted_ids()
        ordered: list[str] = []
        for row in sorted(self.chains, key=self.row_index.__getitem__):
            ordered.extend(self.chains[row])
        for line_id, points in self.sync_lines.items():
            ordered.extend([line_id, *points, _end_id(line_id)])
        placed = set(ordered)
        ordered.extend(node_id for node_id in emitted if node_id not in placed)
        for node_id in ordered:
            dot.nodes.append(self._node(node_id))

        columns: dict[int, list[str]] = defaultdict(list)
        for node_id in emitted:
            columns[self.rank[node_id]].append(node_id)
        last = max(columns, default=-1)
        for rank in range(last + 1):
            column = sorted(columns.get(rank, []), key=self._sort_key)
            spine = _spine_id(rank)
            dot.nodes.append(
                DotNode(
                    spine,
                    {"shape": "point", "style": "invis", "width": "0.01", "class": "omk-spine"},
                )
            )
            dot.ranks.append([*column, spine])
        for rank in range(last):
            dot.edges.append(DotEdge(_spine_id(rank), _spine_id(rank + 1), {"style": "invis"}))

        for edge, source, target in self.edges:
            drawn = self._edge(edge, source, target)
            if drawn is not None:
                dot.edges.append(drawn)
        bar_attrs = {
            **config.sync_bar.attributes(),
            "tailclip": "false",
            "headclip": "false",
            "class": "omk-edge sync-bar",
        }
        for line_id, points in self.sync_lines.items():
            sequence = [line_id, *points, _end_id(line_id)]
            for a, b in zip(sequence, sequence[1:], strict=False):
                dot.edges.append(
                    DotEdge(a, b, dict(bar_attrs), source_port="bar", target_port="bar")
                )
        return dot
