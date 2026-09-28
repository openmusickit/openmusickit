"""Pictures of an `OmkGraph`, laid out by Graphviz `dot`.

```
OmkGraph  ->  layout (what OMK's edges mean for placement)  ->  DotGraph  ->  DOT text
                                                                              |
                                                          local Graphviz `dot` -> SVG, PNG
```

The picture follows the music: NEXT advances along a sequence axis; everything
that a timing walk places at one instant shares a column; chords sit above
the line they are pinned to, lyrics below the line they are sung to, a sync
line is a bar along the bottom with its points on it.

DOT generation needs nothing installed (`GraphRenderer.to_dot`); rendering to
SVG or PNG needs Graphviz's `dot` on the PATH.

>>> from openmusickit.graph.graph import GraphMeta, OmkGraph
>>> from openmusickit.objects.note_event import NoteEvent
>>> from openmusickit.systems.wsmn.temporal.symbols import quarter
>>> from openmusickit.systems.wsmn.tonal.symbols import C, D
>>> graph = OmkGraph(GraphMeta())
>>> graph.add_line([NoteEvent(tones={t}, duration=quarter) for t in (C, D)])
>>> GraphRenderer(graph, VisualizationConfig(direction=SequenceDirection.TOP_TO_BOTTOM)).to_dot().splitlines()[1]
'  rankdir="TB";'
"""

from . import config, dot, labels, layout, renderer
from .config import EdgeStyle, NodeStyle, SequenceDirection, VisualizationConfig
from .dot import DotEdge, DotGraph, DotNode
from .labels import default_label, duration_glyph
from .renderer import GraphRenderer

__all__ = [
    "config",
    "dot",
    "labels",
    "layout",
    "renderer",
    "DotEdge",
    "DotGraph",
    "DotNode",
    "EdgeStyle",
    "GraphRenderer",
    "NodeStyle",
    "SequenceDirection",
    "VisualizationConfig",
    "default_label",
    "duration_glyph",
]
