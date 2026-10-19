"""Properties of the MusicXML writer over generated scores (`_plans/musicxml.md` §9.6).

`exportable_scores()` builds graphs in the form the reader builds;
writing one and reading it back gives an equivalent graph,
and so does writing it stripped of its bar grid and of the bar lines its
meters imply (the sparse form of decision 14), since the writer puts both back.
"""

from __future__ import annotations

import io
import warnings

from hypothesis import given

from openmusickit.errors import OmkWarning
from openmusickit.graph.graph import OmkGraph
from openmusickit.io.musicxml import read, write
from openmusickit.objects.score import Score
from tests.strategies import exportable_scores


def written_and_read(graph: OmkGraph) -> tuple[OmkGraph, list[str]]:
    out = io.BytesIO()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        write(graph, out)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OmkWarning)
        again = read(io.BytesIO(out.getvalue()))
    return again, [str(w.message) for w in caught]


def strip(graph: OmkGraph) -> None:
    """The sparse form: no bar grid, and no bar line its meter would put back."""
    score = next(graph.nodes(Score))
    for sync_line in list(graph.score_sync_lines(score)):
        graph.remove_sync_line(sync_line)
    for head in list(graph.score_lines(score)):
        graph.remove_derivable_divisions(head)


@given(exportable_scores())
def test_a_score_reads_back_as_written(graph):
    again, warned = written_and_read(graph)
    assert warned == []
    assert again.is_equivalent(graph), graph.diff(again)


@given(exportable_scores())
def test_the_sparse_form_reads_back_as_the_full_one(graph):
    full, _ = written_and_read(graph)
    strip(graph)
    again, _ = written_and_read(graph)
    assert again.is_equivalent(full), full.diff(again)
