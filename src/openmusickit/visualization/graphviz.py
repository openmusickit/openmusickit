"""Rendering DOT through the local Graphviz `dot` executable.

Graphviz is a system dependency, never bundled: DOT generation
(`GraphRenderer.to_dot`) needs nothing installed, and only rendering to an
image needs `dot` on the PATH.
"""

from __future__ import annotations

import shutil
import subprocess

from openmusickit.errors import GraphvizNotFoundError, RenderingError

DOT_EXECUTABLE = "dot"

NOT_FOUND_MESSAGE = (
    "Rendering needs Graphviz's `dot` executable, which was not found on the PATH. "
    "Generating DOT (`to_dot()`) works without it. "
    "Install Graphviz with your operating system's package manager "
    "(see https://graphviz.org/download/) and make sure `dot` is on the PATH."
)


def find_dot() -> str | None:
    """The path of the `dot` executable, or None if there is none on the PATH."""
    return shutil.which(DOT_EXECUTABLE)


def render_dot(dot: str, output_format: str) -> bytes:
    """`dot` rendered by Graphviz to `output_format` (`svg`, `png`, ...), as bytes.

    Raises
    ------
    GraphvizNotFoundError
        if `dot` is not on the PATH.
    RenderingError
        if Graphviz rejected the input; its message carries Graphviz's own.
    """
    executable = find_dot()
    if executable is None:
        raise GraphvizNotFoundError(NOT_FOUND_MESSAGE)
    completed = subprocess.run(
        [executable, f"-T{output_format}"],
        input=dot.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RenderingError(
            f"Graphviz `dot` failed with exit code {completed.returncode}: {detail or 'no output'}"
        )
    return completed.stdout
