# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the bottom under "Resolved" with a pointer to the
commit or plan that settled it.

## `MetricalDuration + TiedDuration` raises (2026-09-21)

`MetricalDuration.__add__` handles a tie on the right with
`TiedDuration([self]) + other`, and the `TiedDuration` constructor rejects
fewer than two members, so `quarter + TiedDuration([half, eighth])` raises
`ValueError` while the reverse order works. Addition is therefore not
associative over the symbol table. Pinned by
`test_a_symbol_plus_a_tie_is_the_tie_plus_the_symbol` in
`tests/systems/wsmn/temporal/test_tied_duration.py` and
`test_addition_is_associative` in `test_duration_algebra.py`. Two more
faces of it, found by the property tests (2026-09-21): a single symbol plus
a tie of any lengths (`from_length(1/4) + from_length(5/8)`), pinned by
`test_any_two_lengths_add_in_either_order`, and `TiedDuration.scale` by a
scalar that turns a member into a tie (`TiedDuration([half,
dotted_eighth]).scale(3)`), which re-adds the scaled members and hits the
same path; pinned by `test_scaling_a_tie_by_any_positive_rational_is_exact`
in `test_duration_properties.py`.

## `MetricalDuration + ClockDuration` makes a cross-system tie (2026-09-21)

`MetricalDuration.__add__` accepts any `Duration`; `_merge` declines a
`ClockDuration`, so `quarter + ClockDuration(5)` is
`TiedDuration([quarter, ClockDuration(5)])`, whose `rational_length` adds a
quarter of a whole note to five microseconds. The reverse order raises
`TypeError`. `TemporalCompatibilityError` exists for this. Pinned by
`test_metrical_time_plus_clock_time_is_refused` in
`tests/values/time/test_clock_duration.py`.

## `ClockDuration` small contract gaps (2026-09-21)

Three, each pinned in `tests/values/time/test_clock_duration.py`:

- `ClockDuration(5) + ZeroDuration()` raises `TypeError`, though
  `ZeroDuration() + ClockDuration(5)` and `ClockDuration(5) + grace` work.
  `ZeroDuration` has no `__radd__`; `GraceDuration` does.
  (`test_zero_is_the_additive_identity_on_either_side`)
- `__truediv__` computes `microseconds / scalar`, which for two ints is a
  float, so `ClockDuration(7) / 3` is inexact while `scale(Fraction(1, 3))`
  is exact. (`test_division_by_an_int_is_exact`)
- `scale` accepts zero and negative scalars; `Measurable.scale` says to raise
  `ScalingError`. (`test_scaling_by_a_non_positive_scalar_raises_scaling_error`)

## `Chord.inversion` accepts a bass the chord does not contain (2026-09-21)

`maj.inversion(Db)` and `C(maj) / Db` succeed, setting a bass that is not
one of the chord's tones; the mistake surfaces later as a bare `ValueError`
from `list.index` inside `arpeggiate`. `_resolve_inversion` could check
membership when given a TonalVector. Pinned by
`test_inversion_onto_a_tone_not_in_the_chord_is_rejected` in
`tests/systems/wsmn/tonal/test_chords.py` (Part 5, item 7 of the testing plan).

## `IntervalQuality.augment` past the table raises a bare `KeyError` (2026-09-21)

`QUALITIES[4.5].augment(1)` indexes `QUALITIES` with 5.5 and lets the
`KeyError` out; `TonalVector.from_string` catches it and reports the same
overflow as `ValueError`. The class could do the same. Pinned by
`test_walking_off_the_table_is_a_value_error` in
`tests/systems/wsmn/tonal/test_interval_quality.py` (Part 5, item 6).

## Backend exceptions leak through the adapter (2026-09-21)

Testing plan, Part 5 item 2. `RustworkxAdapter._rxid` raises a raw
`KeyError` for any node or edge it does not know, so `get_node` of an
unknown id (documented on `OmkGraph.get_node` as returning `None`),
`remove_node`, `add_edge`, `get_edge`, `has_edge`, `edges_between`,
`successors`, `predecessors`, `get_next`, `degree`, `remove_edge` and
`get_edge_endpoints` all let it out, against the `GraphError` docstring
("backend exceptions never pass through the adapter boundary"). Separately,
`get_edge` between two nodes with no edge at all lets
`rustworkx.NoEdgeBetweenNodes` escape, where the same call with an edge of
another type present raises `GraphError`. Pinned by the two strict xfails
at the end of `tests/graph/test_adapter_contract.py`.

## `OmkGraph.remove_edge` returns None (2026-09-21)

Testing plan, Part 5 item 3. The method is annotated `-> OmkEdge` and
returns the adapter's `None`. An undo has to keep its own reference to what
it removed. Pinned by `test_remove_edge_returns_the_removed_edge` in
`tests/graph/test_graph_inverses.py`.

## `Branch` and `Simultaneous` regenerate `__repr__` (2026-09-21, noticed in passing)

`TimedEdge` defines a compact `__repr__`, but its subclasses are plain
`@dataclass`es with the default `repr=True`, so `repr(Branch())` is the
generated form with every field. Cosmetic; `@dataclass(repr=False)` on the
two subclasses would restore the intended form.

## NEXT cycles are valid, and walkers do not stop (2026-09-21)

Testing plan, Part 5 item 1, with the developer's note: cyclic music (a
gamelan cycle) is a NEXT cycle, `add_line([a, b, c]); add_next(c, a)`
passes both guards, and that is right. But `walk_line` then goes round
forever, `walk_span` can loop through a head branched from its own tree,
and `transform_tones` and `materialize` walk with them. Walkers need a way
to stop: yield each event once, or stop at the start event, or take a
bound. Pinned by `test_walk_line_terminates_on_a_cyclic_line` in
`tests/graph/test_graph_properties.py`; the state machine in
`test_graph_state_machine.py` never builds a cycle until this is settled.

## Resolved

### `_tonal_modulo` implicit None (2026-09-18, resolved 2026-09-19)

`_tonal_modulo` and `abs_interval` now go through `_check_length`, which raises
`ValueError` for anything but a 2- or 3-tuple. The `tuple[int]` annotations and
the bare `except:` mentioned in the original note had already been cleaned up by
the consistency audit.

### Signed durations / edge displacement (2026-09-18, resolved 2026-09-19)

Durations are signed quantities. `Duration` requires `__neg__` and provides
`__sub__` as `self + (-other)`; `MetricalDuration` carries the sign on its
numerator, and opposite-sign sums resolve by length through `from_length`
(cancelling to `ZeroDuration`). An edge displacement is therefore a plain signed
`Duration`. A negative duration is never an event length: `SequentialEvent`
raises `ValueError` on any attempt to set one. (2026-09-20: the displacement
moved from `Next` to `TimedEdge` -- `Branch` and `Simultaneous`; NEXT carries
no timing. See `_plans/compound-lines.md`.)

### TonalVector construction and interning (2026-09-18, resolved 2026-09-19)

Interning dropped. `TonalVector` is a plain tuple subclass with `__slots__ = ()`
(as are the `Tone` and `Interval` bases): no cache, no `__init__`, no
sentinel, no per-instance state; `pitch` and `interval` build their view
object on access. Reasons found in the walk-through: instances had a
`__dict__` and were not actually immutable; `copy.deepcopy` and `pickle` of
anything holding a `TonalVector` crashed; the cache ignored the class, so a
subclass could never be instantiated for a cached key. Everything compares by
`==` (`ModePattern` was the one `is`). Measured cost: ~80 bytes per
un-interned instance against ~540 for the `NoteEvent` holding it. A cache
behind `__new__` can be added later as a pure optimisation if a real score
ever shows the need; nothing would observe it.

### interval_quality string parser (2026-09-18, resolved 2026-09-19)

`IntervalQuality` is a frozen dataclass; the nineteen instances live in a
module table `QUALITIES` keyed by relative number, replacing the
`__new__`-interning and the `qualities` registry filled from `__init__`. The
string overload of `_get_quality` and `_get_quality_x` were dead (only their
own doctests called them) and are gone; `TonalVector.from_string` is the one
parser. `KeySignature` gained `__getnewargs__` so it too survives copy and
pickle.

### OmkId vs plain UUID strings (2026-09-18, resolved 2026-09-19)

`OmkId` deleted; ids are `uuid.UUID`, generated with `uuid4`. The wrapper's
string equality had no matching `__hash__`, so it could not be used as a key
interchangeably with its string (which is why the adapter stringified
everything); its uuid4-only check was the one thing that would have broken
old scores if the generator ever changed. Any UUID version parses and
coexists; switching generators later is a `default_factory` change.

### `rational_length` on the abstract TemporalElement (2026-09-18, resolved 2026-09-19)

Not every temporal system reduces its elements to one number (chant does
not), so the base no longer requires it. `TemporalElement` now declares only
`temporal_system`; `Measurable(TemporalElement)` carries `rational_length`,
`scale`, and comparison/hashing by length, allowed only between elements of
`compatible_with` systems. Every WSMN element, `ClockDuration` and
`ZeroDuration` are Measurable; `TemporalRatio` and `TemporalUnit.base`
require it (a ratio is a numeric conversion). `ClockDuration`'s hand-written
cross-system guards are gone; the name `rational_length` stays.

### KeySignatureEvent layering (2026-09-18, resolved 2026-09-19)

`values/tone/modal_context.py` defines the abstract `ModalContext` (tonic,
tones, name, transform); WSMN's `Key` implements it. `KeySignatureEvent` is
now `ModalContextEvent` with a single `modal_context` field, and `objects/`
and `graph/` no longer import anything from `systems/wsmn`. The
key-signature-without-key case is `Key.from_signature(...)`; that surfaced a
real distinction, so `NoKey` now has `signature=None` (nothing to transpose)
while an empty bare signature is a signature (transposes to two sharps).

### Lyrics design (2026-09-18, resolved 2026-09-19)

`LyricSyllable` is a `SequentialEvent` (it keeps its name: no `{Thing}Event`
convention exists, and the name says one syllable goes in it). It holds a
shared frozen `Word` (`values/text/word.py`) and an `index`; text, placement
and lexical stress are read from the Word, which also carries the accent
pattern, so the old placement/location validation collapses to a bounds
check. No separate syllable value: nothing is shared, hashed, or transformed
at the syllable level. `LyricSequence` is gone; `LyricSection(Spanner)`
carries the section metadata and language and spans first to last syllable
(the pattern general `Section`s will follow). `parse_lyrics` and
`OmkGraph.add_lyrics` build everything from typed text (`'`/`,` mark
primary/secondary stress). Also fixed on the way: `syl_str` for `END` had the
hyphen on the wrong side, and `unlink_lyric_sequence` stopped on `==` rather
than `is`. See `_plans/completed/lyrics.md`.

### Testing plan, Part 5 items 4, 5 and 8 (2026-09-21, resolved 2026-09-21)

Test-side findings, fixed by the test changes of Steps 1 and 4: the
`tuplet_ratio_symbols` fixture now builds six ratios from the factories;
`test_chords.py` sweeps all 35 roots (the natural-root restriction was
stale); alias names are deduplicated by identity with `tests.domains.distinct`
and every fixture's size is pinned in `tests/test_fixtures.py`.

### `abs_int_diff` returns a negative count (2026-09-21, resolved 2026-09-21)

`abs_int_diff` now returns the magnitude of `tonal_int` of the nearest
difference, so `abs_int_diff((0, 0), (6, 1))` is 1. `abs_interval` still
spells that difference as a doubly diminished second `(1, 11, 0)`; only the
count was wrong. `test_abs_int_diff_is_never_negative` passes.

### `tonal_int` misreads alterations beyond triple (2026-09-21, resolved 2026-09-21)

`tonal_int` now reads every tuple through `_tonal_unmodulo`, the window of
six half-steps the 2-tuple path already used, so the two paths agree and
`int(a - b)` is additive for differences of doubly altered pitches. Nothing
within triple alterations changes. The tuple form itself carries at most six
half-steps of alteration either way (`c` is chromatic mod 12, so C
octuple-sharp and C quadruple-flat are the same tuple); anything more
extreme needs a wider representation, not a wider window. Pinned by
`test_tonal_int_is_additive_beyond_the_domain`.

### `tonal_lower_of` returns an un-normalized tuple on a tie (2026-09-21, resolved 2026-09-21)

`tonal_lower_of` no longer unmodulos its arguments (`tonal_int` already
reads the wrapped chromatic value), so it returns one of them as given on
every path. Pinned by `test_lower_of_returns_a_normalized_tuple_on_a_tie`.

### `higher_of`/`lower_of` tie-break ignores the octave (2026-09-21, resolved 2026-09-21)

Yes, the rule is the diatonic position: `tonal_higher_of` and
`tonal_lower_of` now break an enharmonic tie on `d + 7 * o` (letter alone
for abstract tuples, via `_diatonic_position`), so C4 is the higher of it
and B-sharp 3. Pinned by
`test_higher_of_enharmonic_tie_across_an_octave_goes_to_the_higher_letter`.
