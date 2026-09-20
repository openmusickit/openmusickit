# Plan: compound lines (voices, branches, pins, doubling)

Status: **implemented 2026-09-20** (edges, `Part`/`Stint`, `GraceDuration`, graph
walkers/timing/stints/materialize, `tests/graph/test_compound_lines.py`). Written
2026-09-20 from discussion. Percussion (the conversation's starting point) is parked;
see "Deferred" at the end.

Notes from implementation:
- `walk_stint` yields the events as they are and the consumer reads
  `stint.transposition` once, rather than yielding `(event, transposition)` pairs.
- `materialize(stint)` makes an exact copy of the music on the span (decided
  2026-09-20): events with their NEXT/BRANCHES, plus every mark, annotation, spanner
  and lyric syllable attached to them and whatever attaches to those, with all edges
  among the copied things (one deepcopy memo, so a run of syllables still shares one
  `Word`). Not copied: pins to other lines, other Parts' stints, and any spanner that
  reaches beyond the covered events (dropped with an `OmkWarning`, since the copy has
  no event for its far end).
- `GraceDuration` subclasses `ZeroDuration`, so existing zero-width handling in
  duration arithmetic applies unchanged; all graces compare equal by length.
- `RustworkxAdapter.get_edge_endpoints` (and source/target) returned backend ids,
  not nodes; fixed, since the timing walk is their first caller.

## Context

The graph has one sequential relation, `NEXT`, and it does two jobs: it carries a
relative timing payload (`anchor` + signed `displacement`, `graph/edge.py:60-64`)
*and* it asserts "same line, consecutive". Every walker assumes the second
(`get_next` returns the first NEXT successor it finds, `rx_adapter.py:248`;
`transform_tones`, `zip_lyrics_to_objects` follow one thread; `add_next` never checks
for a second outgoing NEXT). So the model can already say "Y starts when X starts"
but doing so silently breaks every traversal. This is the biggest pitfall of the graph
model: piano music, fugues, drum-kit hands/feet, a one-measure second voice, and
"a melody plus three bars of chords plus a countermelody for bars 12–16" all need
several NEXT chains related in time.

Finale offers two mechanisms (whole-piece layers; a Voice-2 burst inside a measure).
OMK should do both with one mechanism, and also support music that is incomplete and
not written left-to-right from a single origin.

## The model

Three relations. Two of them share a timing payload; they differ in what they assert
about *membership*.

### NEXT — sequence only
- Pure sequence within a line. **No payload** (anchor/displacement removed).
- Invariant, enforced in `OmkGraph.add_next`: at most one incoming and one outgoing
  NEXT per event.
- A **line** is a maximal NEXT chain, identified by its head. A line is not a node.
- Definition: a line is *something being done*. Usually one performer doing it; with
  doubling, several.

### Branch — same doer, a second thing
- The head of a child line hangs off any event of a parent line.
- Carries `anchor: TimingAnchor` (ONSET/OFFSET of the parent event) and signed
  `displacement: Duration | None`.
- Asserts **ownership**: the child belongs to whoever performs the parent. Span walks
  (transpose this part, export this staff) include branches.
- Whole-piece layer (LH/RH, drum hands/feet): child head branched from parent head at
  ONSET+0. One-measure second voice: child branched from the coinciding event (ONSET+0)
  or the preceding one (OFFSET+0). Same edge, different child length. A voice that
  ends just ends; no join/merge edge (a join would give the target two timing paths).
- A head has at most one incoming Branch. Chord divisi inside one `NoteEvent` stays as
  is (degenerate case: identical rhythm); explode/merge between the two forms is a
  future normalizing operation.

### SIMULTANEOUS — a pin between independent lines
- Between any two `SequentialEvent`s in any lines. Same payload as Branch
  (anchor + displacement: the chords may enter a beat after the melody; the
  countermelody may enter under a held note with nothing to pin to exactly).
- Symmetric in meaning (stored directed; queried via `neighbors`).
- Asserts **no ownership**. Span walks never pull a pinned line in.
- This is how incomplete music is joined without a score origin, and later how
  music pins to video keyframes and to a **clock line** (a chain of timestamp events in
  a clock-based temporal system) for musique concrète / stopwatch scores. That covers
  onset-based material without touching NEXT.
- There is no `Score` root. A score is a connected component. `Score`/`Section` may
  arrive later as metadata containers/spanners, not as timing roots.

### Timing consequences
- Branch alone makes timing a tree (always consistent). Pins make it a constraint
  graph: two pins between the same lines can disagree with the lines' internal
  durations. That is *checked and reported* (`OmkWarning` / an explicit check), not
  forbidden — "your countermelody doesn't fit where you pinned it" is a musical fact.
- "Where is X" only ever means "relative to a reference event", only within the
  connected component. `duration=None` events are opaque to propagation.

### Grace notes — a duration, not an edge
- The one within-line case that looked like a NEXT exception. Handle it in
  `values/time`: a nominal duration with **zero metrical width** (limit case of the
  existing nominal-vs-actual machinery: tuplets, `TiedDuration`,
  `duration.py:249`, `metrical_duration.py:255`). Stays in the NEXT chain.
  Walkers generally treat it normally:
   - grace notes transpose.
   - a grace note is under a slur or not by where the composer starts the spanner.
   - lyrics are the exception: `zip_lyrics_to_objects` skips grace notes by default
     (they are sung as part of the target note's syllable), like rests and
     `ContextEvent`s; `connect_lyric_to_object` can still put a syllable on one.

- On-the-beat vs before-the-beat (appoggiatura/acciaccatura, the slash) is semantic
  and notated → a property of the grace. *How much* it steals and from which neighbour
  is realization → outside core.
- Ruled out of core as NEXT payload: legato overlap (notated normally), expressive
  timing (future "OMK Performance" extension; `REALIZES` edge exists), onset-only/IOI
  data (MIDI is its own system, as docs already say; clock line + pins for the rest).
- Reverses the `revisit.md` resolution "durations are signed values
  (`Next.displacement`)" in form only: signed displacement still lives on Branch and
  SIMULTANEOUS.

### Part and Stint — the two new nodes; doubling
- `Part(OmkObject)`: the performer. Minimal fields (name); instrument concept deferred.
- `Stint(Spanner)`: a Part's run on a line. `Part —PERFORMS→ Stint —STARTS_AT→ event`,
  optionally `—ENDS_AT→ event`; no `ENDS_AT` means "to the end of the line, however
  long it grows" (the `transform_tones(end=None)` convention). A Part with several
  stints on several lines is the normal orchestral case (2026-09-20: decided over
  paired PERFORMS_FROM/UNTIL edges, which cannot pair a start with its stop). A full
  performer's part is the Part's stints ordered by `relative_onset` — orderable only
  within a connected component, which is honest.
- **Doubling** = two Parts with stints over the same events. Marks and lyrics on
  shared events are shared by definition. When the parts diverge (different dynamic,
  one drops out), **fork**: `materialize(stint)` copies the covered span and re-points
  the stint. No per-Part marks on shared events.
- The Stint carries an optional tone operation, as a *value*:
  `transposition: Interval | None` (`TonalVector` is already an interval). Piccolo
  doubling 8va, and **transposing instruments as views of the concert-pitch line**.
  Generalize only when a second kind appears (unpitched kit remap is the likely one),
  and then as a tuple of small declarative `ViewOperation` values, never raw callables
  (2026-09-20: `[Callable, *args]` lists rejected — not serializable, and a consumer
  reading through a view must be able to *inspect* the operation, not just run it).
- Reading through a view never manufactures transformed `NoteEvent`s (phantom ids);
  traversal yields `(event, transposition)` and the consumer applies it.
- A Stint never starts at a branched head; the parent's stint covers it.

### Walkers: two modes
- **Along a line**: NEXT only. Lyrics, slurs/ties, "next note in this melody".
  Existing behaviour, stays correct.
- **Over a span**: NEXT plus owned branches whose heads fall inside the range.
  `transform_tones(start, end)` becomes a span walk. Pinned lines are excluded.

## Implementation sketch (when scheduled)

1. `graph/edge.py`: `TimedEdge(OmkEdge)` base with `anchor`, `displacement`, `nudge`;
   `Next(OmkEdge)` loses its payload; `Branch(TimedEdge)`, `Simultaneous(TimedEdge)`.
   New `EdgeType` members `BRANCHES`, `PERFORMS` (consistency-audit item 2.14 wants
   one grammatical form for `EdgeType`). Remove `SIMULTANEOUS` from "unused".
2. `objects/part.py`: `Part(OmkObject)`, `Stint(Spanner)` with `transposition`.
3. `values/time`: grace duration (zero metrical width, nominal value) + on/before-beat;
   WSMN symbols for it.
4. `graph/graph.py`: enforce NEXT invariant in `add_next`; `add_branch(parent_event,
   head, anchor=ONSET, displacement=None)`; `add_simultaneous(a, b, ...)`;
   `add_stint(part, start, end=None, transposition=None)`; `walk_line` / `walk_span`;
   `transform_tones` → span; `relative_onset(a, b)`; `check_alignment()` warning;
   `materialize(stint)`; `zip_lyrics_to_objects` skips grace notes.
5. `rx_adapter.py`: `get_next`/`get_previous` unaffected once the invariant holds;
   add an "owned branches from event" query.
6. Docs: goals/architecture note on lines vs parts vs pins; update `revisit.md`.

## Verification (when scheduled)

Doctests / tests covering, at minimum:
- piano: RH line with a one-measure second voice branched mid-line; LH layer branched
  head-from-head; span-transpose covers all three, line walks don't cross.
- incomplete music: 16-bar melody, 3-bar chord line pinned at bar 1, countermelody
  pinned at bar 12 with a displacement; a deliberately inconsistent second pin
  produces the warning.
- doubling: piccolo `Part` with a `Stint(transposition=P8)` over the flute line,
  ending mid-line while the flute carries on; materialize forks correctly.
- grace: a run of grace notes adds zero width; lyrics zip past them; a manually
  attached syllable on a grace note stays.
- `add_next` refuses a second outgoing/incoming NEXT.

## Deferred (from the percussion survey that started this)

- Unpitched tone: instrument vs stroke as the unit; open per-system vocabulary with
  aliases and relative height; transform pass-through by system compatibility instead
  of `type(tone) is SilentTone`; mixed pitched/unpitched `NoteEvent` policy; kit as a
  `ToneCollection`.
- Notation layer: noteheads, staves/clefs, drum maps, sticking, rolls, ghost notes,
  choke, stick/mallet directives.
- Percussion duration = inter-onset (notated ≠ sounding by instrument kind).
- MIDI as its own system (likely awkward on the graph; separate design).
- **Sync lines** (deferred 2026-09-20, dev note): the clock line is probably one
  instance of a more general *sync line* — a reference line made of any Measurable
  duration that other lines pin to. MIDI is likely an instance (ticks are metrical
  with a tempo map to clock). The same idea maps to West African timeline/bell
  patterns, gamelan colotomic structure, and drum loops (an actual expert is needed
  for those). Open: whether a sync line is a *type* or a *role* any line can play;
  how a `Simultaneous` displacement is expressed across temporal systems (in the
  anchor's system, with ONSET+0 universal, is the obvious first answer).
