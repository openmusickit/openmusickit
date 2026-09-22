"""Hypothesis strategies for the OMK property tests.

Each function returns a `SearchStrategy`. Finite domains (pitch classes,
the symbol tables) are sampled from the lists in `tests.domains`; the
infinite ones (lengths, note events, lines, spellings, lyric texts) are
built from Hypothesis primitives. The spelling strategies yield `(text,
expected)` pairs, since the point of a spelling is what it must parse to.
"""

from __future__ import annotations

from fractions import Fraction

from hypothesis import strategies as st

from openmusickit.objects.note_event import NoteEvent
from openmusickit.systems.wsmn.percussion.percussion_tone import PercussionTone
from openmusickit.systems.wsmn.temporal import symbols as temporal_symbols
from openmusickit.systems.wsmn.temporal.metrical_duration import MetricalDuration
from openmusickit.systems.wsmn.tonal.constants import ACCIDENTALS, DIATONES, QualityType
from openmusickit.systems.wsmn.tonal.tonal_vector import TonalVector
from openmusickit.utils.number_names import ORDINALS
from tests.domains import (
    ABSTRACT_VECTORS,
    ALL_VECTORS,
    PERCUSSION_TONES,
    QUALIFIED_VECTORS,
    distinct,
    symbols_of,
)

DURATION_SYMBOLS = list(distinct(symbols_of(temporal_symbols, MetricalDuration)).values())

# --- tones ----------------------------------------------------------------------


def tonal_vectors(qualified: bool | None = None) -> st.SearchStrategy[TonalVector]:
    """A pitch class (False), an octave-qualified pitch (True), or either (None), from the domain lists."""
    if qualified is None:
        return st.sampled_from(ALL_VECTORS)
    return st.sampled_from(QUALIFIED_VECTORS if qualified else ABSTRACT_VECTORS)


def percussion_tones() -> st.SearchStrategy[PercussionTone]:
    """Any PercussionTone, from the domain list."""
    return st.sampled_from(PERCUSSION_TONES)


# --- durations ----------------------------------------------------------------------


def metrical_durations() -> st.SearchStrategy[MetricalDuration]:
    """A note value: one of the symbols, or a plain value from a whole to a 128th with up to three dots."""
    constructed = st.builds(
        lambda k, dots: MetricalDuration(1, 2**k, dots), st.integers(0, 7), st.integers(0, 3)
    )
    return st.one_of(st.sampled_from(DURATION_SYMBOLS), constructed)


def positive_fractions(max_denominator: int = 64) -> st.SearchStrategy[Fraction]:
    """A positive rational length, up to two maximas long, with a bounded denominator."""
    return st.fractions(min_value=0, max_value=16, max_denominator=max_denominator).filter(
        lambda x: x > 0
    )


# --- events and lines ----------------------------------------------------------------


def note_events(unpitched: bool = False) -> st.SearchStrategy[NoteEvent]:
    """A NoteEvent with zero to three tones and a note value, or, one time in ten, no duration.

    The tones are pitched; with `unpitched=True` percussion tones are mixed
    in, for tests that never transpose."""
    durations = st.integers(0, 9).flatmap(lambda i: st.none() if i == 0 else metrical_durations())
    tone = st.one_of(tonal_vectors(), percussion_tones()) if unpitched else tonal_vectors()
    tones = st.frozensets(tone, max_size=3).map(set)
    return st.builds(NoteEvent, tones=tones, duration=durations)


def lines(
    min_size: int = 1, max_size: int = 6, unpitched: bool = False
) -> st.SearchStrategy[list[NoteEvent]]:
    """A list of fresh note events, ready for `OmkGraph.add_line`."""
    return st.lists(note_events(unpitched), min_size=min_size, max_size=max_size)


# --- spellings ------------------------------------------------------------------------


def _mixed_case(text: str) -> st.SearchStrategy[str]:
    """`text` with each letter's case chosen at random."""
    return st.tuples(*(st.sampled_from([ch.lower(), ch.upper()]) for ch in text)).map("".join)


def _with_whitespace(text: str) -> st.SearchStrategy[str]:
    """`text` with runs of whitespace inserted at random before, between and
    after its characters (the parser strips all of it)."""
    gap = st.sampled_from(["", "", "", " ", "  ", "\t"])
    gaps = st.lists(gap, min_size=len(text) + 1, max_size=len(text) + 1)
    return gaps.map(lambda g: "".join(a + ch for a, ch in zip(g, text, strict=False)) + g[-1])


def _accidental_spellings(offset: int) -> list[str]:
    """ASCII, Unicode, and spelled-out (with and without the space) forms of one accidental."""
    accidental = ACCIDENTALS[offset]
    return [
        accidental.ascii,
        accidental.unicode,
        accidental.name,
        accidental.name.replace(" ", ""),
    ]


def pitch_spellings() -> st.SearchStrategy[tuple[str, TonalVector]]:
    """A letter-name spelling `from_string` must accept (any accidental in any
    of its spellings, joined directly, by a space or by a hyphen, with or
    without an octave number), in random case and whitespace, with the
    TonalVector it must parse to."""

    @st.composite
    def build(draw) -> tuple[str, TonalVector]:
        diatone = draw(st.sampled_from(DIATONES))
        offset = draw(st.sampled_from(sorted(ACCIDENTALS)))
        spelling = draw(st.sampled_from(_accidental_spellings(offset)))
        separator = draw(st.sampled_from(["", " ", "-"])) if spelling else ""
        octave = draw(st.one_of(st.none(), st.integers(-2, 9)))
        text = f"{diatone.letter}{separator}{spelling}" + ("" if octave is None else str(octave))
        c = (diatone.chromatic + offset) % 12
        expected = (
            TonalVector((diatone.degree, c))
            if octave is None
            else TonalVector((diatone.degree, c, octave - 4))
        )
        text = draw(_mixed_case(text))
        text = draw(_with_whitespace(text))
        return text, expected

    return build()


_QUALITY_WORDS = {
    "perfect": ["P", "per", "perfect"],
    "major": ["M", "maj", "major"],
    "minor": ["m", "min", "minor"],
    "augmented": ["aug", "augmented"],
    "diminished": ["dim", "diminished"],
}
_MULTIPLIER_WORDS = {
    1: [""],
    2: ["dbl", "double"],
    3: ["trp", "trpl", "triple"],
    4: ["qua", "quad", "quadruple"],
}
_NUMBER_WORDS = {diatone.degree + 1: diatone.interval_name for diatone in DIATONES}


def interval_spellings() -> st.SearchStrategy[tuple[str, TonalVector]]:
    """An interval spelling `from_string` must accept (a quality its degree
    can take, a multiplier for augmented and diminished, the number as
    digits, an ordinal or a word, an optional octave suffix), in random case
    and whitespace, with the TonalVector it must parse to. Bare `M` and `m`
    keep their case, since that is what tells them apart."""

    @st.composite
    def build(draw) -> tuple[str, TonalVector]:
        number = draw(st.integers(1, 13))
        d, octave = (number - 1) % 7, (number - 1) // 7
        diatone = DIATONES[d]
        perfect_type = diatone.quality_type is QualityType.P
        kinds = ["augmented", "diminished"] + (["perfect"] if perfect_type else ["major", "minor"])
        kind = draw(st.sampled_from(kinds))
        times = draw(st.integers(1, 4)) if kind in ("augmented", "diminished") else 1
        if kind == "augmented":
            modifier = times
        elif kind == "diminished":
            modifier = -times if perfect_type else -(times + 1)
        else:
            modifier = -1 if kind == "minor" else 0
        word = draw(st.sampled_from(_QUALITY_WORDS[kind]))
        multiplier = draw(st.sampled_from(_MULTIPLIER_WORDS[times]))
        forms = [str(number), ORDINALS[number]]
        if number in _NUMBER_WORDS:
            forms.append(_NUMBER_WORDS[number])
        number_form = draw(st.sampled_from(forms))
        shift = draw(st.one_of(st.none(), st.integers(-2, 2)))
        suffix = "" if shift is None else f"{shift:+d}"
        c = (diatone.chromatic + modifier) % 12
        if number > 7 or shift is not None:
            expected = TonalVector((d, c, octave + (shift or 0)))
        else:
            expected = TonalVector((d, c))
        if word not in ("M", "m"):
            word = draw(_mixed_case(word))
        multiplier = draw(_mixed_case(multiplier))
        number_form = draw(_mixed_case(number_form))
        text = draw(_with_whitespace(f"{multiplier}{word}{number_form}{suffix}"))
        return text, expected

    return build()


# --- lyrics -------------------------------------------------------------------------------


def lyric_texts() -> st.SearchStrategy[str]:
    """Typed lyrics `parse_lyrics` must accept: words of one to four
    syllables joined by hyphens, at most one syllable per word carrying the
    primary mark and any others a secondary mark, some words ending in
    trailing punctuation, separated by spaces or newlines."""

    @st.composite
    def word(draw) -> str:
        syllables = draw(
            st.lists(
                st.text(alphabet="abcdefghijklmnopqrstuvwxyzé", min_size=1, max_size=5),
                min_size=1,
                max_size=4,
            )
        )
        primary = draw(st.one_of(st.none(), st.integers(0, len(syllables) - 1)))
        marked = []
        for i, syllable in enumerate(syllables):
            if i == primary:
                marked.append("'" + syllable)
            else:
                marked.append(draw(st.sampled_from(["", "", "", ","])) + syllable)
        return "-".join(marked) + draw(st.sampled_from(["", "", ",", ".", "!"]))

    separator = st.sampled_from([" ", " ", "  ", "\n"])
    return st.lists(st.tuples(word(), separator), max_size=6).map(
        lambda pairs: "".join(w + sep for w, sep in pairs).strip()
    )
