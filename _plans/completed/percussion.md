# Plan: unpitched percussion

Status: **implemented 2026-09-23** (`UnpitchedTone`; `PercussionTone`,
`RelativePitch`, `Stroke`, `WSMN_PERCUSSION`; `PercussionPart`, `LineGroup`,
`Contains`, the group methods on `OmkGraph`; percussion symbols and palettes;
twelve marks; docs). Written as an exploratory memo 2026-09-22, revised
2026-09-23 after dialog; the developer's final notes: the §3 vocabulary is a
start to amend later, body percussion is a palette, the ready-made open tones
are `open_hat` and `open_hand`, and string output through `Tone.__format__`
must work for a tone whose `pitch` is None.

Notes from implementation:

- The tone's field is `relative_pitch`, not `pitch`: a field named `pitch`
  would shadow the `Tone.pitch` property (`PitchRepresentation | None`) that
  `Tone.__format__` reads, and a relative pitch is not a pitch. `pitch` stays
  None, so `f"{tone}"` gives `str(tone)` ("high open", "hit") and a format
  spec is ignored rather than an error.
- `RelativePitch` is an `IntEnum` (ordering for free) with `__str__` giving
  the display form ("low-mid"); `Stroke` values are display forms with
  spaces ("rim shot").
- Palettes include the stroke-only tones as well as the pitched ones (a lone
  djembe plays "slap" with no relative pitch), so `hand_drums` has 40 tones,
  `toms` 36, `bass_drums` 12. `open_hand` is an alias of `open_hat` (one
  object), so the symbol sweep's `distinct` sees one tone.
- `Contains` fixes `anchor` to ONSET with `init=False`; `_timing_neighbours`
  treats a `LineGroup` as a node of the timing graph, so `relative_onset`
  crosses a group and `check_alignment` reports a pin that disagrees with it.
- `add_branch` also refuses a head that is a line of a group, the mirror of
  `add_to_group` refusing a branched head.
- `walk_group` and `group_members` yield lines in no particular order (the
  adapter's edge order is not insertion order), like `stints`.
- The compound-lines piano fixture now puts the left hand in a group; the
  mid-line second voice stays a branch. The `add_branch` docstring and the
  `graph` package docstring no longer call the drummer's feet a branch.
- The thorough Hypothesis profile fails the graph state machine before and
  after this work (`_plans/revisit.md`); the default profile is green.

---

## 0. Decisions so far

1. **`UnpitchedTone(Tone)`** is an abstract marker in `values/tone`
   (no members beyond `Tone`; `pitch` is already `None` there).
   **`PercussionTone(UnpitchedTone)`** is WSMN's implementation, in a new
   `systems/wsmn/percussion/` package with its own `TonalSystem`,
   `WSMN_PERCUSSION`, which is not `compatible_with(WSMN)`:
   nothing here transposes.
2. **A tone abstracts over instruments, as a pitch does.**
   `PercussionTone(pitch, stroke)`: a relative pitch and a stroke,
   either or both unspecified.
   `PercussionTone(HIGH, OPEN)` is the same value on congas, bongos or
   a djembe pair, and the Part says which.
   `PercussionTone()` is a plain hit: a triangle part or a concert bass
   drum part is a line of these, with a stroke only where it differs.
3. **Relative pitch** is an ordered enum of five
   (`LOW, LOW_MID, MID, HIGH_MID, HIGH`), or `None`.
   A definite pitch is never in this slot: pitched percussion
   (timpani, crotales, tuned roto-toms) is a `TonalVector` with technique
   `Mark`s, like any pitched instrument.
4. **Stroke** is a closed `StrEnum` in WSMN percussion.
   `None` is the ordinary stroke.
   A stroke in the enum is spelled as a stroke, never as a mark;
   anything not in the enum ("hit it with a feather duster") is a plain
   tone with a custom technique `Mark`.
   Same precedent as `BarLineComponent`.
5. **Part is the instrument** (Violin, Flute, Congas), and by extension
   whoever plays it.
   A drum kit, or a percussionist covering snare, triangle and cymbals,
   is **several Parts, one per instrument, each on its own line**,
   with the lines held together by a **group node** (decision 9).
   Combining them onto one staff is the renderer's job.
   No performer node.
6. **Palettes.** A `ToneCollection` of `PercussionTone`s is a curated
   vocabulary for a *class* of instrument (hand drums, snare drum,
   hi-hat, cymbal, ...): tested, and eventually with output mappings.
   **`PercussionPart(Part)`** carries one, optionally.
   Core never validates against it; an app may warn, an exporter may
   refuse.
7. **No legend on the graph, no `Kit(ModalContext)`.**
   A key changes how tones are read, not what they are, and a drum map
   only matters to output targets.
   Drum maps and MIDI maps are deferred to the output work;
   if one ever needs to sit in a line it is its own
   `PercussionMap(ContextEvent)`.
8. **Branch stays, scaled down in meaning.** It is Finale's V1/V2:
   a second voice inside one instrument's line.
   A branched line never has a Part of its own; the parent's Stint
   covers it (the existing rule, unchanged).
   Whether Branch is later scaled back further or removed is left to
   discovery; it does not get in the way of this work.
9. **A group node holds lines together.** A `LineGroup` (name open)
   points at line heads (the first event of each NEXT chain) with
   CONTAINS edges and defines those lines as a unit.
   **CONTAINS is a `TimedEdge`** measured from the group's origin,
   default zero displacement: the group is a local timing origin for
   its lines, so a kit or a piano needs no pins, a component entering
   at bar 9 has a displacement, and `relative_onset` crosses the group.
   A Part points either at a line head through a Stint (kit components,
   multi-percussion: one Part per line) or **directly at the group with
   a PERFORMS edge** (piano, organ, harp: one Part for all the lines;
   whole lines, so no run to bound and no Stint).
10. Vocabularies are drafted in §3 for the developer to strike or extend.

---

## 1. The model

### 1.1 Values

```python
# values/tone/unpitched_tone.py
class UnpitchedTone(Tone):
    """A sound with no pitch. The general idea behind a drum stroke, a
    tabla bol, a cymbal crash: WSMN's `PercussionTone` is one
    implementation. `pitch` is None; a system decides what else a sound
    is made of."""
    __slots__ = ()


# systems/wsmn/percussion/wsmn.py
WSMN_PERCUSSION = TonalSystem(
    "WSMN percussion",
    "Unpitched sounds as Western notation distinguishes them: "
    "a relative pitch and a stroke, on whatever instrument the Part names.",
)


# systems/wsmn/percussion/percussion_tone.py
class RelativePitch(IntEnum):
    """Which member of a family of like instruments: the low conga, the
    high bongo, the second of four toms. Ordered, so LOW < HIGH."""
    LOW = 1
    LOW_MID = 2
    MID = 3
    HIGH_MID = 4
    HIGH = 5


class Stroke(StrEnum):
    """How the instrument is struck (§3.2)."""
    ...


@dataclass(frozen=True, slots=True)
class PercussionTone(UnpitchedTone):
    """A relative pitch and a stroke, each optional. `PercussionTone()`
    is a plain hit on whatever the Part is.

    >>> PercussionTone(pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)
    PercussionTone(pitch=RelativePitch.HIGH, stroke=Stroke.OPEN)
    >>> str(PercussionTone(stroke=Stroke.RIM_SHOT)), str(PercussionTone())
    ('rim shot', 'hit')
    """
    pitch: RelativePitch | None = None
    stroke: Stroke | None = None

    @property
    def tonal_system(self) -> TonalSystem:
        return WSMN_PERCUSSION
```

- Frozen, hashable, compares by value; a set member in a `NoteEvent`.
  Not tuple-shaped, so it cannot collide with `TonalVector.__eq__`,
  which compares equal to plain tuples.
- A custom `__repr__` is required (the default prints
  `<RelativePitch.HIGH: 5>`), on the AGENTS.md round-trip rule.
- `Tone.__format__` already falls back to `str()` when `pitch` is None;
  `__str__` is the readable form.
- `from_string` is not implemented on the class (no single string
  grammar; LilyPond's `hho` names an instrument *and* a stroke, which
  is an exporter's table, not a tone's).
- `IntEnum` for `RelativePitch` gives ordering for free;
  the name is read from `.name` when printing.

### 1.2 Palettes

`ToneCollection(tones=[...], root=None, name="hand drum")`, in
`systems/wsmn/percussion/symbols.py`, one per instrument class (§3.3).
Ordered low to high and then by stroke.
A palette is a convenience and a contract for output, not a type:
`ToneCollection.transform` already works on it (a remap is a
`Tone -> Tone` callable), `in` works for validation at the app level.

### 1.3 Part and PercussionPart

`Part` becomes the instrument.
Docstring changes ("an instrument, and by extension whoever plays it");
no fields change.

```python
@dataclass(kw_only=True, slots=True)
class PercussionPart(Part):        # objects/part.py; imports only values
    """An unpitched instrument, with the palette of tones it is expected
    to use, if one has been chosen. Core never checks; an exporter may."""
    palette: ToneCollection | None = None
```

The specific instrument (congas rather than bongos, both on the `hand_drum`
palette) is the Part's `name` for now.
An exporter that needs a GM key or a LilyPond drum name will need a
firmer identity than a display name; that is the deferred "instrument on
Part" question and is noted in §4.

### 1.4 LineGroup

```python
@dataclass(kw_only=True, slots=True)
class LineGroup(OmkObject):        # objects/part.py or objects/line_group.py
    """Lines that belong together as one unit: the components of a drum
    kit, the hands of a pianist, the manuals and pedal of an organ.
    Holds line heads with CONTAINS edges. A Part points at the group
    when one instrument plays all of its lines, or at a line head when
    each line is its own instrument."""
    name: str | None = None
```

- A line is a maximal NEXT chain identified by its head; the group
  points at heads.
  Invariant: the target of a CONTAINS edge has no incoming NEXT and no
  incoming Branch (a branch belongs to its parent's line, which is
  already in the group through its own head).
- **Timing.** `Contains(TimedEdge)`: `anchor` is meaningless here (the
  group has no onset/offset of its own) and is fixed to ONSET;
  `displacement` is the member's start measured from the group's
  origin, default `None` meaning zero.
  `_timing_neighbours` treats a group like an event: two heads in one
  group are `displacement_b - displacement_a` apart, and
  `relative_onset(rh[0], lh[3])` works with no pin.
  `check_alignment` extends naturally: a pin between two lines that are
  also in one group is a second timing path and is checked.
  The group is a local origin, not a score root; a score is still a
  connected component.
- **Part to group.** `Part —PERFORMS→ LineGroup`, a plain edge.
  `stints(part)` stays as it is; a new `groups(part)` (or one
  `performs(part)` yielding both) gives "everything this Part does".
  `Stint.transposition` is not available for a group; if a doubled
  group ever needs a view, that is the `ViewOperation` work.
- Nesting (a kit inside a rhythm section, sections of an orchestra) and
  a line in more than one group are not needed now; no invariant either
  way until one is.

---

## 2. The graph

### 2.1 A drum kit

```python
from openmusickit.systems.wsmn.percussion.symbols import hit, closed  # ready-made tones

hh = [NoteEvent(tones={closed}, duration=eighth) for _ in range(8)]
sn = [Rest(quarter), NoteEvent(tones={hit}, duration=quarter),
      Rest(quarter), NoteEvent(tones={hit}, duration=quarter)]
bd = [NoteEvent(tones={hit}, duration=quarter), Rest(quarter),
      NoteEvent(tones={hit}, duration=quarter), Rest(quarter)]

graph.add_line(hh); graph.add_line(sn); graph.add_line(bd)
kit = LineGroup(name="Drum kit")
graph.add_group(kit, [hh[0], sn[0], bd[0]])          # one unit; heads aligned at the group's origin
graph.add_stint(PercussionPart(name="Hi-hat", palette=hi_hat), Stint(), hh[0])
graph.add_stint(PercussionPart(name="Snare", palette=snare_drum), Stint(), sn[0])
graph.add_stint(PercussionPart(name="Kick", palette=bass_drum), Stint(), bd[0])
```

- One line per instrument; tones on each line are just (pitch, stroke).
  A kick and a closed hi-hat at the same moment are two events on two
  lines, aligned through the group, not two tones in one event.
- A tom line may carry `LOW..HIGH` for four rack toms on one Part, or
  each tom may be its own Part; the palette and the author choose.
- A second voice inside one component (a snare fill under the
  backbeat) is a Branch off the snare line, with no Part of its own.
- `walk_line(sn[0])` is the snare; "everything in the kit" walks each
  member line of the group; `transform_tones` over a line with a remap
  callable re-voices it, and over the group's lines re-voices the kit.
- Hands-up / feet-down, one voice vs two, staff position, notehead:
  all rendering, from the map (deferred), the Parts and the group.
- Weinberg's improvisational notation costs nothing:
  "time" and fills are `NoteEvent(tones=set())` (a duration with
  unspecified content, already defined that way);
  a kick line is a pinned cue line; "ad lib", "fill", "solo",
  "as written" are text marks; simile marks are control flow (later).
- Flams, drags and ruffs are one, two and three `GraceDuration` events
  before the main stroke.
  Rolls are the existing `tremolo` mark.
  Ghost notes, chokes, sticking and beaters are marks (§3.4).
- Cyclic lines (`walk_line` already handles them) cover drum loops.

### 2.2 Piano, organ, harp

One Part, one group, two or three lines:
`add_group(piano_group, [rh[0], lh[0]])` and the Part points at the
group.
A one-measure second voice in the right hand is a Branch, as today.
This replaces the whole-piece "LH branched from RH head" idiom in the
compound-lines doctests; those examples move to the group.

### 2.3 Multi-instrument percussionists

Snare, triangle and suspended cymbal for one player:
three Parts on three lines in one group named for the player
("Percussion 1").
The renderer combines them onto one staff, or three one-line staves,
or a grid; that choice is presentation (Dorico's three kit
presentations) and not in core.
Without a group the three lines are simply pinned, and nothing is said
about who plays them.

### 2.4 `NoteEvent` policy

- **Mixed sets are allowed.** `{A2, PercussionTone()}` on a timpani
  line whose player also has a pedal bass drum is legal; nothing checks
  tonal systems inside a `NoteEvent` today and nothing should start to.
  With one line per instrument this will be rare anyway.
- **Pass-through.** `NoteEvent.transform_tones` skips
  `type(tone) is SilentTone` (`note_event.py:135`).
  Change it to skip `tone.tonal_system.universal`, which is what
  `universal` is for.
  Cross-system pass-through ("transpose the C, leave the hit") needs an
  operation that declares its system; until declarative operations
  exist, `TonalVector.transpose(PercussionTone(), M3)` raises, which is
  loud and correct.
- **Rests** are ordinary `Rest`s.

---

## 3. Drafted vocabularies (for review; strike or add)

### 3.1 `RelativePitch`

`LOW, LOW_MID, MID, HIGH_MID, HIGH`.
Covers every hi/lo pair (bongos, congas, timbales, agogo, wood blocks,
cowbells), GM and LilyPond's four rack toms (`toml, tomml, tommh, tomh`),
two floor toms as a separate Part, five temple blocks.
Larger families (Weinberg's ten toms) split across Parts.
Ordering of a whole setup on a staff is the map's business.

### 3.2 `Stroke`

Glosses in prose; the LilyPond/GM names each member covers in brackets.

Drums, struck with sticks or mallets:

- `CENTER`: centre of the head (Weinberg's centre/edge indications).
- `EDGE`: near the rim; also the edge of a cymbal or gong.
- `RIM`: the rim alone (rim click).
- `RIM_SHOT`: head and rim at once.
- `CROSS_STICK`: stick laid across the head, striking the rim
  [sidestick `ss`, `ssh`, `ssl`].
- `SHELL`: the shell of the drum.
- `DEAD`: pressed stroke, no rebound (dead stroke).

Hand drums:

- `OPEN`: open tone, flat hand at the edge ("open palm")
  [`boho`, `bolo`, `cgho`, `cglo`; also open hi-hat, open triangle,
  open cuica `cuio`].
- `SLAP`: slap tone.
- `BASS`: bass tone, palm in the centre.
- `MUTE`: muted or muffled [`bohm`, `bolm`, `cghm`, `cglm`, `cuim`,
  `trim`].
- `PALM`: flat palm, muffled thump.
- `FINGER`: finger stroke or flick ("finger flick on the low bongo").
- `FIST`: closed fist.
- `HEEL`, `TOE`: heel-toe rocking strokes.

Hi-hat and cymbals:

- `CLOSED` [`hhc`], `HALF_OPEN` [`hhho`], `PEDAL` [`hhp`],
  `FOOT_SPLASH` (pedal opened and released; Weinberg's foot splash).
- `BELL`: the bell of a cymbal [`rb` ride bell].
- `CRASH`: a crash stroke on any cymbal (a ride can be crashed).

Small instruments:

- `SCRAPE`: guiro, cabasa, the edge of a gong [`gui`, `guis`, `guil`].
- `SHAKE`: a single shake of a shaker, maracas or tambourine.
- `THUMB_ROLL`: tambourine friction roll.

Candidates I left out, with the reason:
`BUZZ` (a roll: `tremolo` mark), `CHOKE` (after the hit: mark),
`FLAM`/`DRAG` (grace notes), `SHORT`/`LONG` for guiro and whistle
(durations), `BRUSH_SWEEP` (a beater state plus a sustained sound;
`with_brushes` mark and a duration), `STICK_SHOT` (rare; a mark).
"Rattle" from the dialog: covered by `SHAKE` plus `tremolo`, or its own
member if a distinct sound is meant.

### 3.3 Palettes (`ToneCollection`s)

Each is the meaningful (pitch, stroke) combinations for a class of
instrument; `hit` (`PercussionTone()`) is in every one.
Specific instruments in brackets are what a Part named that way would
use.

- `hand_drum` [congas, bongos, djembe, cajon, frame drums, timbales?]:
  `LOW`/`MID`/`HIGH` × `OPEN, SLAP, BASS, MUTE, PALM, FINGER, FIST,
  HEEL, TOE`, plus bare pitches.
- `snare_drum` [snare, field drum, tenor drum]:
  `RIM_SHOT, CROSS_STICK, RIM, CENTER, EDGE, SHELL, DEAD`.
- `bass_drum` [kick, concert bass drum]: `CENTER, EDGE, MUTE`;
  `LOW`/`HIGH` for a double kick.
- `tom` [rack and floor toms]: `LOW..HIGH` × `RIM_SHOT, RIM, CENTER,
  EDGE, DEAD`.
- `hi_hat`: `CLOSED, OPEN, HALF_OPEN, PEDAL, FOOT_SPLASH, BELL, EDGE`.
- `cymbal` [crash, ride, china, splash, suspended]:
  `BELL, EDGE, CRASH, DEAD`; bowed is the existing `arco` mark.
- `gong` [tam-tam, gong]: `CENTER, EDGE, SCRAPE, MUTE`.
- `bell` [cowbell, agogo, sleigh bells?]: `LOW`/`HIGH` × `OPEN, MUTE,
  EDGE`.
- `block` [wood block, temple blocks, claves, castanets, log drum]:
  `LOW..HIGH` bare.
- `shaker` [shaker, maracas, cabasa, rainstick]: `SHAKE, SCRAPE, MUTE`.
- `tambourine`: `SHAKE, THUMB_ROLL, MUTE, FIST`.
- `triangle`: `OPEN, MUTE, SCRAPE`.
- `scraper` [guiro, ratchet, washboard]: `SCRAPE`.
- `cuica`: `OPEN, MUTE`.
- Single-hit instruments (whip, anvil, brake drum, vibraslap, whistle,
  wind machine, thunder sheet, handclap): `hit` only; no palette needed,
  or one shared `single` palette.
- Body percussion (clap, snap, stomp, thigh slap): unresolved; either
  a `body` palette with `CLAP, SNAP, STOMP` strokes or four Parts.

Ready-made tones in `symbols.py`, the ergonomic layer:
`hit`, `closed`, `open_`? (name clash with the brass mark `open_` in
scoring symbols; perhaps `open_hh`), `rim_shot`, `cross_stick`,
`low`, `high`, and the `low_open`, `high_slap` pairs the hand-drum
palette uses most.

### 3.4 Marks to add (`systems/wsmn/scoring/symbols.py`)

`ghost` (parenthesised head; ARTICULATION), `buzz_roll` (z on the
stem), `choke` (TECHNIQUE; cymbals, distinct from harp `damp`),
`stick_right`/`stick_left` (FINGERING, aliases "R"/"L"),
`with_sticks`, `with_brushes`, `with_hands`, `hard_mallets`,
`soft_mallets` (TECHNIQUE, EITHER; Weinberg's standard beater
pictograms), `snares_on`/`snares_off` (TECHNIQUE, EITHER).
Already present and reused: `tremolo`, `laissez_vibrer`, `arco`
(bowed cymbal), `accent`, `open_` (brass; not for hi-hat, which is a
stroke).

---

## 4. Deferred, with what is now known about each

- **Drum map (staff position, notehead, extra glyph, voice hint).**
  Keyed by (Part's instrument, tone), not by tone alone, since the tone
  no longer names the instrument; the group says which Parts share a
  staff.
  Staff position as an int in MNX's convention (0 = middle line, ±1 per
  half-space).
  Ready-made maps: Weinberg/PAS five-line, one-line.
  Notehead as a function of duration (Weinberg's hollow diamond for
  long cymbal notes) is a map question.
  If it ever sits in a line: `PercussionMap(ContextEvent)`.
- **MIDI.** GM key on channel 10, keyed the same way; note-off is
  irrelevant where the instrument does not sustain.
- **Instrument identity on Part.** `name` is a display string; exporters
  need to tell congas from bongos on the same palette. The deferred
  "instrument" concept, now anchored: Part *is* the instrument, so this
  is a field on Part, not a new node.
- **Sustains / decay.** Notated values are stored as written (Weinberg:
  write the intended duration; short instruments are attack points).
  Whether an instrument sustains is a descriptor for realisation; it
  belongs with the instrument identity above.
- **Remap as a `ViewOperation` on `Stint`.** The second kind
  compound-lines predicted; a `Tone -> Tone` mapping value.
- **One-voice ⇄ two-voice normalisation** (merge several member lines
  into chords on one line, or explode them): a graph operation for
  later, the inverse pair compound-lines already named; now a group
  operation.
- **"The same stretch on every line of a group"** (transpose bars 5 to 8
  of the whole piano part) is a timing question, not a structural one;
  it needs `relative_onset` across the group. `walk_span`'s
  head-in-range rule for branches was never that.
- **Branch's future.** Kept as V1/V2 within one instrument; may be
  scaled back or removed with more discovery.
- **Two spellings.** With strokes in the enum, `Marking(open_)` on a
  hi-hat event is simply wrong; a validation pass may warn. Nothing in
  core.
- **Exporter needs per note**: position, notehead, glyph, voice (from
  the map); external names and sound ids (adapter tables). Nothing in
  core needs a MIDI number.

---

## 5. Still open

All structural decisions are made (§0).
What remains is review of drafts and small naming choices:

1. **The vocabularies in §3** (`Stroke` members, palettes, marks) are
   drafts to strike or extend before stage 4 is built.
2. **Names**: the group node (`LineGroup` is the working name);
   the `__str__` form of a tone ("high open", "hit");
   ready-made tone symbols (`open_` clashes with the brass mark;
   `open_hh` or similar);
   whether body percussion is a palette or four Parts.
3. **`Contains` edge shape**: whether to subclass `TimedEdge` with the
   anchor fixed, or give it only `displacement`. Decide in the code;
   nothing observable depends on it.

---

## 6. Implementation, staged

1. **Core tone.** `values/tone/unpitched_tone.py` (`UnpitchedTone`);
   `NoteEvent.transform_tones` universal check; the three "does not
   exist yet" docstrings (`tone.py:30,86`, `note_event.py:20`).
   Tests: hierarchy tests next to `test_tone_hierarchy.py`.
2. **`PercussionTone` and its enums.**
   `systems/wsmn/percussion/{wsmn,percussion_tone}.py`:
   `WSMN_PERCUSSION`, `RelativePitch`, `Stroke`, `PercussionTone`
   with a round-tripping `__repr__` and `__str__`.
   Tests: value semantics, `eval(repr(...))`, ordering of
   `RelativePitch`, a Hypothesis `percussion_tones()` strategy in
   `tests/strategies.py` and a domain entry so graph property tests mix
   pitched and unpitched events.
   The `Stroke` members are the §3.2 draft; adding or removing a member
   later is a one-line change.
3. **Part, PercussionPart, LineGroup.** Docstring flip on `Part`;
   `PercussionPart`; `LineGroup`; `Contains(TimedEdge)` and
   `EdgeType.CONTAINS` in use; `OmkGraph.add_group(group, heads,
   displacements=None)`, `group_members(group)`, `group_of(head)`,
   `add_performs(part, group)` (name open), `groups(part)`;
   `_timing_neighbours` and `relative_onset` through the group;
   `check_alignment` over group-plus-pin paths.
   Invariant in `add_group`: each head has no incoming NEXT and no
   incoming Branch.
   Compound-lines doctests that use a whole-piece LH branch move to a
   group; Branch tests stay.
   A kit test and a piano-group test in
   `tests/graph/test_compound_lines.py` or a new `test_line_group.py`;
   the graph state-machine test gains group operations.
4. **Palettes, ready-made tones, marks.** `symbols.py` in
   `systems/wsmn/percussion` (§3.3) and the §3.4 additions to
   `systems/wsmn/scoring/symbols.py`; fixture counts in
   `tests/test_fixtures.py`; palette sweeps via `symbols_of`.
   After the §3 review.
5. **Docs.** `_quarto.yml` entries; an `examples.qmd` section building
   the kit in §2.1 (the examples page has no compound-lines example at
   all yet, which percussion would fix); `graph/__init__.py` and the
   `add_branch` docstring stop citing "the drummer's feet" as a branch.

Stages 1 to 3 need nothing further; stage 4 waits on the vocabulary
review; stage 5 closes.
One commit per stage, `uv run pytest` green after each, the plan copied
to `_plans/` at the start and moved to `_plans/completed/` at the end,
as the previous plans did.

---

## 7. Survey (from the first draft, kept for reference)

| System | Identity of a note | Where position/notehead live | Sound |
|---|---|---|---|
| **MusicXML 4** | `<instrument id>` → a `<score-instrument>` per part | per note: `<unpitched><display-step/><display-octave/>`, `<notehead>`, `<stem>`, `<voice>`; `<staff-lines>` | `<midi-unpitched>`, channel 10 |
| **MNX (draft)** | `kitNote.kitComponent` → part-level component `{name, sound, staffPosition}` | on the component; int, 0 = middle line | `sound` id |
| **MEI 5** | `<note>` without `@pname`, `instrDef` | `@loc`, `@head.shape` | instrDef MIDI |
| **LilyPond** | ~70 flattened drum names (`bd`, `sn`, `hhc`, `hho`, `boho`, …) | `drumStyleTable`: name → (notehead, articulation glyph, position); shipped tables incl. `weinberg-drums-style` | `midiDrumPitches` |
| **MuseScore** | the GM key number | `.drm`: pitch → `{name, head, line, voice, stem}` | the key number |
| **Dorico** | (instrument, playing technique) | derived through an editable map; kit = instruments with voices; three presentations per layout | percussion map |
| **Humdrum** | pitch letter for placement; `R` unpitched, `RR` partially pitched | `*clefX`, `*head` | `*Ibdrum` codes |
| **PAS / Weinberg 1994** | the legend is mandatory | snare 3rd space, bass 1st space, hi-hat foot below staff, hi-hat hand above top line, ride top line, crash 1st ledger, cowbell top space (triangle), toms by count; x-heads for cymbals | — |

Findings that survived into the decisions: technique is a distinct note
everywhere except in the drawing; durations are stored as written;
one-voice vs two-voice is presentation; the setup has an ordering its
members lack; improvisational notation needs nothing new.
The finding that did *not* survive: the industry's per-note instrument
id. OMK puts the instrument on the Part and keeps the tone abstract.
