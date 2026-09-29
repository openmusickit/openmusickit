"""The real-music fixtures in `tests/scores/`, one entry per directory.

Each fixture is a score as some notation program exported it,
kept byte-for-byte under its distributed name
(so paths here contain spaces, commas and parentheses;
tests never parse them, they read them from the registry).
The `SOURCE.md` beside each file records provenance and license.

An entry pins the facts a test can check without a reader
(the part names, the measure count),
names the features the file exercises,
and, once the MusicXML reader exists,
the warnings the reader is expected to raise on it
and the canonical-comparison differences accepted for now
(`_plans/musicxml.md` §8 and §9).
A fixture whose XML is wrong relative to its own page
also has a `corrected` companion, an edited copy
whose every edit is listed in its `SOURCE.md`;
the original stays as it was distributed.

>>> FIXTURES["mozart-string-quartet-k464-mvt3"].parts
('Violin 1', 'Violin 2', 'Viola', 'Violoncello')
>>> [slug for slug, fixture in FIXTURES.items() if fixture.musicxml is None]
['red-river-valley-chords']
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

SCORES_DIR = Path(__file__).parent


@dataclass(frozen=True)
class ScoreFixture:
    slug: str
    exporter: str
    category: str
    parts: tuple[str, ...]
    measures: int
    features: frozenset[str]
    musicxml: Path | None = None
    corrected: Path | None = None
    pdf: Path | None = None
    extras: tuple[Path, ...] = ()
    expected_warnings: tuple[str, ...] = ()  # substrings; every warning matches one, each occurs
    known_differences: tuple[str, ...] = ()
    shape: Mapping[str, int] = field(default_factory=dict)  # what the reader builds, pinned

    @property
    def directory(self) -> Path:
        return SCORES_DIR / self.slug

    @property
    def files(self) -> tuple[Path, ...]:
        """Every file the entry names, for existence checks."""
        named = (self.musicxml, self.corrected, self.pdf, *self.extras)
        return tuple(path for path in named if path is not None)


def _fixture(slug: str, **fields) -> ScoreFixture:
    """Builds an entry with its paths resolved under the fixture's directory."""
    directory = SCORES_DIR / slug
    for key in ("musicxml", "corrected", "pdf"):
        if fields.get(key) is not None:
            fields[key] = directory / fields[key]
    fields["extras"] = tuple(directory / name for name in fields.get("extras", ()))
    fields["features"] = frozenset(fields.get("features", ()))
    return ScoreFixture(slug=slug, **fields)


FIXTURES: dict[str, ScoreFixture] = {
    fixture.slug: fixture
    for fixture in (
        _fixture(
            "bach-art-of-fugue-bwv1080-contrapunctus-19",
            exporter="Sibelius 25.7 (MusicXML 3.0)",
            category="J. S. Bach, four-voice fugue in open score",
            parts=("P1", "P2", "P3", "P4"),
            measures=288,
            features={
                "part-group",
                "ties",
                "slurs",
                "grace",
                "wedges",
                "dynamics",
                "words",
                "metronome",
                "cut-time",
                "alto-clef",
            },
            expected_warnings=(
                "minted mark",
                "rests whose <type> and <duration> disagree",
                "slur 2 left open",
                "gradual tempo word 'rit.'",
            ),
            shape={
                "lines": 4,
                "chord_lines": 0,
                "parts": 4,
                "groups": 0,
                "branches": 0,
                "notes": 3996,
                "divisions": 1152,
                "markings": 323,
                "spanners": 1105,
                "ties": 307,
                "slurs": 553,
                "lyric_lines": 0,
                "chords": 0,
                "grid_points": 289,
                "pins": 1156,
            },  # fmt: skip
            musicxml="PMLP5843-fuga_4_soggetti_riemann.mxl",
            pdf="PMLP5843-fuga_4_soggetti_riemann.pdf",
        ),
        _fixture(
            "charleston-mack-johnson",
            exporter="MuseScore 4.7.4 (MusicXML 4.0; our own export of the .mscz)",
            category="voice, piano and chord symbols",
            parts=("Voice", "Piano 2"),
            measures=57,
            features={
                "staves",
                "voices",
                "hidden-staff",
                "harmony",
                "lyrics",
                "extend",
                "repeats",
                "endings",
                "ties",
                "slurs",
                "arpeggio",
                "wedges",
                "grace",
                "metronome",
                "words",
                "cut-time",
            },
            expected_warnings=(
                "minted mark",
                "ties with one start and two ends",
                "<ending> brackets",
            ),
            shape={
                "lines": 5,
                "chord_lines": 1,
                "parts": 2,
                "groups": 2,
                "branches": 26,
                "notes": 976,
                "divisions": 247,
                "markings": 122,
                "spanners": 311,
                "ties": 234,
                "slurs": 58,
                "lyric_lines": 1,
                "chords": 58,
                "grid_points": 58,
                "pins": 174,
            },  # fmt: skip
            musicxml="Charleston.musicxml",
            pdf="IMSLP1058462-PMLP1385673-Charleston.pdf",
            extras=("IMSLP1058463-PMLP1385673-Charleston.mscz",),
        ),
        _fixture(
            "croft-o-god-our-help",
            exporter="Capella via CapToMusic 2.10 (MusicXML 2.0)",
            category="SATB hymn, six stanzas",
            parts=(" ", " ", ""),
            measures=10,
            features={
                "voices",
                "lyrics",
                "verses",
                "pickup",
                "split-measure",
                "part-group",
                "hidden-part",
                "breath-as-words",
                "wrong-syllabic",
            },
            expected_warnings=("minted mark",),
            shape={
                "lines": 3,
                "chord_lines": 0,
                "parts": 3,
                "groups": 0,
                "branches": 2,
                "notes": 122,
                "divisions": 48,
                "markings": 7,
                "spanners": 0,
                "ties": 0,
                "slurs": 0,
                "lyric_lines": 6,
                "chords": 0,
                "grid_points": 11,
                "pins": 33,
            },  # fmt: skip
            musicxml="AMNS_99_St_Anne_Harmony.mxl",
            corrected="AMNS_99_St_Anne_Harmony.corrected.musicxml",
            pdf="AMNS_99_St_Anne_Harmony.pdf",
        ),
        _fixture(
            "moonlight-gaze-big-band",
            exporter="MuseScore 2.1 (MusicXML 3.0)",
            category="big band arrangement",
            parts=(
                "Piano",
                "Acoustic Guitar",
                "Acoustic Bass",
                "Drumset",
                "Alto Saxophone 1",
                "Alto Saxophone 2",
                "Tenor Saxophone 1",
                "Tenor Saxophone 2",
                "Baritone Saxophone",
                "Trumpet",
                "Trumpet 2",
                "Trumpet 3",
                "Trumpet 4",
                "Trombone 1",
                "Trombone 2",
                "Trombone 3",
                "Trombone 4",
                "Bass Trombone",
            ),
            measures=85,
            features={
                "staves",
                "voices",
                "unpitched",
                "transpose",
                "tuplets",
                "repeats",
                "endings",
                "ties",
                "fermata",
                "glissando",
                "wedges",
                "key-change",
                "metronome",
                "percussion-clef",
                "x-noteheads",
            },
            expected_warnings=("minted mark", "<ending> brackets"),
            shape={
                "lines": 26,
                "chord_lines": 0,
                "parts": 25,
                "groups": 2,
                "branches": 32,
                "notes": 3543,
                "divisions": 2210,
                "markings": 24,
                "spanners": 568,
                "ties": 454,
                "slurs": 0,
                "lyric_lines": 0,
                "chords": 0,
                "grid_points": 86,
                "pins": 1548,
            },  # fmt: skip
            musicxml="Moonlight_Gaze_Big_Band.xml",
            pdf="Moonlight_Gaze_Big_Band-Score_and_Parts.pdf",
            extras=("Moonlight_Gaze_Big_Band.mscx", "Moonlight_Gaze_Big_Band.mid"),
        ),
        _fixture(
            "mozart-string-quartet-k464-mvt3",
            exporter="MuseScore 3.6.2 (MusicXML 3.1)",
            category="string quartet movement",
            parts=("Violin 1", "Violin 2", "Viola", "Violoncello"),
            measures=203,
            features={
                "part-group",
                "repeats",
                "endings",
                "tuplets",
                "grace",
                "ties",
                "slurs",
                "staccato",
                "trill",
                "dashes",
                "words",
                "key-change",
                "pickup",
                "implicit-measures",
                "alto-clef",
            },
            expected_warnings=("minted mark", "<ending> brackets"),
            shape={
                "lines": 4,
                "chord_lines": 0,
                "parts": 4,
                "groups": 0,
                "branches": 0,
                "notes": 3707,
                "divisions": 812,
                "markings": 544,
                "spanners": 876,
                "ties": 104,
                "slurs": 724,
                "lyric_lines": 0,
                "chords": 0,
                "grid_points": 204,
                "pins": 816,
            },  # fmt: skip
            musicxml="sq7078259.mxl",
            pdf="sq7078259.pdf",
            extras=("sq7078259.mscx",),
        ),
        _fixture(
            "palestrina-tu-es-petrus",
            exporter="Sibelius 7.5.1 (MusicXML 3.0)",
            category="six-voice Renaissance polyphony",
            parts=(
                "CANTUS (Alto)",
                "QUINTUS (Alto)",
                "ALTUS (Tenor)",
                "TENOR (Bari-tenor)",
                "SEXTUS (Bass)",
                "BASSUS (Bass)",
            ),
            measures=84,
            features={
                "part-group",
                "lyrics",
                "extend",
                "ties",
                "fermata",
                "treble-8-clef",
                "words",
                "non-integer-lyric-numbers",
            },
            expected_warnings=("minted mark 'Prima pars'",),
            shape={
                "lines": 6,
                "chord_lines": 0,
                "parts": 6,
                "groups": 0,
                "branches": 0,
                "notes": 1345,
                "divisions": 504,
                "markings": 7,
                "spanners": 55,
                "ties": 55,
                "slurs": 0,
                "lyric_lines": 6,
                "chords": 0,
                "grid_points": 85,
                "pins": 510,
            },  # fmt: skip
            musicxml="Pal-petdwn5.mxl",
            pdf="Pal-petdwn5.pdf",
            extras=("Pal-petdwn5.sib", "Pal-petdwn5.mid"),
        ),
        _fixture(
            "red-river-valley-chords",
            exporter="plain text (GuitarMan)",
            category="chords-over-lyrics text chart",
            parts=(),
            measures=0,
            features={"text-chart"},
            extras=("red_river_valley.txt", "LICENSE-guitarman.txt"),
        ),
        _fixture(
            "schubert-allegretto-d915",
            exporter="MuseScore 2.1 (MusicXML, no version attribute)",
            category="solo piano",
            parts=("Piano",),
            measures=130,
            features={
                "staves",
                "voices",
                "pedal",
                "wedges",
                "ties",
                "partial-ties",
                "slurs",
                "fermata",
                "fingering",
                "staccato",
                "accent",
                "tenuto",
                "metronome",
                "words",
                "key-change",
                "clef-change",
                "repeats",
                "pickup",
                "hidden-rests",
                "hidden-tempi",
                "cross-voice-ties",
            },
            expected_warnings=("gradual tempo word",),
            shape={
                "lines": 2,
                "chord_lines": 0,
                "parts": 1,
                "groups": 1,
                "branches": 99,
                "notes": 1258,
                "divisions": 269,
                "markings": 214,
                "spanners": 387,
                "ties": 94,
                "slurs": 220,
                "lyric_lines": 0,
                "chords": 0,
                "grid_points": 0,
                "pins": 0,
            },  # fmt: skip
            musicxml="Schubert_-_Allegretto_in_C_Minor_D.915.mxl",
            corrected="Schubert_-_Allegretto_in_C_Minor_D.915.corrected.musicxml",
            pdf="PMLP07743-Schubert_-_Allegretto_in_C_Minor_D.915.pdf",
            extras=("Schubert_-_Allegretto_in_C_Minor_D.915.mscz",),
        ),
        _fixture(
            "second-line-joe-avery",
            exporter="Sibelius 19.5 (MusicXML 3.0)",
            category="jazz lead sheet with slash comping",
            parts=("P1",),
            measures=25,
            features={"harmony", "slash", "measure-repeat", "repeats", "endings", "words"},
            expected_warnings=(
                "minted mark 'Send-off'",
                "<ending> brackets",
                "measure-repeat (%) bars",
            ),
            shape={
                "lines": 2,
                "chord_lines": 1,
                "parts": 1,
                "groups": 0,
                "branches": 0,
                "notes": 106,
                "divisions": 26,
                "markings": 5,
                "spanners": 2,
                "ties": 0,
                "slurs": 0,
                "lyric_lines": 0,
                "chords": 10,
                "grid_points": 0,
                "pins": 10,
            },  # fmt: skip
            musicxml="SECOND LINE, (THE ORIGINAL) (JOE AVERY BLUES).xml",
            pdf="SECOND LINE, (THE ORIGINAL) (JOE AVERY BLUES).pdf",
            extras=("SECOND LINE, (THE ORIGINAL) (JOE AVERY BLUES).sib",),
        ),
        _fixture(
            "tchaikovsky-swan-lake-suite-op20a-no1",
            exporter="Dorico 5.1 (MusicXML 4.0)",
            category="orchestral movement",
            parts=(
                "Flute I",
                "Flute II",
                "Oboe I",
                "Oboe II",
                "Clarinet (A) I",
                "Clarinet (A) II",
                "Bassoon I",
                "Bassoon II",
                "Horn (F) I",
                "Horn (F) II",
                "Horn (F) III",
                "Horn (F) IV",
                "Trumpet (F) I",
                "Trumpet (F) II",
                "Tenor Trombone I",
                "Tenor Trombone II",
                "Bass Trombone",
                "Tuba",
                "Timpani",
                "Harp",
                "Violin I",
                "Violin II",
                "Viola",
                "Violoncello",
                "Contrabass",
            ),
            measures=70,
            features={
                "transpose",
                "tuplets",
                "nested-tuplets",
                "tremolo",
                "staves",
                "rehearsal",
                "wedges",
                "fermata",
                "ties",
                "slurs",
                "key-change",
                "words",
                "common-time",
                "tenor-clef",
            },
            expected_warnings=("gradual tempo word", "minted mark 'espress.'"),
            shape={
                "lines": 26,
                "chord_lines": 0,
                "parts": 25,
                "groups": 1,
                "branches": 41,
                "notes": 4559,
                "divisions": 1874,
                "markings": 676,
                "spanners": 191,
                "ties": 42,
                "slurs": 104,
                "lyric_lines": 0,
                "chords": 0,
                "grid_points": 71,
                "pins": 1775,
            },  # fmt: skip
            musicxml="Swan Lake Suite Op20a - Full score - 01 Flow 1.mxl",
            pdf="PMLP59697-Swan_Lake_Suite_Op20a-pp3-14.pdf",
        ),
    )
}
