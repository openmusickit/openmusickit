# Plan: unify tonal transformation across events (`transform_tones`)

Status: **completed 2026-09-18.** 
commit: 4bf1e52

All seven steps implemented as written;
`uv run pytest` → 2358 passed. Doctests only (no new test files); the four
`NoteEvent.transform` tests in `tests/notes/test_note_event.py` were renamed.

diff: working tree on main (commit pending)

Deviations / notes from implementation:

- Two pre-existing graph bugs on the walk path were fixed with the developer's
  approval, since `OmkGraph.transform_tones` could not run without them:
  `OmkGraph.add_edge` built `OmkEdge(edge_type)` against a `kw_only` dataclass
  (now `OmkEdge(_type=edge_type)`), and `RustworkxAdapter.get_next`/
  `get_previous` passed `EdgeType.NEXT` where rustworkx expects a predicate
  (now `lambda edge: edge.type == EdgeType.NEXT`).
- `KeySignature.transform` raises `ValueError` for non-integer alterations
  (they cannot be expressed as `TonalVector`s), as planned.
- `Key.transform` passes the transformed signature into `Key.of` (deliberate
  change from the old event code, which re-derived it from the mode).

## Context

`NoteEvent.transform` and `Chord.transform` push a Tone→Tone operation through an
object's tonal content (`event.transform(TonalVector.transpose, M3)`), while
`KeySignatureEvent` has a bespoke `transpose(x, TransposeDirection)` because all
the key-specific logic lives in the event rather than on `Key`/`KeySignature`.
`ChordEvent` has no method at all. There is therefore no way to transpose a run
of a score with one call without type-dispatching over event classes.

Goal: one event-level verb, `transform_tones(operation, *args, **kwargs)`, on
every object with tonal content, each delegating to its value type (which is
where the type-specific logic belongs — exactly as `Chord.transform` already
does for chords); a `TonalObject` ABC to mark those objects; and one graph
method that walks a NEXT-linked run of events and applies the operation.

Decisions already made with the developer:

- Event-level name is `transform_tones` (verb-first, like `add_tone`,
  `alter_duration`), leaving room for a separate rhythmic transform later.
  Value types (`ToneCollection`, `Chord`, `Key`, `KeySignature`) keep plain
  `transform` — they hold only one kind of content.
- Marker is an ABC mixin `TonalObject`, not a Protocol (a forgotten
  implementation fails at construction instead of being silently skipped).
- `KeySignatureEvent.transpose` and `TransposeDirection` (incl. `TO_TONIC`) are
  removed. "Transpose to E♭" is a section-level concern (find the governing key,
  compute the interval, transform UP by it) and is **not** built now.
- `KeySignature.transpose` is kept, reimplemented over the new letter-mapping
  `KeySignature.transform`; non-standard signatures now transpose instead of
  raising.
- Section call is a graph method only (no standalone iterable helper).
- No new test files; doctests only (AGENTS.md). Existing tests that reference
  renamed names are updated.

## Changes

### 1. `TonalObject` ABC — [src/openmusickit/objects/omk_object.py](src/openmusickit/objects/omk_object.py)

```python
class TonalObject(ABC):
    """Mixin for objects with tonal content that a Tone -> Tone operation
    can be pushed through (notes, chord symbols, key signatures, ...)."""
    __slots__ = ()          # KeySignatureEvent is a slots dataclass

    @abstractmethod
    def transform_tones(self, operation: Callable[..., Tone], *args, **kwargs) -> None:
        """Replaces this object's tonal content with the result of applying
        `operation(tone, *args, **kwargs)` to it, in place."""
```

Import `Tone` from `openmusickit.values.tone.tone` (no cycle: `values` does not
import `objects`). One-line docstring; contract text as above.

### 2. `NoteEvent` — [src/openmusickit/objects/note/note.py](src/openmusickit/objects/note/note.py)

- `class NoteEvent(SequentialObject, TonalObject)`.
- Rename `transform` → `transform_tones` (line 80); body unchanged; update the
  five doctest calls (lines 100–125).
- Update [tests/notes/test_note_event.py:63-95](tests/notes/test_note_event.py#L63-L95)
  (`note.transform(` → `note.transform_tones(`, `rest.transform(` likewise).

### 3. `ChordEvent` — [src/openmusickit/objects/chord/chord_event.py](src/openmusickit/objects/chord/chord_event.py)

- `class ChordEvent(SequentialObject, TonalObject)`.
- Add:
  ```python
  def transform_tones(self, operation, *args, **kwargs) -> None:
      """Replaces the chord with `self.chord.transform(operation, *args, **kwargs)`."""
      self.chord = self.chord.transform(operation, *args, **kwargs)
  ```
  `ToneCollection.transform` / `Chord.transform` already validate the result
  type. Two-line doctest: `C(maj)` up `M3` → `str(event.chord) == 'E'`.

### 4. `KeySignature.transform` + `transpose` — [src/openmusickit/systems/wsmn/tonal/key.py](src/openmusickit/systems/wsmn/tonal/key.py)

New `transform(self, operation: Callable[..., TonalVector], *args, **kwargs) -> KeySignature`:

1. For each letter `d` in 0..6 with alteration `alt = self[d]`, build the
   letter-tone `TonalVector((d, (MS[d].c + alt) % C_LEN))` (`MS`, `C_LEN` from
   `constants.py`; `TonalVector((0, 11))` is C♭, matching `_modifier_value`'s
   own doctests). Non-integer alterations cannot be expressed as a
   `TonalVector` → raise `ValueError` (the fifths-based code already refused
   these via `fifths`).
2. `new = operation(tone, *args, **kwargs)`; if not a `TonalVector` → `TypeError`
   (same wording style as `NoteEvent`/`ToneCollection`).
3. Read back `new.d` → letter, `new.pitch._modifier_value` → alteration. If two
   inputs land on the same letter → `ValueError` (mirror the message pattern in
   `Key.of`, [key.py:290-294](src/openmusickit/systems/wsmn/tonal/key.py#L290-L294)).
   Seven distinct inputs with no collision ⇒ all seven letters present.
4. `return KeySignature(*(alts[i] for i in range(7)))`.

Doctests (short): `KeySignature().transform(TonalVector.transpose, M2)` →
`KeySignature(c=1, f=1)`; a non-standard one,
`KeySignature(f=1, b=-1).transform(TonalVector.transpose, M2)` →
`KeySignature(f=1, g=1)` (verified by hand: C D E F♯ G A B♭ up a M2 is
D E F♯ G♯ A B C); the `sharpen` op from `NoteEvent`'s doctest → all seven
sharps.

`transpose(x, direction)` becomes
`return self.transform(TonalVector.transpose, x, direction)`; keep its
docstring's examples (they still hold — the two methods agree on standard
signatures) but replace the "raises AttributeError for non-standard" sentence
and doctest (lines 174, 191–194) with the `KeySignature(f=1, g=1)` result.

### 5. `Key.transform` — same file

New `transform(self, operation, *args, **kwargs) -> Key`:

- `tonic is None` (NoKey) → `return self` (a keyless key is unchanged by any
  tonal operation).
- `new_tonic = operation(self.tonic, *args, **kwargs)`; validate `TonalVector`.
- With a mode pattern:
  `Key.of(new_tonic, self._mode, signature=self.signature.transform(operation, *args, **kwargs))`.
  **Deliberate change** from the current event code, which called `Key.of`
  without a signature: passing the transformed signature carries an explicit
  or non-derivable signature along instead of re-deriving (and re-raising)
  from the mode. For standard keys the result is identical.
- Without a mode: `Key(tonic=new_tonic, tones=self.tones.transform(...), signature=self.signature.transform(...))`
  (`_name` left `None`, as today).

Note in the docstring (no code): for non-transposition operations "keep the
mode" and "transform the tones" can diverge (inversion of C Major about C is
C Major by the first, C Phrygian by the second); the mode-preserving rule is
kept because it matches existing behaviour and transposition never diverges.

Doctests: `Key.of(C, Major).transform(TonalVector.transpose, M2).name` →
`'D Major'`; `NoKey.transform(...) is NoKey`.

### 6. `KeySignatureEvent` — [src/openmusickit/objects/context/context_event.py](src/openmusickit/objects/context/context_event.py)

- Delete `TransposeDirection` (lines 20–23) and `transpose` (lines 58–158).
- `class KeySignatureEvent(ContextEvent, TonalObject)`.
- Add `transform_tones(self, operation, *args, **kwargs) -> None`:
  - empty event or NoKey → keep the existing `OmkWarning`
    ("You are attempting to transpose an empty key signature…" → reword to
    "transform") and return;
  - holds a `Key` → `self.set_key(self.key.transform(operation, *args, **kwargs))`;
  - holds only a `KeySignature` → `self.set_key_signature(self._key_signature.transform(...))`.
- Port the surviving doctests from the old `transpose` docstring (Key up M2 →
  `'D Major'`, down P5 → `'G Major'`, bare signature up m3 →
  `KeySignature(e=-1, a=-1, b=-1)`, NoKey warns); drop the `TO_TONIC` ones.
  Direction now comes from `TonalDirection`.
- Remove the now-unused `TonalDirection`/`warnings` imports only if unused.

### 7. Graph walk — [src/openmusickit/graph/graph.py](src/openmusickit/graph/graph.py)

Add next to `define_span` (Sequential Data section):

```python
def transform_tones(self, start: SequentialObject, end: SequentialObject | None,
                    operation: Callable[..., Tone], *args, **kwargs) -> None:
    """Applies `operation` to the tonal content of every TonalObject from
    `start` to `end` (inclusive) along NEXT edges; `end=None` runs to the end
    of the line. Objects without tonal content are passed over."""
```

Walk with the existing idiom from `unlink_lyric_sequence`
([graph.py:191-202](src/openmusickit/graph/graph.py#L191-L202)):
`obj = start; while obj is not None: if isinstance(obj, TonalObject): obj.transform_tones(...); if obj is end: break; obj = self.get_next(obj)`.
If `end` is given but the line runs out first, raise `ValueError` (explicit
failure rather than silently transforming to the end). Mutation is in place,
so nothing is written back to the graph.

Doctest: `add_line([KeySignatureEvent(_key=Key.of(C, Major)), NoteEvent({C,E,G}), ChordEvent(chord=C(maj))])`,
`graph.transform_tones(first, last, TonalVector.transpose, M3)`, then check
key name `'E Major'`, note tones `{E, G♯, B}`, chord `'E'`.

### Out of scope (explicitly not done)

- Rhythmic transforms / renaming `alter_duration`.
- "Transpose to tonic" at section level (needs "governing key at a point"
  which does not exist yet).
- A Score/section container; a Spanner-based overload of `transform_tones`.

## Verification

1. `uv run pytest` — full suite incl. `--doctest-modules` (baseline 2094
   passing at last recorded count); expect only the renamed tests and the
   updated `KeySignature.transpose` non-standard doctest to change.
2. `uv run pytest src/openmusickit/objects src/openmusickit/systems/wsmn/tonal/key.py src/openmusickit/graph -q`
   for the touched modules' doctests specifically.
3. `grep -rn "TransposeDirection\|\.transform(TonalVector" src tests` — no
   remaining references to the removed enum; only value-type `.transform`
   calls remain (`ToneCollection`, `Chord`, `Key`, `KeySignature`).
4. Per repo convention, copy this plan to `_plans/` at implementation start and
   move it to `_plans/completed/` with the resulting commit noted when done.
