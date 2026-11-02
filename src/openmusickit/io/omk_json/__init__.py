"""OMK JSON: a published, language-neutral format for OMK graphs.

The format is specified in `docs/spec/omk-json.qmd`
and the vocabulary pages beside it;
this package is its reference implementation.
The design, and what is deliberately left out, are in `_plans/json-serialization.md`.
"""

from openmusickit.io.omk_json import canonical, primitives

__all__ = ["canonical", "primitives"]
