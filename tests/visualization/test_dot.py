"""The DOT model's text: quoting, HTML-like labels, rank subgraphs, and that
generating DOT never looks for Graphviz."""

import shutil
import subprocess

import pytest

from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.systems.wsmn.tonal.symbols import C, D
from openmusickit.visualization import GraphRenderer
from openmusickit.visualization.dot import DotEdge, DotGraph, DotNode, attribute_list, quote
from tests.graph.helpers import notes


def test_quoting():
    assert quote('a "b"') == '"a \\"b\\""'
    assert quote("back\\slash") == '"back\\\\slash"'
    assert quote("two\nlines") == '"two\\nlines"'
    assert quote("C♯⁴ ♩") == '"C♯⁴ ♩"'


def test_an_html_like_label_is_written_as_it_is():
    assert (
        attribute_list({"label": "<C<SUP>4</SUP>>", "shape": "box"})
        == ' [label=<C<SUP>4</SUP>>, shape="box"]'
    )
    assert attribute_list({"label": "<not html"}) == ' [label="<not html"]'
    assert attribute_list({"id": "<x>"}) == ' [id="<x>"]'


def test_defaults_ranks_ports_and_the_graph_label():
    graph = DotGraph(
        attrs={"rankdir": "TB", "label": "<<B>t</B>>"},
        node_defaults={"fontsize": "10"},
        edge_defaults={"color": "#b0b0b0"},
        nodes=[DotNode("a"), DotNode("b", {"shape": "plain"}), DotNode("c")],
        edges=[
            DotEdge("a", "b", source_port="bar", target_port="bar"),
            DotEdge("b", "c", {"style": "invis"}),
        ],
        ranks=[["a"], ["b", "c"], []],
    )
    assert graph.to_text() == (
        "digraph {\n"
        '  rankdir="TB";\n'
        "  label=<<B>t</B>>;\n"
        '  node [fontsize="10"];\n'
        '  edge [color="#b0b0b0"];\n'
        '  "a";\n'
        '  "b" [shape="plain"];\n'
        '  "c";\n'
        '  { rank=same; "a"; }\n'
        '  { rank=same; "b" -> "c" [style="invis"]; }\n'
        '  "a":bar -> "b":bar;\n'
        '  "b" -> "c" [style="invis"];\n'
        "}\n"
    )


def test_generating_dot_never_looks_for_graphviz(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: pytest.fail("looked for dot"))
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: pytest.fail("ran a process"))
    graph = OmkGraph(GraphMeta())
    graph.add_line(notes(C, D))
    text = GraphRenderer(graph).to_dot()
    assert text.startswith("digraph {") and text.endswith("}\n")
    assert 'rankdir="LR"' in text and 'splines="line"' in text
