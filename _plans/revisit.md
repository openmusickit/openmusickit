# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the bottom under "Resolved" with a pointer to the
commit or plan that settled it.

## Factory functions, one at a time (2026-09-18)

`Rest(duration)` ([src/openmusickit/objects/note_event.py](../src/openmusickit/objects/note_event.py))
is a CapWords function that builds a `NoteEvent` holding a `SilentTone`. It is
deliberately *not* a class: a `Rest` subclass could be un-rested by `add_tone`
and would then be a lie. This is a special case that papers over an OMK concept
(a note event with silent content) to present the music-theory concept (a rest);
it is not a convention to document or repeat. Other places where a CapWords
factory might be wanted should be considered individually, here, as they come up.

## Lyrics design (2026-09-18)

Open questions, to be talked through before touching
[src/openmusickit/objects/lyrics.py](../src/openmusickit/objects/lyrics.py):

- Is a syllable itself the sequential event, or does a `LyricEvent` own a
  syllable (or a run of them)? The code has a TODO saying lyrics need to be
  events; they are currently plain `OmkObject`s placed with NEXT edges.
- `LyricSequence` subclasses `list` and carries an `OmkId`; every other
  collection in OMK wraps a tuple (`ToneCollection`, `CompoundTemporalUnit`,
  `TiedDuration`). Its `section_name` default was `"None None"` (now `None`).
- Validation rules in `LyricSyllable.__post_init__` (placement vs location)
  were written before the event question was settled.

## KeySignatureEvent layering (2026-09-18)

[src/openmusickit/objects/context_event.py](../src/openmusickit/objects/context_event.py)
imports the concrete WSMN types `Key`, `KeySignature` and `TonalVector` into the
system-agnostic `objects` layer, while `NoteEvent` and `ChordEvent` depend only
on the abstract `Tone` / `ToneCollection`. Either `values/tone` grows an abstract
key/key-signature that WSMN implements, or `KeySignatureEvent` moves under
`systems/wsmn/`. goals.md section 1 (Western concepts are implementations on top
of general abstractions) argues for the former.

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
(cancelling to `ZeroDuration`). `Next.displacement` is therefore a plain signed
`Duration`. A negative duration is never an event length: `SequentialEvent`
raises `ValueError` on any attempt to set one.

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
