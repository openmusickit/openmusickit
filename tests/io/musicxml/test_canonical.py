"""Canonical MusicXML comparison (`_plans/musicxml.md` §9.5).

Over the real scores: what the writer makes of what the reader built differs
from the original only in the kinds the registry accepts for that file, each
of which still occurs; the corrected companions differ in nothing; and the
sparse forms (no bar grid, no bar lines the meters imply) write the same
document as the full one. Then the normalizations, one small pair of
documents each: two spellings of the same music compare equal, and a change
to the music is a difference of the right kind.
"""

from __future__ import annotations

import io
import warnings
from functools import cache

import pytest

from openmusickit.errors import OmkWarning
from openmusickit.graph.graph import OmkGraph
from openmusickit.io.musicxml import container, read
from openmusickit.io.musicxml.canonical import Difference, canonicalize, compare
from openmusickit.io.musicxml.writer import to_bytes
from openmusickit.objects.score import Score
from tests.io.musicxml.documents import direction, doc, lyric, measure, note, rest
from tests.io.musicxml.test_corpus import LARGE, WITH_MUSICXML, graph_and_warnings
from tests.io.musicxml.test_reader import BACKUP, TWO_STAVES, Q, h, q, right_barline, w


def fixtures():
    return [
        pytest.param(
            fixture, id=fixture.slug, marks=[pytest.mark.slow] if fixture.slug in LARGE else []
        )
        for fixture in WITH_MUSICXML
    ]


def canonical_bytes(data: bytes):
    return canonicalize(container.load(io.BytesIO(data)))


def quietly_written(graph: OmkGraph) -> bytes:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        return to_bytes(graph)


def quietly_read(path) -> OmkGraph:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        return read(path)


@cache
def differences(slug: str) -> list[Difference]:
    from tests.scores.registry import FIXTURES

    graph, _ = graph_and_warnings(slug)
    original = canonicalize(container.load(FIXTURES[slug].musicxml))
    return compare(original, canonical_bytes(quietly_written(graph)))


@pytest.mark.parametrize("fixture", fixtures())
def test_the_writer_differs_from_the_original_only_as_the_registry_accepts(fixture):
    found = {difference.kind for difference in differences(fixture.slug)}
    unexpected = [d for d in differences(fixture.slug) if d.kind not in fixture.known_differences]
    assert unexpected == [], unexpected[:5]
    assert found == set(fixture.known_differences)  # every accepted kind still occurs


def test_the_corrected_companions_differ_in_nothing():
    for fixture in WITH_MUSICXML:
        if fixture.corrected is None:
            continue
        original = canonicalize(container.load(fixture.corrected))
        written = canonical_bytes(quietly_written(quietly_read(fixture.corrected)))
        assert compare(original, written) == [], fixture.slug


def sparse(graph: OmkGraph, keep_grid: bool) -> OmkGraph:
    """The graph with derivable bar lines removed from every top-level line,
    and its bar grid too unless `keep_grid`."""
    score = next(graph.nodes(Score))
    if not keep_grid:
        for sync_line in list(graph.score_sync_lines(score)):
            graph.remove_sync_line(sync_line)
    for head in list(graph.score_lines(score)):
        graph.remove_derivable_divisions(head)
    return graph


@pytest.mark.parametrize("keep_grid", [False, True], ids=["no grid", "grid kept"])
@pytest.mark.parametrize("fixture", fixtures())
def test_the_sparse_form_writes_the_same_document(fixture, keep_grid):
    full = canonical_bytes(quietly_written(graph_and_warnings(fixture.slug)[0]))
    stripped = sparse(quietly_read(fixture.musicxml), keep_grid)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        data = to_bytes(stripped)
    assert [str(w.message) for w in caught if issubclass(w.category, OmkWarning)] == []
    assert compare(full, canonical_bytes(data)) == []


# --- the normalizations ---------------------------------------------------------------------


def same(a: bytes, b: bytes) -> list[Difference]:
    return compare(canonical_bytes(a), canonical_bytes(b))


def kinds(a: bytes, b: bytes) -> set[str]:
    return {difference.kind for difference in same(a, b)}


def test_presentation_divisions_numbers_and_ids_are_not_differences():
    plain = doc(q("C") + q("D") + h("E"), divisions=4)
    dressed = doc(
        measure(
            '<print new-system="yes"/>'
            + note(
                "C",
                4,
                8,
                "quarter",
                extra='<stem>up</stem><beam number="1">begin</beam>',
                attrs='default-x="12"',
            )
            + note("D", 4, 8, "quarter", alter=None, extra="<stem>up</stem>")
            + note("E", 4, 16, "half"),
            number="0",
            implicit="yes",
        ),
        parts=("X9",),
        part_names=["P1"],
        divisions=8,
    )
    assert same(plain, dressed) == []


def test_voices_are_numbered_by_appearance_and_their_order_does_not_matter():
    one = doc(w("C") + BACKUP + h("A", 3, voice=2) + h("B", 3, voice=2))
    other = doc(h("A", 3, voice=6) + h("B", 3, voice=6) + BACKUP + w("C", voice=3))
    assert same(one, other) == []


def test_a_forward_and_a_hidden_rest_are_alike():
    forward = doc(h("C") + f"<forward><duration>{2 * Q}</duration></forward>")
    hidden = doc(h("C") + rest(2 * Q, "half", attrs='print-object="no"'))
    assert same(forward, hidden) == []
    assert kinds(forward, doc(h("C") + rest(2 * Q, "half"))) == {"rest"}


def test_tie_and_tied_are_one_item():
    both = doc(h("C", tie="start") + h("C", tie="stop"))
    tie_only = doc(  # <tie> without <tied>, as some programs write it
        note("C", 4, 2 * Q, "half").replace("<voice>", '<tie type="start"/><voice>')
        + note("C", 4, 2 * Q, "half").replace("<voice>", '<tie type="stop"/><voice>')
    )
    assert same(both, tie_only) == []
    assert kinds(both, doc(h("C") + h("C"))) == {"tie"}


def test_a_dynamic_in_notations_is_the_dynamic_of_a_direction():
    as_direction = doc(direction("<dynamics><p/></dynamics>") + w("C"))
    as_notation = doc(w("C", extra="<notations><dynamics><p/></dynamics></notations>"))
    assert same(as_direction, as_notation) == []
    assert kinds(as_direction, doc(direction("<dynamics><f/></dynamics>") + w("C"))) == {"dynamics"}


def test_a_chord_mark_counts_once_and_chord_notes_take_the_first_notes_value():
    arpeggio = "<notations><arpeggiate/></notations>"
    every_note = doc(h("C", extra=arpeggio) + h("E", chord=True, extra=arpeggio) + h("D"))
    first_note = doc(h("C", extra=arpeggio) + note("E", 4, 2 * Q, "quarter", chord=True) + h("D"))
    assert same(every_note, first_note) == []


def test_what_sits_on_a_bar_line_goes_where_the_reader_puts_it():
    at_the_end = doc(w("C") + direction("<words>dolce</words>"), w("D"))
    at_the_start = doc(w("C"), direction("<words>Dolce</words>") + w("D"))
    assert same(at_the_end, at_the_start) == []
    stop_late = doc(
        direction('<wedge type="crescendo"/>') + w("C"), direction('<wedge type="stop"/>') + w("D")
    )
    stop_early = doc(
        direction('<wedge type="crescendo"/>') + w("C") + direction('<wedge type="stop"/>'), w("D")
    )
    assert same(stop_late, stop_early) == []


def test_adjacent_rests_are_one_silence():
    halves = doc(rest(2 * Q, "half") + rest(2 * Q, "half"))
    whole_bar = doc(rest(4 * Q, whole_measure=True))
    assert same(halves, whole_bar) == []
    assert kinds(halves, doc(rest(2 * Q, "half") + h("C"))) == {"rest", "note"}


def test_a_key_with_no_number_stands_for_every_staff():
    unnumbered = doc(w("C", staff=1) + BACKUP + w("C", 3, staff=2, voice=5), attributes=TWO_STAVES)
    numbered = doc(
        w("C", staff=1) + BACKUP + w("C", 3, staff=2, voice=5),
        attributes=TWO_STAVES.replace(
            "<key><fifths>0</fifths></key>",
            '<key number="1"><fifths>0</fifths></key><key number="2"><fifths>0</fifths></key>',
        ),
    )
    assert same(unnumbered, numbered) == []


def test_changes_to_the_music_are_differences_of_their_kind():
    base = doc(
        q("C", extra=lyric("la", "single"))
        + q("D")
        + h("E")
        + right_barline("<bar-style>light-heavy</bar-style>")
    )
    assert kinds(base, doc(q("C", extra=lyric("lo", "single")) + q("D") + h("E")
                                + right_barline("<bar-style>light-heavy</bar-style>"))) == {"lyric"}  # fmt: skip
    assert kinds(base, doc(q("C", extra=lyric("la", "single")) + q("D") + h("E"))) == {"barline"}
    assert kinds(base, doc(q("C", extra=lyric("la", "single")) + q("D") + h("F")
                                + right_barline("<bar-style>light-heavy</bar-style>"))) == {"note"}  # fmt: skip
    two_bars = doc(w("C"), w("C"))
    assert {d.kind for d in compare(canonical_bytes(doc(w("C"))), canonical_bytes(two_bars))} == {
        "measures"
    }
    titled = doc(w("C"), header="<work><work-title>T</work-title></work>")
    assert kinds(doc(w("C")), titled) == {"header"}
    renamed = doc(w("C"), part_names=["Oboe"])
    assert kinds(doc(w("C")), renamed) == {"part-list"}


def test_canonicalize_refuses_what_is_not_a_partwise_score():
    import xml.etree.ElementTree as ET

    with pytest.raises(ValueError, match="score-timewise"):
        canonicalize(ET.Element("score-timewise"))
