# Revisit

A single running list of design questions that were noticed, discussed briefly,
and deliberately deferred. One `##` entry per item, newest last. When an item is
resolved, move its entry to the bottom under "Resolved" with a pointer to the
commit or plan that settled it.

## OmkId vs plain UUID strings (2026-09-18)

`OmkId` ([src/openmusickit/utils/id.py](../src/openmusickit/utils/id.py)) wraps a
UUID4 and compares equal to strings so that JSON persistence and graph backends
can use the string form as an atomic identifier. Question: is the wrapper class
earning its keep, or should ids simply be UUID strings? For now string equality
is kept and `__eq__` returns `NotImplemented` for anything other than `OmkId`
or `str`.

## interval_quality string parser (2026-09-18)

`interval_quality._get_quality` (str overload) and `_get_quality_x`
([src/openmusickit/systems/wsmn/tonal/interval_quality.py](../src/openmusickit/systems/wsmn/tonal/interval_quality.py))
contain a `for` loop whose loop variables are never used, and `q_add` can be
referenced before assignment. `tonal_vector.py` has a newer, table-driven parser
(`_QUALITY_KINDS`, `_interval_quality`) covering the same vocabulary. This is the
oldest part of the tonal arithmetic core; to be cleaned up in a dedicated session
together with the rest of `interval_quality.py` (module-global `qualities`
registry, `__new__` interning, bare `except:`).

## Signed durations / edge displacement (2026-09-18)

`ZeroDuration.__sub__` returns `-other` but no `Duration` defines `__neg__`;
`Next.nudge(BACKWARD, amount)` does `self.displacement -= amount` but
`MetricalDuration` has no `__sub__`. Both raise `TypeError` on first use; neither
is called anywhere yet. Question: are durations signed quantities (add
`__neg__`/`__sub__` to the `Duration` contract), or is displacement a signed
offset stored on the `Next` edge with durations staying positive lengths?
Files: [src/openmusickit/values/time/duration.py](../src/openmusickit/values/time/duration.py),
[src/openmusickit/graph/edge.py](../src/openmusickit/graph/edge.py).

## `rational_length` on the abstract TemporalElement (2026-09-18)

`rational_length` is a WSMN notion (the named fractional value of a metrical
duration), yet it is declared abstract on the system-agnostic
`TemporalElement` in `values/time/duration.py` and should probably not be.
It is load-bearing on the base contract, so removing it is a redesign rather
than a cleanup:

- `TemporalElement.__eq__`, `__lt__`, `__hash__` and `_length_of` compare by it;
- `TemporalRatio.r` divides the two sides' `rational_length`, including the
  metrical-over-clock ratios built by `Tempo`;
- `ClockDuration.from_duration`, `ClockDuration.rational_length` (microseconds);
- `CompoundTemporalUnit.remainder` / `first_out_of_bounds`;
- `TemporalUnit.rational_length`.

Removing it means redefining how elements compare and how `TemporalRatio`
computes its multiplier across systems. `ClockDuration` currently keeps
`__eq__`/`__lt__` overrides so it is never compared to metrical time directly.

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

## TonalVector construction and interning (2026-09-18)

`TonalVector` ([src/openmusickit/systems/wsmn/tonal/tonal_vector.py](../src/openmusickit/systems/wsmn/tonal/tonal_vector.py))
has been a tuple subclass and not, and its `__new__`/`__init__` and interning
have been rewritten several times. Today: a class-level `_cache` keyed by the
tuple, `__new__` returning the cached instance, and `__init__` guarded by a
`hasattr(self, "_initialized")` sentinel so the pitch/interval representations
are built once. `IntervalQuality` has a second, different interning scheme
(module-global `qualities` filled from `__new__`). Three places rely on
identity (`is`): `ModePattern.__post_init__`, `NoKey.transform(...) is NoKey`,
and a `Key.of` doctest. The developer wants to walk through exactly what happens
here before any change; the likely cleanup is to build the representations in
`__new__` (dropping `__init__` and the sentinel) or to drop interning and use
`==` at the three sites.

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
