# Lyrics: syllables as events, Word, LyricSection

## Context

`_plans/revisit.md` has one open entry: the lyrics design. `LyricSyllable` is a
plain `OmkObject` that the graph nevertheless places with NEXT edges (a type
mismatch that only works because nothing checks); `LyricSequence` is a `list`
subclass carrying an id and section metadata that `add_lyric_sequence` throws
away; and the placement/location validation keeps three redundant copies of one
fact (which word, which position) mutually consistent without being able to
check `END`/`MIDDLE` at all.

Decisions from the walk-through (2026-09-19):

- **`LyricSyllable` stays `LyricSyllable`** and becomes a `SequentialEvent`. No
  separate syllable value: there is no algebra on syllables, no sharing, and
  `OmkObject.__eq__` already compares content. `{Thing}Event` was never a
  decided convention; the name says "one syllable goes here".
- **A shared, frozen `Word`** replaces the per-syllable `word`/`location`/
  `placement` copies and also carries the accent pattern (stress by index),
  since stress is a property of the word, not of the occurrence. Each syllable
  holds `word` + `index`; text, placement and lexical stress are derived;
  validation collapses to a bounds check. Nobody types a `Word` by hand:
  construction helpers turn typed lyrics (with optional `'`/`,` stress marks)
  into syllables and (optionally) straight into a NEXT line on the graph.
- **`LyricSequence` → `LyricSection(Spanner)`**, over first/last syllable with
  `STARTS_AT`/`ENDS_AT`. It carries the section metadata and the language. This
  sets the pattern for general `Section`s later (also Spanner subclasses).
- `duration` on a syllable is inherited, default `None`; the sung length is the
  attached notes'. Not forced (lyrics without music may carry rhythm).

## Changes

### 1. `values/text/word.py` (new) + `values/text/__init__.py`

`LexicalStress` moves here from `objects/lyrics.py` (it is word-level vocabulary).

```python
@dataclass(frozen=True, slots=True)
class Word:
    """The syllables of one word, as they are sung, and its accent pattern.
    Shared by the LyricSyllables that spell it; humans get one from `parse_lyrics`."""
    syllables: tuple[str, ...]
    stress: tuple[LexicalStress | None, ...]     # parallel to syllables; all None by default

    def __init__(self, syllables: Iterable[str],
                 stress: Mapping[int, LexicalStress] | Iterable[LexicalStress | None] | None = None)
        # object.__setattr__, like ToneCollection; a mapping is index -> stress
    __len__, __getitem__, __iter__               # over syllable strings
    def stress_at(self, index: int) -> LexicalStress | None
    @property primary -> int | None              # index of the PRIMARY syllable, if marked
    def __str__(self) -> str: "".join(self.syllables)
    @classmethod from_string(cls, word: str, hyphen="-", primary="'", secondary=",") -> Word
        # "al-le-'lu-ia": a syllable prefixed with `primary` is PRIMARY, with `secondary` SECONDARY
        # (IPA ˈ ˌ transliterated; a *leading* comma is never punctuation, a trailing one is kept as text)
```

Validation (`LyricConsistencyError`): at least one syllable, none empty;
`stress` same length as `syllables`; at most one `PRIMARY`.
Punctuation stays inside the syllable text (it is the display form: `"ia,"`).

`values/__init__.py` gains `text` (uniform package inits). Docstring notes
`Word` is not system-specific and is not meant to be subclassed.

### 2. `objects/lyrics.py`

- Delete the TODO, `LyricSequence`, and the `word`/`location`/`placement`/
  `lexical_stress`/`language` fields. `LexicalStress` moves to `values/text`.
- `SyllablePlacement` stays (placement is now derived; the four-way enum is
  what notation/MusicXML `syllabic` needs).

```python
@dataclass(kw_only=True, slots=True)
class LyricSyllable(SequentialEvent):
    word: Word
    index: int = 0

    __post_init__: 0 <= index < len(word) else LyricConsistencyError
    text -> word[index]
    lexical_stress -> word.stress_at(index)
    placement -> WHOLE if len(word) == 1; BEGINNING if index == 0;
                 END if index == len(word) - 1; else MIDDLE
    syl_str(hyphen="-")  # fix END: f"{hyphen} {self.text}" (currently wrong way round)
    __str__ -> syl_str()
    __repr__ -> LyricSyllable('lu', 2/4)  or similar compact form
```

```python
@dataclass(kw_only=True, slots=True)
class LyricSection(Spanner):
    """A verse, chorus, refrain ...: a Spanner over a line of LyricSyllables."""
    section_type: str | None = None
    section_number: int | None = None
    section_name: str | None = None      # __post_init__: default f"{type} {number}" only when type is given
    language: str | None = None          # BCP 47 tag (not necessarily two letters)
```

Helper (module level):

```python
def parse_lyrics(text: str, hyphen: str = "-", primary: str = "'", secondary: str = ",") -> list[LyricSyllable]:
    """'Al-le-'lu-ia, sing to 'Je-sus' -> ten syllables in four Words, with
    'lu' and 'Je' marked PRIMARY. Whitespace separates words; `hyphen`
    separates syllables; each word goes through `Word.from_string`. A token
    ending in the hyphen continues into the next token ('Al- le- lu- ia' and
    line-wrapped 'Al-\\nle-lu-ia' both work). Empty pieces from doubled
    hyphens are dropped. Pass `primary=None` to turn stress markup off."""
```

Doctests on `parse_lyrics`, `placement`, `syl_str`, and the bounds error.

### 3. `graph/graph.py` — lyrics section

- Import `LyricSection`, `LyricSyllable`, `parse_lyrics` (drop `LyricSequence`).
- Remove `add_lyric_syllable` (it is `add_node`) and `add_lyric_sequence`.
- Add:

```python
def add_lyrics(
    self,
    lyrics: str | Iterable[LyricSyllable],
    section: LyricSection | None = None,
    after: LyricSyllable | None = None,
) -> list[LyricSyllable]:
    """Adds a line of syllables (NEXT edges made automatically); a string is
    parsed with `parse_lyrics`. `section`, if given, is added as a Spanner
    over the first and last syllable. `after` appends to an existing line.
    Returns the syllables in order, ready for `zip_lyrics_to_objects`."""
```

  Uses `add_line`, `add_next`, `add_spanner`. Empty input with a `section`
  raises `ValueError` (a spanner needs endpoints).
- `unlink_lyric_sequence`: `syllable == stop_syllable` → `is`
  (`OmkObject.__eq__` ignores id, so `==` would stop at any equal-content
  syllable).
- Type hints: `connect_lyric_to_object`, `zip_lyrics_to_objects`, `unlink_*`
  take `LyricSyllable`; `obj` stays `OmkObject`/`SequentialEvent` as now.
- Doctest on `add_lyrics`: parse "Al-le-lu-ia", zip onto four `NoteEvent`s,
  check `get_next` chain, `str()` of each syllable, and the section's
  `STARTS_AT`/`ENDS_AT` edges.

### 4. Tests — `tests/objects/test_lyrics.py` (new)

- `Word`: construction, `from_string` with and without stress marks, stress
  from a mapping and from a sequence, length mismatch / two PRIMARYs / empty
  or blank syllable errors, `stress_at`, `primary`, equality and hashing
  (stress counts), `str`.
- `parse_lyrics`: single words, hyphenated words, trailing-hyphen continuation
  across whitespace and newlines, punctuation retained (trailing comma is
  text, leading comma is SECONDARY), doubled hyphens, `primary=None`
  disables markup, empty string → `[]`; every syllable of one word shares the
  *same* `Word` object (`is`).
- `LyricSyllable`: placement for lengths 1/2/3+, `syl_str` all four
  placements, `lexical_stress` derived, index out of range raises, negative
  index raises, `duration` defaults `None` and accepts a `Duration`.
- `LyricSection`: `section_name` default with and without `section_type`;
  is a `Spanner`.
- Graph: `add_lyrics` with string and with pre-built list, `after=` appends,
  section spanner edges present, `unlink_lyric_sequence` stops at the given
  object and not at an equal-content one.

### 5. Housekeeping

- `objects/__init__.py` docstring still says "that syllable ... LyricSyllable"
  — accurate; no change. `errors.py` `LyricConsistencyError` unchanged.
- Move the "Lyrics design" entry of `_plans/revisit.md` under `## Resolved`
  with a short note (anchor on the full `## Lyrics design ...` heading up to
  the next `^## `). Copy this plan to `_plans/completed/lyrics.md`.
- After leaving plan mode: memory note that `{Thing}Event` naming evolved
  rather than being decided (`NoteEvent` because `Note` is ambiguous with
  several tones; `ChordEvent` because `Chord` was taken), so it is not a
  convention to extend.

## Not doing (noted for later)

- Skipping rests / handling melismas in `zip_lyrics_to_objects` — it is still
  strictly one-to-one.
- Respelling a word already on the graph (changes syllable count → edits the
  line); no helper yet.
- Elision and extender lines in `parse_lyrics`.
- Stress on a `Word` already on the graph: `Word` is frozen, so that is a
  rebuild-and-reassign like any respelling (no helper yet).
- General `Section(Spanner)`.

## Verification

- `uv run pytest` (doctests in `src` run via `--doctest-modules`; the new
  tests under `tests/objects/`).
- `grep -rn "LyricSequence\|add_lyric_sequence\|add_lyric_syllable\|\.location\b" src tests docs`
  returns nothing.
- Round trip in a REPL: `g.add_lyrics("Al-le-lu-ia", section=LyricSection(section_type="verse", section_number=1))`
  then `" ".join(str(s) for s in ...)` gives `"Al - - le - - lu - - ia"` and
  the four notes each have one incoming/outgoing LYRIC edge after zipping.
