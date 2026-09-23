# Clef, Score and text marks: the first slice toward an importer

## Context

Asked what a MusicXML or LilyPond importer would find missing, the gap
analysis (Appendix A) found the mark vocabulary and the pitch/duration
algebra essentially complete, and a handful of score-level objects absent
that appear on nearly every page: a clef, the work's title and composer,
free expression text and rehearsal marks. This plan adds those three, plus
two small pieces they expose: `GraphMeta` finally gets its fields, and the
`Marking` / `MarkSpanner` repr gap in `_plans/revisit.md` gets closed,
because minted text marks make it visible. Repeats and navigation semantics
stay with the future control-flow module; gradual tempo stays in revisit.

Every decision below was made with the developer in this session.

## Decisions

- **Clef** follows the `DivisionShape` / `BarLineShape` pattern: abstract
  `Clef` (a plain `__slots__ = ()` marker class in `values/scoring/clef.py`,
  as `DivisionShape` is; no abstract members, so no ABC),
  WSMN `StaffClef(sign, line, octave_change)` with a `ClefSign` enum
  (G, F, C, PERCUSSION, TAB, NONE) in `systems/wsmn/scoring/staff_clef.py`,
  and `ClefEvent(ContextEvent)` holding a `Clef | None`, beside
  `ModalContextEvent`. `objects/` may not import from `systems/wsmn`, so
  the event is typed by the abstract value. Ready-made clefs in
  `scoring/symbols.py` carry a `_clef` suffix (`treble_clef`, `bass_clef`),
  as bar lines carry `_bar`; `bass` alone already names a percussion tone.
  `StaffClef.reference_tone` gives the pitch the sign names (G4, F3, C4
  shifted by the octave change); staff positions of other pitches are a
  renderer's business.
- **Score metadata lives on a `Score` node** (`objects/score.py`), not on
  the graph: a graph may hold one work, several, or fragments. Fields:
  title, subtitle, composer, lyricist, arranger, copyright, opus,
  dedication, all `str | None`. A Score names a connected component and is
  never a timing origin.
- **A Score contains line heads and Parts** with plain CONTAINS edges. A
  line need not have a Part (a chord line, a sketch), and a Part need not
  have music yet (an orchestration sketch), so both memberships carry
  information. One edge type with type-filtered queries is the PERFORMS
  precedent (a Part performs a Stint or a LineGroup). From a LineGroup a
  CONTAINS edge is the timed `Contains` because a group is a timing origin;
  from a Score it is a plain `OmkEdge` because a score is not. The timing
  walk gets a guard so only `TimedEdge`s count.
- **`GraphMeta` stays**, as a dataclass with `name`, `description`, and an
  `info` dict for arbitrary user storage that OMK never reads, exposed as
  `OmkGraph.meta`. Its docstring stops promising title and composer.
- **Free text is a minted `Mark`**, as `TempoTerm` already allows ("or one
  made for the score"). New `MarkType.EXPRESSION` and `MarkType.REHEARSAL`;
  a rehearsal mark is `Mark(name="A", kind=MarkType.REHEARSAL)` on a
  `Marking`. Ready-made expression words, navigation words (fine, D.C.,
  D.S., al fine, al coda, to coda) beside segno and coda, and instruction
  words (solo, tutti, divisi, unisono, a 2) as `MarkType.OTHER`. Jump
  semantics stay with control flow. `espressivo` stays an articulation.
- **`Mark.__repr__` round-trips** and `Marking` / `MarkSpanner` drop their
  compact reprs. The revisit entry's other idea, printing the ready-made
  symbol's name, needs `objects/` to know `systems/wsmn/scoring/symbols`,
  which the layering rule forbids; a full evaluable `Mark(...)` with
  default-valued fields omitted is the honest form, and it keeps minted
  marks short.
- **Out of scope**, recorded here so the next slice can pick them up: part
  order and bracket grouping on the Score; control flow; gradual tempo;
  per-tone attachments in a chord; the tie and written-vs-sounding rules;
  serialization.

## Files and commits

Six commits, subject `Claude: <what changed>`, no trailer of any kind
(AGENTS.md overrides the harness attribution). Run the heavy set once
before commit 1 as the baseline; fast set plus ruff after each commit.

Things found in the codebase that shape the work:

- `tests/graph/test_compound_lines.py:287` pins the compact
  `MarkSpanner(mark=Mark(name='slur', ...))` string as a warning message;
  it must become `repr(MarkSpanner(mark=slur))`.
- `add_branch` (`graph.py:530-533`) refuses a child head that has a
  CONTAINS in-edge ("is a line of a group"). A Score's line head gets one
  too, and the refusal is right (a branched line reaches the score through
  its parent), but the message and the docstring line at `graph.py:502`
  must say "group or score".
- `_timing_neighbours` (`graph.py:655-664`) calls `_timed_delta` on every
  CONTAINS edge; a plain edge has no `displacement`, so the guard is
  required, not optional. `check_alignment` has the same assumption for
  SIMULTANEOUS edges, which this work never creates plain; leave it.
- `DivisionShape` is a plain class, not an ABC; `Clef` mirrors it.
- `bass` is already a percussion tone in `percussion/symbols.py`, so clef
  symbols take the `_clef` suffix. No other proposed name collides with a
  mark name, alias, or TempoTerm name (checked: `legato` vs. aliases
  "detached legato" and "legato slur" are distinct strings).
- `docs/reference/` is gitignored: `build_reference.py` is a check.
- With a `ClefEvent` first in the example's melody, the clef is the head,
  so `add_line_to_score(score, clef)`, not `melody[0]`.

### Commit 1: `Claude: GraphMeta name, description and info; OmkGraph.meta; plan for clef, score and text marks`

- `src/openmusickit/graph/graph.py:32`: `GraphMeta` becomes
  `@dataclass(kw_only=True, slots=True)` with `name: str | None = None`,
  `description: str | None = None`,
  `info: dict[str, Any] = field(default_factory=dict)`. Docstring: the
  graph as a container; `info` is free-form storage OMK never reads, as
  `OmkObject.meta` is for one object; a graph may hold one score, several,
  or fragments, so a work's metadata lives on `Score`. Doctest
  `GraphMeta()` prints `GraphMeta(name=None, description=None, info={})`;
  the default repr round-trips. Add a `meta` property after `__init__`
  returning `self._meta`, with a doctest. Every existing
  `OmkGraph(GraphMeta())` keeps working.
- Copy this plan to `_plans/clef-score-text.md` (repo convention; moved to
  `_plans/completed/` in commit 6).

### Commit 2: `Claude: Mark repr round-trips; Marking and MarkSpanner take the dataclass repr; resolve the revisit entry`

- `src/openmusickit/values/scoring/mark.py`: add `Mark.__repr__` printing
  the constructor call with fields at their defaults left out and enums as
  full symbols. Explicit lines, not a `fields()` loop:

  ```python
  parts = [f"name={self.name!r}"]
  if self.description is not None: parts.append(f"description={self.description!r}")
  if self.kind is not None: parts.append(f"kind=MarkType.{self.kind.name}")
  if self.attachment_mode is not None: parts.append(f"attachment_mode=AttachmentMode.{self.attachment_mode.name}")
  if self.aliases: parts.append(f"aliases={self.aliases!r}")
  if self.binds: parts.append("binds=True")
  ```

  `staccato` prints
  `Mark(name='staccato', description='A staccato dot: ...', kind=MarkType.ARTICULATION, attachment_mode=AttachmentMode.SINGLE)`;
  a minted `Mark(name='dolce', kind=MarkType.EXPRESSION)` prints as
  written. Fix the class docstring's line breaks to semantic ones while
  there.
- `src/openmusickit/objects/marking.py`: delete both custom `__repr__`s
  (L47-48, L77-78); update the two doctests (L34, L64) to the full form, or
  show a minted mark there to keep them short.
- `tests/objects/test_marking.py`: replace `test_repr_is_compact` with
  `test_repr_round_trips(mark_symbols)`: for every ready-made mark,
  `eval(repr(mark), ns) == mark` and the same for the `Marking` or
  `MarkSpanner` holding it (SPAN marks on a spanner); literal checks for
  `staccato` and for a minted mark. `tests/graph/test_compound_lines.py:287`
  as above.
- `_plans/revisit.md`: remove the first entry. Add one new last entry:
  other custom reprs that do not round-trip (`NoteEvent` prints `tones=[...]`
  for a set field; `LyricSyllable('Al -')`; the edge reprs print bare enum
  values, kept deliberately before the rule existed). `_plans/completed/small-items.md`:
  a dated resolution entry saying what was done and that printing the
  ready-made symbol's name was ruled out by the layering rule.

### Commit 3: `Claude: MarkType.EXPRESSION and REHEARSAL; expression, navigation and instruction words`

- `values/scoring/mark.py`: add `EXPRESSION` and `REHEARSAL` before
  `OTHER`, each with a trailing gloss; expand the `MarkType` docstring:
  text in a score is a Mark too; a word the table lacks, and every
  rehearsal label, is a Mark made for the score, as `TempoTerm` allows.
- `systems/wsmn/scoring/symbols.py`, 25 new marks, total 213 -> 238:
  - New `# EXPRESSION` section between FICTA and OTHER, all
    `kind=EXPRESSION, attachment_mode=EITHER` (any may carry a dashed
    extension): `dolce`, `cantabile`, `legato`, `simile` (alias "sim."),
    `sotto_voce` ("sotto voce"), `agitato`, `tranquillo`, `pesante`,
    `leggiero` (alias "leggero"), `grazioso`, `maestoso`. 11.
  - In the existing navigation subsection after `varcoda`, all
    `kind=NAVIGATION, attachment_mode=SINGLE`, descriptions ending "the
    jump itself is control flow, which a future module owns; the word here
    is what is printed": `fine`, `da_capo` ("da capo", alias "D.C."),
    `dal_segno` (alias "D.S."), `da_capo_al_fine` (alias "D.C. al Fine"),
    `dal_segno_al_fine`, `da_capo_al_coda`, `dal_segno_al_coda`, `to_coda`.
    8. Tighten `coda`'s description to point at `to_coda`.
  - New `# --- instructions to the players ---` subsection under OTHER,
    `kind=OTHER`: `solo`, `tutti`, `divisi` (alias "div."), `unisono`
    (alias "unis."), `a_2` ("a 2", alias "a due"), all SINGLE (a condition
    in force until the next word); `fill` EITHER (a drummer's fill, at a
    point or over a stretch). 6.
  - Module docstring: first sentence mentions expression and navigation
    words; a sentence on minting, with the rehearsal example
    `Marking(mark=Mark(name="A", kind=MarkType.REHEARSAL, attachment_mode=AttachmentMode.SINGLE))`;
    doctests `dolce.kind` and `da_capo.aliases`.
- Counts: `tests/test_fixtures.py:97-98` and `tests/objects/test_marking.py:25,56`
  from 213 to 238. The existing sweeps (`test_mark_table_invariants`,
  `test_attachment_mode_is_checked_for_every_mark`,
  `test_only_slur_and_tie_bind`, the new `test_repr_round_trips`) cover
  every new symbol; no new test file.

### Commit 4: `Claude: Clef, WSMN StaffClef and ClefSign with clef symbols; ClefEvent`

- `src/openmusickit/values/scoring/clef.py` (new): `class Clef` with
  `__slots__ = ()`, docstring in the `DivisionShape` style (what fixes the
  meaning of a staff's lines; `StaffClef` is WSMN's; chant's C and F clefs
  on four lines would be another; `ClefEvent` places one; how pitches map
  to positions is a renderer's business), doctest
  `isinstance(StaffClef(ClefSign.G, 2), Clef)`. Add to
  `values/scoring/__init__.py`.
- `src/openmusickit/systems/wsmn/scoring/staff_clef.py` (new):

  ```python
  class ClefSign(StrEnum):
      G = auto(); F = auto(); C = auto()
      PERCUSSION = auto()  # unpitched: the lines are instruments, not tones
      TAB = auto()         # the lines are strings
      NONE = auto()        # no clef is drawn

  _REFERENCE_TONES = {ClefSign.G: (4, 7, 0), ClefSign.F: (3, 5, -1), ClefSign.C: (0, 0, 0)}  # G4, F3, C4

  @dataclass(frozen=True, slots=True)
  class StaffClef(Clef):
      sign: ClefSign
      line: int | None = None       # 1 is the bottom line, MusicXML's numbering
      octave_change: int = 0        # MusicXML clef-octave-change; -1 for the vocal tenor clef
  ```

  `__post_init__`: G/F/C require `line` an int in 1..5, else
  `ValueError("A G clef sits on a staff line 1 to 5; got None.")`;
  PERCUSSION/TAB/NONE require `line is None`, else
  `ValueError("A TAB clef sits on no particular line; got 3.")`. Plain
  `ValueError`: two construction checks need no new error class.
  `reference_tone` property: the tuple for the sign with `octave_change`
  added to the octave, as a `TonalVector`; `None` for the unpitched signs
  (verified: `(4,7,0)` formats as G4, `(3,5,-1)` as F3, `(0,0,0)` as C4;
  middle C is octave 0). Positional fields so the repr is
  `StaffClef(ClefSign.G, 2)`; custom `__repr__` omits `line` when None and
  `octave_change` when 0, e.g. `StaffClef(ClefSign.G, 2, octave_change=-1)`.
  Add to `systems/wsmn/scoring/__init__.py`.
- `systems/wsmn/scoring/symbols.py`: import `ClefSign, StaffClef`; new
  final `# CLEFS` section after BAR LINES, LilyPond `\clef` name and
  MusicXML sign/line beside each. 19 symbols:
  `treble_clef` G2, `french_clef` G1, `soprano_clef` C1,
  `mezzo_soprano_clef` C2, `alto_clef` C3, `tenor_clef` C4,
  `baritone_clef` C5, `baritone_f_clef` F3 (LilyPond varbaritone),
  `bass_clef` F4, `subbass_clef` F5, `treble_clef_8vb` G2 -1 (LilyPond
  "treble_8", the vocal tenor clef), `treble_clef_8va` G2 +1,
  `bass_clef_8vb` F4 -1, `bass_clef_8va` F4 +1, `treble_clef_15ma` G2 +2,
  `bass_clef_15mb` F4 -2, `percussion_clef`, `tab_clef`, `no_clef`
  (NONE; LilyPond `\omit Clef`, MusicXML sign none). Module docstring adds
  clefs and a `treble_clef` doctest.
- `src/openmusickit/objects/context_event.py`: import `Clef` from
  `values.scoring.clef`; append `ClefEvent(ContextEvent)` with
  `clef: Clef | None = None`. Docstring in the `MeterEvent` style: belongs
  to the line it is in and governs what follows until the next; `None` is
  undefined or undecided; a percussion line takes `percussion_clef`; a clef
  says nothing about the tones, only where a renderer puts them, so it is
  not a `TonalObject` and `transform_tones` over a span leaves it alone.
  Doctests: `ClefEvent(clef=treble_clef)` prints
  `ClefEvent(clef=StaffClef(ClefSign.G, 2))`;
  `ClefEvent(clef=bass_clef_8vb).clef.reference_tone` is
  `TonalVector((3, 5, -2))`; `ClefEvent().clef is None`.
- `docs/_quarto.yml`: `values.scoring.clef` after `values.scoring.tempo_term`;
  `systems.wsmn.scoring.staff_clef` after `systems.wsmn.scoring.bar_line_shape`.
- Tests:
  - `tests/conftest.py`: `clef_symbols` fixture via
    `symbols_of(scoring_symbols, StaffClef)`; `tests/test_fixtures.py`:
    pin 19 / 19 distinct.
  - `tests/systems/wsmn/scoring/test_staff_clef.py` (new), plain functions
    as in `test_bar_line_shape.py`: construction and defaults; pitched
    signs reject `None`, 0, 6, `"2"`; unpitched signs reject a line;
    `reference_tone` for every symbol from an explicit table (G clefs
    `(4,7,0)` shifted by octave change, C clefs `(0,0,0)`, F clefs
    `(3,5,-1)` shifted, unpitched `None`) plus
    `treble_clef.reference_tone.pitch.unicode == "G4"`, bass F3, alto C4;
    `eval(repr(c)) == c` over `clef_symbols` with three literal reprs;
    `isinstance(treble_clef, Clef)` and frozenness; every symbol is a
    distinct hashable `StaffClef`.
  - `tests/objects/test_context_event.py`: add `ClefEvent`, `StaffClef`,
    `ClefSign` to `NAMESPACE`; new tests mirroring the MeterEvent ones
    (zero duration and not `TonalObject`; `ClefEvent(duration=quarter)`
    raises `TypeError`; defaults; equality by clef, ids differ); extend
    `test_repr_round_trips` with `ClefEvent()` and one per `clef_symbols`
    entry; put clef events into the pass-through and deepcopy tests; a new
    `test_transform_tones_leaves_a_clef_alone`.
  - `uv run python docs/build_reference.py` and confirm both new pages.

### Commit 5: `Claude: Score; add_line_to_score, add_part_to_score, score_lines, score_parts, scores_of, walk_score; timing walk skips plain CONTAINS edges`

- `src/openmusickit/objects/score.py` (new): `Score(OmkObject)`,
  `@dataclass(kw_only=True, slots=True)`, fields `title`, `subtitle`,
  `composer`, `lyricist`, `arranger`, `copyright`, `opus`, `dedication`,
  all `str | None = None`. Default repr (round-trips). Docstring: a work as
  far as the graph is concerned; points at the heads of its top-level lines
  and at its Parts with plain CONTAINS edges; not a timing origin (two of
  its lines with no pin between them have no relative onset); the graph as
  a whole is not a work (`GraphMeta` describes the graph); `None` is "not
  given". Add `score` to `objects/__init__.py`.
- `src/openmusickit/graph/graph.py`:
  - import `Score`; in `_timing_neighbours`, in both loops, `continue`
    when `edge is ignoring or not isinstance(edge, TimedEdge)`; docstring
    sentence: a Score's CONTAINS edges are plain, not timed, and are passed
    over.
  - `add_branch` docstring (L502) and message (L530-533): "a line of a
    group or a score".
  - New `# Scores` section before `# Annotations`, modelled on the group
    methods:

    ```python
    def add_line_to_score(self, score: Score, head: SequentialEvent) -> None:
        # same checks as add_to_group: head has no NEXT in, no BRANCHES in
        self.add_edge(score, head, EdgeType.CONTAINS)   # plain OmkEdge; add_edge refuses a second one
    def add_part_to_score(self, score: Score, part: Part) -> None
    def score_lines(self, score) -> Iterator[SequentialEvent]:  successors(score, SequentialEvent, CONTAINS)
    def score_parts(self, score) -> Iterator[Part]:             successors(score, Part, CONTAINS)
    def scores_of(self, node) -> Iterator[Score]:               predecessors(node, Score, CONTAINS)
    def walk_score(self, score):  walk_span from each head, as walk_group
    ```

    Doctests on `add_line_to_score`: two lines and a Score; sorted names of
    `score_lines`; `scores_of(head) == [score]`;
    `relative_onset(score, head)` raises `GraphError`; a mid-line event
    raises `GraphError(... is not the head of a line.)`. `Raises` section:
    not a head, branched, or already in the score.
- `src/openmusickit/graph/__init__.py`: a **Score** bullet after the Part
  bullet (metadata; names one connected component; points at top-level
  heads and Parts; plain CONTAINS because a score is not a timing origin
  while a group is; `walk_score`, `scores_of`), and amend the last
  paragraph: a component is a score whether or not a `Score` names it; a
  graph may hold several, or fragments that are none.
- `src/openmusickit/graph/edge.py`, `Contains` docstring: one line that a
  Score's CONTAINS edges are plain `OmkEdge`s, not this class.
- `docs/_quarto.yml`: `objects.score` after `objects.part`.
- Tests:
  - `tests/objects/test_score.py` (new): fields default `None`;
    `isinstance(Score(), OmkObject)` and not `SequentialEvent`; equality by
    content ignoring id; `eval(repr(s), {"Score": Score}) == s` for empty
    and fully set; deepcopy.
  - `tests/graph/test_score.py` (new), using `notes`, `names`, `snapshot`
    from `tests/graph/helpers.py`; fixture: melody with a two-note second
    voice branched from its second note, a chord line pinned to the melody
    head, `Part("Voice")` with a stint, `Part("Piano")` with no music, a
    `Score`, both heads and both parts added. Tests: `score_lines` /
    `score_parts` id sets; `scores_of` for heads and parts, `[]` for a
    mid-line event and the branched head; `walk_score` covers melody plus
    voice plus chords exactly; membership refused for a mid-line event, a
    branched head, and the same head twice; a score's line cannot then be
    branched; a Score is not a timing node (two unpinned lines raise
    `GraphError`, `relative_onset(score, head)` raises, onsets within a
    line equal a scoreless graph's); a head in a `LineGroup` and a Score at
    once (`groups_of`, `scores_of`, `group_members`, group timing all
    unaffected); removing the Score restores the `snapshot` taken before
    it was added; a part with no music; two Scores in one graph.
  - Run the existing graph suites in the fast set to confirm the guard
    changes nothing for timed edges.

### Commit 6: `Claude: docs: Score and ClefEvent in the score-graph example; clef-score-text plan completed`

- `docs/examples.qmd`, "A small score graph": a sentence on `Score` and
  on a clef being a zero-duration `ClefEvent`; imports for `ClefEvent`,
  `Score`, `treble_clef`; `score = Score(title="Twinkle, Twinkle, Little Star", lyricist="Jane Taylor")`;
  `clef = ClefEvent(clef=treble_clef)`; `graph.add_line([clef, *melody])`;
  `graph.add_line_to_score(score, clef)`; after the pin,
  `graph.add_line_to_score(score, chords[0])`. The table loop, chord walk,
  lyric zip and transposition still start at `melody[0]`. One short new
  block: `score.title`, the count of `walk_score(score)`, and
  `graph.relative_onset(clef, melody[0])` printing `ZeroDuration()`.
- `git mv _plans/clef-score-text.md _plans/completed/clef-score-text.md`.
  Add a revisit entry only for what genuinely surfaced: part order,
  bracket/brace grouping and `LineGroup` membership on a Score are out of
  scope until a renderer or the importer needs staff order.

## Verification

```
uv run pytest --hypothesis-profile=thorough -m ""        # once, before commit 1: the baseline
uv run pytest -q                                          # after every commit
uv run ruff check src tests && uv run ruff format --check src tests
uv run python docs/build_reference.py                    # after commits 4, 5, 6: new pages appear
uv run pytest --hypothesis-profile=thorough -m ""        # once, after commit 6
```

Pinned counts that move: marks 213 -> 238 in three places; new
`clef_symbols` 19. Pages to confirm: `values.scoring.clef`,
`systems.wsmn.scoring.staff_clef`, `objects.score`; `graph.graph` shows
`GraphMeta`'s fields and `OmkGraph.meta`. If Quarto is installed, render
the examples page so the Twinkle block executes.

## Out of scope (deliberately)

- Any renderer, staff layout, or pitch-to-staff-position mapping.
- Control flow for D.C. / D.S. / fine / coda (the descriptions say so).
- Part order, bracket/brace grouping, or `LineGroup` membership on a Score.
- Structured metadata on `Score` (dates, several contributors); strings.
- Gradual tempo (revisit), `check_alignment`'s TimedEdge assumption, the
  other non-round-trip reprs (new revisit entry), and the importer itself.

## Appendix A: the gap analysis this plan came from

The question: if we started an importer for LilyPond or MusicXML, which
concepts that appear on an average page of WSMN sheet music does OMK not yet
account for? Method: read every file in `objects/`, `graph/`, `values/`, and
`systems/wsmn/`; grepped `src/` for each candidate concept; three Explore
agents inventoried the same layers and swept `_plans/` for deferred items so
nothing here re-proposes something already decided.

### What exists (verified)

**Events on a line** (`objects/`): `NoteEvent` (a set of `Tone`s, so a chord
in one voice is one event; zero tones = unspecified content; `Rest` is a
`SilentTone`), `ChordEvent` (a lead-sheet symbol holding a `Chord`),
`DivisionEvent` (a bar line, zero duration, with a `BarLineShape` that is
visual only), `ContextEvent` family: `ModalContextEvent` (key / key
signature), `MeterEvent` (time signature, or any `Measurable`), `TempoEvent`
(metronome mark as `Tempo`, metric modulation as `TemporalRatio`, word as
`TempoTerm`). `LyricSyllable` is its own line, joined to notes by LYRIC edges;
melisma is the absence of an edge; `LyricSection` is a verse / refrain
spanner with a language tag.

**Durations** (`values/time`, `systems/wsmn/temporal`): every WSMN value from
maxima to 128th, dots, tuplet ratio carried on the `MetricalDuration` itself
(nesting by composing ratios), `TiedDuration` (one value drawn as several tied
noteheads), `GraceDuration` (zero width; `on_beat` distinguishes acciaccatura
from appoggiatura), `TimeSignature` incl. additive meters and a printed
presentation, `ClockDuration` / `Tempo`.

**Pitch** (`systems/wsmn/tonal`): `TonalVector` (letter, chromatic, optional
octave), all 35 spellings incl. double accidentals, transposition algebra,
`Key` / `KeySignature` / `ModePattern` (major, minor, the seven church modes),
`NoKey`, `Chord` / `ChordType` with ~80 lead-sheet qualities and slash-chord
inversion. `TonalVector.from_ly` already parses LilyPond pitch names with
relative octaves.

**Marks** (`values/scoring/mark.py`, `systems/wsmn/scoring/symbols.py`):
213 ready-made `Mark`s in 12 `MarkType`s. Articulations (16), dynamics (35,
incl. hairpins and `cresc.`/`decresc.` text as span marks, niente),
ornaments (29, incl. trills, turns, mordents, tremolo, arpeggio), phrasing
(slur, phrase mark, tie, l.v., repeat tie, eight fermatas), breath marks and
caesuras (9), bowing (9), technique (64: strings, fretted, winds, brass,
percussion, piano pedals, organ heel/toe, handbells), fingering / sticking /
string numbers (20), ficta (5), 8va/8vb/15ma/15mb lines, segno / coda /
varcoda, eyeglasses. A mark is placed with `Marking` (one event, MARKS edge)
or `MarkSpanner` (STARTS_AT / ENDS_AT). Coverage is stated to be a superset
of LilyPond's and MusicXML's mark vocabularies.

**Structure** (`graph/`): lines (NEXT chains), branches (a second voice
inside one instrument's line, with onset/offset anchor and displacement),
pins (`Simultaneous`, between independent lines), `LineGroup` (a pianist's
hands, a drum kit) as a local timing origin, `Part` (an instrument; a name)
with `Stint`s (a part's run on a line, optional `transposition` for how the
part reads shared events) or PERFORMS to a group, `PercussionPart` with a
palette. Instrument changes mid-line fall out of Stints. Edge types also
declared but unused by any API: IMPLEMENTS, REALIZES, ACCOMPANIES,
HARMONIZES, VARIATION_OF, DERIVATIVE_OF, REFERENCES, USER_DEFINED.

**Percussion**: `PercussionTone` (relative pitch + stroke), sixteen palettes.
Staff placement is explicitly "an output map's business".

**Persistence**: `OmkGraph.from_json` / `export_to_json` and friends are
`NotImplementedError` stubs. `GraphMeta` is an empty class.

### Already decided or deferred in `_plans/` (so not re-proposed here)

- Measures are never structural; bar lines are `DivisionEvent`s the author
  places; renderers derive the rest and warn on disagreement
  (`_plans/completed/division-event.md`).
- Repeats and jumps belong to "a later control-flow module" that inherits
  the same explicit-wins / derived-fills / mismatch-warns policy
  (division-event plan). Simile marks too (percussion plan).
- `Score` / `Section` "may arrive later as metadata containers/spanners,
  not as timing roots" (compound-lines plan); a general `Section(Spanner)`
  was noted for later in the lyrics plan; `values/tone/tone.py:31-32` says
  base classes for measures and sections "do not exist yet".
- Notation layer deferred: "noteheads, staves/clefs, drum maps"
  (compound-lines plan); a drum map, if it ever sits in a line, would be a
  `PercussionMap(ContextEvent)` (percussion plan).
- Instrument identity is a field on `Part`, not a new node (percussion
  plan); `Part` is a name for now.
- `Stint.transposition` is a read-through view; generalize to declarative
  `ViewOperation`s only when a second kind appears, never raw callables
  (compound-lines and percussion plans).
- `Branch` "may be scaled back or removed with more discovery"
  (percussion plan). An importer mapping MusicXML voices to branches
  depends on this staying.
- Gradual tempo and `context_in_force` are open in `_plans/revisit.md`,
  gated on "a realizer or renderer".
- MIDI is its own musical system, separate design (overview,
  compound-lines plan).
- Layering rule: `objects/` and `graph/` import nothing from
  `systems/wsmn` (small-items.md). So a clef cannot be a WSMN type held by
  an object directly; it needs the `DivisionShape` / `BarLineShape` pattern
  (abstract value in `values/`, WSMN implementation in `systems/wsmn/`).
- `docs/overview.md` already promises "linear scores with standard roadmap
  and expression nodes" and "Output to MusicXML and Lilypond"; neither
  exists. `OmkObject.meta` anticipates "an importer's source reference".
- Inconsistency worth noting: the percussion plan says "'ad lib', 'fill',
  'solo', 'as written' are text marks", but no text-mark mechanism was ever
  defined or deferred. That gap is unrecorded.

### Gaps, ranked by how often an ordinary page hits them

#### Tier 1: on nearly every page, and nothing exists

1. **Clef.** Zero occurrences of the word in `src/`. Every staff opens with
   one, and changes are common (cello, bassoon, piano LH). The consistent
   shape is a WSMN `Clef` value (sign G/F/C/percussion/TAB, staff line,
   octave displacement for treble-8 and bass-8) placed by a `ClefEvent`
   subclass of `ContextEvent`, exactly as a key signature is placed by
   `ModalContextEvent`. Because `objects/` may not import from
   `systems/wsmn`, the event holds an abstract value (a "how pitches are
   placed on the staff" counterpart to `DivisionShape`) and WSMN supplies
   `Clef`, as `BarLineShape` does. `_plans/completed/compound-lines.md`
   lists "staves/clefs" as deferred, so this is known but unscheduled.

2. **Score metadata.** `GraphMeta` (`graph/graph.py:32`) is an empty class
   whose docstring promises title and composer. Every sheet has a title,
   composer, lyricist/arranger, copyright, and often movement / opus numbers.
   MusicXML `<work>`, `<movement-title>`, `<identification>`, `<credit>`;
   LilyPond `\header{}`.

3. **Free text and rehearsal marks.** No object carries text. Expression
   words (dolce, cantabile, sempre, Solo, Tutti, div., unis.), instructions
   ("Fine", "D.C. al Fine", "To Coda", "Swing", "N.C."), and boxed rehearsal
   letters/numbers appear on most band, choral and orchestral pages. `Mark`
   is a fixed vocabulary (one could mint `Mark(name="dolce")`, which
   conflates a vocabulary entry with a one-off instance). ANNOTATES and
   `add_annotation` already accept any `OmkObject`, so the missing piece is
   a text-bearing object (a direction at a point, and a spanner form for
   dashed continuations), plus a rehearsal mark. The lyrics plan deferred a
   general `Section(Spanner)`; rehearsal marks and formal sections (Intro,
   Verse, A/B) are close relatives.

4. **Control flow: repeats, alternate endings, D.C./D.S./Fine/Coda.**
   Repeat dots on a `BarLineShape` and the segno/coda marks are "visual
   only"; `division_event.py:26-28` says repeats are "the business of
   control flow", and `_plans/completed/division-event.md` records that as
   out of scope with the resolution policy already written (explicit wins,
   derived fills gaps, mismatch warns). Nothing for volta brackets, repeat
   counts, jump targets, measure-repeat signs. Hymns, marches, pop, jazz and
   folk sheets hit this constantly; `walk_line` handling a cyclic NEXT chain
   is the only structural hook today. MusicXML `<repeat>`, `<ending>`,
   `<sound dacapo/dalsegno/tocoda/fine>`; LilyPond `\repeat volta`,
   `\alternative`, `\mark`.

5. **Gradual tempo change** (rit., rall., accel., with dashed extension).
   Already in `_plans/revisit.md`; a span with no `MarkType` and no marks.

6. **Serialization** (practical rather than musical). All six JSON
   load/save methods on `OmkGraph` raise `NotImplementedError`. An importer
   produces a graph that can then only live in memory; without a native
   save format the importer's output cannot be inspected, diffed, or
   round-tripped in tests except by re-importing.

#### Tier 2: common, an object exists, but the importer forces a design rule

7. **Ties have two homes.** `TiedDuration` (one event drawn as several tied
   noteheads) and the `tie` span mark (two events). A tie across a bar line
   must be two events because the `DivisionEvent` sits between them in the
   NEXT chain, so the two-event form is the general one. MusicXML and
   LilyPond both hand the importer separate notes. Rule needed: probably
   "always two events plus a tie spanner; `TiedDuration` is what duration
   arithmetic produces, not what an importer emits", or the reverse for
   within-bar ties. Exporters need the same rule in reverse.

8. **Per-tone attachments inside a chord.** `NoteEvent.tones` is a
   `set[Tone]`, so nothing can attach to one tone of a chord: a tie on one
   chord tone, fingering per string, a notehead shape or cautionary
   accidental on one tone, a cross-staff tone. MusicXML notes are per
   notehead, so every chord arrives with per-tone data. Options: split into
   zero-displacement branched single-tone events when per-tone data exists
   (the graph already says "same performer, same time"); or a per-tone
   payload on the event. Guitar and piano pedagogical editions hit this on
   every page; orchestral parts rarely.

9. **Written vs. sounding pitch.** `Stint.transposition` is "how this Part
   reads the shared events" (clarinet in A reading a concert line), which
   implies events hold concert pitch and the Stint carries the written
   offset. That rule fits transposing instruments, octave-transposing clefs
   and 8va lines (the ottava marks are visual only) if written down once:
   importer converts written to sounding, sets `Stint.transposition`, keeps
   the ottava spanner as notation. MusicXML `<transpose>`, LilyPond
   `\transposition`. Not a missing object, but undecided in the docs.

10. **Instrument identity and score order.** `Part` is a name ("for now",
    `part.py:18`; "instrument concept deferred" in the compound-lines plan).
    Missing on the page: part abbreviation (every system after the first),
    the order of parts top to bottom, and bracket/brace grouping of a choir
    or string section (MusicXML `<part-list>` / `<part-group>`; LilyPond
    `StaffGroup`, `PianoStaff`, `ChoirStaff`). `LineGroup` is a timing
    origin, not a bracket, and groups do not nest. MIDI program / sound id
    belong to the planned MIDI system and can go to `meta`.

11. **A line has no node.** "A line is not a node; it is identified by its
    head" (`graph/__init__.py:7-8`). So line-level facts an importer knows
    (this is staff 2 voice 1 of the piano part; this voice is named "Alto")
    have no home except the head event's `meta`, a Stint, or a group. Staff
    assignment and cross-staff movement need somewhere to live before an
    exporter can rebuild a piano part. Related: the obvious mapping of a
    MusicXML second voice is a `Branch`, and the percussion plan says
    `Branch` "may be scaled back or removed with more discovery", so an
    importer would settle that question.

12. **Context in force.** `_plans/revisit.md` records that there is no
    `context_in_force(event, kind)` query. An importer does not need it; an
    exporter and every MusicXML `<attributes>` block does.

#### Tier 3: present on many pages, but presentational or rare; `meta` is defensible for now

13. **Beams.** Zero occurrences. Explicit in every MusicXML file, often
    meaningful (vocal beaming by syllable, irregular groupings). Could be a
    non-binding span mark later; droppable on first import.
14. **Tuplet bracket / number display.** The ratio lives on each duration
    (`MetricalDuration.ratio`); membership is inferred from equal ratios,
    nesting by composing ratios. No grouping object, so "show bracket",
    "show number as 3:2" have no home. Semantics are complete; only display
    is missing.
15. **Stems, noteheads, notehead size (cue, grace), accidental display
    (cautionary, parenthesized, editorial), placement above/below, dashed
    vs. solid lines.** Presentation. Noteheads are explicitly deferred in
    the compound-lines plan. Shape-note (sacred harp) noteheads derive from
    scale degree; slash notation is already the zero-tone `NoteEvent`.
16. **Value-carrying marks.** `Mark` is frozen with no payload: tremolo
    stroke count, trill/turn accidental, harmonic touching pitch, bend
    amount, fingering beyond 0-5 or substitutions ("3-1"), pedal change
    notch. Tremolo count is common in orchestral parts.
17. **Multi-measure rests, measure numbers, pickup flags.** All derivable
    from divisions and durations; MusicXML `<multiple-rest>`, `number`,
    `implicit="yes"` can go to `meta` on the `DivisionEvent` or rest.
18. **Lyrics.** Elision and extender-line parsing were deferred in the
    lyrics plan; the graph already represents a melisma (extender) as the
    absence of a LYRIC edge and an elision as two syllables on one note, so
    only `parse_lyrics` and the MusicXML `<extend>`/`<elision>` mapping are
    open. Verse numbers exist (`LyricSection.section_number`).
19. **No-chord ("N.C.") and chord-symbol spelling.** `ChordEvent.chord`
    requires a `ToneCollection`; nothing says "no harmony here". Symbol
    text style (Cmaj7 vs. CΔ7) is presentation.
20. **Figured bass and Roman numerals.** Promised in `docs/overview.md`
    ("unrealized figured bass"); nothing exists. Rare on an average page;
    analysis is a planned separate package.
21. **Ossia and cue notes.** VARIATION_OF and REFERENCES edge types are
    declared and unused; no small-size flag. Rare.
22. **Unmeasured music.** `MeterEvent(meter=None)` means undefined, not
    "senza misura"; cadenzas and chant need the distinction eventually.
23. **Spacer rests** (LilyPond `s`, MusicXML `<forward>`). A zero-tone
    `NoteEvent` means "unspecified", not "deliberately nothing"; an importer
    needs a rule (probably zero-tone event plus `meta`).
24. **Microtones.** `TonalVector` is integer chromatic; MusicXML
    `<alter>0.5` and LilyPond `cih` are out of the WSMN system by design
    (separate tuning package planned). Importer should warn and skip.
25. **Tempo ranges and approximations.** `Tempo(n, beat)` takes one `int`;
    "♩ = 60–66", "ca. 120" and parenthesized editorial marks have no
    field. Common in critical editions, rare in pop.
26. **Cut and common time glyphs.** `TimeSignature.presentation` is a free
    string pair, so `("C", "")` is expressible and `_scale_presentation`
    already tolerates it, but `cut_time` and `common_time` are defined with
    numeric presentations and there is no glyph constant.
27. **Chord-symbol kinds.** MusicXML `<harmony>` gives root, a `kind` from
    a fixed list, and `<degree>` alterations; LilyPond `\chordmode` gives a
    string. There is no `kind`-to-`ChordType` table and no
    `Chord.from_string`, and a chord with arbitrary degree alterations may
    not be one of the ~80 ready-made types (constructing a one-off
    `ChordType` is possible). Also no "N.C." (gap 19).

### What the two source formats would each hand the importer

**MusicXML** is a fixed schema every notation program exports. Its
organizing units are `<part>` and `<measure>`, both of which OMK
deliberately lacks, so the importer's core job is: one line per (staff,
voice), a `DivisionEvent` at each measure boundary, `<attributes>` into
context events, `<backup>`/`<forward>` into voice bookkeeping, `<note>`s
with `<chord/>` merged into one `NoteEvent`, `<tie>`/`<tied>` into the rule
in gap 7, `<time-modification>` into duration ratios, `<direction>` into
marks (dynamics, hairpins, pedal, octave shift, tempo) or the missing text
object, `<harmony>` into `ChordEvent`, `<lyric>` into syllables. Almost
every mark it can name already exists. What it cannot place today: clef,
metadata, text, rehearsal marks, repeats/endings, rit./accel., beams,
per-notehead data, part abbreviation and order.

**LilyPond** is a programming language (variables, Scheme, `\relative`,
music functions), so a general parser is a large project; a practical
importer targets a subset. `TonalVector.from_ly` already parses pitches
with relative octaves. Beyond the same conceptual gaps, the ly-specific
constructs with no home are `\repeat volta` / `\alternative` (gap 4),
`\mark` (gap 3), `\clef` (gap 1), `\header` (gap 2), `\new Staff` /
`StaffGroup` / `PianoStaff` (gaps 10-11), `\transposition` (gap 9),
markup text `^"dolce"` (gap 3), `R1*4` (gap 17), `s` (gap 23). Everything
else (`\key`, `\time`, `\tempo`, durations and dots, `\tuplet`, `\grace`,
`~`, `(`/`)`, `\<`, `\!`, articulations, `\chordmode`, `\drummode`,
`\addlyrics` with `--`) maps onto existing objects. Recommendation: build
the MusicXML importer first; a LilyPond *exporter* is already promised in
the overview and is far easier than an ly importer.

### Later slices (the order suggested before this plan)

Each is a small, separable piece of work in the style of the recent
commits; the first three unblock any importer, the rest widen coverage.

1. `Clef` value in `systems/wsmn/scoring` and `ClefEvent(ContextEvent)`.
2. `GraphMeta` fields for title / composer / lyricist / arranger /
   copyright / opus, or a metadata dataclass it holds.
3. A text direction object (point and span) attached with ANNOTATES, and a
   rehearsal mark; decide whether formal sections reuse `Spanner`.
4. Write down the tie rule (gap 7) and the written-vs-sounding rule
   (gap 9) in the docs; no code.
5. Native JSON save/load, so importer output has somewhere to go.
6. Control flow (repeats, endings, navigation), following the policy
   already in the division-event plan.
7. Gradual tempo (revisit entry); `Part.abbreviation` and part order;
   per-tone attachments (gap 8) once a guitar or piano fixture needs them.

### How the analysis was verified

This was an assessment, so verification was: each "nothing exists" claim
above was checked by grepping `src/` for the concept and its synonyms, and
each "exists" claim by reading the defining file. The Explore agents'
reports agree with the direct reading. Anything the user disputes can be
re-checked with a grep of the named term.
