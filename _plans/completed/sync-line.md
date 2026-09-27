# SyncLine: a named timing origin that music pins to

Status: **implemented 2026-09-26**

Baseline heavy run before the work: 3,200 passed.
After: 3,243 passed, `ruff check`/`format` clean,
`graph.py` at 98% and `objects/sync_line.py` at 100% line coverage
from `tests/` alone (the nine uncovered `graph.py` lines all predate this work).

## Deviations / notes from implementation

- **`create_sync_point` also needed `add_node(sync_line)` before its first
  read.** The plan called this out for `add_sync_point` only, but
  `create_sync_point` calls `sync_points` while looking for an existing offset,
  and the adapter refuses a node it does not hold. Caught by the doctests.
- **`_sign` returns `int | None`, and an unmeasurable distance skips the pair.**
  Not in the plan. A coverage gap on the non-`Measurable` branch showed the
  behaviour was wrong, not merely untested: returning `0` for a duration with no
  number made `check_sync_alignment` *report* a pair whose music has no
  comparable direction. It now skips, which is the honest answer, and
  `test_music_of_unmeasurable_length_cannot_be_checked_for_order` covers it.
  The mirror branch on the *offset* side was removed instead of tested: offsets
  are guaranteed `Measurable` at add time, so it was unreachable.
- **Three type hints widened**, which the plan did not list but the design
  implies: `relative_onset` and `_relative_onset` take `OmkObject` (a
  `LineGroup`, a `SyncLine` and a `SyncPoint` are all legal ends, and passing
  non-events was already established at `graph.py:1098` and in
  `test_line_group.py`), and `add_simultaneous`'s `other` is
  `SequentialEvent | SyncPoint`, because `sync_event` passes a point.
- **Commits 1 and 2 of the plan landed as one piece**: `check_sync_alignment`
  shares the new API section and was written with it.
- **`docs/_quarto.yml` also needed `objects.sync_line`**, which the plan missed:
  the reference enumerates modules explicitly.
- The two-sided gate was verified by removing one half and confirming that both
  the property test and
  `test_reaching_past_a_point_fails_the_same_way_in_both_directions` fail, the
  latter with the same `ClockDuration + MetricalDuration` `TypeError` that the
  planning review found. Neither test is vacuous.

## Context

OMK has no way to say "measure 10 beat 1 lands on frame 200."
Today two lines relate in time only through a direct `Simultaneous` pin between
them, and there is no origin anywhere in the graph
(`graph/__init__.py:3`, `paper/mathy.md` §5.4).
That is the right default for notated music,
but it leaves out a family of real scores:
stop-watch and duration scores,
music synchronised to film or tape,
and anything whose timing authority is an external medium rather than a tempo.

A **SyncLine** is a named timing origin with no musical content.
It holds **SyncPoint**s — single instants at a signed distance from that origin —
and musical events pin to those points.
A consumer (a future playback or engraving system) reads the
(musical position, timeline position) pairs off the graph
and does whatever it needs with them: fit a tempo curve, drive a click, cue a projector.
Core asserts the correspondence and checks it for obvious nonsense;
core does **not** convert between temporal systems.

This was deferred once already
(`_plans/completed/compound-lines.md:182-189`, 2026-09-20),
with two questions left open.
Both are now answered:

- **Type or role?** A contentless timeline is a **type** (this plan).
  A real musical line that others sync to — a West African bell pattern,
  gamelan colotomic structure, a drum loop — stays a **role**
  that any ordinary line already plays through pins, and needs nothing new.
  They are different things and are deliberately not unified.
- **Cross-system displacement?** Not expressed at all. See "Meet, don't compose".

Prior art to reuse rather than reinvent:
`LineGroup` (`objects/part.py:62`) is already a contentless node that is a local
timing origin, and it works only because `_timing_neighbours` iterates timed edges
on any `OmkObject`. `Score` (`objects/score.py:7`) is already a node whose CONTAINS
edges are plain and therefore invisible to timing. SyncLine sits between the two.

## The model

```python
# src/openmusickit/objects/sync_line.py  (new)

@dataclass(kw_only=True, slots=True)
class SyncLine(OmkObject):
    temporal_system: TemporalSystem      # required
    name: str | None = None
    description: str | None = None

@dataclass(kw_only=True, slots=True)
class SyncPoint(OmkObject):
    offset: Duration                     # required; signed — negative is before the origin
    name: str | None = None
    description: str | None = None
```

- A SyncLine is **a node, not a chain**. "Line" is a conceptual metaphor
  (and probably how it gets drawn); it is not graph topology.
  SyncPoints are never joined to each other by NEXT.
- The SyncLine node **is** the origin. `SyncPoint.offset` is the distance from it,
  and lives **on the node** — the single source of truth, read live by the timing walk.
  Nothing duplicates it on an edge, so nothing can go stale.
- `SyncLine —CONTAINS→ SyncPoint` is a **plain `OmkEdge`**, as a Score's are.
  This matters: `_timing_neighbours` already skips non-`TimedEdge` CONTAINS edges
  (`graph.py:689,695`, from commit 02d88ee), so the existing loop needs no change.
- A musical event attaches with an ordinary `Simultaneous` pin,
  `event → sync_point`, `displacement=None` always.
  The point *is* the displacement; a second one would be a second source of truth.
- Neither class is a `SequentialEvent`. An instant has no duration, and staying off
  `SequentialEvent` makes the structurally-wrong moves impossible: a SyncPoint cannot
  be NEXT-chained into a line, branched from, or added to a Score as a line head.
  It also sidesteps `SequentialEvent.__setattr__`'s non-negative check
  (`omk_object.py:58`), which we do not want here — offsets before the origin are legal.
- `offset` must be a `Measurable`, not merely a `Duration`.
  `rational_length` is declared on `Measurable` (`duration.py:133`), **not** on
  `Duration` (`duration.py:183`, which requires only `__neg__`), and both the
  ordering and the sign check need it. Guard with
  `isinstance(offset, Measurable)`, the same shape as `omk_object.py:59`.

### Meet, don't compose

**Rule: a SIMULTANEOUS edge and a sync line's CONTAINS edge are never consecutive
in a timing path.** Equivalently, and this is the wording for the docstring:
*a sync node offers either its own line or the events pinned to it, never both in
one path.* Pin → pin transits through a shared sync point remain allowed — two
events on the same point genuinely are simultaneous.

Without this rule `relative_onset` between two *musical* events silently answers in
the sync line's temporal system. `ZeroDuration` is universal (`duration.py:251`), so
the walk always gets one free step across a system boundary, and BFS reaches the
5-hop sync route before the 40-hop musical one:

```
m10b1                offset = ZeroDuration     (universal)
 → sp_200   (pin)    offset = ZeroDuration
 → SyncLine          offset = -200 frames
 → sp_335            offset = +135 frames
 → m20b1    (pin)    offset = +135 frames      ← returned instead of ten measures
```

**The gate must be symmetric.** A one-sided gate (blocking only
SIMULTANEOUS → sync-CONTAINS) was tried against the real graph and breaks the
antisymmetry law of `paper/mathy.md:826`: with a WSMN line `a`, a WSMN line `b`,
and a `CLOCK_TIME` sync line whose `P1`/`P2` are pinned to `a1`/`b1`, it gives
`on(P1, b1) == ClockDuration(5s)` but `on(b1, P1) == GraphError`, and
`on(P1, b2)` crashes with a bare `TypeError` from `ClockDuration + MetricalDuration`
(`ClockDuration.__add__` and `MetricalDuration.__radd__` both return
`NotImplemented`). Both halves are required:

| arrived at a sync node by | do not traverse |
|---|---|
| `SIMULTANEOUS` | the sync line's CONTAINS (the new cases below) |
| `CONTAINS` | the SIMULTANEOUS loop |

With both halves, the probes come out symmetric and no existing behaviour changes:

```
on(P1, P2) = 5s          on(P2, P1) = -5s          two points on one line
on(a1, P1) = Zero        on(P1, a1) = Zero         an event and its own point
on(a1, b1) = GraphError  on(b1, a1) = GraphError   music does not route through
on(P1, b1) = GraphError  on(b1, P1) = GraphError   symmetric
on(P1, b2) = GraphError  on(b2, P1) = GraphError   no TypeError
```

Why the BFS dedupe cannot reintroduce asymmetry, and this is worth a comment in the
code: with both halves in place, from a musical root the walk can never reach a
SyncLine at all (the only way in is a point, and the only way to a point is a pin,
which blocks the next step); from a sync root it can never reach a musical node.
The two regions never both feed the same node, so first-arrival-wins is
deterministic here.

`sync_event` never creates a displacement, so no pin the sync API builds can mix
systems. A hand-built cross-system pin can still make `_relative_onset` raise
`TemporalCompatibilityError`; that gap predates this work (`graph.py:666` adds
without a guard) and is out of scope.

### Consistency checks

Four, at the levels where each is actually decidable.

1. **Wrong system, at add time** — an offset must be in the sync line's declared
   `temporal_system` or be a `ZeroDuration`. Use
   `TemporalSystem.compatible_with` (`duration.py:33`), not `==`, following
   `edge.py:107`. Raise `TemporalCompatibilityError`. This is what makes the
   required `temporal_system` load-bearing: without it the declared system
   constrains nothing, since `ZeroDuration` reports `ANY_TEMPORAL_SYSTEM`.
2. **Duplicate offset on one line, at add time** — raise `GraphError`.
   `create_sync_point` finds and reuses, so this only fires when a caller builds a
   `SyncPoint` by hand. Note `==` is by `rational_length`, so
   `GraceDuration(eighth) == ZeroDuration()` collides — correct here, but say so.
3. **Offset order must match music order** — the only check on the correspondence
   itself, and the only one that is soundly decidable. For adjacent pairs of points
   in offset order, the *sign* of the offset difference must equal the sign of the
   relative onset between their synced events: before, at, or after must agree on
   both sides. The zero case is included and earns its keep — it catches two
   simultaneous events pinned to different points on the timeline.

**There is deliberately no magnitude check.** Comparing the interval between two
offsets against the music's elapsed time would need the two to share a metrical
context, and "same temporal system" does not give that: WSMN_TEMPORAL is a
*relative* system, so two WSMN runs at different paces traverse different metrical
distances over the same real interval, and a WSMN sync line's offsets can only agree
with one of them. `TemporalSystem` cannot express the distinction — it carries
`name`, `description`, `universal`, and no notion of an absolute system — and the
graph has no way to know two lines' pacing. Order, by contrast, is invariant under
any positive tempo map, so it is valid in every system, absolute or relative,
without a new concept.

`check_sync_alignment` warns with `OmkWarning` and returns offending pairs, never
raises — the `check_alignment` pattern (`graph.py:748`). It must call
`_relative_onset(..., ignoring=None)` and test for `None`, **not** the public
`relative_onset`, which raises (`graph.py:745-747`).

Adjacent pairs only, not all pairs: O(n × BFS) rather than O(n² × BFS), and it
catches the realistic error. Where a point has several synced events, check every
connected pair of events and report the point pair once if any disagree.

The sign comparison is on `rational_length` (a `Fraction`), which is exact and needs
no system agreement — which is the whole reason this check works across systems.

Expect this to be a no-op on precisely the graphs sync lines exist for: with the
rule in place, two events on different points that are not *otherwise* related have
no relative onset, so there is nothing to compare. It fires when the music is also
related another way — one long line, a group, a pin chain, a shared point. That is
exactly parallel to `check_alignment`, which only ever checks redundant pins. Say so
in the docstring so nobody expects it to validate a fresh sync line.

## Files

### 1. `src/openmusickit/objects/sync_line.py` (new)

The two dataclasses above. Module docstring explains what a sync line is, what it is
not (not a NEXT chain, not musical content, not a converter), and that it is the base
for future media timelines. Class docstrings carry runnable examples.

The default `repr` round-trips but is long, because `TemporalSystem` is a frozen
dataclass of strings and `WSMN_TEMPORAL` / `CLOCK_TIME` live in ordinary modules,
not in any `symbols.py`, so AGENTS.md:180 does not license abbreviating them.
Keep the default repr; prefer `repr` over `str` in doctests, because
`ClockDuration.__str__` mangles negatives (`str(ClockDuration(-5_000_000))` is
`'-1:59:55.000000'`, `clock_time.py:131`) and negative offsets are in scope.

Document that `offset` is not re-validated on assignment — consistent with the rest
of the graph, where guards are insertion-time only.

### 2. `src/openmusickit/graph/graph.py`

**The timing walk.** `_relative_onset` (`:652`) queues `(node, arrived_by)` instead
of bare nodes, the reference with `arrived_by=None`.
`_timing_neighbours` (`:670`) takes `arrived_by` and yields a third element, the
edge type it came by:

```python
def _timing_neighbours(
    self, node: OmkObject, ignoring: OmkEdge | None, arrived_by: EdgeType | None
) -> Iterator[tuple[OmkObject, Duration, EdgeType]]:
    on_sync = isinstance(node, (SyncLine, SyncPoint))
    # ... existing NEXT case, yielding EdgeType.NEXT ...
    for edge_type in (EdgeType.BRANCHES, EdgeType.SIMULTANEOUS, EdgeType.CONTAINS):
        if edge_type is EdgeType.SIMULTANEOUS and on_sync and arrived_by is EdgeType.CONTAINS:
            continue                     # arrived from the sync line: pins are not offered
        # ... existing loops, unchanged, yielding edge_type ...
    if arrived_by is EdgeType.SIMULTANEOUS:
        return                           # arrived by a pin: the sync line is not offered
    if isinstance(node, SyncLine):
        for point in self.sync_points(node):
            yield point, point.offset, EdgeType.CONTAINS
    elif isinstance(node, SyncPoint):
        line = self.sync_line_of(node)
        if line is not None:
            yield line, -node.offset, EdgeType.CONTAINS
```

`EdgeType.CONTAINS` cannot itself distinguish a sync step from a `LineGroup` step,
which is why the first guard also tests `isinstance(node, (SyncLine, SyncPoint))`.
That is sound because a SyncPoint has at most one incoming CONTAINS and guard 2
below guarantees it comes from a SyncLine. Blocking pins after a *group* CONTAINS
would break timing that works today (group → head → pin to a third line).

`_timed_delta` (`:702`) and the two callers of `_relative_onset` (`:647`, `:745`)
need no change. Nothing outside `graph.py` calls either private method.

**New API**, in a `# Sync lines: a named origin that music pins to` section
following the existing sectioning:

```python
def add_sync_line(self, sync_line: SyncLine) -> None
def add_sync_point(self, sync_line: SyncLine, point: SyncPoint) -> None
def create_sync_point(self, sync_line: SyncLine, offset: Duration) -> SyncPoint
def sync_event(self, event: SequentialEvent, sync_line: SyncLine,
               offset: Duration, anchor: TimingAnchor = TimingAnchor.ONSET) -> SyncPoint
def sync_points(self, sync_line: SyncLine) -> list[SyncPoint]
def sync_line_of(self, point: SyncPoint) -> SyncLine | None
def synced_events(self, point: SyncPoint) -> Iterator[SequentialEvent]
def check_sync_alignment(self, sync_line: SyncLine | None = None) -> list[tuple[SyncPoint, SyncPoint]]
```

- `add_sync_point` must `add_node(point)` **before** its guards — the adapter raises
  `GraphError` for a node it does not hold (`rx_adapter.py:44-53`), so
  `in_edges(point, CONTAINS)` on an unadded point raises first. `add_branch`
  gets this order right (`graph.py:552` before `:554-568`); copy it.
- Guards on `add_sync_point`, in order: offset is a `Measurable` (else `TypeError`);
  system compatible (else `TemporalCompatibilityError`); no incoming CONTAINS from
  another sync line (`GraphError`, the `add_branch:559` shape); no *other* point on
  this line with an equal offset (`GraphError`). Exclude `point` itself from the
  duplicate scan, and let `add_edge`'s existing one-edge-per-ordered-pair rule
  (`:238`) supply the "already on this line" error, as `add_line_to_score` does.
- `create_sync_point` is find-or-create: return the existing point whose offset is
  equal (by length — so `MetricalDuration(1,2)` finds one created as `(2,4)`),
  otherwise build one and call `add_sync_point`. Document plainly that it may return
  a point it did not create, and that a caller who needs to know must consult
  `sync_points` first. **Known hole:** this makes `create_sync_point` /
  `sync_event` not self-invertible, since the return value does not say whether a
  node was added. The inverses test therefore exercises `add_sync_point` with fresh
  offsets, where creation is certain. Flagged rather than papered over.
- `sync_event` builds `add_simultaneous(event, sync_point, anchor=anchor)` —
  event as source, so `anchor=OFFSET` means "this event *ends* on the point", which
  is the musically useful reading. No `displacement` parameter. Document that
  `anchor=OFFSET` on an event with `duration=None` silently contributes nothing to
  the walk (`_timed_delta` returns `None`, `:707`) and is skipped by
  `check_alignment` (`:742`) — consistent with offset-anchored branches.
- `sync_points` returns `sorted(..., key=lambda p: p.offset)` as a **list**, not an
  iterator: it materializes, and every other reader documents "no particular order",
  so being honest about both is better. `SyncPoint` has no `order=True` and hence no
  `__lt__`, so the `key=` is required. Sorting cannot raise, because the add-time
  system guard leaves only same-system offsets plus universal `ZeroDuration`s.
- `sync_line_of` is `next(predecessors(point, SyncLine, CONTAINS), None)`;
  `sync_points` is `successors(sync_line, SyncPoint, CONTAINS)` — the exact
  `score_lines` / `score_parts` precedent of disambiguating one edge type by node class.
- `synced_events` unions both pin directions, so hand-built reverse pins are still
  seen by `check_sync_alignment`.
- Document that `remove_node(sync_line)` is **not** the inverse of building one:
  unlike a group, whose member heads pre-exist, a sync line's points are created by
  `create_sync_point`, so removing the line leaves them orphaned. The undo is: remove
  each pin, remove each point, then remove the line.

### 3. `src/openmusickit/graph/__init__.py`

A bullet in "The pieces", after the group bullet, worded so it does not read as
contradicting the opening "Time in the graph is relative, and there is no score
origin": a sync line is a second kind of *local* origin, and deliberately does not
join the lines that pin to it.

### 4. `paper/mathy.md`

§5.4 gains the sync weight case (`w(L, p) = offset(p)`, carried by the node rather
than an edge). §5.7's containment table gains a fourth row
(`CONTAINS (SyncLine)`: origin; not span-inclusive; untimed edge, timed node).

§5.5 needs the real consequence stated: `relative_onset` is no longer a plain path
sum over a weighted graph. The rule restricts the *language* of admissible paths —
forbidding the factors `SIM·SYNC` and `SYNC·SIM` — which is not expressible as a
weight function, so "consistent ⟺ a potential exists" no longer covers the sync
edges. Composition genuinely fails, by design:
`on(a1,P1) = 0`, `on(P1,P2) = 5s`, `on(a1,P2) = ⊥`.
The forest claim survives (a point has one incoming sync CONTAINS; a line has none),
but should name sync containment.

### 5. `tests/graph/test_sync_line.py` (new)

Module docstring naming this plan, and a named fixture in the style of `sketch` /
`piano` / `kit` — a stop-watch score in `CLOCK_TIME`, since that system exists today:
a melody whose measure 10 and measure 20 downbeats are synced to 00:00:05 and
00:00:09. One behaviour per test:

- points come back sorted by offset; `sync_line_of` and `synced_events` round-trip
- `on(p1, p2)` is the clock interval; `on(event, its own point)` is zero both ways
- `on(m10b1, m20b1)` is the **metrical** ten measures, not the clock interval —
  the regression test for the BFS bug
- `on(m10b1, b1_of_an_unrelated_line)` raises `GraphError`, and so does the reverse
- two events on one point derive as simultaneous (the pin → pin transit)
- a negative offset before the origin works
- each of the four guards: wrong system, non-Measurable offset, duplicate offset,
  a point already on another line
- `create_sync_point` returns the existing point for an equal offset, including
  `(1,2)` finding `(2,4)` on a WSMN sync line
- `check_sync_alignment`: out-of-order points warn, with a `CLOCK_TIME` sync line
  over WSMN music (the cross-system case) and with a WSMN sync line alike; two
  simultaneous events pinned to different points warn (the zero case); a fresh
  unrelated sync line reports nothing; a correctly ordered line reports nothing
  even when the metrical distances would not have matched the offsets — the
  regression test for *not* checking magnitude
- `anchor=OFFSET` places the point at the event's release; with `duration=None` it
  contributes nothing

### 6. `tests/graph/test_graph_inverses.py`

Do / inspect / undo for `add_sync_line`, `add_sync_point`, `sync_event`, following
`test_group_can_be_undone_edge_by_edge_or_by_removing_the_node` (`:222-241`) — but
spelling out the full primitive undo, since `remove_node(sync_line)` alone does not
restore the snapshot. The module docstring already permits primitive undos where no
inverse method exists, so no `remove_sync_point` API is needed.

### 7. `tests/graph/test_graph_properties.py`

One property: with a sync line present, `on(u,v) == -on(v,u)` for every pair where
either side is defined, and `GraphError` on one side implies `GraphError` on the
other. This is the property that would have caught the one-sided gate. Keep it
narrow — build a small fixed-shape graph with random durations rather than a new
general strategy.

### 8. `_plans/revisit.md`

New entries: **`TemporalSystem` has no notion of an absolute system** — `universal`
distinguishes "belongs to no system" but nothing distinguishes clock time, where a
unit has a fixed length, from WSMN, where a quarter is a quarter only relative to a
tempo. This is what makes a magnitude check on a sync line undecidable, and it would
matter to any future conversion or realization work; decide it on its own terms, not
as a side effect of this plan. Then: the `create_sync_point` invertibility hole; the state machine does not
exercise sync lines; `ClockDuration.__str__` mangles negatives (`clock_time.py:131`),
found while planning, not this work's to fix; `materialize` drops a forked line's
sync pins along with its other pins (`_attachers:1066` follows only MARKS,
ANNOTATES, STARTS_AT, ENDS_AT, LYRIC), which is consistent but will surprise
someone; `add_to_group(group, sync_point)` is not refused at runtime although the
signature says `SequentialEvent`.

## Commits

1. `SyncLine` and `SyncPoint`; the graph API; the timing-walk gate; doctests;
   the structural tests in `test_sync_line.py`.
2. `check_sync_alignment` and its tests.
3. The inverses additions and the antisymmetry property.
4. `graph/__init__.py`, `paper/mathy.md`, `_plans/revisit.md`.

## Verification

Baseline **before** starting, so a failure at the end can be placed on one side of
the work (AGENTS.md:164):

    uv run pytest --hypothesis-profile=thorough -m ""

Per commit:

    uv run pytest
    uv run ruff check src tests && uv run ruff format --check src tests

At the end, the heavy set again, plus the coverage diagnostic:

    uv run pytest --hypothesis-profile=thorough -m ""
    uv run pytest -q -o addopts="" tests --cov=openmusickit --cov-report=term-missing

End-to-end check by hand — the developer's own example, in clock time:

    uv run python -c "
    from openmusickit.graph.graph import OmkGraph, GraphMeta
    from openmusickit.objects.sync_line import SyncLine
    from openmusickit.objects.note_event import NoteEvent
    from openmusickit.values.time.clock_time import CLOCK_TIME, ClockDuration
    from openmusickit.systems.wsmn.temporal.symbols import whole
    from openmusickit.systems.wsmn.tonal.symbols import C, D, E
    g = OmkGraph(GraphMeta())
    line = [NoteEvent(tones={t}, duration=whole) for t in (C, D, E)]
    g.add_line(line)
    film = SyncLine(temporal_system=CLOCK_TIME, name='Reel 1')
    g.add_sync_line(film)
    p0 = g.sync_event(line[0], film, ClockDuration.from_seconds(5))
    p2 = g.sync_event(line[2], film, ClockDuration.from_seconds(9))
    print(g.relative_onset(p0, p2))          # ClockDuration(4s) -- the timeline gap
    print(g.relative_onset(line[0], line[2]))# 2 wholes -- the music, NOT 4s
    print(g.relative_onset(line[0], p0))     # ZeroDuration
    print(g.check_sync_alignment(film))      # [] -- in order
    "

## Out of scope (deliberately)

- **Any temporal-system conversion.** No tempo, no `TemporalRatio` on a sync line, no
  frames-to-quarters. Fitting a tempo curve to the pinned pairs is the consumer's job.
  `ideas.md`'s System Conversion Class is where that belongs.
- **A magnitude check on the correspondence,** and any `absolute` flag on
  `TemporalSystem` to enable one. Order agreement is the whole of
  `check_sync_alignment`; see "Consistency checks" for why magnitude is not
  decidable from what the graph knows. Do not add it opportunistically.
- **Media subclasses.** No `AudioSyncLine`, `MidiSyncLine`, `VideoSyncLine`. Audio is
  buildable today on `CLOCK_TIME`, but video needs a timecode system that does not
  exist (29.97 drop-frame means timecode ≠ elapsed time) and MIDI needs a tick system
  with PPQ. The base class must therefore stay free of anything clock-specific — no
  sample rate, no file path, no media length. The extension is additive when those
  systems arrive: a declared system plus a resource locator, both data, no behaviour.
- **Score membership.** No `add_sync_line_to_score` / `sync_lines(score)`. It is a
  clean five-line follow-up on the `score_parts` precedent when wanted;
  `scores_of` already works unchanged, and `score_lines` filters `SequentialEvent`
  so nothing leaks either way.
- **The state machine.** No sync rules in `test_graph_state_machine.py`; its
  `num_nodes() == len(self.events) + len(self.groups)` invariant (`:214`) and
  `_register` bookkeeping would both need extending. Revisit entry instead.
- **Fixing `_relative_onset`'s unguarded cross-system addition** (`graph.py:666`),
  which can still raise `TemporalCompatibilityError` for a hand-built cross-system
  pin. Pre-existing; the sync API cannot produce one.
- **A runtime guard on `add_to_group` / `add_simultaneous` against sync nodes.** The
  signatures already say `SequentialEvent`; defending states the contract excludes
  is what AGENTS.md:512 warns off.
