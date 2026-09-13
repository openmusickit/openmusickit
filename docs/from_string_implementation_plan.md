# TonalVector.from_string / from_ly — Findings & Implementation Plan

This document summarizes work done so far in this session and lays out the
concrete plan for implementing `TonalVector.from_string` and
`TonalVector.from_ly`, which are currently stubs (`raise NotImplementedError`)
in `src/openmusickit/systems/wsmn/tonal/tonal_vector.py`.

Test suites for both methods already exist and are approved. **Do not
redesign the test suites** — implement code to satisfy them. If a test looks
wrong once you're implementing, stop and ask rather than silently changing
the test.

---

## 1. Bugs found and already fixed (prerequisites, done)

These were all confirmed with the developer before fixing. All are complete;
no further action needed on them, but noting them here for context.

1. **`constants.py` `AC` table `ly` field was backwards.**
   Real Lilypond convention: `is` suffix = sharp, `es` suffix = flat.
   The table had them swapped. Fixed. Doctests in `tonal_vector.py`
   referencing `.ly`/`.ly_abs8ve` (e.g. `cis`, `bes`, `fis`, `des`) were
   updated to match.

2. **`interval_quality.py` typo:** `'dbl_dimished-from_maj_min'` →
   `'dbl_diminished-from_maj_min'`. Fixed. No other references existed.

3. **`interval_quality.py` sign-flip bug** in the tuple-dispatch
   `_get_quality` (used by `TonalVector.interval.quality`, i.e.
   `iq._get_quality(vector)` where vector is a `(d,c[,o])` tuple). The line

   ```python
   if modifier < 0:
       base_q_val = -base_q_val
   ```

   incorrectly flipped the sign of `base_q_val` for Mm-type diatonic degrees
   (2nds, 3rds, 6ths, 7ths), producing wrong quality names for minor and
   diminished intervals computed directly from a vector. E.g. `(1,1)` (D-flat,
   a minor 2nd) was reported as "diminished" instead of "minor"; `(1,0)`
   (D-double-flat, a diminished 2nd) was reported as "dbl diminished" instead
   of the correct "diminished"... this bug also caused `(2,3)` (Eb, minor
   3rd) to say "diminished", etc. **Fix: deleted the two-line sign-flip
   block entirely** — `base_q_val + modifier` is correct without it, verified
   by sweeping all `(d,c)` combinations for d in 0-6, c in 0-11.

   Confirmed with developer: minor 2nd = `(1,1)` (D-flat), diminished 2nd =
   `(1,0)` (D-double-flat). First tuple member is diatonic degree/letter,
   second is chromatic value (half-steps from C, or half-steps from a
   perfect unison for intervals).

4. **`number_names.py` typo:** `ordinals[10]` was `"10th,"` (stray comma) →
   fixed to `"10th"`. This list will be needed for ordinal-suffix interval
   parsing (`"9th"`, `"11th"`, etc.).

All fixes verified: `uv run pytest tests/ -q --deselect tests/tones/test_from_string.py --deselect tests/tones/test_from_ly.py --deselect tests/tones/test_string_roundtrip.py` → **49 passed**, no regressions. Doctests across `src/` also pass except the two intentionally-unimplemented methods.

---

## 2. API design decisions (already made, confirmed with developer)

### Two separate classmethods, not one

- **`TonalVector.from_string(cls, s, mid_c=4, solfege_style=SolfegeStyle.EURO_FIXED)`**
  Handles everything *except* Lilypond note-name syntax. Rejects Lilypond
  spellings (`is`/`es` accidental suffixes, `'`/`,` octave marks) by raising
  `ValueError` — does not try to guess.

- **`TonalVector.from_ly(cls, s, prev_note=None)`**
  Handles *only* Lilypond note-name syntax (`is`/`es` accidentals, absolute
  `'`/`,` octave marks, or relative-octave resolution via `prev_note`).
  Always returns an **octave-qualified** TonalVector (3-tuple), since
  Lilypond has no notion of an abstract/octave-less pitch. With no octave
  mark and no `prev_note`, defaults to octave 0.

  Known, accepted asymmetry: `from_ly(tv.pitch.ly)` on an **abstract**
  vector `tv` returns `tv.qualify_octave(0)`, not `tv` itself — this is
  intentional and tested for explicitly in `test_string_roundtrip.py`.

Rationale: Lilypond conventions (always-qualified octave, its own
accidental spelling, relative octave marks) are different enough from
every other input form that mixing them into `from_string` created either
ambiguity or asymmetry bugs. Splitting them out was the developer's explicit
decision.

### `SolfegeStyle` enum (added to `constants.py`, done)

```python
class SolfegeStyle(Enum):
    OMK_MOVEABLE = "omk_moveable"
    EURO_FIXED = "euro_fixed"
```

Reason: "Si" is ambiguous. In the existing OMK moveable-do chromatic solfege
table (`DO`, `RE`, `MI`, ... in `constants.py`), `SO[1] == 'si'` means
so-sharp. But in fixed-do (Latin/French) convention, "Si" is just the name
for the natural 7th scale degree (enharmonic to "Ti"). Both are legitimate;
the developer decided `from_string` should default to `EURO_FIXED` (most
common real-world usage) with `OMK_MOVEABLE` available as an explicit
opt-in.

- `EURO_FIXED`: one syllable per diatonic letter, **no chromatic variants of
  their own** — accidentals are applied separately, exactly like a letter
  name (e.g. `"Do#"`, `"Sib"`, `"Sol#"`). New lookup table added:
  ```python
  EURO_SF = {0: 'do', 1: 're', 2: 'mi', 3: 'fa', 4: 'sol', 5: 'la', 6: 'si'}
  ```
  (in `constants.py`, already added). Note `"so"` (no `l`) is also accepted
  per tests — treat as an alias for `"sol"`.

- `OMK_MOVEABLE`: uses the existing `MS[d].sf` dicts (`DO`, `RE`, `MI`, `FA`,
  `SO`, `LA`, `TI`), which map `{-1: flat-variant, 0: natural, 1: sharp-variant}`
  to chromatic syllables directly (e.g. `"Di"` = do-sharp, `"Te"` = ti-flat).
  No separate accidental parsing needed for these — the syllable *is* the
  full chromatic spelling.

### Interval number validity (raised by developer, must implement)

Per the physical structure of `MS` in `constants.py`:
- **Unisons, 4ths, 5ths (and their compounds: 8ves, 11ths, 12ths, etc.)**
  are Perfect-type (`MS[d].q == P`): valid qualities are perfect,
  augmented, diminished, double-augmented, double-diminished, etc. **Major
  and minor are invalid for these.**
- **2nds, 3rds, 6ths, 7ths (and their compounds: 9ths, 10ths, 13ths, etc.)**
  are Mm-type (`MS[d].q == Mm`): valid qualities are major, minor,
  augmented, diminished, etc. **Perfect is invalid for these.**

`from_string` must raise `ValueError` for invalid combinations (e.g. `"P2"`,
`"M4"`, `"m5"`, `"M8"`, `"P9"` — see
`test_invalid_interval_quality_number_combinations_raise` in
`test_from_string.py`). The diatonic index `d = (number - 1) % 7` tells you
`MS[d].q` (via `from .constants import MS`) — check it before/while calling
`iq._get_quality`.

Note `iq._get_quality(qual_str, d)` (the string-dispatch version in
`interval_quality.py`) does **not** currently raise on invalid combinations
itself (confirmed: `_get_quality('P', 1)` returns `perfect` without
complaint, `_get_quality('M', 0)` returns `major` without complaint) — do
**not** rely on it to catch these errors. `from_string` needs to validate
this explicitly itself, e.g.:

```python
from .constants import MS, QualityType

def _validate_interval_quality(quality_word, d):
    is_major_minor_word = quality_word.lower() in ("m", "maj", "major", "min", "minor")
    is_perfect_word = quality_word.lower() in ("p", "per", "perfect")
    expected = MS[d].q  # QualityType.P or QualityType.Mm
    if is_perfect_word and expected != QualityType.P:
        raise ValueError(...)
    if is_major_minor_word and expected != QualityType.Mm:
        raise ValueError(...)
    # aug/dim/double-aug/double-dim are valid for both families, no check needed
```

(This is illustrative, not literal code to paste — integrate into whatever
parsing structure you build.)

### Case-sensitivity rules (confirmed with developer)

- Standalone **`M`** = major, standalone **`m`** = minor (interval quality),
  case-sensitive for the single-letter abbreviation only. Everything else is
  case-insensitive.
- Bare **`A4`/`a4`** and **`D4`/`d4`** (letter + digit, no other qualifier)
  are **always pitches** (A above middle C / D above middle C), regardless
  of case. The interval qualities augmented/diminished must be spelled out
  as `"aug"`/`"dim"` (or `"augmented"`/`"diminished"`) — never as a bare
  `"a"`/`"d"` single-letter abbreviation in `from_string`. (This differs
  from `interval_quality.py`'s internal `_get_quality_x`, which *does*
  accept bare `"a"`/`"d"` — that's fine, it's an internal helper not exposed
  through `from_string`'s public string grammar; `from_string` simply should
  never route a bare `"a"`/`"d"` + number to the interval parser.)

### Octave semantics (confirmed with developer)

- `from_string`'s `mid_c` parameter is the octave *number* that should map
  to OMK's internal octave 0 (middle C). Default `mid_c=4` (MIDI-style, C4 =
  middle C). Internal octave = `octave_number - mid_c`.
  - `mid_c=0`: octave number IS the internal octave directly (OMK's own
    convention, e.g. used by `pitch.unicode`/`pitch.ascii`/`pitch.verbose`).
  - `mid_c=4`: MIDI/common convention (used by `pitch.unicode_C4`/`ascii_C4`,
    and is `from_string`'s default).
  - `mid_c=3`: another common convention, tested explicitly but minimally.
- Compound interval numbers (8-13) produce an **octave-qualified 3-tuple**:
  e.g. `"M9"` → `(1, 2, 1)` (major 2nd + 1 octave), not the abstract 2-tuple.
  Verified formula: `n = number - 1; d = n % 7; o = n // 7; c = (MS[d].c +
  quality.chromatic_modifier) % 12`; result is `(d, c, o)`. Numbers 1-7
  always produce abstract 2-tuples (o is always 0 and gets omitted);
  numbers 8-13 always produce 3-tuples (o >= 1).
- `from_ly` always returns a 3-tuple (octave-qualified), even for octave
  number 0 / no marks at all.

---

## 3. Files already changed (done)

- `src/openmusickit/systems/wsmn/tonal/constants.py`:
  - Fixed `AC.ly` sharp/flat swap.
  - Added `SolfegeStyle` enum.
  - Added `EURO_SF` dict.
- `src/openmusickit/systems/wsmn/tonal/interval_quality.py`:
  - Fixed `dbl_dimished` typo.
  - Removed the sign-flip bug in tuple-dispatch `_get_quality`.
- `src/openmusickit/utils/number_names.py`:
  - Fixed `"10th,"` typo.
- `src/openmusickit/systems/wsmn/tonal/tonal_vector.py`:
  - Updated `.ly`/`.ly_abs8ve` doctests to match corrected `AC` table.
  - `from_string` signature changed to
    `(cls, s, mid_c=4, solfege_style=SolfegeStyle.EURO_FIXED)` (removed old
    `prev_note` param). Still `raise NotImplementedError`, docstring
    updated, doctest examples present (`'C'` → `(0,0)`, `'G#'` → `(4,8)`).
  - New `from_ly` classmethod stub added: `(cls, s, prev_note=None)`. Still
    `raise NotImplementedError`, docstring + doctest examples present
    (`'cis'` → `(0,1,0)`, `"g'"` → `(4,7,0)`).
  - Added `SolfegeStyle` to the imports from `.constants`.

## 4. Test files already written (done, approved — do not redesign)

- `tests/tones/test_from_string.py` — ~150+ parametrized cases covering:
  bare letters; ASCII accidentals (`#`,`b`,`##`,`bb`); Unicode accidentals
  (♯,♭,𝄪,𝄫); rejection of Lilypond spellings (`ValueError`); word modifiers
  (`sharp`,`flat`,`natural`,`double sharp`, etc.); numeric octave (`C4`,
  custom `mid_c`, `mid_c=0`, `mid_c=3`); bare `A4`/`a4`/`D4`/`d4` always
  pitches; `EURO_FIXED` solfege (default) including `"Si"`→B; `EURO_FIXED`
  solfege + accidental (`"Do#"`,`"Sib"`); `OMK_MOVEABLE` solfege (explicit
  `solfege_style=` arg) including `"Si"`→so-sharp; interval abbreviations
  (`P`,`M`,`m`); aug/dim spelled out (not bare `a`/`d`); spelled-out quality
  words (`"Major 3"`, `"perfect fifth"`); ordinal suffixes (`"M3rd"`,
  `"M9th"`); compound intervals 8-13 (octave-qualified); bare `M`/`m`
  case-sensitivity; whitespace tolerance; invalid strings (`ValueError`);
  invalid interval quality/number combinations (`ValueError`, e.g. `"P2"`,
  `"M4"`, `"M8"`, `"P9"`).

- `tests/tones/test_from_ly.py` — cases for: default octave (no marks, no
  prev_note → octave 0); absolute octave marks (`'`,`,`, multiples);
  relative octave via `prev_note` (uses existing `tonal_nearest_instance`
  semantics — verified numerically against `ta.tonal_nearest_instance`);
  invalid strings (`ValueError`).

- `tests/tones/test_string_roundtrip.py` — symmetry tests: `pitch.unicode`/
  `pitch.ascii` round-trip via `from_string(..., mid_c=0)`;
  `pitch.unicode_C4`/`pitch.ascii_C4` round-trip via default `from_string`;
  `pitch.verbose` round-trips via `mid_c=0`; `interval.unicode` round-trips
  for abstract vectors only (doesn't encode octave); `interval.abbr`
  round-trips for all vectors (encodes octave as `+N`/`-N` suffix);
  `pitch.ly` → `from_ly` known asymmetry (qualifies at octave 0, doesn't
  return the abstract vector — tested explicitly, not silently skipped);
  `pitch.ly_abs8ve` round-trips via `from_ly`; `pitch.ly_rel8ve(prev)`
  round-trips via `from_ly(..., prev_note=prev)`.

All three test files currently fail cleanly with `NotImplementedError`
(confirmed no other spurious failures). Collection count ~1870 tests total
in `tests/tones/`.

---

## 5. What's left: implement `from_string` and `from_ly`

### Suggested internal structure

Both methods will likely want to delegate pitch-token parsing (letter +
accidental + octave) to a shared private helper, since `from_ly` also needs
letter+accidental parsing (just with different accidental spelling and
octave rules). Consider a private module-level function or a `cls`-level
helper, e.g. `_parse_letter_and_accidental(token, accidental_table)`
returning `(d, c)`, reused by both.

### `from_string` — parsing steps (suggested order of attempts)

1. **Strip/normalize whitespace.** Test cases have surrounding and internal
   extra whitespace (`" C "`, `"C #"`, `"  M3  "`, `"perfect  fifth"`) that
   must be tolerated. Consider collapsing internal whitespace before/around
   accidental words, or being tolerant at each parsing stage.

2. **Reject Lilypond spellings up front.** If the string (after normalizing
   case) is a valid Lilypond note name (letter + `is`/`es` repeats, optional
   `'`/`,` marks) with no other valid `from_string` interpretation, raise
   `ValueError`. Careful: bare letters like `"c"` should NOT be rejected
   (they're valid `from_string` bare-letter pitches) — only reject when the
   `is`/`es` suffix or `'`/`,` marks are present. Also note ASCII `#`/`b`
   look nothing like Lilypond, so no conflict there. The rejected test cases
   are: `"cis"`, `"ces"`, `"gis"`, `"c'"`, `"c,"`.

3. **Try interval parsing first, or pitch parsing first?** Since interval
   strings look like `<quality><number>` (e.g. `"M3"`, `"aug4"`,
   `"perfect fifth"`) and pitch strings look like `<letter><accidental>
   [octave]` (e.g. `"C#4"`), these grammars are distinguishable: pitch
   strings start with a single letter A-G (case-insensitive) optionally
   followed by accidental/octave; interval strings start with a quality
   token (`P`, `M`, `m`, `aug`, `dim`, `perfect`, `major`, `minor`,
   `augmented`, `diminished`, `dbl aug`, `double diminished`, etc.) followed
   by a number/ordinal. Recommend: try to match the interval grammar
   (quality word/abbr + number) first; if it matches, parse as interval.
   Otherwise try pitch grammar (letter-name or solfege syllable + optional
   accidental + optional octave). If neither matches, raise `ValueError`.

   Watch the ambiguity: `"M"` alone should probably not match anything (no
   number) — falls through to pitch parsing, where `"M"` is not a valid
   pitch letter (A-G only) or solfege syllable, so raises `ValueError`
   (not tested directly but should behave consistently). `"A4"`/`"D4"`
   must resolve to pitch, not interval — per the rule, `from_string` should
   simply never attempt an interval parse when the quality token is a bare
   `"a"`/`"d"` (single letter, either case) — treat those as *only* valid
   pitch letters, never as interval quality abbreviations. `"aug"`/`"dim"`
   (2+ chars) are unambiguous and only ever mean interval quality.

4. **Pitch parsing:**
   - Match leading letter A-G (case-insensitive) OR a solfege syllable
     (EURO_FIXED default table `EURO_SF`, or OMK_MOVEABLE tables via
     `MS[d].sf`, selected by `solfege_style`).
   - For OMK_MOVEABLE: the syllable itself encodes any chromatic alteration
     — look it up directly against all `MS[d].sf` values to find `(d, c)`
     without any further accidental parsing (e.g. `"Di"` → d=0, c=1 directly
     since `DO[1] == 'di'`).
   - For EURO_FIXED (and letter names): after matching the base letter/
     syllable, look for an accidental suffix:
     - ASCII: `#`, `##`, `b`, `bb` (any repeats, though tests only go to
       double).
     - Unicode: `♯`, `𝄪` (double sharp), `♭`, `𝄫` (double flat) — note `𝄫𝄫`
       for quadruple flat etc. per `AC` table, but tests only exercise
       single/double.
     - Word forms: `"sharp"`, `"flat"`, `"natural"`, `"double sharp"`,
       `"double flat"`, optionally with a space or not (`"C sharp"` and
       `"Csharp"` both valid), also `"-sharp"`/`"-flat"` hyphenated form for
       solfege (`"Do-sharp"`).
     - Also accept the modifier word forms from `AC[i].v` directly for
       full generality (e.g. triple/quadruple), even though tests only
       cover single/double — this costs nothing extra since `AC` already
       has all the entries.
   - Compute `(d, c)` from letter/syllable + accidental offset:
     `c = (MS[d].c + accidental_offset) % 12`.
   - After the accidental, look for an optional trailing octave number
     (may be negative, e.g. `"G-1"` for `mid_c=0`). If present, compute
     `internal_octave = octave_number - mid_c` and return the 3-tuple
     `(d, c, internal_octave)`. Otherwise return the abstract 2-tuple
     `(d, c)`.
   - Validate the leading letter is A-G; if not (and it's also not a
     recognized solfege syllable or interval quality), raise `ValueError`
     (covers `"H"`, `"Z9"`, `"banana"`, `""`).

5. **Interval parsing:**
   - Match a quality token: `P`/`p`/`perfect`/`Per`/`per` (case-insensitive)
     → perfect; `M` (must be exactly capital `M`, no other case) →
     major; `m` (must be exactly lowercase `m`) → minor; `maj`/`major`
     (any case) → major; `min`/`minor` (any case) → minor; `aug`/
     `augmented` (any case, 2+ chars) → augmented; `dim`/`diminished` (any
     case, 2+ chars) → diminished; with optional `dbl`/`double` prefix (or
     "dbl dim"/"double diminished"/"dbl aug"/"double augmented") →
     double-augmented/double-diminished. (`interval_quality._get_quality`
     and `_get_quality_x` already implement most of this matching logic —
     reuse them; you mainly need to (a) extract the quality-token substring
     from the input string, (b) determine `d` from the number first so you
     can call `iq._get_quality(quality_token, d)` correctly, and (c) do the
     Perfect vs. Mm-type validation described in section 2 above before or
     after calling `_get_quality`.)
   - Match a number: digits (`"3"`), possibly followed by an ordinal suffix
     (`"3rd"`, `"9th"`) — strip the suffix (a regex stripping trailing
     `st|nd|rd|th` from the digit sequence is simplest; exact
     ordinal-correctness per number isn't being tested letter-for-letter,
     so you don't strictly need `number_names.ordinals` for validation,
     though you're welcome to use it for stripping/validating if it's
     convenient). OR match a spelled-out interval name from `MS[d].i`
     (note MS only has "unison","second",...,"seventh" — there are no
     compound-number words like "ninth" tested, only digit/ordinal forms
     for those: `"M9th"` but not `"major ninth"`). For numbers 1-7, both
     digit forms (`"P1"`) and word forms via `MS[d].i` are tested
     (`"perfect fifth"`, `"major third"`, `"minor sixth"`) — note "1" maps
     to "unison" not "first", so when parsing the word form, look it up
     against `MS[d].i` for d in 0-6, or accept "unison" specially since it
     isn't a standard ordinal word.
   - Compute `n = number - 1`, `d = n % 7`, `o = n // 7`.
   - Validate quality vs. `MS[d].q` (Perfect vs Mm-type) — raise
     `ValueError` on mismatch (see section 2).
   - Get quality object: `quality = iq._get_quality(quality_token_normalized, d)`
     (you may need to normalize/strip whitespace from tokens like
     `"double diminished"` → pass through as-is since `_get_quality_x`
     already does substring matching on `'dim'`/`'aug'`/`'dbl'`/`'double'`).
   - `c = (MS[d].c + quality.chromatic_modifier) % 12`.
   - Return `(d, c, o)` if `o != 0` else `(d, c)`.

6. **Whitespace handling detail:** several interval test cases have a space
   between quality and number (`"aug 4"`, `"dim 5"`, `"double diminished 5"`,
   `"perfect fifth"`) and others don't (`"aug4"`, `"P5"`). A regex like
   `^\s*(?P<quality>[A-Za-z ]+?)\s*(?P<number>\d+)\s*(?:st|nd|rd|th)?\s*$`
   (case preserved for the case-sensitive `M`/`m` check, applied before
   lowering) should handle both, but you'll need a separate branch for
   fully spelled-out number words (`"fifth"`, `"third"`, `"sixth"`) since
   those don't have a digit at all.

### `from_ly` — parsing steps

1. Match Lilypond note name: single letter `c`-`b` (case-insensitive per
   test `"CIS"` → same as `"cis"`), followed by zero or more `is`/`es`
   repeats (NOT mixed — Lilypond doesn't mix sharps and flats in one token,
   and neither do the tests), followed by zero or more `'` or `,` (not
   mixed) for absolute octave marks.
2. Compute `(d, c)` from the letter + accidental count (each `is` = +1
   half-step, each `es` = -1 half-step) exactly like the ASCII `#`/`b`
   accidental logic in `from_string`, just with different token spelling.
3. **Octave resolution:**
   - If `'`/`,` marks present: absolute octave = (count of `'`) - (count of
     `,`), i.e. marks only ever appear as all-`'` or all-`,` in the tests,
     so `octave = len(marks) if marks[0] == "'" else -len(marks)`.
   - If no marks and `prev_note` is given: use
     `ta.tonal_nearest_instance(prev_note, (d,c))` (via
     `TonalVector(prev_note).nearest_instance(TonalVector((d,c)))`, which is
     already implemented and tested) to get the correctly-octave-qualified
     result, honoring Lilypond's "within a fourth of the previous note"
     rule. This is **already implemented** in `tonal_arithmetic.py` /
     `TonalVector.nearest_instance` — just call it, don't reimplement.
   - If no marks and no `prev_note`: default to octave 0 (Lilypond's
     built-in default octave, matching OMK octave 0).
   - If marks ARE present AND `prev_note` is given (relative + shift, e.g.
     `"g'"` from `prev=(0,0,0)` expected `(4,7,0)` — note: relative octave
     of bare "g" from c0 is `(4,7,-1)` per `tonal_nearest_instance`, then
     the `'` mark shifts that up by one more octave → `(4,7,0)`. Similarly
     `"c,"` from `prev=(4,7,0)`: bare "c" relative to g0 is `(0,0,1)`, then
     `,` shifts down one → `(0,0,0)`.) So: compute the relative-octave base
     first (via `nearest_instance` against `prev_note`), THEN apply the
     mark-count as an additional shift on top.
4. Validate the letter is a-g; raise `ValueError` otherwise (covers `"h"`,
   `"c#"` — `#` isn't valid Lilypond so falls through to invalid, `"cx"`,
   `"banana"`, `""`).

### Shared helper suggestion

A function like:
```python
def _accidental_offset_from_suffix_count(is_count, es_count):
    return is_count - es_count
```
and reusing `AC` (from `constants.py`) for `from_string`'s accidental
lookup (both parsing FROM a suffix string and validating range, e.g.
clamping to whatever the `AC` dict actually covers, -4..+4) will keep both
methods consistent internally.

---

## 6. Validation checklist once implemented

Run in this order:
```bash
uv run pytest --doctest-modules src/openmusickit/systems/wsmn/tonal/tonal_vector.py -q
uv run pytest tests/tones/test_from_string.py -q
uv run pytest tests/tones/test_from_ly.py -q
uv run pytest tests/tones/test_string_roundtrip.py -q
uv run pytest -q   # full suite, confirm no regressions
```
All should pass with zero failures when done. If any test in the existing
suites looks actually wrong/contradictory during implementation, **stop and
ask the developer** rather than silently editing the test file.
