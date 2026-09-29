# MusicXML import and export

Status: **drafted 2026-09-29; the decisions in §3 were confirmed with the
developer the same day; nothing started.**
Stage 5 (part order) is a gate that needs its own design session
before the writer can be built.

Written for two readers:
the developer (to approve and to decide the pre-plans in §7),
and the agents who will execute the stages in later sessions
without this conversation's context.
Every count below comes from running code over the fixtures on 2026-09-29;
the scripts were throwaway and are not in the repo.

## 1. Context

`tests/scores/` holds ten real scores
(committed as `55095d8`; each directory has a `SOURCE.md` with provenance
and license), chosen to cover about 90% of ordinary WSMN scores:

| slug | what | MusicXML from |
|---|---|---|
| `schubert-allegretto-d915` | solo piano, 6/8, pedal, 2nd voices | MuseScore 2.1 |
| `mozart-string-quartet-k464-mvt3` | quartet, repeats, triplets, graces | MuseScore 3.6 |
| `tchaikovsky-swan-lake-suite-op20a-no1` | 25-part orchestra, transposing, tremolos | Dorico 5.1 (MusicXML 4.0) |
| `bach-art-of-fugue-bwv1080-contrapunctus-19` | 4-voice fugue, open score | Sibelius 25.7 |
| `croft-o-god-our-help` | SATB hymn, 6 stanzas, pickup | Capella / CapToMusic (MusicXML 2.0) |
| `palestrina-tu-es-petrus` | 6-voice polyphony, lyrics in every voice | Sibelius 7.5 |
| `second-line-joe-avery` | lead sheet, chords, slashes, endings, % bars | Sibelius 19.5 |
| `charleston-mack-johnson` | voice + piano + chords, hidden staff | MuseScore 4.7 (our own export) |
| `moonlight-gaze-big-band` | 18 parts, drum kit, Bb/Eb transpositions | MuseScore 2.1 |
| `red-river-valley-chords` | chords-over-lyrics text; no MusicXML | -- |

Six exporters and three MusicXML versions, which is the point:
the importer must read what notation programs actually write.

What the model already has for an importer is listed in
`_plans/completed/clef-score-text.md`, Appendix A
(the gap analysis of 2026-09-24, ranked by how often a page hits each gap).
Since then clefs, score metadata, free text and rehearsal marks were built;
still open from that list: control flow, gradual tempo, the tie rule,
per-tone attachments, written-vs-sounding pitch, part order and brackets,
line identity, context in force, serialization.

Discovery for this plan, 2026-09-29:

- An element inventory over all ten files
  (which notations, directions, bar lines, harmonies, lyric numbers,
  tuplet ratios, transpositions and clefs each uses).
- Two probes that built `OmkGraph`s from four fixtures with the current model
  (hymn and lead sheet; piano and quartet) and reported, per file,
  what had a home, what was approximate, what had none,
  and which exporter quirks a robust importer must survive.
  Two imports of one file compare `is_equivalent` in well under a second
  (Mozart: 5,943 nodes, 2 s to build), so graph round trips are a workable test.

The findings are folded into §5 (the mapping), §7 (the pre-plans)
and §8 (fixture flaws).

## 2. Principles: the balance between ideal objects and a robust importer

- **Faithful.** The importer records what the file asserts and nothing more.
  It never derives musical content the file does not contain
  (no chord durations, no synthesized context events on lines that lack them,
  no rests for gaps).
  Presentation (layout, stems, beams, positions, fonts, colours) is dropped.
- **Tolerant.** Anything a mainstream exporter produces is the importer's job:
  measure `0` without `implicit="yes"`, a bar split at a line break,
  voice numbers reused for unrelated fragments, held notes re-voiced across
  a bar line, `<forward>` gaps, hidden parts and rests, `<syllabic>` flags
  that contradict the text, non-integer lyric numbers, blank part names,
  `<staves>` after `<key>` inside `<attributes>`, breath marks typed as
  `<words>,</words>`. None of that is normalized away in the fixtures (§8).
- **Loud about loss.** Every musical fact the importer cannot place raises an
  `OmkWarning` naming the element and the measure, and the corpus tests pin
  the warnings each fixture is expected to raise.
  Presentation is dropped silently; that is not loss.
- **Reversible.** Every mapping in §5 states its inverse.
  What the exporter needs and the model cannot hold goes in
  `event.meta["musicxml"]`, a small documented dict (§5.11) that OMK core
  never reads.
- **Positions are `Fraction`s.** `relative_onset` returns a notation-spelled
  `TiedDuration` whose spelling depends on the path
  (`[1/1, 1/4]` one way, `[1/4, 1/1]` the other; 160 members over a
  400-note line).
  The reader and writer keep a cursor in `Fraction`s of a whole note and use
  `rational_length` whenever they consult the graph.

## 3. Decisions (confirmed 2026-09-29)

1. **Voices are runs, mapped to branches.** Each contiguous run of one
   `<voice>` number on a staff (contiguous across measures, broken by a
   `<forward>` or a measure where the number is absent) becomes its own line,
   branched from the main-line event at its onset
   (`add_branch`, with a displacement when the run starts mid-event).
   The main line of a staff is voice 1 (the lowest voice number present).
   The voice number goes to meta.
   This settles the percussion plan's "Branch may be scaled back" note:
   it stays.
2. **Every top-level line carries its own context events.**
   Key, meter, clef and tempo go on the main line of each staff;
   a two-staff part gets two `ModalContextEvent`s per key change.
   Branched lines carry none and are read by their parent's context.
   The writer emits `<key>`/`<time>` once per part when the staves agree
   and with `number=` when they differ.
3. **A drum kit is a `LineGroup` with one line per `<score-instrument>`**,
   each with a `PercussionPart(name=instrument-name)`;
   the tone is the plain `hit` (a stroke or relative pitch needs a drum map,
   which does not exist), with the display step/octave and notehead in meta.
   This is the kit shape of `_plans/completed/percussion.md` §2.1.
4. **`<harmony>` becomes a `ChordEvent` with `duration=None`,**
   on one chord line per part, each chord pinned (`add_simultaneous`) to the
   event at its onset (an `<offset>` becomes the pin's displacement).
   No duration is derived.
5. **Part order and `<part-group>` get their own pre-plan (§7, P1) before the
   writer.** The reader stores the `<part-list>` index and group in
   `Part.meta["musicxml"]` as a stopgap; the writer stage does not start until
   P1 is built, and the stopgap is removed then.
6. **Control flow: record the page, defer the jumps.** Repeat dots are already
   in the bar-line shape. An `<ending>` becomes a `MarkSpanner` over the
   ending's events with a minted `Mark(name="ending 1", kind=NAVIGATION,
   attachment_mode=SPAN)`; a `<measure-repeat>` bar becomes a zero-tone
   `NoteEvent` of the bar's length marked `simile`; both warn.
   The control-flow pre-plan (P2) replaces these.
7. **Spanners may be open-ended:** `add_spanner(spanner, start, end=None)`
   means "to the end of the line", exactly as a `Stint` with no end.
   `una corda` with no `tre corde`, `rit.` with no end, a pedal to the last
   bar import as open spans.
8. **Ties are always two events joined by a `tie` `MarkSpanner`;**
   the importer never produces a `TiedDuration`.
   Evidence: 69 ties in two fixtures cross a bar line, where a
   `DivisionEvent` sits in the NEXT chain, and 79 of Schubert's 94 ties are
   partial-chord ties. The writer splits any `TiedDuration` it meets into tied
   notes. Ties are matched by (staff, pitch), not voice.
9. **Per-tone attachments split the chord.** When tones of one `<chord>`
   differ in what is attached to them (a tie on one tone, a fingering on
   another), the event is partitioned by attachment signature: the largest
   class (ties broken by the lowest tone) stays on the main line and each
   other class becomes a single event branched at zero displacement,
   so every mark and spanner has an event of its own to attach to.
   The writer merges a zero-displacement branch whose events coincide in
   onset and duration with main-line events back into `<chord/>` notes.
   Presentational per-tone data (notehead, accidental display, stem) never
   triggers a split.
10. **Sounding pitch is what the graph holds** (already the developer's rule
    in `_plans/revisit.md`, "Transposition Complications").
    `<transpose>` is applied on the way in and recorded as
    `Stint.transposition` (every transposing part in the corpus is single
    staff); the permanent home is P5. `<octave-shift>` pitches are already
    sounding in MusicXML; the shift becomes an `ottava_alta`/`ottava_bassa`
    `MarkSpanner`.
11. **Fixtures stay raw, plus corrected companions.** Files and names are kept
    byte-for-byte; a registry describes each fixture and its known flaws;
    a fixture whose XML is wrong relative to its own page also gets a
    corrected copy, marked as edited (§8).
12. **The LLM idea becomes review artifacts only.** A script renders the
    exported score through local `mscore` beside the original PDF and writes
    the canonical diff; a human or an agent reviews those. No automated judge,
    no test depends on a model.
13. **API: `openmusickit.io.musicxml.read` / `write`**, with the existing
    `OmkGraph.from_file` / `import_file` stubs dispatching by suffix and an
    `export_file` counterpart added beside the JSON stubs.
    Standard library only (`xml.etree.ElementTree`, `zipfile`); no dependency.
14. **Full divisions, a bar grid for multi-part scores, and a sparse form
    for testing.**
    The reader places a `DivisionEvent` at every measure boundary in every
    line. When the Score has two or more Parts with music, it also builds a
    **bar grid**: a `SyncLine` in WSMN metrical time, named for the score,
    with a `SyncPoint` at the start and at every bar line, to which each
    part pins its head and its divisions (§5.2). The grid is the file's
    assertion that measure n is measure n in every part, made once and
    symmetrically, with no hub part; it is also where score-wide instants
    (rehearsal marks, segno and coda targets, section starts) will live
    when P2 designs them. A score with one Part gets no grid and no pins:
    a lead sheet's chord line is already pinned per chord and its lyric
    lines are attached by LYRIC edges, a piano's two staves are aligned by
    their group, and a solo line has nothing to line up with.
    Two graph operations produce the sparse form:
    `OmkGraph.remove_derivable_divisions(head)` strips the divisions a
    line's meter implies, leaving pickups, split bars, repeats and double
    bars, and `OmkGraph.remove_sync_line(sync_line)` removes a grid with
    its points and pins (§5.12).
    The writer derives both back, so `write(sparse)` must equal
    `write(full)` canonically for every fixture (§9.5): that is the test
    surface the sparse form exists for.

Small choices made here rather than asked, all reversible:
adjacent `:|` and `|:` at one boundary merge into one
`DivisionEvent(double_repeat)`; an explicit `<barline>regular` gives
`single_bar` and an absent `<barline>` gives `shape=None`, so the writer
knows which to emit;
a `<grace>` without `slash="yes"` is `on_beat=True`;
`<sound tempo>` with no `<metronome>` goes to meta, not a `TempoEvent`;
blank `<part-name>` gives `Part(name="")` (the id goes to meta);
`<words>` matching a `TempoTerm` alias becomes a `TempoEvent(term=...)`,
any other `<words>` a `Marking` with a minted `EXPRESSION` mark
(the clef-score-text decision); `<words>,</words>` is a `breath_mark`.

## 4. Package and API

```
src/openmusickit/io/__init__.py            # "Readers and writers for interchange formats."
src/openmusickit/io/musicxml/__init__.py   # read, write, canonicalize, compare
src/openmusickit/io/musicxml/reader.py     # _Reader: document -> OmkGraph
src/openmusickit/io/musicxml/writer.py     # _Writer: OmkGraph -> document
src/openmusickit/io/musicxml/tables.py     # name <-> symbol tables (marks, kinds, clefs, bar styles, note types)
src/openmusickit/io/musicxml/canonical.py  # canonicalize, compare, Difference
src/openmusickit/io/musicxml/container.py  # .mxl zip handling
```

`io/` may import from `systems/wsmn`: MusicXML *is* WSMN, so the layering
rule that keeps `objects/` and `graph/` system-free does not apply here.

```python
def read(source: str | Path | IO[bytes], graph_engine: GraphAdapter | None = None) -> OmkGraph:
    """The score in a MusicXML file (.musicxml, .xml or compressed .mxl) as a graph
    holding one Score. Raises MusicXmlError for a file that is not partwise MusicXML;
    warns (OmkWarning) for every musical fact it cannot place."""

def write(graph: OmkGraph, target: str | Path | IO[bytes], score: Score | None = None) -> None:
    """Writes `score` (the graph's only Score if None) as MusicXML 4.0 partwise;
    .mxl when the target name ends in .mxl. Raises UnexportableError, naming the node,
    for a graph outside the exportable subset (§6.1)."""
```

`errors.py` gains `MusicXmlError(OmkError, ValueError)` and
`UnexportableError(OmkError, ValueError)`.
`OmkGraph.from_file(f)` and `import_file(f)` dispatch on suffix
(`.musicxml`, `.xml`, `.mxl` → this module; `.json` stays `NotImplementedError`);
`OmkGraph.export_file(f)` is added beside `export_json_to_file` with the same
dispatch. `score-timewise` input raises `MusicXmlError`
(no exporter in the corpus writes it; converting is a later nicety).

`canonicalize(tree) -> tree` and `compare(a, b) -> list[Difference]` are
public because "did my export keep the music?" is a user question, not only a
test's (§9.5).

## 5. The mapping (reader), with each rule's inverse

Counts in parentheses are occurrences in the corpus, to show what is common.

### 5.1 Document and Score

- `<work-title>` (or `<movement-title>` when there is no work title) →
  `Score.title`; `<creator type=composer|lyricist|arranger>` → the fields;
  `<rights>` → `copyright`; `<work-number>` → `opus`.
  `<movement-number>`, `<movement-title>` (when not used as title),
  `<encoding>` software and date, `<source>` → `Score.meta["musicxml"]`.
  `<credit>` is dropped (it duplicates the above or is layout).
  A file with none of these (the hymn) gives a `Score` of `None`s;
  no heuristics over `<words>`.
- Inverse: fields → `<work>`/`<identification>`; the writer names itself in
  `<encoding><software>`.

### 5.2 Parts, staves, voices, groups, stints

- `<score-part>` → `Part(name=part-name)` (`PercussionPart` when the part's
  first clef is `percussion` or any note is `<unpitched>`).
  `<part-abbreviation>`, `<score-instrument>`, `<midi-*>`, `<instrument-sound>`
  and the `<part-list>` index → `Part.meta["musicxml"]` (stopgap for P1, P5).
  `<part-group>` start/stop → the same meta on each member Part.
- One staff, one voice → one line; `add_stint(part, Stint(), head)`.
- `<staves>` n (pre-scanned, since it follows `<key>` inside `<attributes>`) →
  `LineGroup(name=part-name)` of n lines (one per staff, `add_group`), and
  `add_performs(part, group)`. Each line head is also added to the Score
  (`add_line_to_score`), since a `LineGroup` cannot be a Score member.
- Voices → branches by decision 1. `<backup>`/`<forward>` are cursor
  arithmetic; a `<forward>` in voice 1 becomes a zero-tone `NoteEvent`
  (unspecified content, the documented meaning) with `meta.forward=True`;
  in any other voice it ends the run.
- Drum kit → decision 3; notes with no `<instrument>` on an unpitched staff go
  on one line named for the part.
- `<transpose>` → decision 10: written pitch + (diatonic, chromatic,
  octave-change) → sounding `TonalVector`; the interval → `Stint.transposition`
  (a `TonalVector` built from diatonic and chromatic, octave from
  octave-change). A transposing part with `<staves>` > 1 (none in the corpus)
  warns and stores the interval in the group's meta until P5.
- `<staff-details print-object="no">` (the hymn's rest-only part, Charleston's
  second voice staff) → imported; `meta.hidden=True` on the line head.
- Ensemble alignment (decision 14): when the Score has two or more Parts
  with music, a `SyncLine(temporal_system=WSMN_TEMPORAL, name=<title or
  "bars">)` is added to the Score (`add_sync_line_to_score`, a new
  membership beside lines and Parts, read back by `score_sync_lines`),
  with a point at offset zero and one at each bar line, offsets being the
  cursor position in whole notes (`MetricalDuration.from_length`; a
  `TiedDuration` is a fine offset). Each part pins the head of its first
  staff line to the origin point and each of that line's divisions to its
  bar's point (`sync_event`, so points are found or made in cursor order).
  Other staff lines of the part are aligned by its group; branches by
  their parents. Points thus number measures + 1, pins parts × (measures +
  1). A one-Part score gets no grid and no pins.
  `check_sync_alignment` on the result must be empty (§9.3).
- Inverse: parts in P1's order; staves from group membership; voices from
  branches, numbered per staff by overlap (a branch overlapping voice 1 gets
  2, and so on); `<transpose>` from `Stint.transposition` with pitches written
  back up.

### 5.3 Measures, divisions and bar lines

- Each `<measure>` boundary → a `DivisionEvent` in every line that has events
  on both sides of it (the main line always; a branch only where it crosses
  the boundary). Shape from the right `<barline>` of the measure before
  (`bar-style` → `single_bar`, `double_bar`, `final_bar`, dashed, etc.;
  `<repeat direction=backward>` adds the dots → `end_repeat`;
  a left `<barline>` with `<repeat forward>` on the next measure merges →
  `start_repeat` or `double_repeat`); no `<barline>` → `shape=None`.
  A left bar line on the first measure → a `DivisionEvent` at the head.
- `number`, `implicit`, `width` → `meta` on the division.
  A pickup and a split bar need nothing: the division arrives where the file
  puts it. Bar lengths are computed from content, never from `implicit`.
- **Measure lengths are checked across the score.** A measure's length in a
  part is the furthest cursor position any of its voices reaches; a main
  line that ends short of it is padded with a zero-tone `NoteEvent`
  (`meta.forward=True`, as for `<forward>`), so every line's bars sum to its
  part's. When two parts disagree on a measure's length the reader warns,
  naming the measure and both parts, and pads the shorter; the graph then
  holds what the notes say plus the file's own inconsistency as a warning.
  After this check the durations determine every downbeat on their own;
  the bar grid of decision 14 is the file's assertion of the same fact,
  recorded so that `check_sync_alignment` can hold the two against each
  other, not a mechanism the alignment depends on.
- `<ending>` → decision 6 (a `MarkSpanner` over the measure's events;
  `number` and `type` in meta). `<measure-repeat>` → decision 6.
  `<multiple-rest>` n → n whole-bar `Rest`s with divisions between them and
  `meta.multiple_rest=n` on the first.
- Inverse: divisions cut a line into `<measure>`s; a line with no
  `DivisionEvent` at all is cut by its `MeterEvent` (the division-event plan's
  rule: derived fills gaps) with a warning; `<divisions>` per part is the lcm
  of the denominators of every `rational_length` in it.

### 5.4 `<attributes>` → context events

- `<key fifths mode>` → `ModalContextEvent(Key.of(tonic, mode))` when a
  mode is given (tonic from fifths and mode), else
  `Key.from_signature(KeySignature.from_alts(fifths))`.
- `<time beats beat-type>` → `MeterEvent(time_signature(n, d))`;
  `"2+3"` → `additive_time_signature`; `symbol="common|cut"` → meta
  (no glyph constant yet; clef-score-text gap 26).
  A restated identical `<time>` (Capella at a system break) is still an
  event; equal restatements are kept, since the writer must reproduce them.
- `<clef sign line clef-octave-change>` → `ClefEvent(StaffClef(...))` on the
  staff's line (`number=` picks the staff; none means every staff).
- Per decision 2 each staff line gets its own copies; `<staff>` on a
  `<direction>` picks the line.
- Inverse: the writer tracks the context in force per line as it walks
  (P7 would replace this with `context_in_force`), and emits `<attributes>`
  when a context event is met, merging staves that agree.

### 5.5 Notes

- `<pitch step alter octave>` → `TonalVector((d, (chromatic + alter) % 12,
  octave - 4))`; a non-integer `<alter>` (microtone) warns and rounds.
  `<rest/>` → `Rest(duration)`; `<rest measure="yes">` or a rest without
  `<type>` → `MetricalDuration.from_length(<duration>/divisions/4)`.
- `<type>` + `<dot>`s → `MetricalDuration(1, 2**k, dots)` (breve, longa,
  maxima as `(2, 1)`, `(4, 1)`, `(8, 1)`); `<time-modification actual normal
  normal-type>` → `ratio=tuplet(actual, normal, base)` with the base from
  `normal-type` when present, else the note's type. Nested tuplets are what
  MusicXML gives cumulatively, so one ratio per note is exact.
  `<duration>` is cross-checked against the result (0 mismatches in 8,000
  notes across the probes); a mismatch warns and the notated value wins.
- `<chord/>` → the tone is added to the previous event, then decision 9 may
  split it.
- `<grace slash>` → `GraceDuration(nominal, on_beat=slash != "yes")`;
  `<cue/>` → meta.
- `<unpitched display-step display-octave>` → `PercussionTone()` (`hit`),
  display pitch and `<notehead>` in meta (decision 3).
- `<notehead>slash` with a pitch (the lead sheet's comping, 16) →
  `NoteEvent(tones=set())`, written pitch in meta.
- `print-object="no"` on a note or rest → kept, `meta.hidden=True`
  (MuseScore pads partial voices with 14 such rests in Schubert).
- Dropped: `<stem>`, `<beam>`, `<accidental>` (the alteration is in
  `<alter>`; courtesy accidentals are presentation), `<notehead>` other than
  slash, `<staff>` (recorded on the line head, and per event only where a
  voice changes staff mid-run: none in the corpus), positions.
- Inverse: `TonalVector` → step/alter/octave; duration → type/dots/
  time-modification with `<duration>` from `rational_length × divisions`;
  `GraceDuration` → `<grace>`; a zero-tone event with a slash pitch in meta →
  the slash note, without → `<forward>` when `meta.forward`, else a
  `<rest>` with a warning that unspecified content was written as silence.

### 5.6 Ties, slurs, other notations

- `<tie>`/`<tied>` → decision 8: `MarkSpanner(tie)` from the start event to
  the stop event, matched by (staff, pitch) in order; an unmatched start warns.
  Partial-chord ties → decision 9.
- `<slur number>` → `MarkSpanner(slur)` matched by number per part
  (numbers reach 4 in Schubert; ends may lie on different lines after
  re-voicing, which `add_spanner` allows).
- `<articulations>`, `<ornaments>`, `<technical>`, `<fermata>`,
  `<arpeggiate>`, `<glissando>`/`<slide>` (span) → `Marking` / `MarkSpanner`
  through `tables.MARKS` (MusicXML element or `<other-*>` text ↔ `Mark`
  symbol, resolved through `Mark.aliases`). An element with no entry mints
  `Mark(name=element, kind=OTHER)` and warns, so nothing is dropped silently.
  `<tremolo>` count (508 in Tchaikovsky), `<fingering>` beyond the symbols,
  `<accidental-mark>` → `meta` on the Marking (P8).
- `<tuplet>` start/stop, `bracket`, `show-number` → meta on the first member
  (P6).
- Inverse: the tables backwards; a `TiedDuration` event is written as tied
  notes; spanners → start/stop pairs with numbers assigned by nesting.

### 5.7 Directions

A `<direction>` has a cursor position and an optional `<staff>`, not a host
note. The reader attaches it to the main-line event of that staff whose onset
is the cursor (or, for a stop, whose offset is), and when the cursor falls
inside an event, to that event with the offset in `meta.offset` (a
`Fraction`); every direction in the four probed files landed on an onset or
offset exactly.

- `<dynamics>` → `Marking(mark)` through the table (p, pp, f, fp, fz, sf, sfz,
  ...; `<other-dynamics>` text minted).
- `<wedge crescendo|diminuendo … stop>` → `MarkSpanner(crescendo|decrescendo)`;
  `<words>cresc.</words>` + `<dashes>` → `MarkSpanner(cresc)` (the model keeps
  the text/hairpin distinction: `cresc` vs `crescendo`).
- `<pedal start|stop|change>` → `MarkSpanner(sustain_pedal)`; `change` ends
  one span and starts the next; a start with no stop is open (decision 7).
- `<octave-shift>` → `MarkSpanner(ottava_alta|ottava_bassa)`; pitches are
  already sounding (decision 10).
- `<metronome beat-unit per-minute>` → `TempoEvent(tempo=Tempo(n, beat))`;
  `<words>` at the same position that name a `TempoTerm` → the same event's
  `term`. `<sound tempo>` alone → meta only.
- `<words>` naming a gradual change (`rit.`, `rall.`, `accel.`, `calando`,
  `poco rit.`) → open `MarkSpanner` with the P3 marks once they exist;
  until then a `Marking` with a minted `EXPRESSION` mark, warning that the
  span has no end.
- `<rehearsal>` → `Marking(Mark(name=text, kind=REHEARSAL))`;
  `<segno>`, `<coda>` → the marks, on the division at that position when
  there is one, else on the event; `<sound dacapo|dalsegno|tocoda|fine>` →
  the navigation words as marks (jumps are P2).
- Any other `<words>` → `Marking(Mark(name=text, kind=EXPRESSION))`;
  `<words>,</words>` → `breath_mark` on the preceding event (the hymn, 2).
- Dropped: `placement`, `<sound dynamics>` (222 in Mozart), positions,
  `<other-direction/>` wrappers.
- Inverse: markings on an event → `<direction>` before the note (dynamics,
  words, rehearsal, tempo); spanners → start/stop directions; a
  `Marking` whose mark is in the notations table → `<notations>` instead.

### 5.8 Lyrics

- `<lyric number>` per (part, staff, voice run, number) → one syllable line
  (`add_lyrics`) with `LyricSection(section_type="verse",
  section_number=n, section_name=<name>, language=xml:lang)`.
  Non-integer numbers (Sibelius `part1verse1`) take the trailing integer.
- Syllables are grouped into `Word`s by `<syllabic>` begin/middle/end/single
  in order, treating the flags as advisory: a run is closed when `end` or
  `single` is seen or when the next syllable is `begin`/`single`, so the
  hymn's 52 wrong flags cannot reorder or lose text. `Word([...])` is built
  directly, never `Word.from_string` (a leading `'` or `,` in sung text is
  text, not a stress mark).
- Each `<lyric>` on a note → `connect_lyric_to_object(syllable, note)`;
  `zip_lyrics_to_objects` is not used (the file says where syllables begin).
  `<extend>` → nothing (a melisma is the absence of an edge);
  `<elision>` → two syllables begun on one note (two LYRIC edges).
  `<humming>`, `<laughing>`, `end-line`/`end-paragraph` → meta.
- Inverse: LYRIC edges → `<lyric number>` with `<syllabic>` from
  `placement`; `<extend>` on a syllable that is followed, before the next
  syllable begins, by at least one sung note; several syllables on one note →
  `<elision>`.

### 5.9 Harmony

- `<harmony>` → decision 4; `<root>` → `TonalVector`; `<kind>` →
  `ChordType` through `tables.KINDS` (the MusicXML kind list is 33 names;
  every kind in the corpus is major, minor, dominant, minor-seventh,
  minor-sixth, diminished, dominant-ninth); `<degree>` adds/alters/subtracts
  → a `ChordType` built from the base type's intervals with the degree
  applied and the MusicXML kind text as its name; `<bass>` →
  `Chord(root, tones, bass=...)` (an inversion when the bass is a chord
  tone); `kind="none"` (N.C.) → warns and skips until P9;
  `<kind text>` and `<frame>` → meta.
- Inverse: the chord line's events → `<harmony>` at the pinned position
  (`<offset>` from a displacement).

### 5.10 Ignored outright

`<defaults>`, `<print>`, `<page-layout>`, `<system-layout>`,
`<staff-layout>`, `<appearance>`, fonts, colours, `default-x/y`,
`relative-x/y`, `<credit>`, `<supports>`, `<midi-device>`, `<bookmark>`,
`<link>`, `<figured-bass>` (warns: OMK Baroque is a planned extension),
`<staff-details>` other than `print-object`.

### 5.11 The `meta["musicxml"]` schema

One dict per node, only present when non-empty; keys are strings, values are
plain Python (int, str, bool, `Fraction`, tuple), so JSON serialization can
carry them later. Keys used, by node:

- `Score`: `movement_number`, `movement_title`, `encoding`, `source`.
- `Part`: `id`, `index`, `abbreviation`, `group`, `instruments`, `midi`.
- line head event: `staff`, `voice`, `hidden`.
- `DivisionEvent`: `number`, `implicit`, `width`, `ending`, `measure_repeat`,
  `multiple_rest`, `time_symbol`.
- `NoteEvent`: `forward`, `hidden`, `cue`, `slash_pitch`, `display`
  (unpitched step/octave), `notehead`, `instrument`, `tuplet`, `staff`
  (only when it differs from the line's).
- `Marking` / `MarkSpanner`: `offset`, `tremolo`, `fingering`,
  `accidental_mark`, `ending`, `element` (for a minted mark, the source
  element name).
- `TempoEvent`: `sound_tempo`.
- `ChordEvent`: `kind_text`, `frame`.

The writer reads these; nothing in `objects/`, `graph/`, `values/` or
`systems/` ever does. Each key is documented in `reader.py`'s module
docstring and dropped from this list when a pre-plan gives it a real home.

### 5.12 The sparse form: `remove_derivable_divisions` and `remove_sync_line`

Two graph operations in `graph/graph.py`, not import options: `read` has
one behaviour, full fidelity, and the sparse graph is derived from it.

`OmkGraph.remove_sync_line(sync_line)` is the undo the `add_sync_line`
docstring spells out (each pin, then each point, then the line) as one
method, plus the Score membership; it returns nothing, since the reader
rebuilds a grid from divisions and the writer never needs one.

Walking the line from `head` with the `MeterEvent` in force, a division is
*derivable* when its onset lies exactly one meter's length after the
previous boundary (the previous division, or the head when there is none)
and its `shape` is `None` or `single_bar`. Derivable divisions are removed;
everything else stays: a pickup (the first division arrives early and the
count restarts from it), a split bar, a division whose shape carries
repeats, a double or final bar, and any division on a line with no meter.
A mark on a removed division (a fermata on a bar line) and a pin to it move
to the first event after it, which has the same onset; the method returns
the removed divisions so a caller can put them back.
Branched lines are handled by the caller, line by line.

The writer's inverse is the rule of `_plans/completed/division-event.md`:
explicit divisions are boundaries, and between them the meter fills the
gaps; parts are aligned by `onsets` from their heads, and a grid, when one
is present, is checked against that alignment rather than used in its
place (a disagreement is an `UnexportableError` naming the bar). So
`write(sparse)` is the same document as `write(full)`, up to
canonicalization, and §9.5 asserts it on every fixture.
`objects/sync_line.py`'s module docstring gains a paragraph on metrical
grids as a second use of the class.

## 6. The writer

### 6.1 The exportable subset

`write` accepts a graph and a `Score` such that:

- every top-level line of the Score, and every branch under them, is a NEXT
  chain without cycles;
- every event's duration is a WSMN `MetricalDuration`, `TiedDuration`,
  `GraceDuration` or `ZeroDuration` (a `ClockDuration` or `None` on a
  `NoteEvent` raises `UnexportableError` naming the event; a `None` on a
  `ChordEvent` is expected);
- every tone is a `TonalVector` with an octave, a `SilentTone` or a
  `PercussionTone`;
- every Part of the Score performs a Stint over a Score line or a
  `LineGroup` whose members are Score lines;
- lines of one Part are timing-related (a group, or pins) so that a
  `<backup>` can be computed; two lines with no relative onset raise.

Everything else on the graph (sync lines, other Scores, annotations that are
not `Marked`) is ignored with a warning naming what was left out.

### 6.2 Algorithm

1. Parts in P1's order (until then, `meta.index`); each Part's lines are
   its group's members (staves, in `meta.staff` order) or its stint's line.
2. Per line, the segments between `DivisionEvent`s are the measures
   (derived from the `MeterEvent` when a line has none, with a warning);
   measures of the lines of one part are aligned by `onsets(head)`
   in `Fraction`s, and a part whose lines disagree on where a measure
   ends raises `UnexportableError`.
3. `<divisions>` per part = lcm of denominators.
4. Per measure: `<attributes>` when a context event is met (per staff
   `number=` where staves differ); voice 1 events, then `<backup>` and each
   branch overlapping the measure as the next voice number; `<forward>` for
   gaps in a branch; chords rebuilt by decision 9's inverse; ties from `tie`
   spanners; slurs and other spanners numbered by nesting; markings as
   `<notations>` or `<direction>` per the tables, at the event's onset
   (`meta.offset` restored); lyrics per §5.8; harmonies from the chord line
   at their pinned onsets; the drum kit's lines interleaved back onto one
   staff with `<instrument>` and display pitches from meta.
5. `Stint.transposition` → `<transpose>`, pitches written back to written
   pitch.
6. Serialize as MusicXML 4.0 partwise with the DOCTYPE, indented; `.mxl`
   through `container.py`.

## 7. Domain pre-plans

Each is a short statement for a future design session
(the developer said these get their own plans);
"v1" is what this plan's importer does meanwhile.

**P1. Part order and bracketing on a Score** (gate before stage 6).
`Score` CONTAINS edges are unordered; `score_parts` returned a quartet
reversed; `<part-group>` (bracket, brace, `group-barline`) has no home;
a piano `LineGroup` cannot be a Score member, so its lines are named
individually. `_plans/revisit.md` asks for an edge-based answer rather than an
ordered id list. Candidates to weigh: an `index` on the Score's CONTAINS
edge; a `PartGroup(Spanner)` over first and last Part with a symbol;
letting a `LineGroup` be a Score member. v1: `Part.meta["musicxml"]`
`index` and `group`.

**P2. Control flow.** Repeats (dots exist), `<ending>` (48 in Mozart, 216 in
the big band), repeat counts, `D.C.`/`D.S.`/`fine`/`coda` jumps (marks
exist), `<measure-repeat>` (7), `<multiple-rest>`. The division-event plan
already fixed the policy (explicit wins, derived fills gaps, mismatch warns)
and left the objects undesigned. REFERENCES / VARIATION_OF edges are declared
and unused and could carry "same as bar n". The bar grid of decision 14
gives jump targets, rehearsal marks and section starts a score-wide instant
to sit on (a named `SyncPoint`), which the design should weigh.
v1: decision 6.

**P3. Gradual tempo marks.** `rit.` (×8 in three fixtures), `poco rit.`,
`accel.`, `rall.`, `calando`, `stringendo`, `più mosso`. The revisit entry's
DEV note already chose the shape: SPAN marks (`MarkType.TEMPO` or reuse
`EXPRESSION`) in `scoring/symbols.py`, playback semantics later.
With decision 7 they can be open-ended. Small enough to do in stage 2 if the
developer approves the mark names; otherwise v1 is a point `Marking`.

**P4. Per-tone attachments.** Decision 9 (split the chord) is the importer's
rule; whether the model wants a per-tone payload instead is worth revisiting
once exported piano scores have been reviewed. No v1 work beyond decision 9.

**P5. Instrument identity and transposition on `Part`** (revisit entry).
`<score-instrument>`, `<instrument-sound>`, `<part-abbreviation>`, `<midi-*>`
appear in every real part list; `<transpose>` on 9 + 10 parts in two
fixtures, including octave-only (`d0 c0 o-1`, guitar, bass, contrabass).
Whether `Part` gains `transposition` and `abbreviation`, or an `Instrument`
value, and how a transposing multi-staff part is read. v1: decision 10 and
meta.

**P6. Tuplet grouping.** `duration.py`'s `TemporalRatio` docstring promises
"a Tuplet node, which groups the constituent Notes"; none exists. Membership
is inferable from equal ratios except that `TemporalRatio(6:4) ==
TemporalRatio(3:2)`, so two 16th triplets and one sextuplet are the same
graph (112 groups in Mozart, 496 in Tchaikovsky). Display (bracket, number)
is presentation. v1: meta on the first member.

**P7. `context_in_force(event, kind)`** (revisit entry, DEV already agreed
the shape). The writer tracks context itself in v1; the query is where that
logic belongs, and decision 2 (a branch reads its parent) is its first rule.

**P8. Value-carrying marks.** `Mark` is frozen with no payload: tremolo
stroke count (508), pedal `change`, trill accidental, fingering
substitutions, tempo ranges ("♩ = 60–66"). v1: meta on the Marking.

**P9. No chord (N.C.) and arbitrary chord kinds.** `ChordEvent.chord` cannot
say "no harmony here"; MusicXML `kind="none"`. Degree-altered kinds build a
one-off `ChordType` (§5.9), which is fine. Whether `chord: ToneCollection |
None`, or a `NoChord` collection. v1: warn and skip.

**P10. Score metadata.** Movement number and title, editor, source and
publisher, encoding date. Strings on `Score`, or a structured contributor
list. v1: meta.

**P11. Line identity and staff assignment.** A line is not a node, so
"staff 2, voice 1" lives on the head's meta; a voice that changes staff
mid-run (cross-staff beaming; none in the corpus, common in piano music)
needs per-event staff. v1: meta.

**P12. Drum map.** The percussion plan §4 deferred it; the importer's kit
lines carry `hit` and display pitches in meta until a map turns
(instrument, display pitch, notehead) into strokes and back.

Two revisit entries to add during stage 2 (not pre-plans):
`relative_onset` returns notation-spelled `TiedDuration`s whose member count
grows with every tuplet (a length, or a normalized spelling, may be the better
return); and `MeterEvent` equality by length means `is_equivalent` cannot
catch a writer that emits 2/2 for 4/4, so round-trip tests compare
`presentation` directly.

## 8. Fixtures

### 8.1 Registry: `tests/scores/registry.py`

```python
@dataclass(frozen=True)
class ScoreFixture:
    slug: str
    musicxml: Path | None          # as distributed; None for the text chart
    corrected: Path | None         # an edited copy, when the original is wrong (8.3)
    pdf: Path | None
    extras: tuple[Path, ...]       # .mscz, .sib, .mid, .mscx, .txt
    exporter: str                  # "MuseScore 2.1", "Sibelius 19.5", ...
    parts: tuple[str, ...]         # <part-name>s in <part-list> order
    measures: int                  # in the first part
    features: frozenset[str]       # "voices", "lyrics", "harmony", "endings", "unpitched", "transpose", ...
    expected_warnings: tuple[str, ...]   # substrings the reader must warn with
    known_differences: tuple[str, ...]   # canonical-diff kinds accepted for now (9.5), each with a reason

FIXTURES: dict[str, ScoreFixture]
```

`tests/scores/test_registry.py` checks every directory has an entry, every
path exists, and the literal counts match the files (like
`tests/test_fixtures.py` pins domain sizes). File names are not changed;
paths are spelled out in the registry so tests never parse them.

### 8.2 Flaws to record in `SOURCE.md` (stage 1)

- Hymn: 52 of 168 `<syllabic>` flags contradict the hyphenation on the page
  (CapToMusic bug); the hidden rest-only part `P1`; metadata typed as
  `<words>`; `<sound tempo="120">` with no printed mark.
- Schubert: 12 hidden playback tempi exported as printed `<metronome>`
  marks (MuseScore 2.1 omits `print-object="no"`); 8 of 35 `<wedge>`s are
  text lines ("cresc. _ _ _") in the source; 14 hidden padding rests; held
  notes re-voiced across bar lines.
- Mozart: `<words>♯</words>` over a trill instead of `<accidental-mark>`;
  `<other-dynamics>calando` glued to an `<f/>`; 16 partial bars after
  repeats numbered `X1`–`X16`.
- Second Line: `<measure-repeat>` bars hold a whole `<rest/>` with no
  `<voice>` (the bar is not silent).
- Charleston: already recorded (hidden second staff of the voice part).

### 8.3 Corrected companions (decision 11)

Only where the XML is wrong relative to its own page, never for exporter
conventions the importer must handle anyway:

- `croft-o-god-our-help/AMNS_99_St_Anne_Harmony.corrected.musicxml`:
  the 52 `<syllabic>` values set to match the PDF's hyphenation.
- `schubert-allegretto-d915/Schubert_-_Allegretto_in_C_Minor_D.915.corrected.musicxml`:
  `print-object="no"` on the 12 metronome marks the `.mscz` marks invisible
  (the wedge-vs-text-line difference is left; fixing it would re-author).

Each companion is uncompressed, listed in `SOURCE.md` with every edit, and
registered as `corrected`; the corpus tests read both the raw and the
corrected file, and the hyphenation and tempo assertions run on the
corrected one.

## 9. Tests

Layout: `tests/io/musicxml/`. Small documents are inline strings built by a
helper `doc(*measures, parts=...)` in `tests/io/musicxml/helpers.py` that
wraps measure bodies in a valid partwise skeleton, so each test shows only
the element under test.

### 9.1 Tables and conversions (`test_tables.py`, exhaustive)

- Pitch: every vector in `tests.domains.QUALIFIED_VECTORS` → step/alter/
  octave → the same vector, and back over the seven steps × alters −2..2 ×
  octaves 0..9.
- Duration: every `duration_symbols` entry (plain, dotted, tuplet members)
  and every `GraceDuration` symbol → type/dots/time-modification → equal
  duration with the same spelling (`numerator`, `denominator`, `dots`,
  `ratio`); `MetricalDuration(1, 2**k, dots)` for k 0..7, dots 0..3;
  `from_length` for whole-measure rests over `time_signature_symbols`.
- Marks: every MusicXML articulation, ornament, technical, fermata and
  dynamics name in the table → a `Mark` symbol → the same name; every
  `Mark` in `scoring_symbols` that the table covers round-trips; the
  uncovered marks are listed in the test as the known set (pinned literal).
- Kinds: all 33 MusicXML kinds → `ChordType` → kind; `chord_type_symbols`
  that have a kind round-trip, the rest are pinned as text-only.
- Keys: fifths −7..7 × modes → `Key` → fifths/mode; clefs: the 19 clef
  symbols ↔ sign/line/octave-change; bar styles ↔ the bar-line symbols.

### 9.2 Reader rules (`test_reader.py`, one small document per rule)

Voices: a one-bar second voice; a voice reused in bars 1 and 5 (two
branches); a `<forward>` splitting a run; a run starting mid-event
(displacement); voices 5–8 on staff 2. Staves: two staves → group, per-staff
key with `number`, `<staves>` after `<key>`. Notes: chord merge; partial tie
split (decision 9: which class stays, the branch's zero displacement, the
tie's endpoints); cross-bar tie; tie matched across voices; grace before a
note and after (zero width via `onsets`); nested tuplet; whole-measure rest
without type; hidden rest; slash notehead; `<duration>` mismatch warning.
Structure: pickup measure `0`; split measure; every bar-line style and the
repeat merges; ending brackets; % bar; multiple rest. Contexts on both staff
lines, none on branches. Directions: each kind at an onset, at an offset,
inside an event (`meta.offset`); open pedal; `words` → tempo term vs minted
expression; `,` → breath. Lyrics: two verses, melisma, elision, wrong
`<syllabic>` flags kept in order, `part1verse1`. Harmony: bass, degrees,
N.C. warning, offset → displacement. Unpitched: kit split by instrument.
Transposition: clarinet in A → sounding pitches, `Stint.transposition`.
Grid: two parts → a `SyncLine` with measures + 1 points at the right
offsets (a pickup puts the second point at 1/4), one pin per part per
point, `score_sync_lines` finds it, `check_sync_alignment` empty; one part
→ no grid and no pins; a lead sheet with a chord line → chord pins only.
Score fields; blank part name; timewise refused; `.mxl` container; unknown
notation minted with a warning. Each test asserts graph shape (node counts by
type, walk order, `onsets` in `Fraction`s) and the exact warnings.

### 9.3 Corpus reads (`test_corpus.py`, parametrized over `FIXTURES`)

For each fixture with a `musicxml`: reads with exactly the
`expected_warnings` (no others); part names and order-in-meta match
`parts`; the first part's `DivisionEvent` count is `measures` (+1 for a
leading bar line); every line's summed `rational_length` equals its part's
other lines'; `check_alignment()` is empty; a grid exists exactly when the
fixture has two or more parts, with measures + 1 points and parts ×
(measures + 1) pins, and `check_sync_alignment()` is empty (this one is
`slow` for the three largest fixtures: it runs a timing search per pair of
pinned events per neighbouring points); per-fixture shape literals
(lines, branches, groups, spanners by mark, lyric lines) pinned in the
registry's `features` companion dict and updated in the same commit as any
mapping change. All ten read in the fast set (a few seconds in total).

### 9.4 Graph round trip (`test_roundtrip.py`)

`g = read(f); g2 = read(write(g))`; `assert g.is_equivalent(g2), g.diff(g2)`
for every fixture; the three largest (`tchaikovsky`, `mozart`,
`moonlight-gaze`) marked `slow`. Then the checks equivalence cannot make:
`MeterEvent.meter.presentation`, `TempoEvent.term.name`, and the
`meta["musicxml"]` keys the writer needs, compared through `correspondence`.

### 9.5 Canonical MusicXML comparison (`test_canonical.py`)

`canonicalize` applies, in order, a documented list of normalizations:
drop §5.10's elements, `<sound>`, `<encoding>`, positions, fonts, colours,
`placement`, `<stem>`, `<beam>`, `<accidental>`, `<notehead>` other than
slash, `id` attributes; unify `<tie>` and `<tied>`; treat a `<forward>` and a
hidden rest alike; rescale `<divisions>` to a common value per part; renumber
voices per staff by first appearance; renumber measures sequentially and drop
`implicit`; renumber slurs by nesting; rename part ids sequentially; sort
attribute order and strip whitespace; reduce `<harmony>` to root/kind/bass/
degrees; reduce `<lyric>` to number/syllabic/text/extend/elision.
`compare(a, b)` returns `Difference(kind, measure, part, detail)` items with
a fixed vocabulary of `kind`s.

For each fixture: `compare(canonicalize(original), canonicalize(write(read(original))))`
has no `kind` outside `known_differences`, and every listed kind actually
occurs (so the allowlist cannot rot). The allowlist is expected to shrink as
pre-plans land; each entry carries its reason.

Sparse form (decision 14): for each fixture, `sparse` is `read(original)`
with `remove_sync_line` applied to its grid (when it has one) and
`remove_derivable_divisions` to every top-level line and every branch;
`compare(canonicalize(write(full)), canonicalize(write(sparse)))`
is empty, and the registry pins how many divisions each fixture keeps
(the hymn keeps its pickup, its split bar and its double and final bars;
the Mozart keeps every repeat). A third form, grid kept but divisions
stripped, checks that the writer's grid-versus-onsets comparison passes on
meter-derived bar lines.

### 9.5a `remove_derivable_divisions` on its own (`tests/graph/test_divisions.py`)

Small graphs, no MusicXML: a line in 4/4 with a division every bar loses
all of them; a pickup keeps the first; a split bar keeps its extra division;
a repeat, a double bar and a final bar stay; a meter change mid-line
restarts the count; a line with no meter keeps everything; a fermata and a
pin on a removed division move to the next event; the returned divisions
re-inserted with `insert_event` give back an equivalent graph.
A Hypothesis property over `lines()`: after adding divisions from a random
meter, removing the derivable ones leaves only those that were placed off
the grid.

### 9.6 Hypothesis (`test_properties.py`)

- `exportable_scores()` in `tests/strategies.py`: a Score with one to three
  Parts; each a single line or a two-line group; lines from `lines()` with
  a meter, divisions every bar or only the off-grid ones, and for two or
  more Parts a bar grid or none (all combinations drawn, so the
  derived-bar-line and onset-alignment paths are covered), optional branches (a run under one event),
  marks from the covered subset of `scoring_symbols`, slurs and ties as
  spanners, a verse of lyrics from `lyric_texts()` (whole words), a chord
  line from `chord_type_symbols`, an optional transposing Stint.
  Property: `read(write(g)).is_equivalent(g)` (100 examples fast, 2,000
  thorough), plus the §9.4 extra checks.
- `musicxml_documents()`: a generator over the same subset, producing the
  XML directly (measures of random notes, rests, chords, tuplets, voices,
  ties, dynamics). Properties: `read` warns nothing; every line's length is
  measures × meter; `read(write(read(d)))` is equivalent to `read(d)`;
  `compare(canonicalize(d), canonicalize(write(read(d))))` is empty.
- Table inverses are exhaustive (9.1), not Hypothesis.

### 9.7 MuseScore smoke (`test_render.py`, `slow`)

Skipped when `shutil.which("mscore")` is None, in the pattern of
`tests/visualization/test_render.py`. For each fixture, `mscore -o out.pdf
exported.musicxml` exits 0 and the PDF has pages; the point is that a real
notation program accepts what we write.

### 9.8 Review artifacts (decision 12): `tests/scores/review.py`

`uv run python -m tests.scores.review <slug> [--out DIR]` writes, per fixture:
the original PDF's pages as PNG (`pdftoppm`), `write(read(f))` rendered
through `mscore` to PDF then PNG, both on opaque white
(`visual-review-needs-opaque-renders`), a side-by-side page image when
ImageMagick's `montage` is present, and `canonical-diff.txt` from §9.5.
Not a test; documented in `docs/` for the developer's sign-off and for an
agent review later. The element inventory used for this plan is kept here
too, as `tests/scores/inventory.py`, since it is how a new fixture gets its
`features` entry.

### 9.9 Doctests

`read`, `write`, `canonicalize` and `compare` each carry a three-line example
over an inline document (`io.StringIO`), per the docstring rule.

## 10. Execution

Stage 0. Heavy baseline: `uv run pytest --hypothesis-profile=thorough -m ""`.

Stage 1. Fixtures. Registry, `test_registry.py`, `SOURCE.md` flaw notes,
the two corrected companions, `tests/scores/inventory.py`.
`Claude: tests/scores registry; fixture flaws recorded; corrected companions`

Stage 2. Model changes this plan needs. `add_spanner(end=None)` with the
walkers, `materialize`'s span check and `_covered_content` handling an
absent ENDS_AT as a Stint's is handled; `remove_derivable_divisions` with
its tests (§9.5a); `add_sync_line_to_score`, `score_sync_lines` and
`remove_sync_line` with tests in `tests/graph/test_sync_line.py` and
`test_score_graph.py` (membership, removal restores the pre-grid snapshot,
`scores_of` a sync line); the sync-line docstring paragraph;
`MusicXmlError`, `UnexportableError`; the two revisit entries; P3's marks
if approved.
`Claude: open-ended spanners; remove_derivable_divisions; sync lines on a Score; MusicXmlError, UnexportableError`

Stage 3. Reader core: document, Score, parts/staves/voices/groups/stints,
attributes, notes and durations, chords and the split rule, ties, divisions
and bar lines; `tables.py` for note types, clefs, bar styles, keys; tests
9.1 (pitch, duration, key, clef, bar style), 9.2 (the structural rules),
9.3 for hymn, lead sheet, Schubert, Mozart.
`Claude: io.musicxml reader: parts, voices, notes, ties, divisions, contexts; tests`

Stage 4. Reader, the rest: notations and directions with the marks table,
lyrics, harmony with the kinds table, unpitched kit, endings and % bars,
transposition, `.mxl`; graph wiring (`from_file`, `import_file`); 9.1
complete, 9.2 complete, 9.3 for all ten.
`Claude: io.musicxml reader: notations, directions, lyrics, harmony, percussion, transposition; tests`

Stage 5. **Gate: P1 (part order and bracketing)** designed and built in its
own session. The reader's `index`/`group` meta is replaced by P1's objects.

Stage 6. Writer: §6, `export_file`, 9.4, 9.6's `exportable_scores`
property, doctests.
`Claude: io.musicxml writer; OmkGraph.export_file; round-trip tests`

Stage 7. Comparison and review: `canonical.py`, 9.5 with the initial
allowlists, 9.6's document generator, 9.7, `review.py`.
`Claude: canonical MusicXML comparison; render smoke test; review script`

Stage 8. Docs: `docs/io.qmd` (how to read and write, what is dropped, the
meta schema, the review script), `_quarto.yml` reference entries for
`io.musicxml`, `docs/overview.md`'s "Output to MusicXML" line made true;
plan moved to `_plans/completed/`; heavy run.
`Claude: docs: MusicXML import and export; plan to completed`

Stages 3 and 4 can begin as soon as stages 1–2 are in; stage 5 blocks 6–7.

## 11. Verification

- `uv run pytest` after every stage (fast set; the ten corpus reads are in it).
- `uv run pytest tests/io -m ""` for the slow round trips and the render
  smoke test.
- `uv run pytest -q -o addopts="" tests --cov=openmusickit
  --cov-report=term-missing` at stages 4 and 7; `io/musicxml` should sit with
  the rest of the package (>95%).
- Stage 7 by hand: `uv run python -m tests.scores.review schubert-allegretto-d915`
  and the same for `second-line-joe-avery` and `croft-o-god-our-help`; the
  developer reviews the side-by-side pages before stage 8.
- Heavy set at stage 0 and stage 8.

## 12. Not doing (deliberately)

LilyPond output (its own plan; the writer's walk is reusable);
JSON serialization (its own plan; `meta["musicxml"]` values are kept
JSON-friendly for it); `score-timewise` input; MusicXML 1.x; `<figured-bass>`
and `<frame>` beyond meta (planned extensions); microtones beyond a warning;
control-flow semantics, drum maps, tuplet display, beams, layout, page
geometry; an automated LLM judge; DTD/XSD validation of input or output
(the render smoke test is the acceptance check).
