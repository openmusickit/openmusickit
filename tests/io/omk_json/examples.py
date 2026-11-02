"""The example documents published with the specification (`docs/spec/examples/`),
built here with fixed ids so that the reference implementation generates them.

    uv run python -m tests.io.omk_json.examples   # rewrite the files after a deliberate change

`test_json_examples.py` checks that the files are what this module builds,
that they round-trip, and that the format page shows the first of them verbatim.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from openmusickit.graph.edge import TimingAnchor
from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.io.omk_json import dumps
from openmusickit.objects.lyrics import LyricSyllable
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent, Rest
from openmusickit.objects.part import Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import slur, staccato
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.text.word import Word
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "docs" / "spec" / "examples"
MIDDLE_C, D4, E4 = TonalVector((0, 0, 0)), TonalVector((1, 2, 0)), TonalVector((2, 4, 0))


def with_fixed_ids(graph: OmkGraph, seed: int) -> OmkGraph:
    """`graph` with its nodes' and edges' ids replaced by ones drawn from `seed`,
    in the order they were added, so the same build always has the same ids."""
    nodes = list(graph.nodes())
    edges = [(edge, *graph.edge_endpoints(edge)) for edge in graph.edges()]
    rng = random.Random(seed)
    for item in [*nodes, *(edge for edge, _, _ in edges)]:
        item._id = UUID(int=rng.getrandbits(128), version=4)
    rebuilt = OmkGraph(graph.meta)
    rebuilt._add_objects(nodes, edges)  # the old graph's index is keyed by the old ids
    return rebuilt


def sketch() -> OmkGraph:
    """One middle-C quarter note with a staccato dot (the format page, §13)."""
    graph = OmkGraph(GraphMeta(name="Sketch"))
    note = NoteEvent(tones={MIDDLE_C}, duration=quarter)
    graph.add_node(note)
    graph.add_articulation(Marking(mark=staccato), note)
    return with_fixed_ids(graph, 1)


def fragment() -> OmkGraph:
    """A scored line under a slur, with a second voice branched off it,
    a sung syllable, an editor's metadata, and the last note pinned to a film's clock."""
    graph = OmkGraph(GraphMeta(name="Fragment", info={"editor": {"zoom": 1.5}}))
    line = [
        NoteEvent(tones={MIDDLE_C}, duration=quarter),
        NoteEvent(tones={D4, E4}, duration=half),
        Rest(eighth),
    ]
    graph.add_line(line)
    graph.add_spanner(MarkSpanner(mark=slur), line[0], line[1])
    graph.add_branch(
        line[1],
        NoteEvent(tones={MIDDLE_C}, duration=quarter),
        anchor=TimingAnchor.OFFSET,
        displacement=-eighth,
    )
    graph.connect_lyric_to_object(LyricSyllable(word=Word(["Ah"]), duration=quarter), line[0])
    score, part = Score(title="Fragment", composer="Anonymous"), Part(name="Voice")
    graph.add_line_to_score(score, line[0])
    graph.add_part_to_score(score, part)
    graph.add_stint(part, Stint(), line[0])
    graph.sync_event(
        line[2], SyncLine(temporal_system=CLOCK_TIME, name="film"), ClockDuration(2_500_000)
    )
    line[0].meta["editor"] = {"x": 120, "selected": True}
    return with_fixed_ids(graph, 2)


EXAMPLES: dict[str, Callable[[], OmkGraph]] = {"sketch": sketch, "fragment": fragment}


def path_of(name: str) -> Path:
    return EXAMPLES_DIR / f"{name}.omk.json"


if __name__ == "__main__":
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in EXAMPLES.items():
        path_of(name).write_text(dumps(build()), encoding="utf-8", newline="")
        print(f"wrote {path_of(name)}")
