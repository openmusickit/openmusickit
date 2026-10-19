"""Graph round trips through the writer, over every real score in `tests/scores/`:
`read(write(read(f)))` holds the same music as `read(f)` (`is_equivalent`),
writing what the reader built warns about nothing,
and what equivalence cannot see survives node by node through the correspondence:
a meter's spelling, a tempo word, and the reader's `meta["musicxml"]`.
"""

from __future__ import annotations

import io
import warnings
from functools import cache

import pytest

from openmusickit.errors import OmkWarning
from openmusickit.io.musicxml import read, write
from openmusickit.objects.context_event import MeterEvent, TempoEvent
from tests.io.musicxml.test_corpus import LARGE, WITH_MUSICXML, graph_and_warnings

# Keys the round trip changes on purpose: the writer names itself as the
# encoder, writes a <sound tempo> beside a metronome mark that had none, and
# puts an extender line on a word's last syllable held over a melisma.
CHANGED_ON_PURPOSE = {
    ("Score", "encoding"),
    ("TempoEvent", "sound_tempo"),
    ("LyricSyllable", "extend"),
}


def fixtures(slow_for_large: bool = True):
    return [
        pytest.param(
            fixture,
            id=fixture.slug,
            marks=[pytest.mark.slow] if slow_for_large and fixture.slug in LARGE else [],
        )
        for fixture in WITH_MUSICXML
    ]


@cache
def round_trip(slug: str):
    """The fixture's graph, the graph read back from writing it, and what writing warned."""
    graph, _ = graph_and_warnings(slug)
    out = io.BytesIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        write(graph, out)
    written = [str(w.message) for w in caught if issubclass(w.category, OmkWarning)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        again = read(io.BytesIO(out.getvalue()))
    return graph, again, written


@pytest.mark.parametrize("fixture", fixtures())
def test_a_round_trip_holds_the_same_music(fixture):
    graph, again, _ = round_trip(fixture.slug)
    assert graph.is_equivalent(again), graph.diff(again)


@pytest.mark.parametrize("fixture", fixtures())
def test_writing_what_the_reader_built_warns_about_nothing(fixture):
    _, _, written = round_trip(fixture.slug)
    assert written == []


@pytest.mark.parametrize("fixture", fixtures())
def test_a_round_trip_keeps_what_equivalence_cannot_see(fixture):
    graph, again, _ = round_trip(fixture.slug)
    pairs = graph.correspondence(again)
    assert pairs is not None
    for before_id, after_id in pairs.items():
        before, after = graph.get_node(before_id), again.get_node(after_id)
        if isinstance(before, MeterEvent):  # 2/2 equals 4/4 by length
            assert getattr(before.meter, "presentation", None) == getattr(
                after.meter, "presentation", None
            )
        if isinstance(before, TempoEvent):
            assert (before.term and before.term.name) == (after.term and after.term.name)
        kind = type(before).__name__
        meta, meta_after = before.meta.get("musicxml", {}), after.meta.get("musicxml", {})
        for key in set(meta) | set(meta_after):
            if (kind, key) not in CHANGED_ON_PURPOSE:
                assert meta.get(key) == meta_after.get(key), (kind, key)


def test_the_corrected_companions_round_trip():
    for fixture in WITH_MUSICXML:
        if fixture.corrected is None:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OmkWarning)
            graph = read(fixture.corrected)
            out = io.BytesIO()
            write(graph, out)
            again = read(io.BytesIO(out.getvalue()))
        assert graph.is_equivalent(again), fixture.slug


def test_a_compressed_round_trip_is_the_same_document(tmp_path):
    graph, _ = graph_and_warnings("second-line-joe-avery")
    plain, packed = tmp_path / "joe.musicxml", tmp_path / "joe.mxl"
    write(graph, plain)
    graph.export_file(packed)
    assert packed.read_bytes()[:4] == b"PK\x03\x04"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        assert read(plain).is_equivalent(read(packed))
