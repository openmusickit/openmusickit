"""A minimal model of a Graphviz DOT graph, and its text.

Nothing here knows about music.
`layout` builds a `DotGraph` from an `OmkGraph`,
the tests inspect the model,
and `to_text` writes the DOT that Graphviz reads.

Every id and attribute value is written double-quoted,
with backslashes and quotes escaped and a newline as `\\n`;
except that a label written between `<` and `>` is passed through as it is,
which is Graphviz's own convention for an HTML-like label.

>>> graph = DotGraph(attrs={"rankdir": "LR"})
>>> graph.nodes.append(DotNode("a", {"label": "say \\"hi\\""}))
>>> graph.nodes.append(DotNode("b", {"label": "<b<SUP>2</SUP>>"}))
>>> graph.edges.append(DotEdge("a", "b", {"constraint": "false"}))
>>> graph.ranks.append(["a", "b"])
>>> print(graph.to_text())
digraph {
  rankdir="LR";
  "a" [label="say \\"hi\\""];
  "b" [label=<b<SUP>2</SUP>>];
  { rank=same; "a" -> "b" [style="invis"]; }
  "a" -> "b" [constraint="false"];
}
<BLANKLINE>
"""

from __future__ import annotations

from dataclasses import dataclass, field

HTML_LABEL_KEYS = frozenset({"label", "xlabel", "headlabel", "taillabel"})


def is_html_label(value: str) -> bool:
    """Whether `value` is an HTML-like label: written between `<` and `>`.

    >>> is_html_label("<C<SUP>4</SUP>>"), is_html_label("C4"), is_html_label("<")
    (True, False, False)
    """
    return len(value) >= 2 and value[0] == "<" and value[-1] == ">"


def quote(value: str) -> str:
    """A double-quoted DOT string.

    >>> quote('a "b" c\\\\d'), quote("two\\nlines")
    ('"a \\\\"b\\\\" c\\\\\\\\d"', '"two\\\\nlines"')
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _attribute(key: str, value: str) -> str:
    if key in HTML_LABEL_KEYS and is_html_label(value):
        return f"{key}={value}"
    return f"{key}={quote(value)}"


def attribute_list(attrs: dict[str, str]) -> str:
    """` [key="value", ...]` in insertion order, or nothing for no attributes.

    >>> attribute_list({"shape": "box", "label": "<i>"}), attribute_list({})
    (' [shape="box", label=<i>]', '')
    """
    if not attrs:
        return ""
    return " [" + ", ".join(_attribute(key, value) for key, value in attrs.items()) + "]"


@dataclass(slots=True)
class DotNode:
    """A node statement: its id and attributes."""

    id: str
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DotEdge:
    """An edge statement, optionally through a port at either end."""

    source: str
    target: str
    attrs: dict[str, str] = field(default_factory=dict)
    source_port: str | None = None
    target_port: str | None = None


@dataclass(slots=True)
class DotGraph:
    """A directed graph: graph, node and edge defaults, the nodes, the edges,
    and `ranks`, one list of node ids per rank in the order they are to be
    laid out across the sequence axis. Each rank becomes a `rank=same`
    subgraph whose nodes are chained by invisible edges in that order."""

    attrs: dict[str, str] = field(default_factory=dict)
    node_defaults: dict[str, str] = field(default_factory=dict)
    edge_defaults: dict[str, str] = field(default_factory=dict)
    nodes: list[DotNode] = field(default_factory=list)
    edges: list[DotEdge] = field(default_factory=list)
    ranks: list[list[str]] = field(default_factory=list)

    def to_text(self) -> str:
        """The DOT source."""
        lines = ["digraph {"]
        for key, value in self.attrs.items():
            lines.append(f"  {_attribute(key, value)};")
        if self.node_defaults:
            lines.append(f"  node{attribute_list(self.node_defaults)};")
        if self.edge_defaults:
            lines.append(f"  edge{attribute_list(self.edge_defaults)};")
        for node in self.nodes:
            lines.append(f"  {quote(node.id)}{attribute_list(node.attrs)};")
        for column in self.ranks:
            if not column:
                continue
            if len(column) == 1:
                lines.append(f"  {{ rank=same; {quote(column[0])}; }}")
            else:
                chain = " -> ".join(quote(node_id) for node_id in column)
                lines.append(f'  {{ rank=same; {chain} [style="invis"]; }}')
        for edge in self.edges:
            source = quote(edge.source) + (f":{edge.source_port}" if edge.source_port else "")
            target = quote(edge.target) + (f":{edge.target_port}" if edge.target_port else "")
            lines.append(f"  {source} -> {target}{attribute_list(edge.attrs)};")
        lines.append("}")
        return "\n".join(lines) + "\n"
