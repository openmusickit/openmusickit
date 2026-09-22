# DivisionEvent: an explicit, optional, zero-duration division in a line

## Context

OMK has no barline, measure, or repeat concept. `ContextEvent` is the only zero-duration node kind, time signatures are values with no node, and there are no renderers yet. Divisions (bar lines, in WSMN) become explicit graph nodes: a `DivisionEvent` is placed in the NEXT chain wherever the author says a division is, irrespective of any time signature. Users may place all, some, or none. Measures are never structural; future renderers derive bar lines from time signatures where none are given, and warn where explicit ones disagree (LilyPond's behaviour). Repeats are visual here; a later control-flow module owns the jumps and inherits the same policy: explicit wins, derived fills gaps, mismatch warns.

Naming:

- `DivisionShape` — the abstract base class, implemented by arbitrary systems.
- `BarLineShape` — the WSMN implementation of `DivisionShape`.
- `DivisionEvent` — the object that holds a `DivisionShape` in the graph.

Decisions made in discussion:

- **Value + node**, the `Mark`/`Marking` pattern. A frozen, hashable shape is shared vocabulary (every ordinary bar in a score has the same one) and lets the WSMN symbols module export named constants.
- **Abstract base now**, the `ModalContext`/`Key` pattern. Chant and other systems have their own division vocabularies (quarter bar, half bar, full bar), so the lines-and-dots grammar is WSMN's, not universal. `DivisionShape` (ABC, core) and `BarLineShape` (WSMN concrete).
- **Ordered components, not before/after dot counts.** A WSMN bar line is a tuple of `BarLineComponent` members in time order, exactly LilyPond's `\bar` grammar (`:|.` is dots, thin, thick). Handles both-sided repeats, dots after lines, and later a segno component. Empty tuple is the invisible bar line.
- **`BarLineComponent`** is a closed `StrEnum` of seven members: THIN, THICK, DASHED, DOTTED, SHORT, TICK, DOTS. Covers every MusicXML `bar-style`, every MusicXML `<repeat>`, and every LilyPond glyph, with the empty tuple for the invisible bar. User-defined components are a future enum addition, not machinery now.
- **No dot count.** LilyPond's `:`, MusicXML's `<repeat>`, MEI's `barLine@form` and SMuFL's `repeatDots` all draw a fixed two dots; no target takes a count. Repeat dots are one member, `DOTS`. Four-dot repeats (early prints) become a `FOUR_DOTS` member if an importer ever meets one.
- `DivisionEvent` is **not** a `ContextEvent` and does not subclass it. No new shared zero-duration base class either; two classes fixing `duration` to `ZeroDuration` is fine.

## Files

### 1. `src/openmusickit/values/scoring/division_shape.py` (new)

`DivisionShape(ABC)` with `__slots__ = ()` and no abstract members, modelled on `Spanner` / `Marked` (an isinstance target with a documented contract) and on the `ModalContext` docstring style (`src/openmusickit/values/tone/modal_context.py:12`). Docstring says: how a notation system draws a division in a sequence; WSMN's `BarLineShape` is one implementation; chant's quarter/half/full bars would be another; nothing here is measure-based. Include a doctest showing `isinstance(BarLineShape(), DivisionShape)`.

Add `division_shape` to `values/scoring/__init__.py` (`from . import division_shape, mark` and `__all__`).

### 2. `src/openmusickit/systems/wsmn/scoring/bar_line_shape.py` (new)

```python
class BarLineComponent(StrEnum):
    THIN = auto()
    THICK = auto()
    DASHED = auto()
    DOTTED = auto()
    SHORT = auto()   # the lower part of the staff only (MusicXML "short", LilyPond ",")
    TICK = auto()    # a small stroke at the top line (MusicXML "tick", LilyPond "'")
    DOTS = auto()    # repeat dots, as the glyph draws them; visual only, control flow owns repeats

@dataclass(frozen=True, slots=True, init=False)
class BarLineShape(DivisionShape):
    """A WSMN bar line: its components in time order (the order LilyPond's
    `\bar` strings use: `:|.` is DOTS, THIN, THICK)."""
    components: tuple[BarLineComponent, ...]

    def __init__(self, *components: BarLineComponent) -> None:
        object.__setattr__(self, "components", components)

    def __repr__(self) -> str:
        inner = ", ".join(f"BarLineComponent.{c.name}" for c in self.components)
        return f"{type(self).__name__}({inner})"
```

- **Varargs constructor**: `BarLineShape(DOTS, THIN, THICK)`; `BarLineShape()` with no components is the invisible bar line (LilyPond `\bar ""`, MusicXML `none`). `init=False` keeps the dataclass-generated `__eq__`, `__hash__` and frozenness while the hand-written `__init__` takes the components positionally, so `components` is always a tuple.
- **`__repr__` round-trips**: `BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK)` evaluates to an equal object given `from openmusickit.systems.wsmn.scoring.bar_line import BarLineComponent, BarLineShape`. Full enum symbols, not bare member names. (The default dataclass repr would print `<BarLineComponent.DOTS: 'dots'>`, which does not evaluate.)
- Enum convention: module-level, `auto()`, trailing `#` glosses, as in `values/scoring/mark.py:5`.

Add `bar_line_shape` to `systems/wsmn/scoring/__init__.py`.

### 3. `src/openmusickit/systems/wsmn/scoring/symbols.py`

New section `# === BAR LINES ===` after the marks, importing `BarLineComponent, BarLineShape` from the new module. Constants, all `BarLineShape` instances built positionally, e.g. `end_repeat = BarLineShape(DOTS, THIN, THICK)` (Python name is the name; no `name` field):

| symbol | components | MusicXML / LilyPond |
|---|---|---|
| `single_bar` | (THIN,) | regular / `\|` |
| `double_bar` | (THIN, THIN) | light-light / `\|\|` |
| `final_bar` | (THIN, THICK) | light-heavy / `\|.` |
| `reverse_final_bar` | (THICK, THIN) | heavy-light / `.\|` |
| `heavy_bar` | (THICK,) | heavy / `.` |
| `double_heavy_bar` | (THICK, THICK) | heavy-heavy / `..` |
| `dashed_bar` | (DASHED,) | dashed / `!` |
| `dotted_bar` | (DOTTED,) | dotted / `;` |
| `short_bar` | (SHORT,) | short / `,` |
| `tick_bar` | (TICK,) | tick / `'` |
| `invisible_bar` | () | none / `""` |
| `start_repeat` | (THICK, THIN, DOTS) | heavy-light + forward / `.\|:` |
| `end_repeat` | (DOTS, THIN, THICK) | light-heavy + backward / `:\|.` |
| `double_repeat` | (DOTS, THIN, THICK, THIN, DOTS) | `:\|.\|:` |

Update the module docstring's first line and add a doctest (`end_repeat.components[0]`). 14 symbols.

### 4. `src/openmusickit/objects/division_event.py` (new)

```python
@dataclass(kw_only=True, slots=True)
class DivisionEvent(SequentialEvent):
    shape: DivisionShape | None = None
    duration: Duration = field(default_factory=ZeroDuration, init=False)
```

Mirror `ContextEvent` (`src/openmusickit/objects/context_event.py:13`): `duration` fixed to `ZeroDuration`, `init=False`, doctest showing `DivisionEvent(duration=None)` raises `TypeError`. `shape=None` means "a division here; its drawing is unspecified", the same reading as `ModalContextEvent.modal_context=None`; the core never defaults to a WSMN value.

Docstring carries the policy so future renderers and the control-flow module inherit it rather than reinvent it:

- Divisions are optional and per line. Different lines may have different divisions (polymetric voices, early music). A pickup is simply a bar line that arrives early.
- A renderer that derives bar lines from a time signature fills gaps and warns where an explicit division disagrees. Repeat dots are visual; control flow, when it exists, follows the same rule.
- Marks attach to a division as to any node: a segno or fermata on a bar line is a `Marking` with a MARKS edge to the `DivisionEvent` (doctest via `graph.add_edge(marking, division, EdgeType.MARKS)`, cf. `graph.py:205`).

Add `division_event` to `objects/__init__.py` imports and `__all__`.

### 5. `src/openmusickit/graph/graph.py`

`_begins_syllable` (`graph.py:1061-1069`): replace the `ContextEvent` and `GraceDuration` checks with one rule, `isinstance(obj.duration, ZeroDuration)` (GraceDuration subclasses ZeroDuration, `duration.py:300`). Update the docstring at `graph.py:1017` to say "anything of zero duration (a context event, a division, a grace note)". Drop the `ContextEvent` import if it is then unused (line 465 is a doctest import, separate); keep `GraceDuration` only if still referenced.

### 6. `docs/_quarto.yml`

Add `values.scoring.division_shape` after `values.scoring.mark`; `systems.wsmn.scoring.bar_line_shape` before the scoring symbols entry; `objects.division_event` after `objects.context_event`.

### 7. Tests

Style: plain functions, one behaviour each, as in `tests/objects/test_marking.py`.

- `tests/systems/wsmn/scoring/test_bar_line.py` (new dir, add `__init__.py` only if the other test dirs have one; check `tests/systems/wsmn/tonal`): `BarLineShape(THIN).components == (THIN,)`; `BarLineShape()` has empty components and hashes; equality and hash by components; `eval(repr(shape)) == shape` for every symbol (round-trip); `isinstance(..., DivisionShape)`; symbol sweep over `bar_line_symbols` (all `BarLineShape`, all hashable, all distinct, `end_repeat` and `start_repeat` mirror each other reversed).
- `tests/conftest.py`: `bar_line_symbols` fixture via `symbols_of(scoring_symbols, BarLineShape)`; `tests/test_fixtures.py`: pin `len == 14`, `distinct == 14`. `mark_symbols` stays at 201 (`symbols_of` matches exact type).
- `tests/objects/test_division_event.py`: zero duration and cannot be set at construction; `alter_duration` / assignment of a positive duration is either rejected or leaves ZeroDuration (decide: assignment is allowed by the dataclass, so document the contract as "construct-time only", matching ContextEvent); equality ignores id and compares shape; `DivisionEvent()` has `shape is None`; a `Marking(mark=segno)` attaches with a MARKS edge.
- `tests/objects/test_lyrics.py`: extend `test_zip_skips_rests_and_context_events` (line 272) or add a sibling so a `DivisionEvent` between two notes receives no syllable.
- `tests/graph/`: one test that `relative_onset` across a `DivisionEvent` equals the onset without it (zero duration passes through, `graph.py:645`).

## Verification

```
uv run pytest -q
uv run ruff check src tests && uv run ruff format --check src tests
```

Doctests run automatically (`--doctest-modules` in pyproject). Then confirm the docs list the new modules:

```
uv run python docs/build_reference.py
```

and that the three new pages appear under Values, WSMN, and Objects.

## Out of scope (deliberately)

- Any renderer, measure computation, or TimeSignature node.
- Control flow / repeat semantics.
- User-defined line shapes and four-dot repeats (add an enum member when a real score needs one).
- A segno or bracket component (add when a renderer or importer needs the in-glyph position).
