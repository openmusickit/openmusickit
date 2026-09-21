# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the bottom under "Resolved" with a pointer to the
commit or plan that settled it.

## `abs_int_diff` returns a negative count (2026-09-21)

`abs_int_diff((0, 0), (6, 1))` (C and B double-sharp) is `-1`. The nearest
difference between them is a doubly diminished second, an interval of minus
one half-step, and `abs_int_diff` returns `tonal_int` of that interval
rather than its magnitude. `abs_interval((6, 1, -1))` has the same shape:
it returns `(1, 11, 0)`, whose `tonal_int` is `-1`. Pinned by
`test_abs_int_diff_is_never_negative` in
`tests/systems/wsmn/tonal/test_tonal_arithmetic.py`. Only pairs whose
difference is beyond a double alteration are affected; every in-domain pair
satisfies the "smaller side of the octave" law.

## `tonal_int` misreads alterations beyond triple (2026-09-21)

`tonal_int` adjusts the chromatic value into a window of three half-steps
either side of the letter's natural, so a quadruple alteration wraps: the
difference of D-sharp and F-double-flat is `(2, 0, 0)`, a third of zero
half-steps, and `tonal_int` of it is 12. Such tuples arise only as
differences of two doubly altered pitches, so `int(a - b)` is wrong for
those pairs while `(a - b) + b == a` still holds. Either the domain (at
most triple alterations) should be documented on `tonal_int` and `__int__`,
or the window widened to six like `_tonal_unmodulo`. Pinned by
`test_tonal_int_is_additive_beyond_the_domain`.

## `tonal_lower_of` returns an un-normalized tuple on a tie (2026-09-21)

`tonal_lower_of` unmodulos both arguments and, when they are the same size,
returns one of them without re-normalizing: `tonal_lower_of((6, 0), (6, 0))`
is `(6, 12)` and `tonal_lower_of((6, 11, 0), (0, 11, 1))` is `(0, -1, 1)`.
Pinned by `test_lower_of_returns_a_normalized_tuple_on_a_tie`.

## `higher_of`/`lower_of` tie-break ignores the octave (2026-09-21)

On an enharmonic tie the docstring says the larger diatonic value wins
(a diminished fifth over an augmented fourth), and the code compares `d`
alone. Across an octave boundary that names B-sharp 3 the higher of it and
C4, though C4 is spelled on the higher letter. Is the intended rule the
diatonic *position* (`d + 7 * o`)? Pinned, under that reading, by
`test_higher_of_enharmonic_tie_across_an_octave_goes_to_the_higher_letter`.

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
