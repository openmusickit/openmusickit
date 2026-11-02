"""The OMK JSON document (format specification §5, §8, §10–11):
a graph written as canonical text, and canonical text read back as a graph.

>>> from openmusickit.graph.graph import GraphMeta, OmkGraph
>>> from openmusickit.objects.note_event import NoteEvent
>>> from openmusickit.systems.wsmn.temporal.symbols import quarter
>>> from openmusickit.systems.wsmn.tonal.symbols import C
>>> graph = OmkGraph(GraphMeta(name="Sketch"))
>>> note = NoteEvent(tones={C}, duration=quarter)
>>> graph.add_node(note)
>>> text = dumps(graph)
>>> again = loads(text)
>>> again.get_node(note.id) == note, again.meta.name, dumps(again) == text
(True, 'Sketch', True)
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import UUID

from openmusickit.errors import GraphError, OmkJsonError, UnexportableError
from openmusickit.graph.edge import OmkEdge
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.graph.graph_adapter import GraphAdapter
from openmusickit.io.omk_json import canonical
from openmusickit.io.omk_json.core import CORE
from openmusickit.io.omk_json.primitives import decode_string, decode_uuid, encode_uuid
from openmusickit.io.omk_json.vocabulary import Decoder, Encoder, Vocabulary
from openmusickit.io.omk_json.wsmn import WSMN
from openmusickit.objects.omk_object import OmkObject

FORMAT = "omk-json"
DOCUMENT_KEYS = {"format", "vocabularies", "graph", "nodes", "edges"}
NODE_KEYS = {"@id", "@type", "@meta"}
EDGE_KEYS = {"@id", "@type", "@meta", "@source", "@target"}


def vocabularies_with(extra: Iterable[Vocabulary]) -> list[Vocabulary]:
    """The core and WSMN vocabularies, which are always given, followed by `extra`."""
    return [CORE, WSMN, *extra]


# --- writing ---------------------------------------------------------------------------------


def dumps(graph: OmkGraph, vocabularies: Iterable[Vocabulary] = ()) -> str:
    """The canonical document of `graph` (§9).
    `vocabularies` are any beyond the core and WSMN that the graph's types need.

    Raises
    ------
    UnexportableError
        if the graph holds a type no vocabulary defines, a value outside its domain,
        a system no vocabulary declares, or metadata that is not JSON data;
        the message names the node or edge.
    """
    encoder = Encoder(vocabularies_with(vocabularies))
    nodes = [_encode_node(node, encoder) for node in graph.nodes()]
    edges = [_encode_edge(edge, graph, encoder) for edge in graph.edges()]
    document = {
        "format": FORMAT,
        "graph": {
            "name": graph.meta.name,
            "description": graph.meta.description,
            "info": _metadata(graph.meta.info, "the graph's info"),
        },
        "nodes": sorted(nodes, key=lambda node: node["@id"]),
        "edges": sorted(edges, key=lambda edge: edge["@id"]),
        "vocabularies": {
            vocabulary.prefix: {"uri": vocabulary.uri, "version": vocabulary.version}
            for vocabulary in encoder.used
        },
    }
    return canonical.dumps(document)


def write(graph: OmkGraph, path: str | Path, vocabularies: Iterable[Vocabulary] = ()) -> None:
    """Writes the canonical document of `graph` to a file, as UTF-8 with LF line endings.

    Raises
    ------
    UnexportableError
        as `dumps` does.
    """
    text = dumps(graph, vocabularies)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(text)


def _encode_node(node: OmkObject, encoder: Encoder) -> dict[str, Any]:
    described = f"{type(node).__name__} {node.id}"
    data = _encode(lambda: encoder.tagged(node, "node"), described)
    data["@id"] = encode_uuid(node.id)
    data["@meta"] = _metadata(node.meta, described)
    return data


def _encode_edge(edge: OmkEdge, graph: OmkGraph, encoder: Encoder) -> dict[str, Any]:
    described = f"{type(edge).__name__} edge {edge.id}"
    source, target = graph.edge_endpoints(edge)
    data = _encode(lambda: encoder.tagged(edge, "edge"), described)
    data["@id"] = encode_uuid(edge.id)
    data["@source"] = encode_uuid(source.id)
    data["@target"] = encode_uuid(target.id)
    data["@meta"] = _metadata(edge.meta, described)
    return data


def _encode(encode, described: str) -> dict[str, Any]:
    try:
        return encode()
    except UnexportableError as error:
        raise UnexportableError(f"Cannot write {described}: {error}") from error
    except (ValueError, TypeError) as error:  # a value outside its domain
        raise UnexportableError(f"Cannot write {described}: {error}") from error


def _metadata(meta: dict[str, Any], described: str) -> dict[str, Any]:
    """`meta` itself, once it is known to be JSON data (§4.9)."""
    try:
        canonical.dumps(meta)
    except (ValueError, TypeError) as error:
        raise UnexportableError(f"The metadata of {described} is not JSON data: {error}") from error
    return meta


# --- reading ---------------------------------------------------------------------------------


def loads(
    text: str,
    vocabularies: Iterable[Vocabulary] = (),
    graph_engine: GraphAdapter | None = None,
) -> OmkGraph:
    """A new graph holding the document's nodes and edges, with their ids,
    and its metadata, on `graph_engine` if given.
    `vocabularies` are any beyond the core and WSMN that the document requires.

    Raises
    ------
    OmkJsonError
        if the text is not an OMK JSON document, requires a vocabulary that was
        not given, or breaks any rule of the specification (§10).
    """
    meta, nodes, edges = decode(text, vocabularies)
    graph = OmkGraph(meta, graph_engine)
    try:
        graph._add_objects(nodes, edges)
    except GraphError as error:  # two edges of one relation between two nodes; a second NEXT
        raise OmkJsonError(f"The document's edges break a rule of the graph: {error}") from error
    return graph


def read(
    path: str | Path,
    vocabularies: Iterable[Vocabulary] = (),
    graph_engine: GraphAdapter | None = None,
) -> OmkGraph:
    """The graph a document file holds (see `loads`).

    Raises
    ------
    OmkJsonError
        if the file is not UTF-8, or as `loads` does.
    """
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise OmkJsonError(f"{path} is not UTF-8: {error}.") from error
    return loads(text, vocabularies, graph_engine)


def decode(
    text: str, vocabularies: Iterable[Vocabulary] = ()
) -> tuple[GraphMeta, list[OmkObject], list[tuple[OmkEdge, OmkObject, OmkObject]]]:
    """The document's graph metadata, its nodes (with their ids and meta set),
    and its edges with their source and target nodes, checked against every rule
    of the specification but the graph's own (one edge of a relation between two
    nodes, one NEXT in and out), which adding them to a graph checks.

    Raises
    ------
    OmkJsonError
        as `loads` does.
    """
    data = canonical.loads(text)
    if type(data) is not dict or set(data) != DOCUMENT_KEYS:
        raise OmkJsonError(
            f"An OMK JSON document is an object with exactly {sorted(DOCUMENT_KEYS)}."
        )
    if data["format"] != FORMAT:
        raise OmkJsonError(
            f"The `format` of an OMK JSON document is {FORMAT!r}, not {data['format']!r}."
        )
    decoder = Decoder(vocabularies_with(vocabularies), data["vocabularies"])
    meta = _decode_graph_meta(data["graph"])
    seen: set[UUID] = set()
    nodes = [
        _decode(item, decoder, "node", NODE_KEYS, seen) for item in _array(data["nodes"], "nodes")
    ]
    by_id = {node.id: node for node in nodes}
    edges = [_decode_edge(item, decoder, seen, by_id) for item in _array(data["edges"], "edges")]
    return meta, nodes, edges


def _array(data: Any, name: str) -> list[Any]:
    if type(data) is not list:
        raise OmkJsonError(f"`{name}` must be an array.")
    return data


def _decode_graph_meta(data: Any) -> GraphMeta:
    if type(data) is not dict or set(data) != {"name", "description", "info"}:
        raise OmkJsonError(
            "`graph` must be an object with exactly `description`, `info` and `name`."
        )
    if type(data["info"]) is not dict:
        raise OmkJsonError("The graph's `info` must be an object.")
    return GraphMeta(
        name=None if data["name"] is None else decode_string(data["name"]),
        description=None if data["description"] is None else decode_string(data["description"]),
        info=data["info"],
    )


def _decode_edge(
    data: Any, decoder: Decoder, seen: set[UUID], nodes: dict[UUID, OmkObject]
) -> tuple[OmkEdge, OmkObject, OmkObject]:
    edge = _decode(data, decoder, "edge", EDGE_KEYS, seen)
    ends = []
    for key in ("@source", "@target"):
        node = nodes.get(decode_uuid(data[key]))
        if node is None:
            raise OmkJsonError(
                f"Edge {edge.id}: its {key[1:]} {data[key]} is not a node of the document."
            )
        ends.append(node)
    return edge, ends[0], ends[1]


def _decode(data: Any, decoder: Decoder, role: str, keys: set[str], seen: set[UUID]) -> Any:
    if type(data) is not dict or {key for key in data if key.startswith("@")} != keys:
        raise OmkJsonError(
            f"A {role} is an object with exactly the keys {sorted(keys)} besides its fields."
        )
    identifier = decode_uuid(data["@id"])
    if identifier in seen:
        raise OmkJsonError(f"Two nodes or edges have the id {identifier}.")
    seen.add(identifier)
    if type(data["@meta"]) is not dict:
        raise OmkJsonError(f"The {role} {identifier}: `@meta` must be an object.")
    try:
        obj = decoder.tagged(data, role)
    except OmkJsonError as error:
        raise OmkJsonError(f"The {role} {identifier}: {error}") from error
    obj._id = identifier  # the id the document gives it, as `graph._fork` sets a new one
    obj.meta = data["@meta"]
    return obj
