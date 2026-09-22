# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the _plans/completed/small-items.md document.

## `Marking.__repr__` and `MarkSpanner.__repr__` do not round-trip (2026-09-22)

Both print `Marking(mark=Mark(name='staccato', ...))`, which does not evaluate
(`src/openmusickit/objects/marking.py:47`, `:77`). Noticed while designing
`BarLineShape.__repr__` (`_plans/division-event.md`), where the rule became
"a `__repr__` round-trips" (AGENTS.md, Technical Details). Make these two
evaluable: print the symbol's name when the mark is one of the ready-made
`symbols`, or the full `Mark(...)` otherwise. Check whether `Mark.__repr__`
itself (dataclass default) evaluates, and whether any other custom `__repr__`
in `src/` was written for compactness rather than fidelity.

## Verbal tempo indications have no home (2026-09-22)

`TempoEvent` holds the ratio (a metronome marking, a metric modulation, a
cross-system pacing); the word that usually goes with it (Allegro, Andante,
rit., a tempo) is notation with nowhere to go: `MarkType`
(`src/openmusickit/values/scoring/mark.py`) has no tempo kind and the WSMN
marks table has no tempo words. Decide whether they are marks (a `Marking`
attached to the `TempoEvent` with a MARKS edge, or to a note when there is no
ratio) or a text attribute on the event, and whether gradual changes (rit.,
accel.) are spanners. Noticed while adding `TemporalContextEvent`.

## No graph query for the context in force at an event (2026-09-22)

There is no way to ask the graph which meter, tempo, or modal context governs
a given event; a consumer walks back along NEXT edges and picks the nearest
`MeterEvent` / `TempoEvent` / `ModalContextEvent` itself. Whether a line with
no context of its own is read by the context of a line it is pinned or grouped
with is also undecided (the `TemporalContextEvent` docstring says so). A
`context_in_force(event, kind)` on `OmkGraph` is the obvious shape; decide
when a realizer or analysis module first needs one.
