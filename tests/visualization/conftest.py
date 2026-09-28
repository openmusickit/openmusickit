"""The graph the visualization tests draw: the plan's example picture
(`_plans/graph-visualization-example.png`) as a graph.

The docs' Twinkle melody under a treble clef, a chord line pinned to the
first note, the lyrics with a verse section, a staccato on the third note,
a slur over the fifth and sixth, a lower second voice branched from the
fifth, a Voice part with a stint, a Score, and a film reel as a sync line
with two pinned points (one named and described) and one unpinned.
"""

from types import SimpleNamespace

import pytest

from openmusickit.graph.graph import GraphMeta, OmkGraph
from openmusickit.objects.chord_event import ChordEvent
from openmusickit.objects.context_event import ClefEvent
from openmusickit.objects.lyrics import LyricSection
from openmusickit.objects.marking import Marking, MarkSpanner
from openmusickit.objects.note_event import NoteEvent
from openmusickit.objects.part import Part, Stint
from openmusickit.objects.score import Score
from openmusickit.objects.sync_line import SyncLine
from openmusickit.systems.wsmn.scoring.symbols import slur, staccato, treble_clef
from openmusickit.systems.wsmn.temporal.symbols import eighth, half, quarter, whole
from openmusickit.systems.wsmn.tonal.symbols import C, F, maj
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration


def build_twinkle() -> SimpleNamespace:
    """The example graph and handles on its parts."""
    graph = OmkGraph(GraphMeta())
    pitches = "C4 C4 G4 G4 A4 A4 G4".split()
    rhythm = [quarter] * 6 + [half]
    melody = [
        NoteEvent(tones={TonalVector.from_string(p)}, duration=d)
        for p, d in zip(pitches, rhythm, strict=True)
    ]
    clef = ClefEvent(clef=treble_clef)
    graph.add_line([clef, *melody])

    chords = [
        ChordEvent(chord=C(maj), duration=whole),
        ChordEvent(chord=F(maj), duration=half),
        ChordEvent(chord=C(maj), duration=half),
    ]
    graph.add_line(chords)
    graph.add_simultaneous(melody[0], chords[0])

    verse = LyricSection(section_type="verse", section_number=1)
    syllables = graph.add_lyrics("Twin-kle, twin-kle, lit-tle star,", section=verse)
    graph.zip_lyrics_to_objects(syllables[0], melody[0])

    dot = Marking(mark=staccato)
    graph.add_articulation(dot, melody[2])
    arc = MarkSpanner(mark=slur)
    graph.add_spanner(arc, melody[4], melody[5])

    voice = [NoteEvent(tones={TonalVector.from_string(p)}, duration=eighth) for p in ("E4", "F4")]
    graph.add_line(voice)
    graph.add_branch(melody[4], voice[0])

    singer, stint = Part(name="Voice"), Stint()
    graph.add_stint(singer, stint, clef)

    score = Score(title="Twinkle, Twinkle, Little Star", lyricist="Jane Taylor")
    graph.add_line_to_score(score, clef)
    graph.add_line_to_score(score, chords[0])
    graph.add_part_to_score(score, singer)

    reel = SyncLine(temporal_system=CLOCK_TIME, name="Reel 1")
    p5 = graph.sync_event(melody[0], reel, ClockDuration.from_seconds(5))
    p9 = graph.sync_event(melody[4], reel, ClockDuration.from_seconds(9))
    p9.name = "door slams"
    p9.description = "the front door, off screen"
    p12 = graph.create_sync_point(reel, ClockDuration.from_seconds(12))

    return SimpleNamespace(
        graph=graph,
        clef=clef,
        melody=melody,
        chords=chords,
        syllables=syllables,
        verse=verse,
        staccato=dot,
        slur=arc,
        voice=voice,
        singer=singer,
        stint=stint,
        score=score,
        reel=reel,
        points=(p5, p9, p12),
    )


@pytest.fixture
def twinkle() -> SimpleNamespace:
    return build_twinkle()
