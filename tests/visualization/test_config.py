"""Styles: lookup by class along the MRO, overrides, and the label hook."""

from openmusickit.graph.edge import EdgeType
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import OmkObject, SequentialEvent
from openmusickit.systems.wsmn.temporal.symbols import quarter
from openmusickit.systems.wsmn.tonal.symbols import C, D, maj
from openmusickit.visualization import EdgeStyle, GraphRenderer, NodeStyle, VisualizationConfig
from openmusickit.visualization.config import DEFAULT_EDGE_STYLES, DEFAULT_NODE_STYLES
from tests.graph.helpers import notes
from tests.visualization.dot_helpers import edge, nid, node


def test_a_rest_is_styled_as_a_sequential_event():
    config = VisualizationConfig()
    assert config.node_style(Rest(quarter)) is DEFAULT_NODE_STYLES[SequentialEvent]
    assert config.node_style(NoteEvent(tones={C})) is DEFAULT_NODE_STYLES[SequentialEvent]


def test_an_override_replaces_the_default_for_that_class_and_its_subclasses_only():
    circle = NodeStyle(shape="circle")
    config = VisualizationConfig(node_styles={NoteEvent: circle})
    assert config.node_style(NoteEvent(tones={C})) is circle
    assert config.node_style(Rest(quarter)) is circle
    assert config.node_style(ChordEvent(chord=C(maj))) is DEFAULT_NODE_STYLES[ChordEvent]


def test_a_more_specific_default_beats_a_less_specific_override():
    config = VisualizationConfig(node_styles={OmkObject: NodeStyle(shape="hexagon")})
    assert config.node_style(ChordEvent(chord=C(maj))) is DEFAULT_NODE_STYLES[ChordEvent]
    assert config.node_style(OmkObject()).shape == "hexagon"


def test_a_plain_shape_sets_nothing_else():
    assert NodeStyle(shape="plain").attributes() == {"shape": "plain"}


def test_node_style_attributes():
    style = NodeStyle(
        shape="box",
        rounded=True,
        fill_color="#eeeeee",
        border_color="#333333",
        font_color="#111111",
        font_name="monospace",
        font_size=8,
        width=1.5,
        height=0.5,
        margin="0.1,0.05",
    )
    assert style.attributes() == {
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": "#eeeeee",
        "color": "#333333",
        "fontcolor": "#111111",
        "fontname": "monospace",
        "fontsize": "8",
        "width": "1.5",
        "height": "0.5",
        "margin": "0.1,0.05",
    }


def test_edge_style_overrides_by_type():
    blue = EdgeStyle(color="steelblue", style="dashed")
    config = VisualizationConfig(edge_styles={EdgeType.LYRIC: blue})
    assert config.edge_style(EdgeType.LYRIC) is blue
    assert config.edge_style(EdgeType.NEXT) is DEFAULT_EDGE_STYLES[EdgeType.NEXT]
    assert config.edge_style(EdgeType.CONTAINS).style == "dotted"


def test_the_branch_default_is_solid_thin_with_an_open_arrowhead():
    attrs = DEFAULT_EDGE_STYLES[EdgeType.BRANCHES].attributes()
    assert attrs["style"] == "solid"
    assert attrs["arrowhead"] == "empty"
    assert float(attrs["penwidth"]) < 1


def test_relational_defaults_show_their_type_and_next_does_not():
    assert DEFAULT_EDGE_STYLES[EdgeType.HARMONIZES].show_type
    assert not DEFAULT_EDGE_STYLES[EdgeType.NEXT].show_type


def test_styles_and_hooks_reach_the_model():
    line = notes(C, D)
    graph = OmkGraph(GraphMeta())
    graph.add_line(line)
    config = VisualizationConfig(
        node_styles={NoteEvent: NodeStyle(shape="circle", fill_color="#ffeeaa")},
        edge_styles={EdgeType.NEXT: EdgeStyle(style="dashed", color="red", arrowhead="vee")},
        label=lambda obj: "note!",
        font_name="Courier",
        splines="ortho",
        node_sep=0.5,
        rank_sep=1,
    )
    model = GraphRenderer(graph, config).dot_graph()
    first = node(model, nid(line[0]))
    assert first.attrs["label"] == "note!"
    assert first.attrs["shape"] == "circle"
    assert first.attrs["style"] == "filled"
    assert first.attrs["fillcolor"] == "#ffeeaa"
    following = edge(model, nid(line[0]), nid(line[1]))
    assert (following.attrs["style"], following.attrs["color"], following.attrs["arrowhead"]) == (
        "dashed",
        "red",
        "vee",
    )
    assert model.attrs["fontname"] == "Courier"
    assert model.attrs["splines"] == "ortho"
    assert (model.attrs["nodesep"], model.attrs["ranksep"]) == ("0.5", "1")
    assert model.node_defaults["fontname"] == "Courier"
