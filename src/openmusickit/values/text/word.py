from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.errors import LyricConsistencyError


class LexicalStress(StrEnum):
    UNSTRESSED = auto()
    SECONDARY = auto()
    PRIMARY = auto()


@dataclass(frozen=True, slots=True)
class Word:
    """The syllables of one word, as they are sung, and its accent pattern.

    One Word is shared by the `LyricSyllable`s that spell it; each of them
    holds an index into it. Nobody needs to build one by hand: lyrics are
    typed as text and go through `parse_lyrics` (or `Word.from_string`).

    Syllables are the display form, so punctuation stays inside them
    (`"ia,"`). `stress` is parallel to `syllables`; unmarked syllables are
    `None`, and at most one syllable is `PRIMARY`.

    >>> word = Word.from_string("al-le-'lu-ia")
    >>> word
    Word('al', 'le', 'lu', 'ia', stress={2: 'primary'})
    >>> str(word), len(word), word[2], word.primary
    ('alleluia', 4, 'lu', 2)
    >>> word.stress_at(2), word.stress_at(0)
    (<LexicalStress.PRIMARY: 'primary'>, None)

    Stress can also be given by index or as a parallel sequence:

    >>> Word(["al", "le", "lu", "ia"], stress={2: LexicalStress.PRIMARY}) == word
    True
    >>> Word(["al", "le", "lu", "ia"], stress=[None, None, LexicalStress.PRIMARY, None]) == word
    True

    >>> Word([])
    Traceback (most recent call last):
    ...
    openmusickit.errors.LyricConsistencyError: A Word needs at least one syllable.
    >>> Word(["al", ""])
    Traceback (most recent call last):
    ...
    openmusickit.errors.LyricConsistencyError: A syllable cannot be empty: ['al', ''].
    >>> Word(["al", "le"], stress={0: LexicalStress.PRIMARY, 1: LexicalStress.PRIMARY})
    Traceback (most recent call last):
    ...
    openmusickit.errors.LyricConsistencyError: A Word has at most one PRIMARY stress, got 2 in ['al', 'le'].
    """

    syllables: tuple[str, ...]
    stress: tuple[LexicalStress | None, ...]

    def __init__(
        self,
        syllables: Iterable[str],
        stress: Mapping[int, LexicalStress] | Iterable[LexicalStress | None] | None = None,
    ) -> None:
        syllables = tuple(syllables)
        if not syllables:
            raise LyricConsistencyError("A Word needs at least one syllable.")
        if any(not syllable.strip() for syllable in syllables):
            raise LyricConsistencyError(f"A syllable cannot be empty: {list(syllables)!r}.")

        if stress is None:
            stress = (None,) * len(syllables)
        elif isinstance(stress, Mapping):
            marks = [None] * len(syllables)
            for index, mark in stress.items():
                if not 0 <= index < len(syllables):
                    raise LyricConsistencyError(
                        f"Stress index {index} is out of range for {list(syllables)!r}."
                    )
                marks[index] = mark
            stress = tuple(marks)
        else:
            stress = tuple(stress)
            if len(stress) != len(syllables):
                raise LyricConsistencyError(
                    f"stress has {len(stress)} entries for {len(syllables)} syllables: {list(syllables)!r}."
                )
        primaries = stress.count(LexicalStress.PRIMARY)
        if primaries > 1:
            raise LyricConsistencyError(
                f"A Word has at most one PRIMARY stress, got {primaries} in {list(syllables)!r}."
            )

        object.__setattr__(self, "syllables", syllables)
        object.__setattr__(self, "stress", stress)

    @classmethod
    def from_string(
        cls,
        word: str,
        hyphen: str = "-",
        primary: str | None = "'",
        secondary: str | None = ",",
    ) -> Word:
        """Builds a Word from its hyphenated spelling.

        A syllable prefixed with `primary` carries the primary stress, one
        prefixed with `secondary` a secondary stress (the IPA marks ˈ and ˌ,
        transliterated). A *leading* comma is never punctuation, so the
        default marks do not collide with a trailing one. Empty pieces from
        doubled or trailing hyphens are dropped. Pass `primary=None` (and
        `secondary=None`) to turn stress markup off.

        >>> Word.from_string("Je-sus")
        Word('Je', 'sus')
        >>> Word.from_string("'Je-sus,")
        Word('Je', 'sus,', stress={0: 'primary'})
        >>> Word.from_string(",un-der-'stand")
        Word('un', 'der', 'stand', stress={0: 'secondary', 2: 'primary'})
        >>> Word.from_string("'tis", primary=None)
        Word("'tis")
        >>> Word.from_string("Al--le-")
        Word('Al', 'le')
        """
        syllables = []
        stress = {}
        for piece in word.split(hyphen):
            if not piece:
                continue
            if primary and piece.startswith(primary):
                stress[len(syllables)] = LexicalStress.PRIMARY
                piece = piece[len(primary) :]
            elif secondary and piece.startswith(secondary):
                stress[len(syllables)] = LexicalStress.SECONDARY
                piece = piece[len(secondary) :]
            syllables.append(piece)
        return cls(syllables, stress)

    def stress_at(self, index: int) -> LexicalStress | None:
        return self.stress[index]

    @property
    def primary(self) -> int | None:
        """The index of the PRIMARY syllable, if one is marked."""
        try:
            return self.stress.index(LexicalStress.PRIMARY)
        except ValueError:
            return None

    def __iter__(self):
        return iter(self.syllables)

    def __len__(self):
        return len(self.syllables)

    def __getitem__(self, index):
        return self.syllables[index]

    def __str__(self) -> str:
        return "".join(self.syllables)

    def __repr__(self) -> str:
        syllables = ", ".join(repr(syllable) for syllable in self.syllables)
        marks = {index: str(mark) for index, mark in enumerate(self.stress) if mark is not None}
        stress = f", stress={marks!r}" if marks else ""
        return f"{type(self).__name__}({syllables}{stress})"
