"""Rendering through the local Graphviz: the errors when it is missing or
unhappy, and, where `dot` is installed, a real SVG and PNG."""

import html
import shutil
import subprocess

import pytest

from openmusickit.errors import GraphvizNotFoundError, OmkError, RenderingError
from openmusickit.visualization import GraphRenderer
from openmusickit.visualization import graphviz as graphviz_module
from tests.visualization.dot_helpers import nid

HAS_DOT = shutil.which("dot") is not None


def test_a_missing_dot_is_a_friendly_error(twinkle, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    renderer = GraphRenderer(twinkle.graph)
    with pytest.raises(GraphvizNotFoundError) as caught:
        renderer.to_svg()
    message = str(caught.value)
    assert "Graphviz" in message and "to_dot()" in message and "package manager" in message
    assert isinstance(caught.value, RenderingError)
    assert isinstance(caught.value, OmkError)
    assert isinstance(caught.value, RuntimeError)
    assert renderer.to_dot().startswith("digraph")  # still works
    assert renderer._repr_svg_() is None  # Jupyter falls back to the plain repr


def test_rich_display_is_the_svg(twinkle, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: "/usr/bin/dot")

    def fake_run(command, input, capture_output, check):
        return subprocess.CompletedProcess(command, 0, stdout=b"<svg/>", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert GraphRenderer(twinkle.graph)._repr_svg_() == "<svg/>"


def test_a_failing_dot_reports_graphviz_output(twinkle, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: "/usr/bin/dot")

    def failing_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, 1, stdout=b"", stderr=b"Error: syntax error in line 3"
        )

    monkeypatch.setattr(subprocess, "run", failing_run)
    with pytest.raises(RenderingError, match="exit code 1.*syntax error in line 3"):
        GraphRenderer(twinkle.graph).to_png()


def test_render_dot_passes_the_format_and_the_text(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: "/opt/dot")
    seen = {}

    def fake_run(command, input, capture_output, check):
        seen["command"], seen["input"] = command, input
        return subprocess.CompletedProcess(command, 0, stdout=b"<svg/>", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert graphviz_module.render_dot("digraph {}", "svg") == b"<svg/>"
    assert seen == {"command": ["/opt/dot", "-Tsvg"], "input": b"digraph {}"}


@pytest.mark.skipif(not HAS_DOT, reason="Graphviz `dot` is not installed")
def test_graphviz_accepts_the_dot_and_renders_svg_and_png(twinkle):
    renderer = GraphRenderer(twinkle.graph)
    canonical = subprocess.run(
        ["dot", "-Tcanon"], input=renderer.to_dot().encode(), capture_output=True, check=False
    )
    assert canonical.returncode == 0, canonical.stderr.decode()
    svg = html.unescape(renderer.to_svg())  # Graphviz writes `-` as `&#45;` in attributes
    assert svg.lstrip().startswith("<?xml") and "<svg" in svg
    for event in twinkle.melody:
        assert f'id="{nid(event)}"' in svg
    assert 'class="node omk-node NoteEvent SequentialEvent OmkObject"' in svg
    assert 'class="edge omk-edge next"' in svg
    assert renderer.to_png()[:8] == b"\x89PNG\r\n\x1a\n"
    assert renderer._repr_svg_() == renderer.to_svg()
