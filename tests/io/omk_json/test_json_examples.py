"""The example documents published with the specification: each is exactly what
the reference implementation writes (`tests.io.omk_json.examples` builds them),
reads back and writes the same bytes, and the format page shows the first verbatim."""

import re

import pytest

from openmusickit.io.omk_json import dumps, loads, read
from tests.io.omk_json.examples import EXAMPLES, EXAMPLES_DIR, path_of
from tests.io.omk_json.identity import assert_same_graph

FORMAT_PAGE = EXAMPLES_DIR.parent / "omk-json.qmd"


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_an_example_is_what_the_implementation_writes(name):
    graph = EXAMPLES[name]()
    text = path_of(name).read_text(encoding="utf-8")
    assert dumps(graph) == text, "rewrite with `uv run python -m tests.io.omk_json.examples`"
    assert dumps(loads(text)) == text
    assert_same_graph(graph, read(path_of(name)))


def test_the_examples_directory_holds_only_the_examples():
    assert sorted(p.name for p in EXAMPLES_DIR.iterdir()) == sorted(
        f"{n}.omk.json" for n in EXAMPLES
    )


def test_the_format_page_shows_the_sketch_verbatim():
    page = FORMAT_PAGE.read_text(encoding="utf-8")
    section = page[page.index("## 13. Examples") :]
    shown = re.search(r"```json\n(.*?)```", section, re.DOTALL).group(1)
    assert shown == path_of("sketch").read_text(encoding="utf-8")


def test_examples_build_the_same_every_time():
    for build in EXAMPLES.values():
        assert dumps(build()) == dumps(build())
