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

## `_tonal_modulo` implicit None (2026-09-18)

`tonal_arithmetic._tonal_modulo`
([src/openmusickit/systems/wsmn/tonal/tonal_arithmetic.py](../src/openmusickit/systems/wsmn/tonal/tonal_arithmetic.py))
returns `None` for tuples that are not of length 2 or 3. Same arithmetic core as
the item above; handle together (the whole module also uses `tuple[int]` to mean
variable-length tuples and has a bare `except:` in `_tonal_unmodulo`).

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
