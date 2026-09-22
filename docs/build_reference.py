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


def main() -> None:
    docs_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(docs_dir)
    sys.path.append(docs_dir)
    blueprint.BlueprintTransformer._fetch_members = _fetch_members_keeping_dunders
    builder = Builder.from_quarto_config("_quarto.yml")
    builder.build()
    _quote_dunders(builder.dir)


if __name__ == "__main__":
    main()
