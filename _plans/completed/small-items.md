# Resolved Items from the revisit.md doc

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

### `MetricalDuration + TiedDuration` raises (2026-09-21, resolved 2026-09-21)

`MetricalDuration.__add__` now folds a tie on the right in member by
member, the mirror of what `TiedDuration.__add__` does with a symbol on
the right, so `quarter + (half + eighth)` is a double-dotted half and
addition is associative over the symbol table. `TiedDuration.scale` and
`from_length(x) + from_length(y)` for any two lengths follow. The four
tests named above pass, and `test_lengths_add_and_subtract` no longer
excludes symbol-and-tie pairs.

### `MetricalDuration + ClockDuration` makes a cross-system tie (2026-09-21, resolved 2026-09-21)

`MetricalDuration.__add__` and `TiedDuration.__add__` now check
`temporal_system.compatible_with` before anything else and raise
`TemporalCompatibilityError` for a Duration of another system, so
`quarter + ClockDuration(5)` names the incompatibility. The reverse order
still declines with `TypeError` (`ClockDuration.__add__` returns
`NotImplemented`), which a grace on the right relies on. Pinned by
`test_metrical_time_plus_clock_time_is_refused`.

### `ClockDuration` small contract gaps (2026-09-21, resolved 2026-09-21)

All three closed. `ZeroDuration` has `__radd__` (any Duration plus zero
is that Duration, and `sum` may start from 0), so `ClockDuration(5) +
ZeroDuration()` works. `ClockDuration.__truediv__` divides through
`Fraction`, so `ClockDuration(7) / 3` is exact. `ClockDuration.scale`
raises `ScalingError` for anything but a positive rational, as
`Measurable.scale` requires. The three tests in
`tests/values/time/test_clock_duration.py` pass.

### `Chord.inversion` accepts a bass the chord does not contain (2026-09-21, resolved 2026-09-21)

`_resolve_inversion` now raises `ValueError` for a TonalVector that is
not one of the chord's tones, so `maj.inversion(Db)` and `C(maj) / Db`
fail at once. This is a placeholder: the developer notes that C major over
B-flat is a real object, a C7 in third inversion, and naming it needs a
chord lookup system that does not exist yet; a TODO in the method says so.
Pinned by `test_inversion_onto_a_tone_not_in_the_chord_is_rejected`.

### `IntervalQuality.augment` past the table raises a bare `KeyError` (2026-09-21, resolved 2026-09-21)

`IntervalQuality.augment` (and so `diminish`, `+`, `-`) now raises
`ValueError` naming the overflow and the table's range. Pinned by
`test_walking_off_the_table_is_a_value_error`.

### Backend exceptions leak through the adapter (2026-09-21, resolved 2026-09-21)

`RustworkxAdapter._rxid` raises `GraphError` for anything not on the
graph, `get_node` answers `None` for an unknown id, and `get_edge`
treats `rustworkx.NoEdgeBetweenNodes` as no edge of any type, so every
adapter method now honours the boundary rule, which the `GraphAdapter`
class docstring states. The two contract tests run unmarked against both
adapters.

### `OmkGraph.remove_edge` returns None (2026-09-21, resolved 2026-09-21)

`OmkGraph.remove_edge` now returns the edge it removed, so an undo has
its type, displacement and metadata to hand. The adapter's `remove_edge`
still returns `None`. Pinned by `test_remove_edge_returns_the_removed_edge`,
which puts the same edge object back through the adapter and checks the
snapshot.

### `Branch` and `Simultaneous` regenerate `__repr__` (2026-09-21, resolved 2026-09-21)

`Next`, `Branch` and `Simultaneous` are `@dataclass(repr=False)`, so
they inherit the compact `__repr__` of `OmkEdge` and `TimedEdge`
(`Branch(anchor=onset, displacement=None)`); `Next` had the same
generated form against `OmkEdge.__repr__`. Each class docstring shows its
repr.

### NEXT cycles are valid, and walkers do not stop (2026-09-21, resolved 2026-09-21)

Walkers yield each event once. `walk_line` stops when the next event is
one it already yielded, so a cycle comes out as one pass from wherever the
walk starts, and an `end` that is never reached is a `ValueError` rather
than a hang; `walk_span` shares one set of seen events down its
recursion, so a head branched from its own tree is entered once;
`transform_tones`, `walk_stint` and `materialize` inherit both. The raw
follower is factored out as `OmkGraph._follow_next`, which never stops on
a cycle, so a future realization walker that means to go round
continuously, or a counted number of times, bounds it its own way (the
developer's note, 2026-09-21). Pinned by
`test_walk_line_terminates_on_a_cyclic_line` and
`test_walk_span_terminates_when_lines_branch_into_each_other`. The state
machine in `test_graph_state_machine.py` still builds no cycles, because
its model tracks lines by head and tail; teaching it cycles is a follow-up.

### Graph state machine is flaky under the thorough profile (2026-09-22, resolved 2026-09-22)

Not a Hypothesis defect and not the percussion work: latent since the
state machine was written (95c322e, 2026-09-21). `remove_pin` drew from
`sorted(self.pins, key=str)`, an order set by the uuid4 ids, which differ
on every run. Hypothesis records a draw as an index and compares runs that
share a prefix of choices, so the same index removed a different pin the
next time; that changed whether `pin` early-returned and whether
`remove_pin`'s precondition held, and rule selection (rejection sampling
over all rules, then a first-time `is_enabled` boolean) drew a different
type at the same position, which the choice tree reports as
`FlakyStrategyDefinition`. The thorough profile failed within seconds; the
default profile failed 4 of 10 runs once the example database held the
failing case. `pins` is now an insertion-ordered list sampled directly,
and the module docstring states the rule: every `sampled_from` in the
machine draws from a list in insertion order, never from anything ordered
by id. Verified: three thorough and ten default runs green; the full suite
green under both profiles.

### `ContextEvent` repr printed its fixed duration (2026-09-22, resolved 2026-09-22)

`ContextEvent.duration` is now `repr=False`, as `DivisionEvent`'s already was,
so `ContextEvent()`, `ModalContextEvent(modal_context=None)` and the new
`MeterEvent` / `TempoEvent` reprs evaluate. Done while adding the temporal
context events, whose reprs inherit the field. `Tempo.__repr__` had the same
kind of defect (it printed the two `TemporalUnit`s, which `Tempo(n, beat)`
cannot take back) and now prints the constructor's arguments, with the clock
time only when it is not the default minute. The `Marking` / `MarkSpanner`
half of the revisit entry is still open.

### Verbal tempo indications have no home (2026-09-22, resolved 2026-09-22)

A tempo word is a `TempoTerm` (`values/scoring/tempo_term.py`: `name`,
`description`, `aliases`; frozen; no range field, the conventional
beats-per-minute range is description only), held by `TempoEvent.term` beside
or instead of the ratio. It is not a `Mark`: nothing places it with a MARKS
edge, and `kind`, `attachment_mode` and `binds` mean nothing for it. The WSMN
table (`systems/wsmn/scoring/symbols.py`, TEMPO TERMS) has the twenty ranged
words of the conventional modern table and the five restorers (a tempo, tempo
primo, l'istesso tempo, rubato, ad libitum). Gradual changes (rit., accel.)
stay open in `revisit.md`.

### `Marking.__repr__` and `MarkSpanner.__repr__` do not round-trip (2026-09-22, resolved 2026-09-22)

`Mark.__repr__` now prints the constructor call with full enum symbols and
the fields at their defaults left out, so a mark made for one score
(`Mark(name="dolce", kind=MarkType.EXPRESSION)`) prints as written and a
ready-made mark prints every field it sets. `Marking` and `MarkSpanner` drop
their compact reprs and take the dataclass default, so
`Marking(mark=Mark(...))` evaluates given the `mark` module's names. The
entry's other idea, printing the ready-made symbol's name, was not possible:
`objects/marking.py` may not import `systems/wsmn/scoring/symbols`. Pinned by
`test_repr_round_trips` in `tests/objects/test_marking.py` over every
ready-made mark. The other custom reprs in `src/` were checked; the ones that
do not evaluate are a new entry in `revisit.md`.
