# Plan: consistency audit — Tier 0 fixes

Status: **Tier 0 completed 2026-09-18** (commits b6c61d6..d0539a8); Tiers 1–4 still to be discussed, so this plan stays open.
`uv run pytest` → 2362 passed (was 2358; four new doctests).

Deviations / notes from implementation:

- 0.3 required an adjacent fix: `RustworkxAdapter.get_next`/`get_previous` raised
  `rustworkx.NoSuitableNeighbors` at the end of a line instead of returning `None`
  as their contract says, which broke every line-walking method
  (`zip_lyrics_to_objects`, `unlink_lyric_sequence`, `transform_tones` with
  `end=None`). Fixed in the same commit (ddf84b6).
- 0.1: `ZeroDuration` has no `__repr__`, so the doctest checks `isinstance`.
- 0.7: `OmkId == str` remains True while `hash(OmkId) != hash(str)` — the same
  eq/hash asymmetry removed from `TonalVector` in 0.6, kept here by decision and
  logged in `revisit.md`.
- 0.12: a root-position `ChordType`/`Chord` still compares equal to a plain
  `ToneCollection` with the same tones and root (Python falls back to
  `ToneCollection.__eq__` when the chord side returns `NotImplemented`).

# OMK consistency audit — inventory for discussion

## Context

The codebase has evolved through several design phases and its conventions have drifted:
naming (singular/plural, verb/noun, abbreviations), typing style, dataclass usage,
import hygiene, error signalling, and docstring style are all applied unevenly. The
design itself is settled; this is a catalog of the *inconsistencies* found by reading
every module in `src/` and `tests/`, ordered by severity, each with a proposed fix and
blast radius. Nothing here is implemented yet — the user will pick items to fix.

Baseline: `uv run pytest` → 2358 passed. No linter/formatter/type-checker is configured.

Legend for blast radius: **L** = one file, no API change · **M** = a few files or a
rename callers must follow · **H** = touches import paths or public constructor shapes
across the package.

---

## Tier 0 — Latent bugs surfaced by the audit — DECIDED (2026-09-18)

Each item below is a small, independent change. One commit per item (or per obviously related pair).

**0.1 `ContextEvent.duration`** — [context_event.py:11-18](src/openmusickit/objects/context/context_event.py#L11-L18).
The `@property` is dead: `slots=True` rebuilds the class and the inherited `duration` field default (`None`) replaces it. Decision: context events are always zero-length and callers cannot pass a duration.
Do: replace the property with `duration: Duration = field(default_factory=ZeroDuration, init=False)`; drop `slots=True` from `ContextEvent` and `KeySignatureEvent` (parent `SequentialObject` is not slotted, so slots buy nothing and caused this).

**0.2 `LyricSyllable` typos** — [lyrics.py:41,70-80](src/openmusickit/objects/lyrics/lyrics.py#L41-L80).
Do: rename `__post__init__` → `__post_init__` (validation starts running; `word=None` now defaults to `s`); delete the `id`/`meta` property overrides (they read nonexistent `self.__id`; `OmkObject` already provides them); rename `__string__` → `__str__`.

**0.3 `OmkGraph` methods that cannot run** — [graph.py:179-237](src/openmusickit/graph/graph.py#L179-L237).
Decision: `MARKS` and `ANNOTATES` are the correct edge types (articulation/annotation were renamed). Unlink methods should simply find the LYRIC edge and remove it; the `remove_edge(obj, syl, type)` three-arg calls, the one-arg `get_edges(syllable)`, and `edge._from`/`edge._to` are cruft from API changes.
Do: `add_articulation` → `EdgeType.MARKS`, `add_annotation` → `EdgeType.ANNOTATES`; `unlink_lyric_from_object` → `self.remove_edge(self.get_edge(obj, lyric_syllable, EdgeType.LYRIC))`; `unlink_lyric_sequence` → for each syllable, `for edge in list(self._graph.incident_edges(syllable, EdgeType.LYRIC)): self.remove_edge(edge)`.

**0.4 NEXT uniqueness guard** — [rx_adapter.py:85-88](src/openmusickit/graph/rx_adapter.py#L85-L88).
Decision: one outgoing NEXT per node, as the docstring says.
Do: replace the duplicated `has_edge(source, target, NEXT)` check with `any(self.out_edges(source, EdgeType.NEXT))`.

**0.5 `get_edges` annotations** — [graph_adapter.py:44](src/openmusickit/graph/graph_adapter.py#L44), [rx_adapter.py:125](src/openmusickit/graph/rx_adapter.py#L125), [graph.py:75](src/openmusickit/graph/graph.py#L75).
Decision: keep the `(forward, backward)` pair.
Do: annotate all three as `tuple[list[OmkEdge], list[OmkEdge]]`.

**0.6 `TonalVector.__eq__`** — [tonal_vector.py:723-748](src/openmusickit/systems/wsmn/tonal/tonal_vector.py#L723-L748).
Decision: drop int equality (`C == 0` was breaking the eq/hash contract).
Do: equal to `TonalVector` or a plain tuple with the same values; `NotImplemented` for anything else; update the doctest at line 737 (`TonalVector((0,1)) == 1` → show `int(TonalVector((0,1))) == 1` instead). Check `tests/` for any `== <int>` comparisons on vectors before committing.

**0.7 `OmkId.__eq__`** — [id.py:54-55](src/openmusickit/utils/id.py#L54-L55).
Decision: keep string equality for now (JSON persistence and graph backends need atomic string ids); return `NotImplemented` for types other than `OmkId` and `str`. Log in `_plans/revisit.md`: whether `OmkId` should exist at all versus plain UUID strings.

**0.8 `interval_quality` string parser** — DEFERRED. Decade-old arithmetic core; to be looked at together in a dedicated session. Log in `_plans/revisit.md`. Do nothing now.

**0.9 `_tonal_modulo` falls off the end** — DEFERRED with 0.8. Log in `_plans/revisit.md`.

**0.10 Dependencies and unused imports** — [pyproject.toml:17-22](pyproject.toml#L17-L22).
Do: remove `scipy` and `pydantic`; rewrite specifiers as PEP 508 (`"rustworkx>=0.18.1"`, `"bidict>=0.24.1"`); delete `poetry.lock`; `uv sync`. Remove unused imports: `bidict` (mark.py:3), `List` (duration.py:6), `Any`/`field` and the duplicate `dataclass` line (id.py:2,5-6), `Iterable` (graph_adapter.py:2, rx_adapter.py:1), `field` (lyrics.py:1), `TemporalElement` (metrical_duration.py:5), `D_LEN`/`AC` (interval_quality.py:4 — import only, no logic change), `TemporalSystem` (clock_time.py:7), `m3`/`P4`/`m7` (tests/tones/test_key.py:12).

**0.11 Negative durations (`ZeroDuration.__sub__`, `Next.nudge`)** — DEFERRED. Neither displacement nor nudging is used yet. Log in `_plans/revisit.md`: are durations signed, or is displacement a signed offset on the edge?

**0.12 `Chord`/`ChordType` equality** — [chords.py](src/openmusickit/systems/wsmn/tonal/chords.py), inheriting [tone_collection.py:65-71](src/openmusickit/values/tone/tone_collection.py#L65-L71).
Decision: bass counts toward equality; suffix and name do not (consistent with `ToneCollection` ignoring `name`).
Do: on `ChordType`, `__eq__` = `super().__eq__(other) and self.bass == other.bass` (with the `isinstance` / `NotImplemented` guard), `__hash__` = `hash((super().__hash__(), self.bass))`; `Chord` gets the same (or they share it once 4.3 gives them a common base). Add a doctest: `C(maj) == C(maj) / E` → `False`.

**0.13 `ClockDuration` incomparable to metered time** — [clock_time.py:49-57](src/openmusickit/values/time/clock_time.py#L49-L57).
Decision: deliberate; keep the overrides. `rational_length` is a WSMN notion (the named fractional value) and cross-system comparison must go through a `TemporalRatio`/`Tempo`.
Do: add a short comment on `__eq__`/`__lt__` (and any other method that could receive a metered duration) pointing to `from_duration` and `TemporalRatio`.
Note for `_plans/revisit.md` (user, mid-session): `rational_length` is a WSMN concept and should probably not live on the abstract `TemporalElement` in `values/`. Not done now because it is load-bearing on the base contract: `TemporalElement.__eq__/__lt__/__hash__` and `_length_of` ([duration.py:15-91](src/openmusickit/values/time/duration.py#L15-L91)), `TemporalRatio.r` (divides the two sides' lengths, including metered-over-clock ratios built by `Tempo`), `ClockDuration.from_duration`, `CompoundTemporalUnit.remainder/first_out_of_bounds`, `TemporalUnit.rational_length`. Removing it means redefining how elements compare and how `TemporalRatio` computes its multiplier across systems.

**0.14 Test hygiene** — delete the 0-byte `tests/harmony/test_tone_collection.py`; rename `test_test` in `tests/tones/test_tonal_arithmetic.py:4` to describe what it asserts.

**0.15 Create `_plans/revisit.md`** — a single running file of deferred design questions (the user asked for one place for these). Seed it with 0.7, 0.8, 0.9, 0.11, and the `rational_length` note from 0.13. Format: one `##` heading per item, date, one-paragraph statement of the question, file pointers.

---

> **Status of Tiers 1–4:** not yet discussed — these remain the raw audit inventory (tables). They will be walked through in dialog the same way as Tier 0 before anything in them is implemented.

## Tier 1 — Cross-cutting conventions (mechanical, high value)

### 1.1 Typing style
- `Optional[X]` → `X | None`: `graph/graph_adapter.py` (17 sites), `graph/rx_adapter.py` (mixed — line 201 already uses `| None`).
- Implicit Optional (`x: T = None`): `tonal/chords.py:26-27,89,184,190,214`, `temporal/metrical_duration.py:38,144,152`, `temporal/time_signature.py:27`.
- `Tuple[str, str]` → `tuple[str, str]`: `temporal/time_signature.py:4,27,43,96`.
- `tuple[int]` used to mean "variable length" → `tuple[int, ...]`: throughout `tonal_arithmetic.py` and `TonalVector.__add__/__sub__/…`.
- Spacing: `int|Fraction`, `OmkId|str`, `direction: TonalDirection=TonalDirection.UP` → PEP 8 `int | Fraction`, `direction: TonalDirection = …` (`duration.py`, `graph.py`, `tonal_vector.py`, `chords.py`, `metrical_duration.py`).
- Wrong generic syntax `dict[int:str]` → `dict[int, str]` (`constants.py:97`); `_diatone -> dict` should be `-> Diatone` (`tonal_vector.py:346`).
- Missing return types on many public methods in the older modules (`tonal_vector.py` `qualify_octave`/`unqualify_octave`/`o`; `metrical_duration.py` `n/d/dots/real_n/…`; `clock_time.py` `from_*`; `interval_quality.py` everything).
- Untyped `__init__` params: `TonalSystem(name, desc)`, `IntervalQuality(name, rel_number)`, `_IntervalRepresentation(vector)`, `ToneCollection.combinations(k)`, `Tone.from_string(cls, s)` (vs `Interval.from_string(cls, s: str)`).
- Forward references three ways: `from __future__ import annotations` + bare names (12 modules), quoted `"Chord"`/`"ChordType"` strings (`chords.py` only), and `__future__` imported where nothing needs it (`silent_tone.py`). `typing.Self` never used although every `transform`/`scale`/`from_*` is self-returning.
- `Callable`/`Iterable`/`Iterator` imported from `typing` everywhere; nothing uses `collections.abc` (ruff `UP035` flags this).
- **Fix**: mechanical; `ruff --select UP,FA` handles most. **Blast: L** (annotations only).

### 1.2 Import headers
Three styles coexist, sometimes in one file:
- Relative (`from .tone import`) in `values/*`, `wsmn/temporal/symbols.py`; absolute (`from openmusickit…`) in `objects/*`, `graph/*`; **mixed in one header** in `graph/graph.py`, `objects/lyrics/lyrics.py`, `wsmn/tonal/tonal_vector.py`, `wsmn/tonal/chords.py`, `wsmn/tonal/symbols.py`, `wsmn/tonal/key.py`.
- Groups not separated/sorted: `rx_adapter.py` (third-party after first-party), `mark.py` (no blank line before `bidict`), `omk_object.py` (stray blank line between first-party imports), `clock_time.py`, `key.py`.
- Module docstring *after* imports in `values/__init__.py`.
- `from fractions import Fraction as F` in `metrical_duration.py` vs `Fraction` in every other module; `import functools`/`import math`/`import itertools` (module style, `interval_quality.py`, `tonal_arithmetic.py`) vs `from functools import total_ordering`/`from math import lcm`/`from itertools import combinations` elsewhere; module aliases `as ta`/`as iq` only in `tonal_vector.py`.
- Within `wsmn/tonal/`, `key.py` imports its siblings absolutely while `chords.py`, `symbols.py`, `interval_quality.py`, `tonal_arithmetic.py`, `tonal_vector.py` import the same siblings relatively.
- `tests/rhythm/test_metered_duration.py` is the only file in the repo with a correctly separated stdlib / third-party / first-party header.
- **Fix**: pick absolute imports everywhere (matches the majority and doctests), adopt ruff `I` (isort) + `F401`. **Blast: L** — pure header edits; ruff `--fix` does it.

### 1.3 Bare `except:` and exception chaining (AGENTS.md explicitly forbids the former)
- Bare `except:` at `interval_quality.py:46,51`, `tonal_arithmetic.py:527`, `tonal_vector.py:342`.
- Re-raise style: `raise … from None` once (`tonal_vector.py:193`); every other re-raise inside an `except` (`chords.py:80`, `metrical_duration.py:373`, `time_signature.py:85`, `duration.py:217,279`, `tonal_vector.py:756`) omits `from`, giving implicit "During handling…" chains.
- Unimplemented-method bodies: `raise NotImplementedError` in `graph_adapter.py` vs bare `pass` in `OmkGraph.load_from_json/load_from_file/import_*/export_*` (`graph.py:30-48`) — the latter silently return `None` with a declared `-> OmkGraph`.
**Fix**: typed excepts; `from e` / `from None` consistently; `NotImplementedError` for the graph stubs. **Blast: L**.

### 1.4 `__eq__` for foreign types
`SilentTone.__eq__` (returns `False`), `TonalVector.__eq__` (returns `False`), `OmkId.__eq__` (compares strings) vs `ToneCollection`, `TemporalElement`, `TemporalRatio`, `ClockDuration` (return `NotImplemented`). **Fix**: `NotImplemented` everywhere; for `SilentTone` and `OmkId` just delete the hand-written method (see Tier 3). **Blast: L**.

### 1.5 Identity/type comparisons
`type(a) != type(b)` (`edge.py:68`, `lyrics.py:50`), `type(self) == type(x)` (`tonal_vector.py:743`), `prev == None` (`tonal_vector.py:1077`), `type(tone) is SilentTone` (`note.py:131`, defensible). **Fix**: `is not`/`isinstance`/`is None`. **Blast: L**.

### 1.6 Factory-function naming
`Rest(duration)` and `Tempo(n, beat)` are CapWords functions; `time_signature()`, `additive_time_signature()`, `tuplet()`, `triplet()` are snake_case. **Fix**: snake_case (`rest`, `tempo`) per PEP 8 — or promote `Rest` to a real subclass if you want `isinstance(x, Rest)`. **Blast: M** (callers: `graph.py` doctest, `note.py` doctests, `tests/notes/test_note_event.py`, `clock_time.py` docstrings).

### 1.7 Underscore-prefixed dataclass fields leaking into constructors
`OmkEdge(_type=…)`, `KeySignatureEvent(_key=…, _key_signature=…)`, `Key(_mode=…, _name=…)`, `ClockDuration(_microseconds)`, `OmkObject(_id=…, _meta=…)`. The "private" name is the public kwarg. `Next` already shows the better pattern (`field(init=False)`).
**Fix**: (a) `_id`/`_meta` → `field(init=False)` + keep the property, or accept them as plain public fields `id`/`meta` (dataclass `repr=False`); (b) `OmkEdge._type` → public `type`; (c) `KeySignatureEvent._key/_key_signature` → public `key`/`key_signature` with the XOR check in `__post_init__` and `set_key`/`set_key_signature` kept (or replaced by a `@key.setter` that clears the other); (d) `Key._mode/_name` → `mode: ModePattern | None`, `name` override via `field(default=None)` with the computed fallback in a property named differently (`display_name`), or keep as is. (e) `ClockDuration._microseconds` → `microseconds` (and drop the rounding property, or rename it `microseconds_int`).
**Blast: M–H** — every construction site: `symbols.NoKey`, `Key.of`, `graph.py:82`, doctests in `graph.py`/`context_event.py`, tests.

### 1.8 `__repr__` class-name style
Hardcoded (`'TemporalUnit(…'`, `'ClockDuration(…'`, `'Next(…'`, `'NoteEvent(…'`, `'TonalVector(…'`, `'TiedDuration(…'`, `'TimeSignature(…'`, `'MeteredDuration(…'`), `self.__class__.__name__` (`CompoundTemporalUnit`, `OmkEdge`), `type(self).__name__` (`ToneCollection`, `KeySignature`). **Fix**: `type(self).__name__` everywhere (subclass-safe). **Blast: L** (doctest strings unchanged for the base classes).

### 1.9 Docstring section style
NumPy (`Examples\n--------`, `Parameters\n----------`, `Raises\n------`) in most of `wsmn/*`, `tone_collection.py`, `note.py`; Google (`Raises:`, `Returns:`, `Examples:` indented) in `duration.py`, `clock_time.py`, `key.py`, `metrical_duration.py:352`, `time_signature.py`; fenced ```` ``` ```` code blocks (not doctests) in `duration.py`, `clock_time.py`, `tone.py`, `metrical_duration.py`. `Example\n-------` (singular) in `tonal_vector.py:762,790,806`. **Fix**: pick NumPy (majority); convert fenced examples to doctests where they'd run. **Blast: L**.

### 1.10 Tooling (enables 1.1–1.3, 1.5 mechanically)
No `ruff`/`mypy`/`pyright` config (the `# noqa: F841` in `tests/rhythm/test_metered_duration.py:378` is a no-op). ~115 trailing-whitespace lines (`tonal_vector.py` 35, `constants.py` 25, `duration.py` 23, `key.py` 17, `metrical_duration.py` 15) and 15 files without a final newline. **Fix**: add `[tool.ruff]` with `select = ["E","F","I","UP","B","FA"]`, `target-version = "py312"`, and (optionally) `[tool.pyright] typeCheckingMode = "basic"`. Run `ruff check --fix` + `ruff format` once. **Blast: L** (config + one formatting commit).

---

## Tier 2 — Naming

| # | Inconsistency | Proposed fix | Blast |
|---|---|---|---|
| 2.1 | Module `wsmn/temporal/metrical_duration.py` holds `MeteredDuration`; test file is `test_metered_duration.py`. | Rename module → `metered_duration.py`. | M (imports in `temporal/__init__`, `temporal/symbols`, tests, doctests) |
| 2.2 | Package layout mixes singular/plural and one-module packages: `objects/note/note.py`, `objects/chord/chord_event.py`, `objects/context/context_event.py`, `objects/lyrics/lyrics.py`, `graph/edges/edge.py`. Module names don't match class names (`note.py` → `NoteEvent`). | Flatten: `objects/note_event.py`, `objects/chord_event.py`, `objects/context_event.py`, `objects/lyrics.py`, `objects/omk_object.py`; `graph/edge.py`. Or keep sub-packages but name them uniformly (`objects/note/note_event.py`, `objects/lyric/lyric_syllable.py`). | H (import paths; mechanical `sed`) |
| 2.3 | `__init__.py` re-export style: most re-export *modules*; `objects/chord/__init__.py` re-exports the *class*; `objects/context/__init__.py` empty; `values/scoring/` and `systems/wsmn/scoring/` have **no** `__init__.py` (implicit namespace packages); `objects/__init__.py` omits `chord`, `context`; `values/__init__.py` omits `scoring`; `systems/wsmn/__init__.py` omits `scoring`; `wsmn/tonal/__init__.py` omits `key` but includes the empty `str_to_vec`; `graph/__init__.py` hoists `edge` out of `edges/`. | One rule (re-export modules, list every submodule). Add the two missing `__init__.py`. | L |
| 2.4 | Vestigial modules: `tonal/str_to_vec.py` (docstring only; parsing now lives in `tonal_vector.py`), `values/time/meter.py` (0 bytes), `tonal/wsmn.py` (a `TonalSystem` instance nothing references), empty classes `TemporalSystem`, `GraphMeta`, `Spanner`. `TemporalSystem` is `pass` while `TonalSystem` has `name`/`desc`. | Delete `str_to_vec.py`, `meter.py`; either give `TemporalSystem` the same shape as `TonalSystem` (and an instance in `temporal/`) or drop both until needed. | L |
| 2.5 | `Event` suffix: `NoteEvent`, `ChordEvent`, `ContextEvent`, `KeySignatureEvent` vs `LyricSyllable`, `Spanner`; base class is `SequentialObject`; graph API says `insert_event` but `add_node`/`add_line`/`add_next(current, next)`; `objects/__init__.py` docstring talks about `Note`. `lyrics.py:27` TODO says lyrics should be events. | Decide the vocabulary: either `SequentialObject` → `Event` (and `LyricSyllable` → `LyricEvent`?) or drop `Event` from `NoteEvent`/`ChordEvent`. Graph method names follow. | H (design decision; rename is mechanical) |
| 2.6 | Cryptic module-level tables: `MS`, `AC` (built by **rebinding a name from a list-of-dicts to a list-of-objects**, `constants.py:113-124,169-182`), `q_vals`, `qualities`, `ordinals`, `fractionals` (lowercase constants), `EURO_SF`. | `MS` → `DIATONES` (or `MAJOR_SCALE`), `AC` → `ACCIDENTALS`, build them directly from `Diatone(...)`/`Accidental(...)` literals; `ORDINALS`, `FRACTIONALS`, `QUALITY_NAMES`. | M (`MS`/`AC` used in 5 modules) |
| 2.7 | Single-letter / abbreviated public attributes: `Diatone.d c q i ln sf f z` (ctor uses `i` but the dict key is `'in'`), `Accidental.v u a ly` (ctor params `uni`, `asc` ≠ property names `u`, `a`), `TemporalRatio.r` `_n` `_c`, `MeteredDuration.n d tr`, `TonalSystem.desc`, `LyricSyllable.s`, `TimeSignature.n/d` (**strings**) vs `MeteredDuration.n/d` (**ints**), `TonalVector.o` (int) vs `_IntervalRepresentation.o` (str). | Keep `d`/`c`/`o` on `TonalVector` (domain vocabulary, documented) but spell out everything else: `Diatone.degree/chromatic/quality_type/interval_name/letter/solfege/function/dissonance`, `Accidental.offset/name/unicode/ascii/ly`, `TemporalRatio.nominal/contextual/multiplier`, `MeteredDuration.numerator/denominator/ratio`, `TimeSignature.top/bottom` (or `presentation` only), `LyricSyllable.text`, `TonalSystem.description`. | M (Diatone/Accidental attrs used across `tonal_vector`, `tonal_arithmetic`, `key`, `interval_quality`) |
| 2.8 | Method names in `_PitchRepresentation`: `unicode_C4`/`ascii_C4` (capital), `ly_abs8ve` (property) vs `ly_rel8ve(prev)` (method), `_unicode(mid_c)` vs `_ascii(octave_modifier, show_nat)` (same param, different name; `show_nat` is unused), `verbose`. `_ln`, `_modifier`, `_modifier_value` are "private" but used from `key.py`. `_IntervalRepresentation` never implements the abstract `ascii` (unenforced — see 3.8). | `unicode_c4`/`ascii_c4` (or `unicode_at(mid_c)`), `ly_absolute`/`ly_relative(prev)`, one param name `mid_c`; make `letter`, `accidental`, `alteration` public; add `ascii` to the interval representation. | M |
| 2.9 | Misspelling `arpegiate` (`chords.py:40,195`); "diszonance", "rhthmic", "reprenting", "designeted" in docstrings. | `arpeggiate`; fix typos. | L |
| 2.10 | Builtin shadowing: chord symbol **`min`** (`symbols.py:77` — `from symbols import *` clobbers `min()`), params `id` (`graph.py:53`, `lyrics.py:104`), `next` (`graph.py:91,105,124`), `oct` (`tonal_vector.py:759,780`), local `sum` (`tonal_arithmetic.py:43`), field `type` (`mark.py:40`, `edge.py`). | `min` → `mnr`/`minor`/`min_` (your call; `maj` stays); `id` → `node_id`; `next` → `following`/`successor`; `oct` → `octave`; `sum` → `total`; `Mark.type` → `kind`. | M for `min` (used in doctests/tests), L otherwise |
| 2.11 | Constructor classmethod names: `from_string`, `from_ly`, `from_fraction`, `from_length`, `from_alts`, `from_minutes`, `from_timedelta`, `from_duration` vs `Key.of()`, `OmkId.new()`, `OmkId.parse()`, `OmkGraph.load_from_json/load_from_file`. `to_timedelta` is a **property** with a verb name. `from_fraction(value, tr=None)` takes `tr` positionally, sibling `from_length(length, *, tr=None)` keyword-only. `OmkGraph.export_to_json` / `export_json_to_file` / `import_json_graph` / `import_file` — four shapes. | `Key.of` → `Key.from_mode(tonic, mode)`; `OmkId.parse` → `from_string`; `from_alts` → `from_fifths` (it's the inverse of `.fifths`); `to_timedelta` → method or `timedelta` property; `load_from_*` → `from_*`; make `tr` keyword-only in both. | M |
| 2.11a | Graph query vocabulary: `get_node/get_edge/get_edges/get_next/get_previous/get_edge_endpoints/get_source_of_edge/get_target_of_edge` vs un-prefixed `nodes()/edges()/edges_between()/successors()/out_edges()/degree()/num_nodes()/filter_edges()` in the same class. `get_edges(a, b)` (two lists) overlaps `edges_between(a, b)` (iterator); `OmkGraph.get_edges_by_type(t)` overlaps `edges(t)`. `connect_lyric_to_object` / `unlink_lyric_from_object` (connect/unlink). `OmkGraph._graph`/`_meta` have no accessor while `RustworkxAdapter.graph` is public. | Drop `get_` where the method takes no lookup key (`next_of(node)`, `previous_of(node)`), or keep `get_` only for by-id lookups; remove the two overlapping pairs; `connect`/`disconnect`. | M (adapter ABC + implementation + OmkGraph) |
| 2.12 | Predicates: `is_rest` (property) vs `SyllablePlacement.is_beginning()` / `is_ending()` (methods), `_has_octave` (private property). | Properties for arg-less predicates on values; make `has_octave` public. | L |
| 2.13 | Three "quality" names: `chords.Quality` (chord), `constants.QualityType` (P vs Mm), `interval_quality.IntervalQuality`. | `ChordQuality`, `IntervalQualityType` (or `QualityClass`). | M |
| 2.14 | Enum base: `Enum` (`LexicalStress`, `SyllablePlacement`, `Quality`, `QualityType`, `SolfegeStyle`) vs `StrEnum` (`MarkType`, `AttachmentMode`, `EdgeType`, `EdgeOrigin`, `TimingAnchor`, `NudgeDirection`, `TonalDirection`); values `auto()` vs explicit strings vs floats (`QualityType.Mm = 0.5` is used arithmetically). Member names: `Quality.MAJ/MIN/SUS/POW/AUG/DIM/DOM/HDM` (3-letter) vs full words everywhere else; `QualityType.P`/`Mm` mixed-case with module aliases `P`, `Mm`. `EdgeType` mixes verbs (`ANNOTATES`, `MARKS`), adjectives (`SIMULTANEOUS`), prepositions (`STARTS_AT`) and a bare noun (`LYRIC`). | `StrEnum` + `auto()` for all label-like enums; full-word members (`MAJOR`, `HALF_DIMINISHED`, …); leave `QualityType` numeric but document it; decide one grammatical form for `EdgeType` (verbs: `SINGS`/`HAS_LYRIC` for `LYRIC`). | L–M |
| 2.15 | Sharp symbols use `x` (`Cx` = C♯, `Cxx` = C𝄪) though `x` conventionally means double-sharp. | Consider `Cs`/`Css` (LilyPond-ish) or `C_`/`C__`. Your call — flagged only. | H if changed (used everywhere in doctests/tests) |
| 2.16 | Tests: dirs `harmony/notes/rhythm/tones` don't mirror `src`; `tests/tones/test_fixtures.py` is collected as a test module but only defines fixtures; `harmony/chord_fixtures.py` must be imported explicitly; no `conftest.py`; test files named after methods (`test_from_ly.py`), modules (`test_key.py`), and concepts (`test_string_roundtrip.py`). | `tests/conftest.py` holding all fixtures; dirs mirror `src` (`tests/values/`, `tests/systems/wsmn/tonal/`, …). | L |
| 2.17a | Test idioms: `@pytest.parametrize` in `test_from_string.py` (19), `test_key.py` (11), `test_string_roundtrip.py` (10), `test_from_ly.py` (6) vs assert-in-`for`-loop (55 loops) in `test_chords.py`, `test_metered_duration.py`, `test_tonal_arithmetic.py`, `test_tone_hierarchy.py`, `test_key.py` (both styles in the same file). `pytest.raises(match=)` used once out of ~40 sites. `test_metered_duration.py:19-28` helpers `_tuplet`/`_sig` duplicate `temporal/symbols.tuplet`/`time_signature`; `test_string_roundtrip.py:21-34` re-implements the `tonal_tuples` fixture. In-function imports of already-imported names (`test_chords.py:110,123,207`); mid-file import (`test_tonal_arithmetic.py:85`). No tests at all for `graph/`, `objects/lyrics`, `objects/context`, `utils/`, `values/scoring` (doctests only). | Parametrize where the loop body is a single assertion; `match=` on `raises`; reuse `symbols` helpers and the shared fixtures. | L |
| 2.18 | `Key.mode` property returns the mode's *name string*, `Key._mode` holds the `ModePattern`; `Key.signature` (field) vs `KeySignatureEvent.key_signature` (property) vs class `KeySignature`. `ChordEvent.chord` (singular) holds a `ToneCollection`; `NoteEvent.tones` (plural) holds a set. | `Key.mode` → the `ModePattern`, `Key.mode_name` for the string (or drop); `ChordEvent.chord` is fine if `Chord` is the type — annotate it `Chord`, not `ToneCollection`. | L |
| 2.17 | `_id`/`_meta` accessed directly across the adapter boundary (`rx_adapter.py` uses `node._id` 8×) although `OmkObject.id` exists; `TimeSignature.__init__` reads `spec._units`; `key.py` reads `tone.pitch._modifier_value`, `._ln`. | Use the public accessors (and make the pitch ones public per 2.8). | L |

---

## Tier 3 — Dataclass / value-semantics consistency

| # | Inconsistency | Proposed fix | Blast |
|---|---|---|---|
| 3.1 | Hand-rolled value classes (`__init__` storing `_x` + read-only properties, sometimes `__eq__`/`__hash__`/`__repr__`) where a frozen dataclass would be identical: `TonalSystem`, `Diatone`, `Accidental`, `TemporalUnit`, `TemporalRatio`, `CompoundTemporalUnit`, `TiedDuration`, `ToneCollection`, `MeteredDuration`, `IntervalQuality`. Meanwhile `Mark`, `OmkId`, `ModePattern`, `Key`, `SilentTone`, `ClockDuration` *are* frozen dataclasses. | `@dataclass(frozen=True)` for the first six (pure data); `ToneCollection` too (`tones: tuple[Tone, ...]`, `root`, `name_template`; `Key.of` must stop mutating `tones.root` — pass root into `transform`); `MeteredDuration` via `__post_init__` normalisation + `object.__setattr__`, or keep the class and just add `__eq__`-by-fields. | L for the six; M for `ToneCollection` (Chord/ChordType `__init__` signatures) and `MeteredDuration` |
| 3.2 | Mutable-but-hashable: `TemporalUnit.count/base` public & mutable, hashed by `rational_length`; `Chord`/`ChordType.bass/quality/suffix` public & mutable, inherit `ToneCollection.__hash__`; `ToneCollection.root` public & mutable, in the hash. | Freeze (3.1). | as 3.1 |
| 3.3 | `ClockDuration` is `frozen=True` yet hand-writes `__eq__`, `__lt__`, `__hash__`, `__repr__` that duplicate the generated/inherited ones; field is `_microseconds`. | Delete the four methods (keep `__str__`); rename field. | L |
| 3.4 | `SilentTone` is `frozen=True` and hand-writes `__eq__` (returns `False` for others) and `__repr__` (`f'SilentTone()'` — no placeholders) that the dataclass would generate. | Delete both. | L |
| 3.5 | `slots=True` used on `ContextEvent`/`KeySignatureEvent` whose parent `SequentialObject` has `__dict__` (no memory benefit, and it is what killed the `duration` property — 0.1), and on `Mark`, `OmkId`, `ModePattern`, `Key`; not on `NoteEvent`, `ChordEvent`, `OmkObject`, `SilentTone`. | Rule: `slots=True` only on frozen leaf value types; never in the `OmkObject` hierarchy. | L |
| 3.6 | `OmkEdge._meta: dict` (untyped) vs `OmkObject._meta: dict[str, Any]`; `Next` re-declares `type` property that `OmkEdge` already provides. | Align; delete the override. | L |
| 3.7 | Builtin subclassing vs wrapping for collections: `TonalVector(tuple)`, `KeySignature(tuple)`, `LyricSequence(list)` vs wrappers `ToneCollection`, `CompoundTemporalUnit`, `TiedDuration`. `LyricSequence(list)` is the outlier (mutable list carrying an `id`, `section_name` defaults to `"None None"`). | Make `LyricSequence` an `OmkObject` wrapper (`syllables: tuple[...]`), or a plain `SequentialObject` list-like in line with `ToneCollection`. | M (`graph.add_lyric_sequence`) |
| 3.8 | Abstract-method style: `PitchRepresentation(ABC)` uses `@abstractmethod` **and** `raise NotImplementedError` (redundant); `IntervalRepresentation` has `@abstractmethod` but **no `ABC` base** so it isn't enforced; `Tone.from_string`/`Interval.from_string` raise `NotImplementedError` without `@abstractmethod` (fine if optional — say so); `GraphAdapter` uses both. (`TonalObject` being an ABC mixin rather than a Protocol was a deliberate decision in `_plans/completed/transform-tones.md` — keep.) | `ABC` + `@abstractmethod` with a docstring body only, everywhere; document `from_string` as optional. | L |
| 3.9 | `TemporalRatio._nominal`/`_contextual` "kept for backwards compatibility" (`duration.py:338-345`) — AGENTS.md forbids compat shims. | Delete. | L |
| 3.10 | Two interning mechanisms: `TonalVector._cache` + `hasattr(self, '_initialized')` sentinel (`tonal_vector.py:236-308`) and the module-global `qualities` registry populated by `IntervalQuality.__new__` (`interval_quality.py:30-103`). Code relies on identity: `ModePattern.__post_init__` (`is not TonalVector((0,0))`), `NoKey.transform(...) is NoKey`, `fs.tones.root is Fx` in doctests. | Either keep interning but make it explicit (`functools.cache` on a classmethod, no `_initialized`), or drop it and use `==` at the three identity sites. `IntervalQuality` → frozen dataclass + a plain dict `QUALITIES`. | M |
| 3.11 | `ClockDuration.temporal_system` returns the **string** `"RealTime"`; `TemporalUnit.temporal_system` returns `self.base.temporal_system` (a `TemporalSystem`); `Duration` doesn't declare it at all (commented out at `duration.py:55-59`). | Either restore the abstract property and give `MeteredDuration`/`ClockDuration` real `TemporalSystem` instances, or delete all three. | L |
| 3.12 | Layering: `objects/context/context_event.py:8-9` imports concrete WSMN types (`Key`, `KeySignature`, `TonalVector`) into the system-agnostic `objects` layer, while siblings `note.py`/`chord_event.py` depend only on abstract `Tone`/`ToneCollection` (goals.md §1, AGENTS.md "Keep the domain model independent"). | Either move `KeySignatureEvent` under `systems/wsmn/` or give `values/tone` an abstract `Key`/`KeySignature` that WSMN implements. | M (design decision) |
| 3.13 | `OmkObject` family: dataclass `eq=True` gives **structural** equality on `(_id, _meta, duration, tones…)` and `__hash__ = None`, so entities are unhashable and `==` compares contents. `graph.py:231` compares syllables with `==`, `graph.py:170` with `is`; the adapter indexes by `str(node._id)` to work around it. AGENTS.md: "do not accidentally use structural equality where entity identity matters." | `@dataclass(eq=False)` on `OmkObject` (identity eq/hash), or `__eq__`/`__hash__` on `_id`. | L–M (any test comparing two freshly built events by `==` will change) |

---

## Tier 4 — Control flow, idioms, duplication

| # | Inconsistency | Proposed fix | Blast |
|---|---|---|---|
| 4.1 | `transform(operation, …)` validation written five ways: `ToneCollection` (checks every result is a `Tone`), `NoteEvent` (same, skips `SilentTone`), `KeySignature`/`Key` (checks `TonalVector`), `Chord` (checks **root only**). Error messages differ. | One private helper per tone type (`_apply_tone_operation(tone, operation, *a, **kw)`) or at least identical checks/messages; `Chord.transform` should validate every tone. | L |
| 4.2 | `OmkGraph.add_line` and `add_lyric_sequence` are the same loop; `insert_line_from_list` re-implements `add_line`; `define_span` and `add_spanner` are the same operation. | `add_lyric_sequence` → `self.add_line(lyric_sequence)`; `insert_line_from_list` → `add_line` + two `add_next`; keep one of `define_span`/`add_spanner`. | L |
| 4.3 | `Chord.inversion/arpegiate` call `ChordType._resolve_inversion(self, …)` / `ChordType._rotate_to_bass(self)` — unbound methods of a sibling class invoked on a foreign instance. | Module-level private functions, or a `_ChordBase(ToneCollection)` both inherit. | L |
| 4.4 | Duplicated tables/logic: `sharp_order = [3,0,4,1,5,2,6]` in `KeySignature.from_alts` and `.fifths`; octave-break correction in `interval_quality._get_quality(tuple)` and `_PitchRepresentation._modifier_value`; `tonal_int` and `_tonal_unmodulo` are near-duplicates with thresholds 3 vs 6; `TemporalUnit.scale` and `TimeSignature.scale` both implement "push leftover into base". | Hoist `SHARP_ORDER` to `constants`; one `alteration(d, c)` helper; document or unify the 3/6 thresholds. | L |
| 4.5 | Error signalling: `KeySignature.fifths` raises **`AttributeError`** as a domain error (pre-built as `error = …` and raised thrice); `TonalVector.o` raises `AttributeError` from a bare except; `RustworkxAdapter.get_edge` raises **`rx.NoEdgeBetweenNodes`** (backend exception through the adapter — AGENTS.md) while `add_edge` raises `ValueError`; `LyricSyllable` validation raises `LyricConsistencyError` ×4 and bare `ValueError` ×1 **in the same method**; `TemporalUnit.__init__` raises `ValueError` for a bad count but `TemporalUnit.scale` raises `ScalingError` for a bad scalar; `LyricConsistencyError(ValueError)` in `objects/lyrics/errors.py`, `TemporalError(Exception)` hierarchy in `values/time/errors.py`, `OmkWarning` in `utils/omk_warning.py`. | `fifths` → `ValueError` (or return `None`); adapter raises a `GraphError`/`KeyError`; one `openmusickit/errors.py` with `OmkError` base + `OmkWarning`, or a consistent per-package `errors.py`; one exception type per validation site. | L–M |
| 4.5a | "Does this vector have an octave?" is asked five ways: `len(self) == 3` (`tonal_vector.py:783`), `_has_octave` property (`:350`), `try: x[2] except:` (`tonal_arithmetic.py:525`), `try: self._v.o except AttributeError` (`tonal_vector.py:1104`), `if m['octave'] is None` (`:113`). `% 7` literal (`key.py:89`, `tonal_vector.py:391`) vs `% D_LEN` elsewhere. | One public `has_octave` property; `D_LEN` everywhere. | L |
| 4.6 | String building: `"".join([a, b])` (30+ sites in `tonal_vector.py`), `"{}".format(...)` (`__repr__`/`__str__`), `self.quality.__str__()` vs f-strings elsewhere. | f-strings. | L |
| 4.7 | Truthiness on objects: `spanner or Spanner()`, `bass or self.root`, `tr or None`, `if self._name:`, `self._key_signature or (… ) or None`; `x[0] in range(D_LEN)` vs `0 <= x < D_LEN`; `[spec,]`. | `is None` checks; range comparison. | L |
| 4.8 | Enum dispatch: `if/elif/else: raise ValueError("Invalid direction")` for a `StrEnum` param (`transpose`, `nudge`) — the `else` is unreachable for a typed caller. | Drop the `else` or use `match`. Consistent either way. | L |
| 4.9 | Dead code / commented-out code / non-comment strings: `duration.py:55-59`, `tonal_vector.py:290-303` (a string literal used as a comment inside `__init__`), `tonal_arithmetic.py:10-11,49,93,414-417` (references a `@tonal_args` decorator and `tonal_greater_of` that don't exist), `symbols.py:655` (`"""Modes and Keys"""` as a section header), `values/__init__.py:8-11` (string after `__all__`), `graph_adapter.py:202-215` (trailing blank lines), the same `# NOTE: subgraph/… removed pending a redesign` duplicated in `graph_adapter.py:202` and `rx_adapter.py:326`, `graph.py:47,212` question-comments. Narrating comments beside single-letter fields in `constants.py:67-74,131-135` (would vanish with 2.7). | Delete. | L |
| 4.10 | Stale docstrings: `Tone` (mentions `harmony`, `structure`, `time` sub-packages, `PercussionTone`, `Gesture`, `RhythmicSystem`), `NoteEvent` ("A MultiNote is…", `UnpitchedTone`), `objects/__init__` (`Note`, `TonalVector(0,1,0)`, `TemporalDuration(1,4)`), `values/tone/__init__` ("`tones` module … `TonalVector`"), `ChordType.__call__` (`openmusickit.values.symbols`), `Chord` (`maj(E)`), `Spanner` (`OmkEdges … STARTS_AT`), `MeteredDuration` (`Duration(n=1, …)`), `TonalVector.distance` (truncated). | Rewrite to match code. | L |
| 4.11 | Middle-C convention: `from_string(mid_c=4)` default vs `pitch.unicode`/`ascii` rendering middle C as `0` (with `unicode_C4` for 4). Round-tripping requires `mid_c=0` (tests document this). | One default (OMK's is C0 everywhere else) — `from_string(mid_c=0)`, and expose `unicode_at(mid_c)` symmetric with it. | M (doctests `Bb3` etc., roundtrip tests) |
| 4.12 | Section-comment styles: `# ---- x ----`, `# ==== X ====`, `### Util ###`, `## Pitches ##`, `# Basic Add, Connect, Remove`, `###########`. | One style (`# --- x ---` as in `temporal/symbols.py`). | L |
| 4.14 | `SequentialObject.alter_duration(operation, operand)` (one positional operand, `Any`-typed) vs `transform_tones(operation, *args, **kwargs)` — the two in-place "apply a callable to my content" methods on the same base class have different shapes and verbs. (Renaming was explicitly deferred in `transform-tones.md`; flagged for when rhythmic transforms land.) | `transform_duration(operation, *args, **kwargs)` mirroring `transform_tones`. | L |
| 4.13 | Multi-value returns: `real_note_duration -> tuple[int, int]`, `get_edges -> (forward, backward)`, `_resolve_inversion -> (bass, name)` vs `Fraction` elsewhere. `real_n`/`real_d`/`real_note_duration`/`nominal_length`/`rational_length`/`scalar_length` — six names for two ideas. | `nominal_length` (Fraction) and `rational_length` only; drop `real_*`, `scalar_length`. | L |

---

## Execution — this session: Tier 0 only

Implement 0.1–0.7, 0.10, 0.12–0.15 (0.8, 0.9, 0.11 are deferred into `_plans/revisit.md`, created in 0.15). Order: 0.15 first (so deferred notes land immediately), then 0.10 (dependency/import cleanup, so later diffs are clean), then the rest in number order. One commit per item; `uv run pytest` (2358 passing at baseline) must stay green after each. Follow the `_plans/` convention: copy this plan into `_plans/` at implementation start and move it to `_plans/completed/` at the end, as the previous plans did.

Tiers 1–4: separate dialog session, then a separate plan.

## Verification

- `uv run pytest` after every item; doctest output strings updated where behaviour deliberately changed (0.6 int equality, 0.12 chord equality).
- Probe script, read-only, after 0.1–0.4:
  - `ContextEvent().duration` is a `ZeroDuration` instance;
  - `LyricSyllable(s="hel", word=None)` sets `word == "hel"`; `LyricSyllable(s="x", word="abc")` raises `LyricConsistencyError`;
  - build a three-node graph with a lyric attached, call `unlink_lyric_from_object` and `unlink_lyric_sequence`, confirm the LYRIC edges are gone;
  - adding a second NEXT edge from one node raises `ValueError`.
- `uv sync` succeeds after 0.10 and `uv run pytest` still passes without scipy/pydantic installed.
