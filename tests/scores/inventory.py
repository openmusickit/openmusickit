"""What a MusicXML file uses: an element census for sizing up a fixture.

Run it on one file or on every registered fixture:

    uv run python -m tests.scores.inventory tests/scores/mozart-string-quartet-k464-mvt3/sq7078259.mxl
    uv run python -m tests.scores.inventory

It reports the parts, staves and voices, clefs, meters and keys,
transpositions, note values and tuplets, and every notation, direction,
bar line, harmony kind and lyric number the file contains, with counts.
The `features` entry of a new fixture in `registry.py` is written from this.
It is a survey tool, independent of the reader, so it says what the file
contains rather than what OMK makes of it.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path


def load_musicxml(path: Path) -> ET.Element:
    """The root element of a `.musicxml`/`.xml` file or of the score inside a `.mxl` zip."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            inner = container.find(".//rootfile").get("full-path")
            return ET.fromstring(archive.read(inner))
    return ET.parse(path).getroot()


def _typed(element: ET.Element) -> str:
    """The element's tag with its `type` attribute, as `wedge[stop]`."""
    kind = element.get("type")
    return f"{element.tag}[{kind}]" if kind else element.tag


def inventory(root: ET.Element) -> dict[str, object]:
    notations: Counter[str] = Counter()
    for block in root.iter("notations"):
        for child in block:
            if child.tag in ("articulations", "ornaments", "technical", "dynamics"):
                notations.update(f"{child.tag}/{sub.tag}" for sub in child)
            else:
                notations[_typed(child)] += 1
    directions: Counter[str] = Counter()
    for block in root.iter("direction-type"):
        for child in block:
            if child.tag == "dynamics":
                directions["dynamics/" + ",".join(sub.tag for sub in child)] += 1
            elif child.tag == "words":
                directions[f"words={(child.text or '').strip()[:20]!r}"] += 1
            else:
                directions[_typed(child)] += 1
    barlines: Counter[str] = Counter()
    for barline in root.iter("barline"):
        key = f"{barline.get('location', 'right')}:{barline.findtext('bar-style')}"
        repeat, ending = barline.find("repeat"), barline.find("ending")
        if repeat is not None:
            key += f" repeat={repeat.get('direction')}"
        if ending is not None:
            key += f" ending={ending.get('type')}#{ending.get('number')}"
        barlines[key] += 1
    harmonies: Counter[str] = Counter()
    for harmony in root.iter("harmony"):
        key = harmony.findtext("kind") or "?"
        if harmony.find("bass") is not None:
            key += "/bass"
        if degrees := len(harmony.findall("degree")):
            key += f" +{degrees}deg"
        harmonies[key] += 1
    part_list = root.find("part-list")
    first_part = next(root.iter("part"))
    return {
        "encoding": [(e.tag, (e.text or "").strip()) for e in root.iter("encoding") for e in e],
        "parts": [p.findtext("part-name") for p in part_list.iter("score-part")],
        "part-groups": [
            (g.get("type"), g.findtext("group-symbol")) for g in part_list.iter("part-group")
        ],
        "staves": Counter(s.text for s in root.iter("staves")),
        "voices per part": {
            p.get("id"): len({v.text for v in p.iter("voice")}) for p in root.iter("part")
        },
        "measures": len(list(first_part.iter("measure"))),
        "first measure numbers": [m.get("number") for m in first_part.iter("measure")][:3],
        "implicit measures": sum(1 for m in root.iter("measure") if m.get("implicit") == "yes"),
        "clefs": Counter(
            f"{c.findtext('sign')}{c.findtext('line') or ''}"
            + (
                f"({c.findtext('clef-octave-change')})"
                if c.find("clef-octave-change") is not None
                else ""
            )
            for c in root.iter("clef")
        ),
        "times": Counter(
            f"{t.findtext('beats')}/{t.findtext('beat-type')}"
            + (f"[{t.get('symbol')}]" if t.get("symbol") else "")
            for t in root.iter("time")
        ),
        "keys": Counter(
            f"{k.findtext('fifths')} {k.findtext('mode') or ''}".strip() for k in root.iter("key")
        ),
        "transpose": Counter(
            f"d{t.findtext('diatonic')} c{t.findtext('chromatic')} o{t.findtext('octave-change')}"
            for t in root.iter("transpose")
        ),
        "note types": Counter(t.text for t in root.iter("type")),
        "time-modification": Counter(
            f"{t.findtext('actual-notes')}:{t.findtext('normal-notes')}"
            for t in root.iter("time-modification")
        ),
        "noteheads": Counter(n.text for n in root.iter("notehead")),
        "measure-style": Counter(
            _typed(child) for ms in root.iter("measure-style") for child in ms
        ),
        "tags": Counter(el.tag for el in root.iter()),
        "notations": notations,
        "directions": directions,
        "barlines": barlines,
        "harmonies": harmonies,
        "lyric numbers": Counter(lyric.get("number") for lyric in root.iter("lyric")),
    }


INTERESTING_TAGS = (
    "part",
    "measure",
    "note",
    "rest",
    "chord",
    "grace",
    "cue",
    "tie",
    "tied",
    "slur",
    "backup",
    "forward",
    "voice",
    "staff",
    "beam",
    "accidental",
    "dot",
    "time-modification",
    "tuplet",
    "direction",
    "harmony",
    "lyric",
    "extend",
    "elision",
    "barline",
    "repeat",
    "ending",
    "print",
    "sound",
    "attributes",
    "clef",
    "key",
    "time",
    "transpose",
    "staff-details",
    "part-group",
    "credit",
    "unpitched",
    "notehead",
    "measure-style",
    "fermata",
    "arpeggiate",
    "glissando",
    "slide",
    "tremolo",
    "pedal",
    "wedge",
    "octave-shift",
    "dashes",
    "bracket",
    "rehearsal",
    "segno",
    "coda",
    "words",
    "metronome",
    "dynamics",
    "figured-bass",
)


def report(path: Path) -> str:
    counts = inventory(load_musicxml(path))
    lines = [f"{path}"]
    for key, value in counts.items():
        if key == "tags":
            value = {tag: value[tag] for tag in INTERESTING_TAGS if value[tag]}
        elif isinstance(value, Counter):
            value = dict(value.most_common())
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    if argv:
        paths = [Path(arg) for arg in argv]
    else:
        from tests.scores.registry import FIXTURES

        paths = [f.musicxml for f in FIXTURES.values() if f.musicxml is not None]
    print("\n\n".join(report(path) for path in paths))


if __name__ == "__main__":
    main(sys.argv[1:])
