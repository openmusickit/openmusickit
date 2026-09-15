# Plan: repair the `Tone` class hierarchy

Status: **completed 2026-09-14.** All five steps implemented as written; test
suite went from 2063 to 2094 passing (`uv run pytest`). New tests live in
`tests/tones/test_tone_hierarchy.py` and `tests/notes/test_note_event.py`,
plus doctests on `Tone`, `Interval`, `SilentTone`, `TonalVector`,
`TonalVector.pitch` / `.interval`, and `NoteEvent`.

diff: main 2ae44e8

Deviations / notes from implementation:

- `NoteEvent` gained an `is_rest` property (`SilentTone() in self.tones`)
  to replace the three broken `SilentTone in self.tones` checks.
- `NoteEvent.__repr__` uses `repr(tone)` for each tone, sorted, so output is
  deterministic across set ordering.
- With `pitch` non-abstract, `Tone` has no abstract members, so `Tone()`
  itself instantiates. Accepted as a consequence of the step 3 decision.
- `numpy` is still present in `uv.lock` as a transitive dependency of
  `scipy`; only the direct dependency was removed.
- The `__init__` re-entry guard is now `_initialized` and verified to fire
  (`pitch`/`interval` objects are stable across interned lookups).

## Symptoms

All of these were found while adding `NoteEvent.transform` (2026-09-14). They look
unrelated but share one root cause.

1. `isinstance(x, Tone)` raises
   `TypeError: type.__subclasscheck__() takes exactly one argument (0 given)`.
2. `SilentTone()` cannot be instantiated:
   `TypeError: type.__new__() takes exactly 3 arguments (0 given)`.
   Consequently `Rest(...)` and `NoteEvent.make_rest()` crash.
3. `TonalVector` is not a `Tone`. `isinstance(TonalVector((0,0)), Tone)` is False
   (once symptom 1 is fixed), even though `Tone`'s docstring lists it as the
   primary example of a subclass, and `ToneCollection`, `NoteEvent`, etc. are
   typed in terms of `Tone`.
4. `TonalVector` is not an `Interval` either, despite the docstring
   ("TonalVector also subclasses Interval").
5. In `NoteEvent`, `SilentTone in self.tones` (in `__post_init__`, `add_tone`,
   `__repr__`) tests membership of the *class*, not an instance, so it is always
   False.
6. `NoteEvent.__repr__` does `tone.name`, which no Tone defines; `repr` of any
   NoteEvent containing a TonalVector raises `AttributeError`.

Because of 3, `NoteEvent.transform` currently validates results with
`isinstance(new_tone, type(tone))` rather than `isinstance(new_tone, Tone)`.
That is a reasonable contract on its own, but it was chosen as a workaround.

## Root cause

`src/openmusickit/values/tone/tone.py`:

```python
class Tone(ABC, FrozenMeta):
```

`FrozenMeta` (`utils/meta.py`) is a subclass of `type`, i.e. a *metaclass*.
Here it is used as an ordinary *base class*. `Tone` and every subclass are
therefore simultaneously ABCs and metaclasses. Two consequences:

- `type.__new__` is used to construct instances, so plain subclasses like
  `SilentTone` cannot be instantiated (symptom 2). `TonalVector` only works
  because it never subclasses `Tone` at all -- it is a bare `tuple` subclass
  with its own `__new__`.
- `ABCMeta.__instancecheck__` ends up calling `type.__subclasscheck__` with the
  wrong receiver (symptom 1).

Symptoms 3-6 are downstream: the hierarchy was never actually wired up, so
nothing exercised the `Tone` contract and the sloppiness in `NoteEvent` went
unnoticed.

### History (from git)

- `3e1af90` (2025-04-21) introduced `FrozenMeta` and `class Tone(ABC, FrozenMeta)`.
  At that time `Tone` declared a `TONAL_SYSTEM: TonalSystem` class attribute
  and `__init_subclass__` required every subclass to define it. `FrozenMeta`
  was meant to make that binding immutable (its `__setattr__` refuses any
  class attribute whose name contains "system"). The intent was sound; the
  bug is that `FrozenMeta` was written in the bases list instead of as
  `metaclass=FrozenMeta`. `TonalVector` did subclass `Tone` and `Interval`
  at this point.
- `63183dd` (2025-05-07) replaced `TONAL_SYSTEM` with
  `@WSMN.register_tone_type()`, which sets `cls.tonal_system` from outside,
  and commented out the `__init_subclass__` check. This contradicts
  `FrozenMeta`'s purpose: the registration works only because `FrozenMeta`
  was never actually the metaclass.
- `3de8a3e` (2026-07-10, "fixed wsmn tonal tests") changed
  `class TonalVector(tuple, Tone, Interval)` to `class TonalVector(tuple)`,
  severing the hierarchy entirely -- most likely to get past the
  ABC/metaclass errors above.

Nothing in the codebase reads `tonal_system`; only the decorator writes it.

## Proposed approach

Work in this order; each step should leave the test suite green
(`uv run pytest`), which currently has 2063 passing doctests/tests.

### 1. Remove `FrozenMeta`; make `Tone` a plain ABC

```python
# values/tone/tone.py
class Tone(ABC):
```

Delete `utils/meta.py` (`FrozenMeta` has no other users) and the import in
`tone.py`.

Also remove the tone-system registration machinery, which is the other half
of the same abandoned design:

- `TonalSystem.register_tone_type` and `TonalSystem.tone_type`
- the `@WSMN.register_tone_type()` decorator on `TonalVector`
- the commented-out `TONAL_SYSTEM` attribute and `__init_subclass__` check
  on `Tone`

Keep the `TonalSystem` class itself and the `WSMN` instance in `wsmn.py`;
they are a cheap, useful name for the system.

Decision (2026-09-14): the registry's purpose was to let a graph query
answer "which tonal system does this NoteEvent's content belong to?" (for
mixed-system graphs, e.g. a chant line with a WSMN organ accompaniment).
That answer is already recoverable from `type(tone)`, and mixed-system
content lives in different lines, so different NoteEvent nodes. Revisit
when a second tonal system actually exists; the simplest form will likely
be a plain class attribute on the Tone subclass.

`FrozenMeta` itself: the immutability guarantee it was meant to provide
protects an attribute nothing reads, its substring match on "system" is
fragile, and it directly conflicts with the registration decorator that
superseded the original `TONAL_SYSTEM` design. If a read-only binding is
ever needed, a write-once `__setattr__` on an `ABCMeta` subclass is a
five-line addition that can be made then.

Prototyped in a scratch script: with `Tone` as a plain ABC, `isinstance`
works and a minimal frozen-dataclass subclass instantiates, fixing symptoms
1 and 2.

### 2. Make `TonalVector` subclass `Tone` (and `Interval`)

```python
class TonalVector(tuple, Tone, Interval):
```

Multiple inheritance from `tuple` and an ABC works (checked in the prototype),
and `TonalVector`'s interning `__new__` is unaffected.

Rename the inner representation classes at the same time (decision
2026-09-14), so the name `Interval` inside `tonal_vector.py` means only the
ABC:

- `TonalVector.Pitch` -> `TonalVector._PitchRepresentation`
- `TonalVector.Interval` -> `TonalVector._IntervalRepresentation`

They are internal (only constructed in `TonalVector.__init__`), hence the
underscore. Update: the two constructor calls in `__init__`; the doctest at
`type(TonalVector((0,0)).pitch)` whose expected output names the class; and
the "see `TonalVector.Pitch` / `TonalVector.Interval`" pointers in the
docstrings of `PitchRepresentation` (`tone.py`) and `IntervalRepresentation`
(`interval.py`).

### 3. Drop the vectorization contract, then implement what is left

Decision (2026-09-14): `to_array`, `__array__`, `abstract_array_len`, and
`qualified_array_len` on `Tone` and `Interval` are removed. They date from a
plan to have every object emit its own vectorization for ML work. That is
now considered the wrong layer: different AI projects will need different
vectorization schemas, so that belongs in a separate library (working name
"OMK Vectors") rather than in the domain objects. Nothing in `src` or
`tests` implements or calls any of these methods.

After removing them, the only abstract member left on `Tone` is the `pitch`
property, and `Interval` has no abstract members at all (its `from_string`
is a plain classmethod that raises `NotImplementedError`).

Decision (2026-09-14): `Tone.pitch` becomes a non-abstract property that
returns `None`, with a one-line docstring saying unpitched tones (silence,
percussion) have no pitch. Its type is `PitchRepresentation | None`. With
one pitched Tone type in existence, ABC enforcement buys little, and
forcing every unpitched type to implement a "not applicable" method is
ceremony. `SilentTone` then needs no `pitch` at all.

`TonalVector.pitch` is currently a plain instance attribute set in
`__init__`. It must become a property backed by e.g. `self._pitch`, because
a property on the base class has no setter and `self.pitch = ...` will
raise `AttributeError: can't set attribute`. Do the same for `interval`
for symmetry (there is no base-class property in the way, but the two
should look alike).

Also remove, as part of the same decision:

- `TonalVector.abstract_vector_len` and `TonalVector.qualified_vector_len`,
  the WSMN counterparts of the removed `*_array_len` classmethods (under a
  different name, so they never actually overrode anything). Nothing calls
  them.
- The `numpy` dependency in `pyproject.toml`. With `to_array` gone, nothing
  in `src` imports numpy. Remove it with `uv remove numpy` so `uv.lock` is
  updated too. (`poetry.lock` is also checked in; it is stale relative to
  `uv.lock` and unrelated to this task -- leave it.)

### 4. Fix `NoteEvent`

- Replace `SilentTone in self.tones` with `SilentTone() in self.tones`
  (`SilentTone` is a frozen dataclass with constant hash and type-based
  equality, so this works) or `any(isinstance(t, SilentTone) for t in ...)`.
- `__repr__`: replace `tone.name` with something every Tone provides.
  `Tone` has no display contract at all right now; the simplest fix is to use
  `repr(tone)` / `str(tone)`. Alternatively, add `__str__` as part of the
  `Tone` contract.
- Switch `NoteEvent.transform`'s check to `isinstance(new_tone, Tone)`
  (decision 2026-09-14: an operation may legitimately translate tones from
  one tonal system to another, so same-type is too strict). Update the
  docstring and the error message, which currently say "of the same type".

### 5. Reconcile the docstrings

`Tone`'s and `TonalVector`'s docstrings currently describe the intended
hierarchy; after this work they will be true. Check `Interval`'s docstring and
`values/tone/__init__.py` for the same.

## Problems this fix is likely to encounter

### `TonalVector.__init__` re-entry guard

`__init__` uses `hasattr(self, '__initialized')` / `self.__initialized = True`.
Name mangling turns the attribute into `_TonalVector__initialized`, but the
`hasattr` string is the *unmangled* name, so the guard never fires and
`__init__` re-runs (harmlessly, rebuilding `Pitch` and `Interval`) on every
interned lookup. Unrelated to the hierarchy fix, but you will be in that
`__init__` when converting `pitch` to a property, so it is worth noting. Fix
by using a single-underscore name.

### `TonalVector.__eq__` is loose

`TonalVector == int` and `TonalVector == tuple` are both True by design.
Once TonalVectors and SilentTones share a `set[Tone]` in `NoteEvent`, mixed
comparisons happen: `SilentTone.__eq__` returns False for anything that is
not a SilentTone, and `TonalVector.__eq__(SilentTone())` falls through to
`tuple(self) == x or int(self) == x`, both False. So it is safe today, but any
Tone subclass whose `__eq__` is also permissive could produce surprising set
behaviour. Nothing to do now; just be aware.

### Doctests that depend on current behaviour

- `tonal_vector.py` `__new__` doctest: `TonalVector((0,0)).d = 1` raising
  `AttributeError` still holds (property without setter).
- The doctest that does `type(TonalVector((0,0)).pitch)` names the inner
  class in its expected output; update it for the rename.

## Decisions

None outstanding. All decisions are recorded inline in the step where they
apply (dated 2026-09-14):

- `FrozenMeta` and the tone-system registration machinery: removed (step 1).
- Inner classes renamed to `_PitchRepresentation` / `_IntervalRepresentation`
  (step 2).
- Vectorization contract (`to_array`, `__array__`, `*_array_len`,
  `*_vector_len`) and the `numpy` dependency: removed (step 3).
- `Tone.pitch`: non-abstract, returns `None` for unpitched tones (step 3).
- `NoteEvent.transform` validates with `isinstance(_, Tone)` (step 4).

## Validation

- `uv run pytest` stays green throughout.
- After the fix, these should all work and are worth adding as doctests on
  the classes involved:
  - `isinstance(TonalVector((0,0)), Tone)` -> `True`
  - `isinstance(TonalVector((0,0)), Interval)` -> `True`
  - `SilentTone() == SilentTone()` and `SilentTone() in {SilentTone()}`
  - `repr(Rest(None))` -> `'Rest(duration=None)'`
  - `repr(NoteEvent(tones={C}))` does not raise
  - `NoteEvent(tones={C, SilentTone()})` raises `ValueError` (the
    `__post_init__` guard finally fires)
  - `rest = Rest(None); rest.transform(TonalVector.transpose, M3)` leaves the
    rest silent
  - `SilentTone().pitch is None`
  - `grep -rn 'FrozenMeta\|register_tone_type\|tonal_system\|TONAL_SYSTEM' src`
    finds nothing
  - `grep -rn 'to_array\|__array__\|_array_len\|_vector_len\|numpy' src pyproject.toml`
    finds nothing
