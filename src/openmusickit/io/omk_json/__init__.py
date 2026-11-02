"""OMK JSON: a published, language-neutral format for OMK graphs.

`dumps` a graph to its canonical text and `loads` it back, or `write` and `read` a file:

    from openmusickit.io.omk_json import read, write
    write(graph, "score.omk.json")
    graph = read("score.omk.json")

Ids persist, and a round trip is exact both ways:
a canonical document read and written again is the same bytes,
and a graph written and read again has the same ids, types, fields and metadata.
A graph that holds an extension's types is written and read with that
extension's `Vocabulary` passed as `vocabularies`;
the core and WSMN vocabularies are always included.

The format is specified in `docs/spec/omk-json.qmd`
and the vocabulary pages beside it;
this package is its reference implementation.
The design, and what is deliberately left out, are in `_plans/json-serialization.md`.
"""

from openmusickit.io.omk_json import canonical, core, document, primitives, vocabulary, wsmn
from openmusickit.io.omk_json.core import CORE
from openmusickit.io.omk_json.document import dumps, loads, read, write
from openmusickit.io.omk_json.vocabulary import TypeCodec, Vocabulary
from openmusickit.io.omk_json.wsmn import WSMN

__all__ = [
    "CORE",
    "WSMN",
    "TypeCodec",
    "Vocabulary",
    "canonical",
    "core",
    "document",
    "dumps",
    "loads",
    "primitives",
    "read",
    "vocabulary",
    "write",
    "wsmn",
]
