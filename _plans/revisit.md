# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the _plans/completed/small-items.md document.

## `Marking.__repr__` and `MarkSpanner.__repr__` do not round-trip (2026-09-22)

Both print `Marking(mark=Mark(name='staccato', ...))`, which does not evaluate
(`src/openmusickit/objects/marking.py:47`, `:77`). `ContextEvent` and
`ModalContextEvent` have the same defect from the other side: the default
dataclass repr prints the `init=False` field, `ContextEvent(duration=ZeroDuration())`,
which the constructor rejects (`DivisionEvent` marks that field `repr=False`). Noticed while designing
`BarLineShape.__repr__` (`_plans/division-event.md`), where the rule became
"a `__repr__` round-trips" (AGENTS.md, Technical Details). Make these two
evaluable: print the symbol's name when the mark is one of the ready-made
`symbols`, or the full `Mark(...)` otherwise. Check whether `Mark.__repr__`
itself (dataclass default) evaluates, and whether any other custom `__repr__`
in `src/` was written for compactness rather than fidelity.


