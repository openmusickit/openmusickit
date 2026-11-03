"""The published JSON Schemas (`docs/spec/schema/`): valid schemas themselves,
satisfied by everything the writer writes (the real scores, the examples,
generated graphs), and failed by documents with the faults they can see.
What a schema cannot see (the canonical form, the graph's rules, domains that
span fields) is the reader's to refuse, and is tested in `test_json_document.py`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.omk_json import dumps
from tests.io.musicxml.test_corpus import WITH_MUSICXML, graph_and_warnings
from tests.io.omk_json.examples import EXAMPLES, path_of
from tests.io.omk_json.test_json_document import CHANT, Neume
from tests.strategies import any_graphs

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "docs" / "spec" / "schema"
SCHEMAS = {
    path.name: json.loads(path.read_text(encoding="utf-8")) for path in SCHEMA_DIR.glob("*.json")
}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()
)
VALIDATOR = Draft202012Validator(SCHEMAS["omk-json.schema.json"], registry=REGISTRY)


def errors_in(document: dict[str, Any]) -> list[str]:
    return [error.message for error in VALIDATOR.iter_errors(document)]


def test_the_schemas_are_valid_schemas():
    assert sorted(SCHEMAS) == ["omk-json.schema.json", "omk.schema.json", "wsmn.schema.json"]
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_the_examples_satisfy_the_schemas(name):
    assert errors_in(json.loads(path_of(name).read_text(encoding="utf-8"))) == []


@pytest.mark.slow
@pytest.mark.parametrize("fixture", WITH_MUSICXML, ids=lambda fixture: fixture.slug)
def test_the_real_scores_satisfy_the_schemas(fixture):
    graph, _ = graph_and_warnings(fixture.slug)
    assert errors_in(json.loads(dumps(graph)))[:3] == []


@settings(max_examples=50)
@given(any_graphs())
def test_any_graph_satisfies_the_schemas(graph):
    assert errors_in(json.loads(dumps(graph))) == []


def test_an_extension_type_is_checked_only_as_a_tagged_object():
    graph = OmkGraph(GraphMeta())
    graph.add_node(Neume(shape="podatus"))
    assert errors_in(json.loads(dumps(graph, [CHANT]))) == []


def sketch() -> dict[str, Any]:
    return json.loads(path_of("sketch").read_text(encoding="utf-8"))


def note_of(document: dict[str, Any]) -> dict[str, Any]:
    return next(node for node in document["nodes"] if node["@type"] == "NoteEvent")


@pytest.mark.parametrize(
    "edit",
    [
        lambda d: d.update(format="omk-xml"),
        lambda d: d.update(extra=None),
        lambda d: d["vocabularies"].pop("omk"),
        lambda d: d["vocabularies"]["omk"].update(version="1"),
        lambda d: d["graph"].pop("info"),
        lambda d: note_of(d).pop("@meta"),
        lambda d: note_of(d).update({"@id": "NOT-A-UUID"}),
        lambda d: note_of(d).update(extra=1),
        lambda d: note_of(d)["tones"][0].update(diatonic=7),
        lambda d: note_of(d)["tones"][0].update(chromatic=-1),
        lambda d: note_of(d)["tones"].append(note_of(d)["tones"][0]),
        lambda d: note_of(d)["tones"][0].update({"@type": "wsmn:MetricalDuration"}),
        lambda d: note_of(d).update(duration={"@type": "ClockDuration", "microseconds": 1.5}),
        lambda d: note_of(d).update(duration={"@type": "ClockDuration", "microseconds": "2/4x"}),
        lambda d: note_of(d)["duration"].update(dots=-1),
        lambda d: d["edges"][0].update(relation="Marks"),
        lambda d: d["edges"][0].update(origin="ASSERTED"),
        lambda d: d["edges"][0].pop("@target"),
        lambda d: next(n for n in d["nodes"] if n["@type"] == "Marking")["mark"].update(
            kind="loud"
        ),
        lambda d: next(n for n in d["nodes"] if n["@type"] == "Marking")["mark"].update(
            {"@type": "Word"}
        ),
    ],
)
def test_a_document_with_a_fault_the_schemas_can_see_fails_them(edit):
    document = sketch()
    edit(document)
    assert errors_in(document)
