"""The public entry point: an `OmkGraph` and a `VisualizationConfig` in,
DOT text out, and SVG or PNG through the local Graphviz."""

from __future__ import annotations

from openmusickit.graph.graph import OmkGraph
from openmusickit.visualization.config import VisualizationConfig
from openmusickit.visualization.dot import DotGraph
from openmusickit.visualization.layout import build


class GraphRenderer:
    """Draws an `OmkGraph`.

    `to_dot` needs nothing installed. `to_svg` and `to_png` run Graphviz's
    `dot`, which must be on the PATH, and raise `GraphvizNotFoundError` when
    it is not.

    The DOT model is built afresh on every call: the graph is mutable, and a
    renderer is cheap to keep around.

    >>> from openmusickit.graph.graph import GraphMeta
    >>> from openmusickit.objects.note_event import NoteEvent
    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter
    >>> from openmusickit.systems.wsmn.tonal.symbols import C, D
    >>> graph = OmkGraph(GraphMeta())
    >>> c, d = (NoteEvent(tones={t}, duration=quarter) for t in (C, D))
    >>> graph.add_line([c, d])
    >>> dot = GraphRenderer(graph).to_dot()
    >>> dot.startswith("digraph {"), 'rankdir="LR"' in dot, f'"{c.id}" -> "{d.id}"' in dot
    (True, True, True)
    """

    def __init__(self, graph: OmkGraph, config: VisualizationConfig | None = None):
        self.graph = graph
        self.config = config if config is not None else VisualizationConfig()

    def dot_graph(self) -> DotGraph:
        """The DOT model (see `dot.DotGraph`) of the graph under this config."""
        return build(self.graph, self.config)

    def to_dot(self) -> str:
        """The DOT source."""
        return self.dot_graph().to_text()
