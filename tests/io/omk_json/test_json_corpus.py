"""The real scores of `tests/scores/` through OMK JSON: each reads back with the
same ids, content and metadata, writes the same text again, and writes the same
music to MusicXML as before. The MusicXML is compared canonically
(`io.musicxml.canonical`), not byte for byte, because the MusicXML writer orders
some output by the graph's storage order, which JSON does not keep
(`_plans/json-serialization.md`, D19; `_plans/revisit.md`).
"""

from __future__ import annotations

import io
import warnings
import xml.etree.ElementTree as ET

import pytest

from openmusickit.errors import OmkWarning
from openmusickit.io.musicxml import canonicalize, compare
from openmusickit.io.musicxml import write as write_musicxml
from openmusickit.io.omk_json import dumps, loads
from tests.io.musicxml.test_corpus import LARGE, WITH_MUSICXML, graph_and_warnings
from tests.io.omk_json.identity import assert_same_graph

FIXTURES = [
    pytest.param(
        fixture, id=fixture.slug, marks=[pytest.mark.slow] if fixture.slug in LARGE else []
    )
    for fixture in WITH_MUSICXML
]


def musicxml_of(graph) -> ET.Element:
    out = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        write_musicxml(graph, out)
    return canonicalize(ET.fromstring(out.getvalue()))


@pytest.mark.parametrize("fixture", FIXTURES)
def test_a_score_reads_back_the_same_through_json(fixture):
    graph, _ = graph_and_warnings(fixture.slug)
    text = dumps(graph)
    again = loads(text)
    assert dumps(again) == text
    assert_same_graph(graph, again)
    assert compare(musicxml_of(graph), musicxml_of(again)) == []
