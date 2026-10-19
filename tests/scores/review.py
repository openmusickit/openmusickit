"""Review artifacts for the MusicXML writer (`_plans/musicxml.md` §9.8):
the original engraving beside MuseScore's engraving of what the writer made
of it, for a person (or an agent) to look over. Not a test.

    uv run python -m tests.scores.review schubert-allegretto-d915
    uv run python -m tests.scores.review second-line-joe-avery croft-o-god-our-help --out /tmp/review
    uv run python -m tests.scores.review            # every fixture with MusicXML

For each fixture it reads the corrected companion when there is one (the file
as the page has it; `--raw` reads the file as distributed) and writes, in
`<out>/<slug>/` (`_review/` by default, which git ignores):

- `exported.musicxml`: `write(read(file))`;
- `exported.pdf` and `exported-<page>.png`: that, engraved by MuseScore (`mscore`);
- `original-<page>.png`: the fixture's own PDF, page by page (`pdftoppm`);
- `side-by-side-<page>.png`: the two, original on the left, where ImageMagick's
  `montage` is installed (page n beside page n: an original with a title page
  is one page ahead);
- `canonical-diff.txt`: what `canonical.compare` finds between the original
  file and the export, counted by kind and then listed, with the kinds the
  registry accepts for the fixture and why.

Every image is on an opaque white page, so it shows in a dark editor theme.
A tool that is not installed is skipped with a note; the canonical diff
needs none.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import warnings
from collections import Counter
from pathlib import Path

from openmusickit.errors import OmkWarning
from openmusickit.io.musicxml import container, read, write
from openmusickit.io.musicxml.canonical import canonicalize, compare
from tests.scores.registry import FIXTURES, SCORES_DIR, ScoreFixture

DEFAULT_OUT = SCORES_DIR.parent.parent / "_review"
RESOLUTION = "80"  # dots per inch for the page images


def review(fixture: ScoreFixture, out: Path, raw: bool = False) -> list[str]:
    """Writes the review artifacts for one fixture into `out`, from its
    corrected companion when it has one and `raw` is False; returns notes
    on what was read and what was skipped."""
    out.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    source = fixture.musicxml if raw or fixture.corrected is None else fixture.corrected
    if source != fixture.musicxml:
        notes.append(
            f"read the corrected companion {source.name} (--raw for the file as distributed)"
        )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", OmkWarning)
        graph = read(source)
        exported = out / "exported.musicxml"
        write(graph, exported)
    (out / "warnings.txt").write_text("".join(f"{w.message}\n" for w in caught))
    write_canonical_diff(fixture, source, exported, out / "canonical-diff.txt")
    if shutil.which("mscore") is None:
        notes.append("mscore is not installed: no engraving of the export")
    else:
        pdf = out / "exported.pdf"
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        subprocess.run(["mscore", "-o", str(pdf), str(exported)], check=True, env=environment,
                       capture_output=True, timeout=300)  # fmt: skip
        pages(pdf, out / "exported", notes)
    if fixture.pdf is None:
        notes.append("the fixture has no PDF to compare with")
    else:
        pages(fixture.pdf, out / "original", notes)
    side_by_side(out, notes)
    return notes


def pages(pdf: Path, prefix: Path, notes: list[str]) -> None:
    """`pdf` as one PNG per page, `<prefix>-<page>.png`, on white."""
    if shutil.which("pdftoppm") is None:
        notes.append("pdftoppm is not installed: no page images")
        return
    subprocess.run(
        ["pdftoppm", "-png", "-r", RESOLUTION, str(pdf), str(prefix)], check=True, timeout=300
    )


def side_by_side(out: Path, notes: list[str]) -> None:
    """Each original page beside the exported page of the same number."""
    if shutil.which("montage") is None:
        notes.append("ImageMagick's montage is not installed: no side-by-side images")
        return
    originals = sorted(out.glob("original-*.png"))
    exports = sorted(out.glob("exported-*.png"))
    for number, (original, exported) in enumerate(zip(originals, exports, strict=False), 1):
        target = out / f"side-by-side-{number}.png"
        subprocess.run(
            ["montage", str(original), str(exported), "-tile", "2x1", "-geometry", "+8+8",
             "-background", "white", str(target)],
            check=True, timeout=300,
        )  # fmt: skip
    if len(originals) != len(exports):
        notes.append(f"the original has {len(originals)} pages, the export {len(exports)}")


def write_canonical_diff(fixture: ScoreFixture, source: Path, exported: Path, target: Path) -> None:
    original = canonicalize(container.load(source))
    written = canonicalize(container.load(io.BytesIO(exported.read_bytes())))
    differences = compare(original, written)
    lines = [f"{fixture.slug}: {len(differences)} differences (- {source.name}, + export)", ""]
    for kind, count in sorted(Counter(d.kind for d in differences).items()):
        reason = fixture.known_differences.get(kind) if source == fixture.musicxml else None
        accepted = f"  (accepted: {reason})" if reason else "  (NOT accepted by the registry)"
        lines.append(f"{count:6d} {kind}{accepted}")
    lines.append("")
    for difference in differences:
        where = (
            f"part {difference.part}, measure {difference.measure}"
            if difference.measure
            else "score"
        )
        lines.append(f"[{difference.kind}] {where}: {difference.detail}")
    target.write_text("\n".join(lines) + "\n")


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("slugs", nargs="*", help="fixtures to review (default: all with MusicXML)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="read the file as distributed, not its corrected companion",
    )
    options = parser.parse_args(arguments)
    slugs = options.slugs or [slug for slug, fixture in FIXTURES.items() if fixture.musicxml]
    for slug in slugs:
        fixture = FIXTURES.get(slug)
        if fixture is None or fixture.musicxml is None:
            print(f"{slug}: no such fixture with MusicXML", file=sys.stderr)
            return 2
        out = options.out / slug
        notes = review(fixture, out, options.raw)
        print(f"{slug}: {out}")
        for note in notes:
            print(f"  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
