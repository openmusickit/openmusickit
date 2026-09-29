"""Guards on the fixture registry: every score directory has an entry,
every path an entry names exists, and the facts a test can check
without a reader (part names, measure count) match the files.

The counts are pinned so that a fixture swapped or re-exported
fails loudly here rather than somewhere in an importer test.
"""

import xml.etree.ElementTree as ET

import pytest

from tests.scores.inventory import load_musicxml
from tests.scores.registry import FIXTURES, SCORES_DIR

WITH_MUSICXML = [fixture for fixture in FIXTURES.values() if fixture.musicxml is not None]


def test_every_directory_is_registered():
    directories = {
        path.name
        for path in SCORES_DIR.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    assert directories == set(FIXTURES)


def test_every_registered_file_exists():
    for fixture in FIXTURES.values():
        assert fixture.directory.is_dir()
        assert (fixture.directory / "SOURCE.md").is_file()
        for path in fixture.files:
            assert path.is_file(), path


def test_every_file_in_a_directory_is_registered_or_documentation():
    for fixture in FIXTURES.values():
        on_disk = {path for path in fixture.directory.iterdir() if path.name != "SOURCE.md"}
        assert on_disk == set(fixture.files), fixture.slug


@pytest.mark.parametrize("fixture", WITH_MUSICXML, ids=lambda f: f.slug)
def test_parts_and_measures_match_the_file(fixture):
    root = load_musicxml(fixture.musicxml)
    assert root.tag == "score-partwise"
    names = tuple(part.findtext("part-name") for part in root.find("part-list").iter("score-part"))
    assert names == fixture.parts
    first_part = next(root.iter("part"))
    assert len(list(first_part.iter("measure"))) == fixture.measures


@pytest.mark.parametrize(
    "fixture", [f for f in WITH_MUSICXML if f.corrected is not None], ids=lambda f: f.slug
)
def test_a_corrected_companion_is_the_same_score(fixture):
    """The companion differs from the original only in the edits SOURCE.md lists,
    so its parts, measures and note count are the original's."""
    original = load_musicxml(fixture.musicxml)
    corrected = ET.parse(fixture.corrected).getroot()
    for tag in ("part", "measure", "note", "lyric", "direction"):
        assert len(list(corrected.iter(tag))) == len(list(original.iter(tag))), tag


def test_the_hymn_companion_corrects_only_syllabic_flags():
    fixture = FIXTURES["croft-o-god-our-help"]
    original = [lyric.findtext("text") for lyric in load_musicxml(fixture.musicxml).iter("lyric")]
    corrected = ET.parse(fixture.corrected).getroot()
    assert [lyric.findtext("text") for lyric in corrected.iter("lyric")] == original
    for lyric in corrected.iter("lyric"):
        assert lyric.findtext("syllabic") in ("single", "begin", "middle", "end")


def test_the_schubert_companion_hides_the_playback_tempi():
    fixture = FIXTURES["schubert-allegretto-d915"]
    corrected = ET.parse(fixture.corrected).getroot()
    metronomes = [d for d in corrected.iter("direction") if d.find(".//metronome") is not None]
    printed = [d for d in metronomes if d.get("print-object") != "no"]
    assert len(metronomes) == 13 and len(printed) == 1
    assert printed[0].find(".//per-minute").text == "118"
