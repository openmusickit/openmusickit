"""What a visualization looks like: the sequence direction, the styles of
nodes (by class) and edges (by type), the label hook, and the graph-wide settings.

Nothing here says anything about layout;
what aligns and what goes above what is `layout`'s business.
The default tables are meant to be tuned:
a class or an edge type gets an entry,
the most specific class in a node's MRO wins,
and an entry in `VisualizationConfig.node_styles` or `edge_styles`
beats the default entry for the same class or type.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from openmusickit.graph.edge import EdgeType
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import ClefEvent, ContextEvent
from openmusickit.objects.division_event import DivisionEvent
from openmusickit.objects.lyrics import LyricSection, LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.omk_object import OmkObject, SequentialEvent
from openmusickit.objects.part import LineGroup, Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine, SyncPoint
from openmusickit.visualization.labels import default_label

DARK = "#303030"
MID = "#606060"
LIGHT = "#b0b0b0"


class SequenceDirection(StrEnum):
    """Which way NEXT advances across the page. The values are Graphviz's `rankdir`.

    >>> SequenceDirection.LEFT_TO_RIGHT.value, SequenceDirection.TOP_TO_BOTTOM.horizontal
    ('LR', False)
    """

    LEFT_TO_RIGHT = "LR"
    RIGHT_TO_LEFT = "RL"
    TOP_TO_BOTTOM = "TB"
    BOTTOM_TO_TOP = "BT"

    @property
    def horizontal(self) -> bool:
        """Whether the sequence axis runs across the page."""
        return self in (SequenceDirection.LEFT_TO_RIGHT, SequenceDirection.RIGHT_TO_LEFT)


def _number(value: float) -> str:
    return f"{value:g}"


@dataclass(frozen=True, slots=True, kw_only=True)
class NodeStyle:
    """How a class of node is drawn. `None` leaves Graphviz's default.

    `shape="plain"` is a text-only node, no outline, no margin.

    >>> NodeStyle(shape="box", rounded=True, font_size=8).attributes()
    {'shape': 'box', 'style': 'rounded', 'fontsize': '8'}
    """

    shape: str | None = None
    rounded: bool = False
    fill_color: str | None = None
    border_color: str | None = None
    font_color: str | None = None
    font_name: str | None = None
    font_size: float | None = None
    width: float | None = None
    height: float | None = None
    margin: str | None = None

    def attributes(self) -> dict[str, str]:
        """The Graphviz node attributes this style sets."""
        attrs: dict[str, str] = {}
        if self.shape is not None:
            attrs["shape"] = self.shape
        styles = []
        if self.rounded:
            styles.append("rounded")
        if self.fill_color is not None:
            styles.append("filled")
        if styles:
            attrs["style"] = ",".join(styles)
        if self.fill_color is not None:
            attrs["fillcolor"] = self.fill_color
        if self.border_color is not None:
            attrs["color"] = self.border_color
        if self.font_color is not None:
            attrs["fontcolor"] = self.font_color
        if self.font_name is not None:
            attrs["fontname"] = self.font_name
        if self.font_size is not None:
            attrs["fontsize"] = _number(self.font_size)
        if self.width is not None:
            attrs["width"] = _number(self.width)
        if self.height is not None:
            attrs["height"] = _number(self.height)
        if self.margin is not None:
            attrs["margin"] = self.margin
        return attrs


@dataclass(frozen=True, slots=True, kw_only=True)
class EdgeStyle:
    """How a type of edge is drawn. `None` leaves Graphviz's default.
    `show_type` labels the edge with its type's name.

    >>> EdgeStyle(style="dotted", color="#b0b0b0", arrowhead="none").attributes()
    {'style': 'dotted', 'color': '#b0b0b0', 'arrowhead': 'none'}
    """

    style: str | None = None
    color: str | None = None
    pen_width: float | None = None
    arrowhead: str | None = None
    arrow_size: float | None = None
    show_type: bool = False

    def attributes(self) -> dict[str, str]:
        """The Graphviz edge attributes this style sets."""
        attrs: dict[str, str] = {}
        if self.style is not None:
            attrs["style"] = self.style
        if self.color is not None:
            attrs["color"] = self.color
        if self.pen_width is not None:
            attrs["penwidth"] = _number(self.pen_width)
        if self.arrowhead is not None:
            attrs["arrowhead"] = self.arrowhead
        if self.arrow_size is not None:
            attrs["arrowsize"] = _number(self.arrow_size)
        return attrs


# --- defaults: the tuning tables ---------------------------------------------------------

_SMALL = NodeStyle(shape="plain", font_size=8, font_color=MID)
_MONOSPACE = NodeStyle(shape="plain", font_name="monospace")

DEFAULT_NODE_STYLES: dict[type[OmkObject], NodeStyle] = {
    OmkObject: NodeStyle(),
    SequentialEvent: NodeStyle(shape="box", rounded=True),
    ContextEvent: NodeStyle(shape="box", font_size=8),
    ClefEvent: NodeStyle(shape="plain"),
    DivisionEvent: NodeStyle(shape="box", font_size=8),
    ChordEvent: _MONOSPACE,
    LyricSyllable: _MONOSPACE,
    Marking: _SMALL,
    MarkSpanner: _SMALL,
    LyricSection: _SMALL,
    Part: _SMALL,
    Stint: _SMALL,
    LineGroup: _SMALL,
    Score: NodeStyle(shape="plain"),
    SyncLine: NodeStyle(shape="plain"),
    SyncPoint: NodeStyle(shape="plain"),
}

_DOTTED = EdgeStyle(style="dotted", color=LIGHT, arrow_size=0.6)
_RELATIONAL = EdgeStyle(style="dotted", color=LIGHT, arrow_size=0.6, show_type=True)

DEFAULT_EDGE_STYLES: dict[EdgeType, EdgeStyle] = {
    EdgeType.NEXT: EdgeStyle(style="solid", color=DARK, arrowhead="normal", arrow_size=0.7),
    EdgeType.BRANCHES: EdgeStyle(
        style="solid", color=DARK, pen_width=0.7, arrowhead="empty", arrow_size=0.8
    ),
    EdgeType.SIMULTANEOUS: EdgeStyle(style="dotted", color=LIGHT, arrowhead="none"),
    EdgeType.CONTAINS: _DOTTED,
    EdgeType.PERFORMS: _DOTTED,
    EdgeType.STARTS_AT: _DOTTED,
    EdgeType.ENDS_AT: _DOTTED,
    EdgeType.MARKS: _DOTTED,
    EdgeType.ANNOTATES: _DOTTED,
    EdgeType.LYRIC: _DOTTED,
    EdgeType.ACCOMPANIES: _RELATIONAL,
    EdgeType.HARMONIZES: _RELATIONAL,
    EdgeType.VARIATION_OF: _RELATIONAL,
    EdgeType.DERIVATIVE_OF: _RELATIONAL,
    EdgeType.REFERENCES: _RELATIONAL,
    EdgeType.IMPLEMENTS: _RELATIONAL,
    EdgeType.REALIZES: _RELATIONAL,
    EdgeType.USER_DEFINED: _RELATIONAL,
}

SYNC_BAR_STYLE = EdgeStyle(style="solid", color=LIGHT, pen_width=4, arrowhead="none")


@dataclass(kw_only=True, slots=True)
class VisualizationConfig:
    """Everything a `GraphRenderer` is told: the direction, style overrides
    by class and by edge type, the label hook, and the graph-wide settings.

    >>> from openmusickit.objects.note_event import NoteEvent
    >>> config = VisualizationConfig(node_styles={NoteEvent: NodeStyle(shape="circle")})
    >>> config.node_style(NoteEvent(tones=set())).shape, config.node_style(Part(name="x")).shape
    ('circle', 'plain')
    >>> config.edge_style(EdgeType.NEXT).style, config.direction
    ('solid', <SequenceDirection.LEFT_TO_RIGHT: 'LR'>)
    """

    direction: SequenceDirection = SequenceDirection.LEFT_TO_RIGHT
    node_styles: Mapping[type[OmkObject], NodeStyle] = field(default_factory=dict)
    edge_styles: Mapping[EdgeType, EdgeStyle] = field(default_factory=dict)
    sync_bar: EdgeStyle = SYNC_BAR_STYLE
    label: Callable[[OmkObject], str] = default_label
    font_name: str = "Helvetica"
    splines: str = "line"
    node_sep: float = 0.15
    rank_sep: float = 0.35

    def node_style(self, node: OmkObject) -> NodeStyle:
        """The style of `node`: the entry for the most specific class in its
        MRO, an override beating the default for the same class."""
        for cls in type(node).__mro__:
            if cls in self.node_styles:
                return self.node_styles[cls]
            if cls in DEFAULT_NODE_STYLES:
                return DEFAULT_NODE_STYLES[cls]
        return NodeStyle()

    def edge_style(self, edge_type: EdgeType) -> EdgeStyle:
        """The style of edges of `edge_type`: the override, else the default."""
        if edge_type in self.edge_styles:
            return self.edge_styles[edge_type]
        return DEFAULT_EDGE_STYLES.get(edge_type, EdgeStyle())
