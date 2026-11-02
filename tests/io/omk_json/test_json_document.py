"""OMK JSON documents: whole graphs out and back, the `OmkGraph` methods and
suffix dispatch, an extension vocabulary, and every refusal of the format
specification's §10 (readers) and §11 (writers)."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import pytest

from openmusickit.errors import GraphError, OmkJsonError, UnexportableError
from openmusickit.graph.edge import EdgeType, Next, OmkEdge, TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.omk_json import TypeCodec, Vocabulary, dumps, loads, read, write
from openmusickit.io.omk_json.primitives import decode_string
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.omk_object import SequentialEvent
from openmusickit.objects.part import Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import slur, staccato
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter
from openmusickit.systems.wsmn.tonal.symbols import C, D, E
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration
from tests.graph.dict_adapter import DictAdapter
from tests.io.omk_json.identity import differences


def small_graph() -> tuple[OmkGraph, list[NoteEvent]]:
    """A scored line of three notes with a staccato, a slur, a branch, metadata and a sync point."""
    graph = OmkGraph(GraphMeta(name="Sketch", description="a test", info={"app": {"zoom": 1.5}}))
    notes = [
        NoteEvent(tones={C}, duration=quarter),
        NoteEvent(tones={D, E}, duration=half),
        Rest(eighth),
    ]
    graph.add_line(notes)
    graph.add_articulation(Marking(mark=staccato), notes[0])
    graph.add_spanner(MarkSpanner(mark=slur), notes[0], notes[1])
    second = NoteEvent(tones={E}, duration=quarter)
    graph.add_branch(notes[1], second, anchor=TimingAnchor.OFFSET, displacement=-eighth)
    score, part = Score(title="Test"), Part(name="Flute")
    graph.add_line_to_score(score, notes[0])
    graph.add_part_to_score(score, part)
    graph.add_stint(part, Stint(), notes[0])
    film = SyncLine(temporal_system=CLOCK_TIME, name="film")
    graph.sync_event(notes[2], film, ClockDuration(2_000_000))
    notes[0].meta["editor"] = {"x": 10, "selected": True, "tags": ["a", None]}
    graph.get_edge(notes[0], notes[1], EdgeType.NEXT).meta["note"] = "first"
    return graph, notes


def assert_same_graph(graph: OmkGraph, again: OmkGraph) -> None:
    """The same node and edge ids, the same endpoints, identical content and equal meta."""
    assert again.meta == graph.meta
    nodes = {node.id: node for node in graph.nodes()}
    assert {node.id for node in again.nodes()} == set(nodes)
    for node in again.nodes():
        assert not differences(nodes[node.id], node), differences(nodes[node.id], node)
        assert node.meta == nodes[node.id].meta
    edges = {edge.id: edge for edge in graph.edges()}
    assert {edge.id for edge in again.edges()} == set(edges)
    for edge in again.edges():
        original = edges[edge.id]
        assert not differences(original, edge)
        assert edge.meta == original.meta
        ends, original_ends = again.edge_endpoints(edge), graph.edge_endpoints(original)
        assert [node.id for node in ends] == [node.id for node in original_ends]


def document(graph: OmkGraph) -> dict[str, Any]:
    return json.loads(dumps(graph))


def text_of(data: dict[str, Any]) -> str:
    return json.dumps(data)


# --- round trips -------------------------------------------------------------------------------


def test_a_graph_reads_back_the_same_with_its_ids():
    graph, _ = small_graph()
    assert_same_graph(graph, loads(dumps(graph)))


def test_a_document_reads_back_and_writes_the_same_text():
    graph, _ = small_graph()
    text = dumps(graph)
    assert dumps(loads(text)) == text


def test_the_text_does_not_depend_on_the_adapter_or_the_order_in_the_file():
    graph, _ = small_graph()
    text = dumps(graph)
    assert dumps(loads(text, graph_engine=DictAdapter())) == text
    shuffled = json.loads(text)
    rng = random.Random(0)
    rng.shuffle(shuffled["nodes"])
    rng.shuffle(shuffled["edges"])
    assert dumps(loads(json.dumps(shuffled, indent=None))) == text


def test_the_empty_graph():
    assert dumps(OmkGraph(GraphMeta())) == (
        "{\n"
        '  "edges": [],\n'
        '  "format": "omk-json",\n'
        '  "graph": {\n'
        '    "description": null,\n'
        '    "info": {},\n'
        '    "name": null\n'
        "  },\n"
        '  "nodes": [],\n'
        '  "vocabularies": {\n'
        '    "omk": {\n'
        '      "uri": "https://openmusickit.org/spec/omk",\n'
        '      "version": "0.1"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_only_the_vocabularies_used_are_listed():
    graph = OmkGraph(GraphMeta())
    graph.add_node(Part(name="Flute"))
    assert list(document(graph)["vocabularies"]) == ["omk"]
    graph.add_node(NoteEvent(tones={C}))
    assert list(document(graph)["vocabularies"]) == ["omk", "wsmn"]


def test_nodes_and_edges_are_in_id_order_with_their_structural_keys():
    graph, _ = small_graph()
    data = document(graph)
    for items, keys in [
        (data["nodes"], {"@id", "@type", "@meta"}),
        (data["edges"], {"@id", "@type", "@meta", "@source", "@target"}),
    ]:
        assert [item["@id"] for item in items] == sorted(item["@id"] for item in items)
        assert all({key for key in item if key.startswith("@")} == keys for item in items)


def test_a_score_contains_plain_edges_and_a_branch_is_timed():
    graph, notes = small_graph()
    kinds = {edge["@type"] for edge in document(graph)["edges"]}
    assert kinds == {"Next", "Branch", "Simultaneous", "Edge"}
    branch = next(edge for edge in document(graph)["edges"] if edge["@type"] == "Branch")
    assert branch["anchor"] == "offset" and branch["displacement"]["numerator"] == -1


# --- OmkGraph methods and files ----------------------------------------------------------------


def test_the_graph_methods_and_files(tmp_path):
    graph, _ = small_graph()
    assert graph.export_to_json() == dumps(graph)
    assert_same_graph(graph, OmkGraph.from_json(graph.export_to_json()))
    path = tmp_path / "sketch.omk.json"
    graph.export_json_to_file(path)
    assert path.read_bytes() == dumps(graph).encode("utf-8")
    assert_same_graph(graph, read(path))
    assert_same_graph(graph, OmkGraph.from_file(path))  # keeps the graph's metadata
    other = tmp_path / "other.json"
    graph.export_file(other)
    assert other.read_text(encoding="utf-8") == dumps(graph)
    with pytest.raises(ValueError, match="whole graph"):
        graph.export_file(other, score=next(graph.nodes(Score)))


def test_write_uses_lf_line_endings(tmp_path):
    graph, _ = small_graph()
    write(graph, tmp_path / "a.json")
    assert b"\r" not in (tmp_path / "a.json").read_bytes()


def test_import_adds_a_document_to_a_graph_but_not_its_metadata():
    graph, notes = small_graph()
    target = OmkGraph(GraphMeta(name="Target"))
    target.add_node(Part(name="Oboe"))
    target.import_json_graph(dumps(graph))
    assert target.meta.name == "Target"
    assert target.get_node(notes[0].id) is not None
    assert len(list(target.nodes())) == len(list(graph.nodes())) + 1


def test_import_file_dispatches_json(tmp_path):
    graph, notes = small_graph()
    path = tmp_path / "a.json"
    write(graph, path)
    target = OmkGraph(GraphMeta(name="Target"))
    target.import_file(path)
    assert target.meta.name == "Target" and target.get_node(notes[0].id) is not None


def test_an_import_that_clashes_or_fails_adds_nothing():
    graph, _ = small_graph()
    text = dumps(graph)
    target = OmkGraph(GraphMeta())
    target.import_json_graph(text)
    before = dumps(target)
    with pytest.raises(GraphError, match="already on the graph"):
        target.import_json_graph(text)  # the same ids again
    broken = json.loads(text)
    broken["edges"][-1]["@source"] = "00000000-0000-4000-8000-000000000000"
    with pytest.raises(OmkJsonError):
        target.import_json_graph(json.dumps(broken))
    assert dumps(target) == before


# --- an extension vocabulary -------------------------------------------------------------------


@dataclass(kw_only=True, slots=True)
class Neume(SequentialEvent):
    """A test-only node type, standing in for an extension's."""

    shape: str


def _encode_neume(neume: Neume, e) -> dict[str, Any]:
    return {"duration": e.optional(neume.duration), "shape": neume.shape}


def _decode_neume(f: dict[str, Any], d) -> Neume:
    return Neume(duration=d.optional(f["duration"], "Duration"), shape=decode_string(f["shape"]))


CHANT = Vocabulary(
    prefix="chant",
    uri="https://example.org/spec/chant",
    version="0.3",
    codecs=(
        TypeCodec("Neume", Neume, "node", ("duration", "shape"), _encode_neume, _decode_neume),
    ),
)


def test_an_extension_vocabulary_is_written_required_and_read():
    graph = OmkGraph(GraphMeta())
    neume = Neume(shape="podatus", duration=quarter)
    graph.add_line([neume, NoteEvent(tones={C}, duration=quarter)])
    with pytest.raises(UnexportableError, match="No vocabulary defines Neume"):
        dumps(graph)
    text = dumps(graph, [CHANT])
    data = json.loads(text)
    assert data["vocabularies"]["chant"] == {
        "uri": "https://example.org/spec/chant",
        "version": "0.3",
    }
    assert {node["@type"] for node in data["nodes"]} == {"chant:Neume", "NoteEvent"}
    with pytest.raises(OmkJsonError, match=r"https://example.org/spec/chant version 0.3"):
        loads(text)
    again = loads(text, [CHANT])
    assert_same_graph(graph, again)
    assert dumps(again, [CHANT]) == text


def test_a_document_prefix_is_local_to_the_document():
    graph = OmkGraph(GraphMeta())
    graph.add_node(Neume(shape="punctum"))
    data = json.loads(dumps(graph, [CHANT]))
    data["vocabularies"]["gr"] = data["vocabularies"].pop("chant")
    data["nodes"][0]["@type"] = "gr:Neume"
    again = loads(json.dumps(data), [CHANT])
    assert dumps(again, [CHANT]) == dumps(graph, [CHANT])  # written back with the preferred prefix


# --- what a reader refuses (§10) ------------------------------------------------------------


def edited(edit) -> str:
    graph, _ = small_graph()
    data = document(graph)
    edit(data)
    return json.dumps(data)


def first_of(data: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(node for node in data["nodes"] if node["@type"] == kind)


NEXT_EDGE_ID = "00000000-0000-4000-8000-0000000000ff"


@pytest.mark.parametrize(
    "edit, message",
    [
        (lambda d: d.update(format="omk-xml"), "format"),
        (lambda d: d.update(extra=1), "exactly"),
        (lambda d: d.pop("graph"), "exactly"),
        (lambda d: d["vocabularies"].pop("omk"), "core vocabulary"),
        (lambda d: d["vocabularies"].update(core=d["vocabularies"].pop("omk")), "core vocabulary"),
        (lambda d: d["vocabularies"]["wsmn"].update(version="0.2"), "wsmn version 0.2"),
        (lambda d: d["vocabularies"]["wsmn"].update(version="1"), "wsmn version 1"),
        (
            lambda d: d["vocabularies"].update(
                x={"uri": "https://example.org/x", "version": "1.0"}
            ),
            "example.org/x",
        ),
        (lambda d: d["vocabularies"].update(again=d["vocabularies"]["wsmn"]), "listed twice"),
        (lambda d: d["vocabularies"]["wsmn"].update(extra=1), "exactly `uri` and `version`"),
        (lambda d: d["vocabularies"].update(W=d["vocabularies"].pop("wsmn")), "prefix"),
        (lambda d: first_of(d, "NoteEvent").update({"@type": "wsmn:NoteEvent"}), "not a type"),
        (lambda d: first_of(d, "NoteEvent").update({"@type": "x:NoteEvent"}), "does not declare"),
        (lambda d: first_of(d, "NoteEvent").update({"@extra": 1}), "exactly the keys"),
        (lambda d: first_of(d, "NoteEvent").pop("@meta"), "exactly the keys"),
        (lambda d: first_of(d, "NoteEvent").update({"@meta": []}), "@meta"),
        (lambda d: first_of(d, "NoteEvent").pop("duration"), "fields"),
        (lambda d: first_of(d, "NoteEvent").update(duration=None, extra=1), "fields"),
        (
            lambda d: first_of(d, "NoteEvent").update({"@id": first_of(d, "Part")["@id"]}),
            "Two nodes or edges",
        ),
        (lambda d: d["edges"][0].update({"@id": d["nodes"][0]["@id"]}), "Two nodes or edges"),
        (lambda d: first_of(d, "NoteEvent").update({"@id": "NOT-A-UUID"}), "UUID"),
        (
            lambda d: d["edges"][0].update({"@target": "00000000-0000-4000-8000-000000000000"}),
            "not a node",
        ),
        (lambda d: d["edges"][0].update({"@type": "NoteEvent"}), "is a node, not an edge"),
        (lambda d: d["nodes"][0].update({"@type": "Next"}), "is an edge, not a node"),
        (
            lambda d: first_of(d, "NoteEvent").update(
                tones=[first_of(d, "NoteEvent")["tones"][0]] * 2
            ),
            "twice",
        ),
        (
            lambda d: first_of(d, "NoteEvent").update(
                duration={"@type": "ClockDuration", "microseconds": -1}
            ),
            "negative",
        ),
        (lambda d: d["edges"][0].update(origin="ASSERTED"), "not one of"),
        (lambda d: d.update(nodes={}), "array"),
        (lambda d: d["graph"].update(info=[]), "info"),
        (lambda d: d["graph"].update(name=3), "not a string"),
    ],
    ids=repr,
)
def test_a_reader_refuses(edit, message):
    with pytest.raises(OmkJsonError, match=message):
        loads(edited(edit))


def test_a_reader_refuses_two_edges_of_one_relation_or_a_second_next():
    graph, notes = small_graph()
    data = document(graph)
    next_edge = next(edge for edge in data["edges"] if edge["@type"] == "Next")
    plain = {**next_edge, "@id": NEXT_EDGE_ID, "@type": "Edge", "relation": "next"}
    data["edges"].append(plain)
    with pytest.raises(OmkJsonError, match="rule of the graph"):
        loads(json.dumps(data))
    data = document(graph)
    next_edge = next(edge for edge in data["edges"] if edge["@type"] == "Next")
    other = next(node for node in data["nodes"] if node["@type"] == "Part")["@id"]
    data["edges"].append({**next_edge, "@id": NEXT_EDGE_ID, "@target": other})
    with pytest.raises(OmkJsonError, match="rule of the graph"):
        loads(json.dumps(data))


@pytest.mark.parametrize(
    "text",
    ["", "[]", "{", '{"format": "omk-json", "format": "omk-json"}', "﻿{}"],
    ids=repr,
)
def test_a_reader_refuses_what_is_not_a_document(text):
    with pytest.raises(OmkJsonError):
        loads(text)


def test_a_file_that_is_not_utf8_is_refused(tmp_path):
    path = tmp_path / "latin.json"
    path.write_bytes('{"name": "Dvořák"}'.encode("cp1250"))
    with pytest.raises(OmkJsonError, match="not UTF-8"):
        read(path)


# --- what a writer refuses (§11) ------------------------------------------------------------


@pytest.mark.parametrize(
    "meta",
    [
        {"t": (1, 2)},
        {"f": Fraction(1, 2)},
        {1: "x"},
        {"n": float("nan")},
        {"s": {1, 2}},
        {"s": "\ud800"},
    ],
    ids=repr,
)
def test_a_writer_refuses_metadata_that_is_not_json(meta):
    graph = OmkGraph(GraphMeta())
    note = NoteEvent(tones={C})
    graph.add_node(note)
    note.meta.update(meta)
    with pytest.raises(UnexportableError, match=f"NoteEvent {note.id}"):
        dumps(graph)
    with pytest.raises(UnexportableError, match="graph's info"):
        dumps(OmkGraph(GraphMeta(info=meta)))


def test_a_writer_refuses_edge_metadata_that_is_not_json_and_names_the_edge():
    graph = OmkGraph(GraphMeta())
    a, b = NoteEvent(tones={C}), NoteEvent(tones={D})
    graph.add_line([a, b])
    edge = graph.get_edge(a, b, EdgeType.NEXT)
    edge.meta["t"] = (1,)
    with pytest.raises(UnexportableError, match=f"Next edge {edge.id}"):
        dumps(graph)


def test_a_writer_refuses_a_node_type_no_vocabulary_defines():
    graph = OmkGraph(GraphMeta())
    graph.add_node(SequentialEvent(duration=quarter))
    with pytest.raises(UnexportableError, match="SequentialEvent"):
        dumps(graph)


def test_a_writer_refuses_a_system_no_vocabulary_declares():
    from openmusickit.values.time.duration import TemporalSystem

    graph = OmkGraph(GraphMeta())
    graph.add_node(SyncLine(temporal_system=TemporalSystem("Mine", "a private clock")))
    with pytest.raises(UnexportableError, match="system"):
        dumps(graph)


def test_plain_edges_and_their_classed_twins_are_both_kept():
    """A plain NEXT edge (from `add_edge`) and a `Next` differ in the model,
    so the format keeps them apart (`_plans/revisit.md`)."""
    graph = OmkGraph(GraphMeta())
    a, b, c = (NoteEvent(tones={t}) for t in (C, D, E))
    graph.add_node(a)
    graph.add_node(b)
    graph.add_node(c)
    graph.add_edge(a, b, EdgeType.NEXT)
    graph.add_next(b, c)
    again = loads(dumps(graph))
    kinds = sorted(type(edge).__name__ for edge in again.edges())
    assert kinds == ["Next", "OmkEdge"]
    assert (
        type(again.get_edge(again.get_node(a.id), again.get_node(b.id), EdgeType.NEXT)) is OmkEdge
    )
    assert isinstance(
        again.get_edge(again.get_node(b.id), again.get_node(c.id), EdgeType.NEXT), Next
    )
