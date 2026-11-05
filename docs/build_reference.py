"""Build the API reference with quartodoc, keeping dunder methods.

Run from this directory: ``uv run python build_reference.py``.
It does what ``quartodoc build`` does, with one change.

quartodoc's only switch for underscore names is ``include_private``,
which admits every ``_name`` and ``__name__`` alike.
OMK's value types carry their algebra in dunders
(``__add__``, ``__sub__``, ``__lt__``, ``__format__``, ...),
so those belong in the reference,
while single-underscore helpers do not.
This script patches quartodoc's member filter accordingly,
and also drops members griffe synthesizes (a dataclass's generated ``__init__``).
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

from quartodoc import Builder
from quartodoc.builder import blueprint

# Dunders that are implementation hooks rather than part of the type's interface.
HIDDEN_DUNDERS = {"__post_init__", "__getnewargs__"}

_fetch_members = blueprint.BlueprintTransformer._fetch_members


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _fetch_members_keeping_dunders(self, el, obj):
    """Fetch members as quartodoc does, then drop private names that are not dunders."""
    include_private = el.include_private
    el.include_private = True
    try:
        names = _fetch_members(self, el, obj)
    finally:
        el.include_private = include_private
    members = obj.all_members if el.include_inherited else obj.members
    return [
        name
        for name in names
        if (not name.startswith("_") or (_is_dunder(name) and name not in HIDDEN_DUNDERS))
        and not _is_synthesized(members[name])
    ]


def _is_synthesized(member) -> bool:
    """True for members griffe invents rather than reads, such as a dataclass ``__init__``."""
    target = member.final_target if member.is_alias else member
    return not target.lineno


_DUNDER_HEADING = re.compile(r"^(#+ )(__\w+__)( \{)", re.MULTILINE)
_DUNDER_LINK = re.compile(r"\[(__\w+__)\]\(")


def _quote_dunders(reference_dir: str) -> None:
    """Wrap dunder names in backticks in headings and summary-table links.

    Markdown would otherwise read ``__add__`` as bold ``add``.
    """
    for path in pathlib.Path(reference_dir).glob("*.qmd"):
        text = path.read_text()
        fixed = _DUNDER_HEADING.sub(r"\1`\2`\3", text)
        fixed = _DUNDER_LINK.sub(r"[`\1`](", fixed)
        if fixed != text:
            path.write_text(fixed)


_DOCTEST_PROMPT = re.compile(r"( {0,3})>>>( |$)")


def _fence_doctests(text: str) -> str:
    """Wrap bare doctest blocks in Python code fences.

    griffe fences the examples under an ``Examples`` heading,
    but passes a bare ``>>>`` through as Markdown,
    which reads it as a nested blockquote.
    A blank line always ends a doctest block, since doctest requires it to end the expected output.
    Four or more spaces of indent is already a Markdown code block, so is left alone.

    Examples
    --------
    >>> _fence_doctests("Text.\\n\\n>>> 1 + 1\\n2\\n\\nMore.")
    'Text.\\n\\n```python\\n>>> 1 + 1\\n2\\n```\\n\\nMore.'
    """
    result = []
    in_fence = False
    doctest_indent = None  # the open doctest block's indent; None when there is no open block
    for line in text.split("\n"):
        if doctest_indent is not None:
            if line.strip():
                result.append(line)
                continue
            result.append(f"{doctest_indent}```")
            doctest_indent = None
        elif line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and (prompt := _DOCTEST_PROMPT.match(line)):
            doctest_indent = prompt.group(1)
            result.append(f"{doctest_indent}```python")
        result.append(line)
    if doctest_indent is not None:
        result.append(f"{doctest_indent}```")
    return "\n".join(result)


def _fence_all_doctests(reference_dir: str) -> None:
    """Apply ``_fence_doctests`` to every generated reference page."""
    for path in pathlib.Path(reference_dir).glob("*.qmd"):
        text = path.read_text()
        fixed = _fence_doctests(text)
        if fixed != text:
            path.write_text(fixed)


def main() -> None:
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(docs_dir)
    sys.path.append(docs_dir)
    blueprint.BlueprintTransformer._fetch_members = _fetch_members_keeping_dunders
    builder = Builder.from_quarto_config("_quarto.yml")
    builder.build()
    _quote_dunders(builder.dir)
    _fence_all_doctests(builder.dir)


if __name__ == "__main__":
    main()
