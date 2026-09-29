# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the _plans/completed/small-items.md document.

## Gradual tempo changes (rit., accel.) have no home (2026-09-22)

`TempoEvent` holds the word (`term: TempoTerm`,
`src/openmusickit/values/scoring/tempo_term.py`; the WSMN words are in
`src/openmusickit/systems/wsmn/scoring/symbols.py`), so Allegro, Andante,
a tempo and the other indications at a point have a home. Gradual changes
(rit., rall., accel., and their dashed extensions) do not: they are a process
over a stretch of material, not a context in force from a point, so a
`MarkSpanner` looks more like them than a `TempoEvent`, but `MarkType` has no
tempo kind and the marks table has no such marks. Deferred until a realizer or
renderer needs them.

DEV:
Solution: We make spanning Mark symbols for them so they can be recorded on score,
and defer playback-oriented logic until we build a playback engine.

## No graph query for the context in force at an event (2026-09-22)

There is no way to ask the graph which meter, tempo, or modal context governs
a given event; a consumer walks back along NEXT edges and picks the nearest
`MeterEvent` / `TempoEvent` / `ModalContextEvent` itself. Whether a line with
no context of its own is read by the context of a line it is pinned or grouped
with is also undecided (the `TemporalContextEvent` docstring says so). A
`context_in_force(event, kind)` on `OmkGraph` is the obvious shape; decide
when a realizer or analysis module first needs one.

DEV:
No consumer needs this yet, but it's easy enough and expected.
`graph.context_in_force(event, kind)` is the right shape.
`kind` should take a ContextEvent type so it automatically keeps up as we add others.

## Other custom reprs that do not round-trip (2026-09-22)

Found while resolving the `Marking` repr entry. `NoteEvent.__repr__` prints
`tones=[...]`, a list, for a `set` field, so `eval(repr(note))` builds a
NoteEvent whose `tones` is a list and does not compare equal;
`LyricSyllable.__repr__` prints `LyricSyllable('Al -')`, which is not a
constructor call; the edge reprs (`Next(next, origin=asserted)`,
`Branch(anchor=offset, displacement=...)`) print enum values bare. The edge
form was kept deliberately on 2026-09-21, before the round-trip rule went
into AGENTS.md. Decide whether the rule applies to edges and to
`Rest(duration=None)`, which evaluates through the factory function.

DEV:
All reprs should roundtrip, so we should fix the broken ones.
Rest reprs should continue to use the Rest factory spelling, as that does roundtrip
(right? even duration=None ?). Assuming it round trips cleanly, keep it.



## Part order and bracketing have no home on a Score (2026-09-22)

A `Score` (`src/openmusickit/objects/score.py`) names its top-level lines
and its Parts with plain CONTAINS edges, which are unordered. The order of
parts down the page, the bracket or brace that groups a choir or a string
section (MusicXML `<part-group>`, LilyPond `StaffGroup` / `PianoStaff`),
and whether a `LineGroup` may be a member in place of its heads were left
out of the clef-score-text plan. Decide when a renderer or the importer
first needs staff order; an ordered list of ids on the Score is the
registry smell AGENTS.md warns against, so look for an edge-based answer.




## Transposition Complications (added by DEV, 2026-09-23)

On a Stint, transposition means these "notes sound differently than written."
This is specifically to support doubling at the octave (or, I guess, organum).
In a realized score, the notes will actually be transposed.

We haven't done it yet, but Part (representing, more or less, an instrument)
should likely have a transposition attribute that says 
what a transposed score should put on the page.
We will always store the concert pitch spelling on the graph.

8va/b and 15va/b are currently ambiguous, but I *think* they should mean
"the notes in the graph play as written; and are transposed only in output scores".

I think we might need an Instrument class that can be an attribute on Part.
In WSMN at least, the Instrument would carry a name, range, and transposition
(and perhaps details of what tonal system it uses, so we can separate pitched and unpitched)
(Should WSMN_Tonal and WSMN_Percussion each have their own Instrument subclasses?)
(btw, for consistency, we should rename WSMN to WSMN_Tonal)



## `TemporalSystem` has no notion of an absolute system (2026-09-26)

`TemporalSystem` (`src/openmusickit/values/time/duration.py:12`) carries `name`,
`description` and `universal`. `universal` says "belongs to no system in
particular" (a `ZeroDuration`), but nothing distinguishes a system in which a
unit has a fixed length, as a microsecond of `CLOCK_TIME` does, from one in
which it does not: a quarter note is a quarter note only relative to a tempo.

This surfaced while designing `check_sync_alignment` (`_plans/sync-line.md`).
Comparing the *distance* between two sync points against the elapsed music
needs both sides to be paced the same way, and "the same temporal system" does
not give that -- two stretches of metrical music at different tempos cover the
same real time in different numbers of quarter notes, so a metrical sync line's
offsets can only ever agree with one of them. The check was therefore limited to
order, which survives any positive tempo map and needs no such distinction.

An `absolute` flag would enable a distance check for clock-time music on a
clock-time sync line, and would likely matter to any conversion or realization
work. Deferred deliberately, to be decided on its own terms rather than as a
side effect of sync lines.

## `create_sync_point` is not self-invertible (2026-09-26)

`OmkGraph.create_sync_point` finds or creates, and its return value does not say
which it did, so a caller cannot know whether to remove the point on undo.
`sync_event` inherits this. Find-or-create is what the API wants -- the normal
way to sync an event should not care whether the instant already exists -- but it
means the graph has one mutator whose inverse is not determined by its result.
`tests/graph/test_graph_inverses.py` therefore exercises `add_sync_point`, where
creation is certain. Options if it ever bites: return a `(point, created)` pair,
or split strict-create from lookup.

## The graph state machine does not exercise sync lines (2026-09-26)

`tests/graph/test_graph_state_machine.py` generates lines, branches, pins,
groups and stints, but no `SyncLine`. Adding rules for them means extending the
`adapters_agree` invariant, whose node count is
`len(self.events) + len(self.groups)` (`:214`), and the `_register` bookkeeping.
Worth doing when the machine is next touched; the sync line's own laws are
covered by `tests/graph/test_sync_line.py` and the antisymmetry property in
`tests/graph/test_graph_properties.py` in the meantime.

## `ClockDuration.__str__` mangles negative durations (2026-09-26)

`str(ClockDuration(-5_000_000))` is `'-1:59:55.000000'`:
`ClockDuration.__str__` (`src/openmusickit/values/time/clock_time.py:131`) uses
floor `divmod`, which carries the sign into the wrong field. Noticed while
planning sync lines, where negative offsets (a count-in before the origin) are
ordinary; not that work's to fix, and `repr` is used in its doctests instead.

## `materialize` drops a forked line's sync pins (2026-09-26)

`OmkGraph._attachers` (`src/openmusickit/graph/graph.py`) follows MARKS,
ANNOTATES, STARTS_AT, ENDS_AT and LYRIC, so a `SyncPoint` -- reached by a
SIMULTANEOUS edge -- is not copied content, and the pin is dropped exactly as
pins to events outside the span are. That is consistent with the documented
contract and with group membership, but it means "fork the second oboe at bar
40" silently loses the forked line's timeline anchoring, which someone will
notice. Also unenforced: `add_to_group(group, sync_point)` is typed
`head: SequentialEvent` but is not refused at runtime, and a sync point reached
by a group's timed CONTAINS would leak past the sync gate.

## The timing walk returns notation-spelled `TiedDuration`s (2026-09-29)

`relative_onset` and `onsets` sum event durations with `+`, so over a long
line the answer is a `TiedDuration` whose spelling depends on the path
(`[1/1, 1/4]` one way round, `[1/4, 1/1]` the other) and whose member count
grows with every tuplet (25–32 members across a quartet movement, 160 over a
synthetic 400-note line). The values are equal and `rational_length` is
exact, so nothing is wrong, but a position is a number, not a spelling.
Found while probing MusicXML import; the reader and writer keep their own
`Fraction` cursors. Decide whether the walk should return a length, or a
normalized spelling, when a second consumer wants positions.

## `MeterEvent` equality is by length (2026-09-29)

`MeterEvent(meter=four_four) == MeterEvent(meter=two_two)`, because
`Measurable`s compare by length, so `OmkGraph.is_equivalent` cannot tell a
round trip that wrote 2/2 for 4/4 from one that kept it. The MusicXML tests
compare `TimeSignature.presentation` directly through `correspondence`.
Whether a meter *event* should compare its presentation too is a small
question for when the next consumer of meters appears.
