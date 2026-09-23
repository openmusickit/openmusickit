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

## No graph query for the context in force at an event (2026-09-22)

There is no way to ask the graph which meter, tempo, or modal context governs
a given event; a consumer walks back along NEXT edges and picks the nearest
`MeterEvent` / `TempoEvent` / `ModalContextEvent` itself. Whether a line with
no context of its own is read by the context of a line it is pinned or grouped
with is also undecided (the `TemporalContextEvent` docstring says so). A
`context_in_force(event, kind)` on `OmkGraph` is the obvious shape; decide
when a realizer or analysis module first needs one.

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

## Part order and bracketing have no home on a Score (2026-09-22)

A `Score` (`src/openmusickit/objects/score.py`) names its top-level lines
and its Parts with plain CONTAINS edges, which are unordered. The order of
parts down the page, the bracket or brace that groups a choir or a string
section (MusicXML `<part-group>`, LilyPond `StaffGroup` / `PianoStaff`),
and whether a `LineGroup` may be a member in place of its heads were left
out of the clef-score-text plan. Decide when a renderer or the importer
first needs staff order; an ordered list of ids on the Score is the
registry smell AGENTS.md warns against, so look for an edge-based answer.
