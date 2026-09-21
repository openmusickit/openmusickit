# Testing audit and test-development plan

Status: **approved 2026-09-21; Step 1 done 2026-09-21.** Steps 2-12 unexecuted; update this line as each lands.

Written 2026-09-21 for two readers: the developer (to approve) and the agents who
will execute it in later sessions without this conversation's context.
Every claim marked *(verified)* was reproduced by running code in this audit;
everything else comes from reading the source and tests.

This file is the copy in the repo; keep the Status line above current so executing
agents know where to pick up.

## Context

The suite is 2,468 collected items and passes in ~1.5 s. Line coverage is 94%
(91% counting only `tests/`, without doctests). Those numbers overstate the
state of things. Most of the collected items are one parametrized round-trip
file (1,680 of 2,325 test-file items), the doctests cover a lot of lines with
one example each, and several whole areas have no test at all: the graph
adapters, node/edge removal, `IntervalQuality`, `ToneCollection`, duration
negation/subtraction, `TiedDuration`, and every JSON/file method (which are
`NotImplementedError` stubs).

The developer's three testing principles, restated so the plan can be checked
against them:

1. **Docstring examples.** Most user-facing methods and functions carry at
   least one short, realistic `>>>` example. (Doctests run under
   `--doctest-modules` already, so examples are tests.)
2. **Exhaustive algebra on finite domains.** Anything that is OMK-implemented
   abstract algebra (tones, intervals, durations, tempos, ratios, keys,
   chords, time signatures) is checked for its laws against *every* musically
   valid value in the domain, using the `tests/conftest.py` symbol fixtures.
3. **Do / inspect / undo on the graph.** Graph operations are potentially
   infinite, so test them algebraically: perform the operation and inspect the
   graph, then reverse it and confirm the graph is back where it was.

Hypothesis is worth adding as a dev dependency for the graph layer, the
infinite-domain duration functions, and parser robustness. A separate fuzzing
library is not (reasons in Part 4).

## Numbers at a glance

| Measure | Value |
|---|---|
| Collected items | 2,468 (2,325 in `tests/`, 143 doctests) |
| Line coverage, all | 94% |
| Line coverage, `tests/` only | 91% |
| Public callables in `values/` + `systems/wsmn/` | 234 |
| ...with a `>>>` example | 83 (35%): `values/` 8 of 99, `systems/wsmn/` 75 of 135 |
| `OmkGraph` public methods with a `>>>` example | 11 of 37 |
| Adapter (`graph_adapter.py`, `rx_adapter.py`) tests or doctests | 0 |
| `conftest.py` fixtures never used by any test | 5 of 9 (`mode_pattern_symbols`, `key_symbols`, `duration_symbols`, `tuplet_ratio_symbols`, `time_signature_symbols`) |
| `tuplet_ratio_symbols` fixture contents | empty: `temporal/symbols.py` has no `TemporalRatio` constants, only factory functions *(verified)* |

## Part 1: What is tested today, how, and how well

### 1a. Tonal arithmetic tuples: exhaustive, algebraic, the model to copy

`tests/systems/wsmn/tonal/test_tonal_arithmetic.py` (8 tests) runs every law
over every pair of the 35 pitch classes and the 175 octave-qualified tuples
from `tonal_tuples` / `tonal_oct_tuples`: `(x + y) - y == x`,
`invert(invert(x)) == x`, `x + (-x) == 0`. This is exactly principle 2 and
it is the best file in the suite.

```python
def test_tonal_sum_diff(tonal_tuples, tonal_oct_tuples):
    """Addition and subtraction are opposite operations,
    therefore (x + y) - y should equal x."""
    for x in tonal_tuples:
        for y in tonal_tuples:
            assert x == ta.tonal_diff(ta.tonal_sum(x, y), y)
```

Weaknesses: three tests assert only a bound (`< 7` half-steps) rather than a
value (`test_tonal_abs_diff`, `test_abs_int_diff`, `test_nearest_instance`);
a function returning a constant passes `test_abs_int_diff`.
`tonal_nearest_instance` is never checked to return an instance *of y*, which
is its whole purpose (the law holds: *verified* over all 35x35).
Six public functions in the module have no test outside their doctest:
`tonal_abs`, `tonal_higher_of`, `tonal_lower_of`, `tonal_larger_of`,
`tonal_smaller_of`, `abs_interval`.

### 1b. TonalVector string forms: exhaustive round trips, sampled hand-written dialects

`test_string_roundtrip.py` checks `from_string(f(v)) == v` for all 210 vectors
and 8 string transforms (1,680 cases), and documents the one accepted
asymmetry (Lilypond has no abstract pitch). This is principle 2 applied to
parsing and it is solid.

`test_from_string.py` (150) and `test_from_ly.py` (56) are parametrized tables
of hand-picked spellings ("C double sharp", "aug 4", "dbl dim5", solfege,
ordinals, whitespace). They sample the dialects rather than enumerate them.
Invalid input is 6 + 5 strings. Lilypond relative-octave resolution from a
non-C previous note is 4 examples; the round-trip file only ever uses C4 as
`prev_note`.

### 1c. Keys: exhaustive derivation, sampled transposition

`test_key.py` (246) is exhaustive over 35 tonics x 9 diatonic modes for
`Key.of` (tonic, tones, signature, fifths, name), over `range(-21, 22)` for
`from_alts`/`fifths`/`repr`, and uses an *independent* oracle
(`LETTER_FIFTHS + 7 * alteration + MODE_FIFTHS_OFFSET`) rather than the
implementation's own formula. Good.

Not exhaustive: `Key.transform` has two assertions (on `NoKey` and an empty
signature); `Key.from_signature` appears once; `KeySignature.transpose` is
doctest-only. The obvious missing law,
`Key.of(t, m).transform(transpose, i) == Key.of(t + i, m)` and back, holds
*(verified over 9 modes x 35 tonics x 7 intervals)* until the result needs
more than triple sharps/flats, where `KeySignature` raises `ValueError`. That
boundary is part of the law and should be asserted, not skipped.

### 1d. Chords: exhaustive symbol well-formedness, tautological realization oracle

`test_chords.py` (22) checks all 78 `ChordType` symbols contain a root and
have a `ChordQuality`, and realizes each at the 7 natural roots. The
realization assertion recomputes its expectation with the operation under
test (`[t + root for t in chord_type]`), so it proves delegation, not
spelling. The only literal spelling assertion in the file is
`dom7(C) == [C, E, G, Bb]`.

The docstring restriction to natural roots ("a pre-existing issue in
interval_quality's lookup table") is stale: all 35 roots x 78 chord types
realize, and every resulting tone renders in unicode, ascii, verbose, ly,
and interval forms *(verified)*. Inversions, slash chords, `arpeggiate`, and
`__str__` are tested on one major triad.

### 1e. Durations and time signatures: large, example-based, no parametrize

`test_metrical_duration.py` (75 tests, 1,409 lines) is the temporal system's
whole budget: `MetricalDuration`, `TiedDuration`, `TemporalUnit`,
`CompoundTemporalUnit`, `TemporalRatio`, `TimeSignature`, `ClockDuration`,
`Tempo`, and the symbols. Style is named scenarios with many assertions each
and module-level lists (`standard_duration_denominators`,
`common_time_signature`) swept by nested loops. There is no
`@pytest.mark.parametrize` and no use of `duration_symbols` or
`time_signature_symbols`.

What is exhaustive: creation and dots over 7 denominators; `scale(2)` /
`scale(1/2)` with 0-4 dots; commutativity and associativity of `+` over 7x7
denominators (asserted on `rational_length`, so it mostly tests `Fraction`);
bar filling over 11 signatures x 7 denominators.

What is sampled: tuplets, nested tuplets, mixed-base ratios, ties,
`from_length` synthesis, clock time, tempo, presentation scaling.

What is absent: `__neg__` and `__sub__` on every duration class (one `-quarter`
in the graph tests is the only negation in the suite); `TemporalRatio`
equality and hashing; `TiedDuration` as a type (no docstring examples either);
`TimeSignature.__repr__` is checked only for balanced parentheses.

The laws hold *(verified over all 68 duration symbols)*: `-(-d) == d`,
`d - d == ZeroDuration()`, `d + zero == d`, `a + b == b + a`,
`(a + b) - b == a` over all pairs, `scale(k).scale(1/k) == d`, and
`from_length(d.rational_length) == d`. None of this is asserted anywhere.

### 1f. Objects and lyrics: example-based, decent for their size

`test_note_event.py` (12), `test_marking.py` (6), `test_lyrics.py` (43).
The lyrics file is the best of these: it covers `Word` validation with a
parametrized rejection table, the zip semantics as a decision table of five
scenarios (binding spans, ties vs hairpins, rests and context events,
abutting spans, running out of syllables), and one zip-then-unlink test.

Weak spots: `test_marking.py:28-33` is four constructor calls with no
assertion; `ChordEvent` and `ContextEvent`/`ModalContextEvent` are only ever
constructed as props for other tests; `zip -> unlink` never re-asserts the
full pre-zip state and `unlink_lyric_from_object` is untested;
`Stint.transposition` is stored but never applied.

### 1g. Graph: scenario tests, invariants as error paths, no inverses

`test_compound_lines.py` (18) builds named scenarios (`piano`, `sketch`) with
two helpers (`notes()`, `names()`) and asserts walk order, relative onsets,
alignment warnings, stint views, and one large `materialize` test.
The invariants that are tested are tested well as error paths (one NEXT in,
one NEXT out; a head is branched once and must be a head).

There is no do/undo pair anywhere in the graph tests: transposition is
applied but never reversed, nodes and edges are never removed, branches and
pins are never undone. Untested outright: `remove_node`, `remove_edge`,
`insert_event`, `insert_line_from_list`, `branches_from`, `edges()`,
`unlink_lyric_from_object`, `add_annotation`, `TimedEdge.nudge`, the
six serialization stubs, and both adapter modules.

## Part 2: Tested, but not well enough, and what to add

Each item names the gap, the law or table to add, and where it goes.

**2.1 Tonal arithmetic value assertions** (`test_tonal_arithmetic.py`).
Replace bound-only asserts with laws: `tonal_nearest_instance(x, y)` is an
instance of `y` (same pitch class) and within a tritone; `abs_int_diff`
equals `abs(int(a) - int(b))` reduced mod 12 to the smaller side; add the six
untested functions with their laws (`higher_of`/`lower_of` are a total order
with `higher_of(x, y) == lower_of(y, x)` complement; `abs_interval` is
idempotent; `tonal_abs(x) == tonal_abs(invert(x))`).

**2.2 TonalVector-level algebra** (new `tests/systems/wsmn/tonal/test_tonal_vector_algebra.py`).
The tuple functions are exhaustive but the class that users touch is not.
Over `ALL_VECTORS` x `ABSTRACT_VECTORS`: `(a + i) - i == a`;
`a.transpose(i).transpose(i, DOWN) == a`; `a.transpose(i) - i == a`;
`inversion` is an involution; `abs(a - b) == abs(b - a)`; `<`/`>` are
antisymmetric and total up to `int()` equality *(all verified)*;
`eval(repr(v)) == v`; `hash` agrees with `==`; pitch/interval alias symbols
are the same object (`C is P1`, `Bb is m7`, all 35 pairs). Note the inverse
of an upward transposition is `transpose(i, DOWN)` or `- i`, not
`transpose(i.inversion())`, which adds an octave on qualified vectors
*(verified)*; the test should pin that distinction.

**2.3 Key transposition law** (`test_key.py`).
For every mode symbol, every tonic in `chromatic_tonics`, every interval in
the 35 abstract vectors: `Key.of(t, m).transform(transpose, i) ==
Key.of(t + i, m)`, and transposing back restores the key, *or* both sides
raise `ValueError` because the signature would exceed triple alterations.
Also `KeySignature.transpose` by fifths: `from_alts(n).transpose(P5).fifths == n + 1`
for the representable range. Use the `mode_pattern_symbols` fixture (currently dead).

**2.4 Chord realization with a real oracle** (`test_chords.py`).
Lift the natural-root restriction (stale, see 1d) to all 35 roots. Replace
the tautological oracle with a literal table of expected spellings for at
least one root per chord family (triads, sixths, sevenths, added-tone,
ninths, elevenths, thirteenths, sus, altered dominants, diminished), and an
independent check that the semitone content of `chord_type(root)` equals the
semitone content of `chord_type` shifted by `int(root)` mod 12. Inversion
laws over every chord type: `ct.inversion(k).bass == ct[k]`;
`ct.inversion(0) == ct`; `ct / ct[k] == ct.inversion(k)`; `arpeggiate`
starts at the bass and is a rotation of the tones.

**2.5 Duration algebra over the symbol domain** (new `tests/systems/wsmn/temporal/test_duration_algebra.py`).
Use `duration_symbols` (dead today), deduplicated by object. Laws listed in
1e, plus: `__lt__` agrees with `rational_length`; `hash` agrees with `==`
across spellings (`dotted_quarter == quarter + eighth`); `sum([...])` of any
symbol list has the summed length and `from_length` of that length equals
the sum; `TemporalRatio(6:4) == TemporalRatio(3:2)` and hashes equal;
scaling by a non-power-of-two either preserves length or raises
`ScalingError`, never anything else. Time signatures over
`time_signature_symbols` (dead today): equality by total length
(`four_four == two_two`), `scale(k).rational_length == k * length`,
`remainder` and `first_out_of_bounds` against every duration symbol.

**2.6 String parsing coverage tables** (`test_from_string.py`, `test_from_ly.py`).
Generate the spelling tables rather than hand-picking: every letter x every
`ACCIDENTALS` entry x each of the three spellings (`unicode`, `ascii`,
`name`) x optional octave, and every solfege syllable in both styles.
For `from_ly` relative octave: every qualified vector as `prev_note` x every
Lilypond name (210 x 35), asserting the within-a-fourth rule with an
independent formula. Add a rejection table built from the grammar's edges:
every quality with every degree it cannot take (`P3`, `M5`, `m4`), numbers
outside `1..13`, mismatched ordinals, multipliers on non-aug/dim.

**2.7 Lyrics zip/unlink as an inverse** (`test_lyrics.py`).
`zip_lyrics_to_objects` then `unlink_lyric_sequence(first)` restores the
LYRIC edge set exactly (snapshot the edges before, compare after), the NEXT
chain among syllables survives, and zipping again reproduces the same edges.
Add `unlink_lyric_from_object` as the inverse of `connect_lyric_to_object`.

**2.8 Marking tests** (`test_marking.py`). Replace the four assertion-free
constructor calls with a parametrized table over every `Mark` symbol:
`Marking(mark=m)` succeeds iff `m.attachment_mode in {SINGLE, EITHER}`,
`MarkSpanner(mark=m)` succeeds iff `m.attachment_mode in {SPAN, EITHER}`,
everything else raises `ValueError`. Also table invariants on the 201 marks:
unique names, unique aliases across the table, `binds` only on span-capable
marks.

## Part 3: Not tested at all, and what to build

**3.1 Graph adapters** (`graph_adapter.py`, `rx_adapter.py`): zero tests, zero
doctests. Eleven of the 29 ABC methods are never called by anything
(`filter_*`, `has_*`, `num_*`, `nodes`, `neighbors`, `degree*`), and three
private helpers in `rx_adapter.py` are dead code. Build: a contract test
module `tests/graph/test_adapter_contract.py` parametrized over adapter
implementations, asserting the contract in `graph_adapter.py` (idempotent
`add_node`; duplicate same-type edge rejected with `GraphError`; NEXT
one-in/one-out; `remove_node` removes incident edges and decrements
`num_edges` accordingly; `has_edge` with and without type; `edges(predicate)`;
`successors`/`predecessors` with `node_type` and `predicate` filters; backend
exceptions never escape). The same module is where a tiny dict-based
reference adapter (Step 6 below) gets exercised, which makes the contract
tests also a differential test for `RustworkxAdapter`.

**3.2 Graph do/undo** (new `tests/graph/test_graph_inverses.py`): principle 3.
For each mutator, do it, inspect, undo it, compare a canonical snapshot:

| Do | Inspect | Undo |
|---|---|---|
| `add_node(x)` | `get_node(x.id) is x` | `remove_node(x)` |
| `add_next(a, b)` | `get_next(a) is b`, `get_previous(b) is a` | `remove_edge(get_edge(a, b, NEXT))` |
| `add_line([...])` | `walk_line(head)` is the list | remove every NEXT edge |
| `insert_event(e, a, b)` | `walk_line` has `e` between `a` and `b` | remove both edges, `add_next(a, b)`, `remove_node(e)` |
| `insert_line_from_list` | same | same |
| `add_branch(p, h)` | `branches_from(p) == [h]`, `relative_onset(p, h)` | `remove_edge(get_edge(p, h, BRANCHES))` |
| `add_simultaneous(a, b)` | `relative_onset(a, b)` known | remove the SIMULTANEOUS edge, `relative_onset` raises `GraphError` |
| `transform_tones(head, None, transpose, i)` | `names(...)` shifted | `transform_tones(..., transpose, i, DOWN)`, names restored |
| `add_stint(part, stint, a, b)` | `stints(part)`, `walk_stint` | remove STARTS_AT/ENDS_AT/PERFORMS edges and the stint node |
| `add_spanner(s, a, b)`, `add_articulation`, `add_annotation` | edges present | `remove_edge` each, `remove_node(s)` |
| `TimedEdge.nudge(FORWARD, d)` | displacement is `d` | `nudge(BACKWARD, d)` gives `ZeroDuration()`, and `relative_onset` agrees with the original |

The snapshot helper (Step 5) is what makes "back where we were" checkable.
Where no inverse method exists (`remove_branch`, `remove_stint`,
`remove_spanner`, `unpin`), the test spells out the primitive undo; the
report does not propose adding API.

**3.3 Graph laws that hold for any graph** (Hypothesis, Step 8):
`relative_onset(a, a) == ZeroDuration()`; `relative_onset(a, b) ==
-relative_onset(b, a)` on tree-shaped timing; `relative_onset` of
consecutive events equals the first event's duration;
`walk_span` is a superset of `walk_line` and never crosses a pin;
`check_alignment()` is empty on a graph with no redundant pins; every
composite operation equals its primitive expansion (`add_line` ==
repeated `add_next`; `insert_event` == two edges); `materialize` yields
equal content with disjoint ids and leaves the original snapshot unchanged.

**3.4 Value-layer classes with no test module**: `ToneCollection`
(`combinations`, `all_combinations`, `transform` law
`transform(transpose, i).transform(transpose, i, DOWN) == self`, containment,
order preservation, equality ignores `name_template`); `ModalContext`
(that `Key` satisfies the ABC and `NoKey.transform` is identity);
`IntervalQuality` (19-entry table: `augment`/`diminish` are inverses,
`q + n - n == q`, `abbr` parses back through `from_string`, `chromatic_modifier
== floor(rel_number)`, past the table raises, currently a bare `KeyError`
*(verified)*); `ClockDuration` full ring (`+ - neg * /`, `from_*`/accessor
pairs, `timedelta` round trip, `str` format); `TiedDuration` (iteration,
length, `scale`, `+` merge rules, `__neg__`); `Word` string round trip laws
(`from_string(str(w))` is lossy by design, pin that; stress marks parse and
render); `errors` hierarchy (`LyricConsistencyError` is a `ValueError`,
every `OmkError` subclass is catchable as `OmkError`).

**3.5 Serialization**: six `NotImplementedError` stubs. Nothing to test yet;
when implemented, the graph snapshot helper becomes the round-trip oracle
(`from_json(export_to_json(g))` snapshot-equal to `g`).

**3.6 Docstring examples**: 151 public callables in `values/` and
`systems/wsmn/` have none, and `values/` sits at 8%. Worst modules:
`values/time/duration.py` (41 callables, 1 example), `clock_time.py` (22, 1),
`metrical_duration.py` (22, 2; `TiedDuration` has none anywhere),
`word.py` (9, 1), `interval_quality.py` (8, 1), `time_signature.py` (3, 0),
`chords.py` (`__call__`, `__truediv__` have pseudo-code blocks that doctest
never runs). `OmkGraph`: 26 of 37 methods lack one, including every query
(`get_node`, `get_next`, `edges_between`, `branches_from`, `stints`,
`walk_line`, `walk_stint`) and every remove/insert. Adapters: none, by
design acceptable (not user-facing), but the ABC docstrings should state the
contract precisely enough for 3.1.

## Part 4: Hypothesis and fuzzing

**Recommendation: add `hypothesis` to the `dev` dependency group. Do not add a
fuzzing library.**

Where Hypothesis earns its place:

- **Graph layer.** The domain is infinite, the preconditions are real
  (a node must be on the graph before `add_next`; a branch head must be an
  unbranched line head), and the composite-equals-primitives and do/undo
  laws are exactly what `RuleBasedStateMachine` expresses. A state machine
  with bundles for "nodes on graph", "line tails", "unbranched heads" and a
  parallel dict model will find ordering bugs no hand-written scenario will.
  It also gives the adapter contract tests a second implementation to
  differ against for free.
- **Infinite duration domains.** `MetricalDuration.from_length(x)` for any
  positive `Fraction`, `scale` by any positive `Fraction`, `TiedDuration`
  merging, `TimeSignature.remainder` over random sequences. The law
  `from_length(x).rational_length == x` is the module's central promise and
  is currently four examples. `st.fractions(min_value=0, max_denominator=64)`
  covers it; larger denominators are a deliberate slow-profile run.
- **Parser robustness.** `TonalVector.from_string`, `from_ly`,
  `Word.from_string`, `parse_lyrics`: the property is "any `str` either
  parses or raises `ValueError` (or its subclass `LyricConsistencyError`),
  never `IndexError`/`KeyError`/`AttributeError`/`TypeError`", plus
  "whatever parses re-renders and parses to the same value". `st.text()`,
  `st.from_regex(grammar)`, and case/whitespace mutation of known-valid
  spellings give this. This is what a fuzzer would do, without a C
  harness, a corpus directory, or a second runner. Hypothesis's database
  keeps failing inputs across runs, which is the part of fuzzing that
  matters here.

Where Hypothesis is the wrong tool: the tonal tuple arithmetic, keys, chords,
symbol tables, and every other finite domain. There, exhaustive loops over
fixtures are stronger (complete, deterministic, and faster) and match the
existing style. Do not rewrite those with Hypothesis.

Why not a fuzzer (atheris, pythonfuzz): the parsers are pure Python regex
dispatch with no memory-safety surface; the failure mode is a wrong exception
type or a wrong value, which Hypothesis reports with a minimal example and a
replayable seed. A coverage-guided fuzzer would add a dependency, a
compile-time instrumentation step, and a corpus to maintain for no additional
class of bug.

Hypothesis settings to adopt (in `tests/conftest.py`): a `default` profile
(`max_examples=100`, `deadline=None` because graph tests allocate) and a
`thorough` profile (`max_examples=2000`) selected with
`--hypothesis-profile=thorough`. Mark heavy exhaustive tests `@pytest.mark.slow`
and register the marker in `pyproject.toml`; the default run stays under a
few seconds.

## Part 5: Defects and stale assumptions the audit surfaced

These are findings, not fixes. Each gets a test in the plan; whether the
test is `xfail(strict=True)` pointing at `_plans/revisit.md` or a same-session
fix is the developer's call (see Open questions).

1. **A NEXT cycle is accepted and `walk_line` never terminates.** *(verified)*
   `add_line([a, b, c]); add_next(c, a)` passes both guards (c has no NEXT
   out, a has no NEXT in). `walk_span` can loop the same way through mutual
   branches. Any Hypothesis graph test must exclude cycles in the generator
   or cap steps, or it hangs instead of failing.
   - NOTE FROM DEV: NEXT cycles are valid (Gamelan and other cyclic music)
     so walkers will need way to stop when appropriate.
     We should add this to revisit.md
2. **`KeyError` leaks through the adapter for a missing node.** *(verified)*
   `get_node` docstring says it returns `None`; `remove_node` docstring says
   "raises an exception"; both raise a raw `KeyError` from `_rxid`, against
   the `GraphError` contract in `errors.py` that backend exceptions never
   cross the adapter boundary.
3. **`OmkGraph.remove_edge` is annotated `-> OmkEdge` but returns `None`.**
   *(verified)* A do/undo test cannot re-add what it removed from the return
   value; it must keep its own reference.
4. **`tuplet_ratio_symbols` fixture is empty.** *(verified)* Any test using it
   runs zero cases silently.
5. **`test_chords.py` natural-root restriction is stale.** *(verified)* All
   35 x 78 realizations and renderings succeed.
6. **`IntervalQuality.augment` past the table raises a bare `KeyError`.**
   *(verified)* `tonal_vector` catches it and re-raises `ValueError`; the
   class itself does not.
7. **`Chord.inversion(tone_not_in_chord)` does not raise** *(verified)*;
   the bad bass surfaces later as a `ValueError` from `list.index` in
   `arpeggiate`.
8. **`_symbols_of` uses exact type**, so `GraceDuration` symbols are invisible
   to `duration_symbols`, and alias names double-count objects (68 names for
   39 durations, 70 for 35 vectors). Fine for iteration, wrong for counts.

## Part 6: Development plan

Each step is self-contained, lists its files, and ends with a check. Steps
1 to 5 are infrastructure and have no dependency on Hypothesis; steps 6 to 9
need it. Steps 10 to 12 are the docstring pass and can run in parallel with
anything. Run everything with `uv run pytest`; never bare `pytest`.
Follow AGENTS.md: no new features, no API changes, no fixes to production
code beyond obvious typos unless the developer has said which of the Part 5
items to fix. Commit messages are `Claude: <what changed>` with no trailer.

### Step 1. Shared domain module and fixture repair

Files: new `tests/domains.py`; edit `tests/conftest.py`;
edit `tests/systems/wsmn/tonal/test_string_roundtrip.py`.

- Move the tuple builders out of `conftest.py` and the private copies in
  `test_string_roundtrip.py` into `tests/domains.py` as plain module-level
  lists, so both fixtures and `@pytest.mark.parametrize` can import them:
  `TONAL_TUPLES` (35), `TONAL_OCT_TUPLES` (175), `ABSTRACT_VECTORS`,
  `QUALIFIED_VECTORS`, `ALL_VECTORS`.
- In `conftest.py`, keep the existing fixture names (tests depend on them)
  but source them from `domains.py`. Add a `distinct(symbols)` helper that
  dedupes by identity, and new fixtures: `grace_duration_symbols`
  (`GraceDuration`), `mark_symbols` (all `Mark` objects in
  `scoring/symbols.py`), `interval_qualities` (`QUALITIES.values()`),
  `tuplet_ratio_factories` (the six factory functions).
- Resolve `tuplet_ratio_symbols`: point it at
  `{name: fn(quarter) for the six factories}` so it is non-empty, and note
  in its docstring why (there are no ratio constants). Do not add constants
  to `temporal/symbols.py` in this step.
- Add a guard test `tests/test_fixtures.py` asserting every symbol fixture
  is non-empty and its distinct count matches a literal, so a future empty
  fixture fails loudly.

Check: `uv run pytest -q` still 2,468 + the guard tests; no test file
defines its own copy of the 35 tuples.

Execution notes (2026-09-21): `distinct()` lives in `tests/domains.py`, not
`conftest.py`, because pytest discourages importing from conftest and tests
need to import it. Making `tests.domains` importable took two config lines
in `pyproject.toml`: `pythonpath = ["."]` under pytest and `"tests"` in
ruff's `known-first-party`. `tuplet_ratio_symbols` is the five named
factories on `quarter` plus `tuplet(7, 6, quarter)`, six ratios.

### Step 2. Tonal algebra at the class level

Files: edit `tests/systems/wsmn/tonal/test_tonal_arithmetic.py`;
new `tests/systems/wsmn/tonal/test_tonal_vector_algebra.py`.

Implement 2.1 and 2.2. House style: a docstring stating the law in musical
terms, nested `for` over the domain lists, `assert ..., (a, b)` context on
the loop body.

```python
def test_transpose_up_then_down_is_identity():
    """Transposing up by an interval and then down by the same interval
    returns the original pitch, with its octave if it had one."""
    for a in ALL_VECTORS:
        for i in ABSTRACT_VECTORS:
            assert a.transpose(i).transpose(i, TonalDirection.DOWN) == a, (a, i)
            assert a.transpose(i) - i == a, (a, i)


def test_inversion_is_not_the_inverse_of_transposition_on_qualified_vectors():
    """Pitch-class inversion of M2 is m7; going up M2 then up m7 lands an
    octave higher, not back home. The octave is the point of a qualified vector."""
    C4, M2 = TonalVector((0, 0, 0)), TonalVector((1, 2))
    assert C4.transpose(M2).transpose(M2.inversion()) == TonalVector((0, 0, 1))
```

Check: new tests pass; the module's six untested functions each appear in at
least one law.

### Step 3. Duration and time-signature algebra over the symbol domain

Files: new `tests/systems/wsmn/temporal/test_duration_algebra.py`;
new `tests/values/time/test_clock_duration.py`;
new `tests/systems/wsmn/temporal/test_tied_duration.py`.

Implement 2.5 and the `ClockDuration`/`TiedDuration` parts of 3.4, using
`duration_symbols` and `time_signature_symbols` through `distinct()`.

```python
def test_a_duration_and_its_negation_cancel(duration_symbols):
    """d + (-d) is the zero duration, and negation is an involution,
    for every note value in the symbol table."""
    for name, d in distinct(duration_symbols).items():
        assert d - d == ZeroDuration(), name
        assert -(-d) == d, name


def test_addition_is_commutative_and_subtraction_undoes_it(duration_symbols):
    for (na, a), (nb, b) in itertools.product(distinct(duration_symbols).items(), repeat=2):
        assert a + b == b + a, (na, nb)
        assert (a + b) - b == a, (na, nb)
```

Check: the laws in 1e all appear; `scale` by `{2, 3, 1/2, 2/3, 3/2}` either
round-trips or raises `ScalingError` only.

### Step 4. Keys, chords, qualities, collections, marks, parsers

Files: edit `test_key.py`, `test_chords.py`, `test_marking.py`,
`test_from_string.py`, `test_from_ly.py`;
new `tests/systems/wsmn/tonal/test_interval_quality.py`;
new `tests/values/tone/test_tone_collection.py`;
new `tests/values/text/test_word.py` (move the Word tests out of
`test_lyrics.py`); new `tests/test_errors.py`.

Implement 2.3, 2.4, 2.6, 2.8, and the `IntervalQuality`, `ToneCollection`,
`ModalContext`, `Word`, `errors` parts of 3.4. For 2.4, delete the stale
docstring and loop over `pitch_symbols`. For the key law, express the domain
boundary as part of the law:

```python
def test_key_transposition_agrees_with_key_of(chromatic_tonics, mode_pattern_symbols):
    """Transposing a key by an interval gives the key on the transposed
    tonic, or both raise because the signature would need more than
    triple sharps or flats. Transposing back restores the key."""
    for mode in mode_pattern_symbols.values():
        for tonic in chromatic_tonics:
            for i in ABSTRACT_VECTORS:
                key = Key.of(tonic, mode)
                try:
                    expected = Key.of(tonic + i, mode)
                except ValueError:
                    with pytest.raises(ValueError):
                        key.transform(TonalVector.transpose, i)
                    continue
                moved = key.transform(TonalVector.transpose, i)
                assert moved == expected, (key.name, i)
                assert moved.transform(TonalVector.transpose, i, TonalDirection.DOWN) == key
```

Check: `mode_pattern_symbols`, `key_symbols`, `mark_symbols`,
`interval_qualities` are all used; `test_chords.py` sweeps 35 roots.

### Step 5. Graph test helpers and do/undo tests

Files: new `tests/graph/helpers.py`; new `tests/graph/test_graph_inverses.py`;
new `tests/graph/test_adapter_contract.py`; edit `tests/objects/test_lyrics.py`.

`helpers.py` holds `notes()`, `names()` (moved from `test_compound_lines.py`,
which imports them), and:

```python
def snapshot(graph: OmkGraph) -> tuple[list, list]:
    """A canonical, comparable picture of a graph: node ids with their
    repr, and edges as (source id, target id, type, repr)."""
    adapter = graph._graph
    nodes = sorted((str(n.id), repr(n)) for n in adapter.nodes())
    edges = sorted(
        (str(s.id), str(t.id), e.type.name, repr(e))
        for e in adapter.edges()
        for s, t in [adapter.get_edge_endpoints(e)]
    )
    return nodes, edges
```

`test_graph_inverses.py` implements the 3.2 table, one test per row:

```python
def test_branch_can_be_undone():
    graph = OmkGraph(GraphMeta())
    parent, child = notes(C, D), notes(A, B)
    graph.add_line(parent); graph.add_line(child)
    before = snapshot(graph)
    graph.add_branch(parent[0], child[0])
    assert graph.branches_from(parent[0]) == [child[0]]
    assert graph.relative_onset(parent[0], child[1]) == quarter
    graph.remove_edge(graph.get_edge(parent[0], child[0], EdgeType.BRANCHES))
    assert graph.branches_from(parent[0]) == []
    assert snapshot(graph) == before
```

`test_adapter_contract.py` implements 3.1, parametrized over a list of
adapter factories that starts with `RustworkxAdapter` (Step 6 adds the
reference adapter to the list). Include a test for Part 5 item 2 (a missing
node raises `GraphError`, or returns `None` for `get_node`) marked
`xfail(strict=True, reason="revisit: KeyError leaks through adapter")`
unless the developer chose to fix it.

Extend `test_lyrics.py` with 2.7 using `snapshot`.

Check: every mutator in 3.2 has a do/inspect/undo test; `remove_node`,
`remove_edge`, `insert_event`, `insert_line_from_list`, `branches_from`,
`edges()`, `add_annotation`, `unlink_lyric_from_object`, `nudge` are
executed by `tests/` (confirm with the coverage command in Verification).

### Step 6. Add Hypothesis and a reference adapter

Files: `pyproject.toml` (dev group), `uv.lock`; `tests/conftest.py`
(profiles, `slow` marker); new `tests/graph/dict_adapter.py`.

- `uv add --group dev hypothesis` (needs the developer's approval; see Open
  questions). Register profiles as in Part 4. Register the `slow` marker in
  `[tool.pytest.ini_options]` and skip it by default with
  `addopts = ["--doctest-modules", "-m", "not slow"]`; document that
  `uv run pytest -m slow` runs the heavy set.
- `dict_adapter.py`: a test-only `DictAdapter(GraphAdapter)` backed by three
  dicts (`nodes`, `edges`, `endpoints` keyed by `str(id)`) plus out/in
  adjacency. It implements all 29 ABC methods (11 are one-liners) and the two
  contract rules (`GraphError` on duplicate same-type edge; NEXT
  one-in/one-out). It lives in `tests/`, not `src/`; it is a test oracle,
  not a backend. Add it to the factory list in `test_adapter_contract.py`.

Check: `uv run pytest` passes with both adapters; `uv run pytest
--hypothesis-profile=thorough -m slow` is runnable.

### Step 7. Hypothesis strategies

Files: new `tests/strategies.py`.

Strategies, each a small function returning a `SearchStrategy`:
`tonal_vectors(qualified: bool | None)` sampled from the domain lists;
`metrical_durations()` sampled from `distinct(duration_symbols)` plus
constructed `MetricalDuration(1, 2**k, dots=0..3)`; `positive_fractions(max_denominator=64)`;
`note_events()` with a tone set and a duration (or `None` at low
probability); `lines(min_size=1, max_size=6)` as lists of note events;
`pitch_spellings()` built from the letter, accidental, and octave tables
with random case and whitespace; `interval_spellings()` likewise;
`lyric_texts()` from words, hyphens, and stress marks.

Check: `uv run python -c "from tests.strategies import *"` imports; each
strategy has a one-line docstring and a `.example()` smoke test in
`tests/test_strategies.py`.

### Step 8. Property tests for durations, parsers, and the graph

Files: new `tests/systems/wsmn/temporal/test_duration_properties.py`;
new `tests/systems/wsmn/tonal/test_parser_properties.py`;
new `tests/objects/test_lyrics_properties.py`;
new `tests/graph/test_graph_properties.py`;
new `tests/graph/test_graph_state_machine.py`.

Durations:

```python
@given(positive_fractions(max_denominator=64))
def test_from_length_is_exact(length):
    """Whatever notation from_length picks, its real length is the input."""
    assert MetricalDuration.from_length(length).rational_length == length
```

Parsers (the fuzz role):

```python
@given(st.text(max_size=12))
def test_from_string_only_ever_raises_value_error(s):
    try:
        v = TonalVector.from_string(s)
    except ValueError:
        return
    assert TonalVector.from_string(v.pitch.unicode) == v
```

Graph laws (3.3) as `@given(lines(), tonal_vectors(qualified=False))` tests,
and a `RuleBasedStateMachine` with bundles `on_graph`, `line_tails`,
`unbranched_heads`, rules `add_node`, `append_next`, `branch`, `pin`,
`remove_node`, `remove_edge`, and invariants: NEXT degree is at most one
each way; every `relative_onset(a, a)` is zero; `walk_line` from any head
terminates within `num_nodes` steps; the `DictAdapter` model and
`RustworkxAdapter` agree on `snapshot`. The generator must never create a
NEXT cycle (only `append_next(tail, fresh_node)`) until Part 5 item 1 is
resolved; add a separate `xfail(strict=True)` test that constructs the
cycle and asserts `walk_line` raises `GraphError`, with a `timeout`.

Check: `uv run pytest` default profile finishes in under ~10 s; the
thorough profile is documented in the test module docstrings.

### Step 9. Coverage as a check, not a target

Files: `pyproject.toml` (dev group gets `pytest-cov`); `AGENTS.md` (one line
under Tooling).

Add `pytest-cov` and document
`uv run pytest --cov=openmusickit --cov-report=term-missing -o addopts=""
tests` as the way to see what only doctests cover. No coverage threshold in
CI; the number is a diagnostic. Record the before/after in the plan's
Status line.

### Step 10. Docstring examples: `values/`

Files: `values/time/duration.py`, `values/time/clock_time.py`,
`values/text/word.py`, `values/tone/tone_collection.py`,
`values/tone/tone.py`, `values/tone/interval.py`, `values/tone/modal_context.py`.

For each public callable without a `>>>` example, add one that a user would
plausibly type, using the symbol modules (`quarter`, `C`, `M3`) rather than
raw constructors where a symbol exists. Rules: one to three lines of input,
one line of output, no setup that is not itself illustrative; abstract
methods get the example on the class docstring showing a concrete subclass;
container dunders (`__iter__`, `__len__`) get one example on the class, not
each. Prose in the touched docstrings moves to semantic line breaks per
AGENTS.md. Priority order within the step: `duration.py` `Duration.__neg__`/
`__sub__`, `ZeroDuration`, `TemporalUnit.scale`, `CompoundTemporalUnit.remainder`/
`first_out_of_bounds`, `TemporalRatio.multiplier`; `clock_time.py` the
arithmetic dunders and `from_*`/accessor pairs; `word.py` `stress_at`,
`primary`, `__str__`.

Check: `uv run pytest src` passes; the callable count with examples in
`values/` goes from 8 to at least 60 of 99 (count with a one-off script
using `inspect.getdoc`, not committed).

### Step 11. Docstring examples: `systems/wsmn`

Files: `metrical_duration.py` (`TiedDuration` class and every method,
`scale`, `__add__` merge rules, `from_fraction`), `time_signature.py`
(`__init__`, `scale`, `_scale_presentation`), `temporal/symbols.py`
(`triplet`..`septuplet`), `interval_quality.py` (`augment`, `diminish`,
`__add__`, `__sub__`, `abbr`), `key.py` (`KeySignature.__new__` with the
raising case, `ModePattern`, `Key` class docstrings), `chords.py` (convert
the three pseudo-code blocks in `__call__`/`__truediv__` to real doctests;
`inversion` on both classes), `tonal_vector.py`
(`conditional_qualify_octave`, `__call__`, `__hash__`).

Check: `uv run pytest src` passes; `systems/wsmn` goes from 75 to at least
110 of 135.

### Step 12. Docstring examples: graph and objects

Files: `graph/graph.py`, `graph/edge.py`, `objects/*.py`.

`OmkGraph`: an example on every query and every mutator that lacks one
(`get_node`, `add_node`, `remove_node`, `get_edge`, `edges_between`,
`edges`, `add_edge`, `remove_edge`, `get_next`, `get_previous`,
`insert_event`, `add_line`, `insert_line_from_list`, `walk_line`,
`branches_from`, `stints`, `walk_stint`, `add_articulation`,
`add_annotation`, `add_spanner`, `connect_lyric_to_object`,
`unlink_lyric_from_object`, `unlink_lyric_sequence`). Skip the six
`NotImplementedError` stubs. Objects: `TonalObject`, `Spanner`, `Marked`
class docstrings; `ChordEvent` a construction example. Edge: `Branch`,
`Simultaneous` construction examples showing `anchor`/`displacement`.

Check: `uv run pytest src` passes; `OmkGraph` goes from 11 to at least 30 of
37 (the stubs excluded).

## Verification

After each step:

```
uv run pytest -q                       # default: fast set, doctests included
uv run pytest -q -m slow               # exhaustive and thorough property runs
uv run ruff check src tests
```

After Step 9, to see what only doctests reach:

```
uv run pytest -q -o addopts="" tests --cov=openmusickit --cov-report=term-missing
```

Expected end state: every conftest fixture used by at least one test; every
`OmkGraph` mutator with a do/inspect/undo test; every algebraic dunder on
`TonalVector`, `MetricalDuration`, `TiedDuration`, `ClockDuration`,
`IntervalQuality`, `KeySignature`, `Key`, `ChordType`/`Chord`,
`ToneCollection` asserted as a law over its full symbol domain; parsers
proven to raise only `ValueError`; the adapter contract executed against two
implementations; the Part 5 findings each pinned by a test (passing or
strict-xfail) and listed in `_plans/revisit.md`.

## Decisions (settled with the developer, 2026-09-21)

These were asked and answered before the plan was approved. Executing agents
treat them as fixed; do not re-ask.

1. **Dependencies.** Add `hypothesis` and `pytest-cov` to the `dev`
   dependency group, dev-only. This is the developer's approval for the
   `uv add --group dev` calls in Steps 6 and 9; no further permission needed.
2. **Defects found by new tests.** Do not fix production code. Write the
   test, mark it `xfail(strict=True, reason=...)`, and add an entry to
   `_plans/revisit.md` describing the defect and pointing at the test.
   Fixes are separate small commits the developer approves one by one.
   Part 5 items 1 and 2 are the ones that matter; 3 to 8 are cosmetic or
   test-side (4, 5 and 8 are fixed by Step 1 and Step 4 as test changes).
3. **Docstring scope.** User-facing callables only. Skip the adapter
   modules, `__post_init__` validators, and trivial accessors such as
   `KeySignature.c`. Everything else in Steps 10 to 12 gets one example.
4. **Location.** Step 0 of execution: copy this document to
   `_plans/testing.md` with a `Status:` line under the title, and update
   that line as steps land, following `_plans/compound-lines.md`.
