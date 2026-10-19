"""A real notation program accepts what the writer writes
(`_plans/musicxml.md` §9.7): where MuseScore is installed, each real score,
read and written again, renders through `mscore` to a PDF with pages.
Skipped without `mscore`; slow, since it starts MuseScore once per score.
"""

import os
import shutil
import subprocess

import pytest

from openmusickit.io.musicxml import write
from tests.io.musicxml.test_corpus import WITH_MUSICXML, graph_and_warnings

MSCORE = shutil.which("mscore")

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(MSCORE is None, reason="MuseScore (mscore) is not installed"),
]


@pytest.mark.parametrize("fixture", WITH_MUSICXML, ids=lambda fixture: fixture.slug)
def test_musescore_renders_what_the_writer_writes(fixture, tmp_path):
    graph, _ = graph_and_warnings(fixture.slug)
    exported, pdf = tmp_path / "exported.musicxml", tmp_path / "exported.pdf"
    write(graph, exported)
    result = subprocess.run(
        [MSCORE, "-o", str(pdf), str(exported)],
        capture_output=True,
        timeout=300,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")[-2000:]
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page") + data.count(b"/Type/Page") > 0
