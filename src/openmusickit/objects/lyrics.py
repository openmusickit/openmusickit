from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.errors import LyricConsistencyError
from openmusickit.objects.omk_object import SequentialEvent, Spanner
from openmusickit.values.text.word import LexicalStress, Word


class SyllablePlacement(StrEnum):
    BEGINNING = auto()
    MIDDLE = auto()
    END = auto()
    WHOLE = auto()

    @property
    def is_beginning(self) -> bool:
        return self in (SyllablePlacement.BEGINNING, SyllablePlacement.WHOLE)

    @property
    def is_ending(self) -> bool:
        return self in (SyllablePlacement.END, SyllablePlacement.WHOLE)


@dataclass(kw_only=True, slots=True)
class LyricSyllable(SequentialEvent):
    """One sung syllable: the `index`-th syllable of `word`.

    The syllables of a word share one `Word`, so the text, the position in
    the word and the lexical stress are all read from it. Syllables are
    placed in sequence with NEXT edges, and a LYRIC edge from a note marks
    the syllable's onset: the notes that go on sustaining it (a melisma)
    carry no edge, and a note may begin several syllables (a reciting
    tone). The duration is normally `None`: the sung length is the notes'.

    >>> word = Word.from_string("Al-le-'lu-ia")
    >>> lu = LyricSyllable(word=word, index=2)
    >>> lu.text, lu.placement, lu.lexical_stress
    ('lu', <SyllablePlacement.MIDDLE: 'middle'>, <LexicalStress.PRIMARY: 'primary'>)
    >>> [str(LyricSyllable(word=word, index=i)) for i in range(4)]
    ['Al -', '- le -', '- lu -', '- ia']
    >>> LyricSyllable(word=word, index=4)
    Traceback (most recent call last):
    ...
    openmusickit.errors.LyricConsistencyError: Index 4 is out of range for Word('Al', 'le', 'lu', 'ia', stress={2: 'primary'}).
    """

    word: Word
    index: int = 0

    def __post_init__(self):
        if not 0 <= self.index < len(self.word):
            raise LyricConsistencyError(f"Index {self.index} is out of range for {self.word!r}.")

    @property
    def text(self) -> str:
        return self.word[self.index]

    @property
    def lexical_stress(self) -> LexicalStress | None:
        return self.word.stress_at(self.index)

    @property
    def placement(self) -> SyllablePlacement:
        """
        >>> LyricSyllable(word=Word(["sing"])).placement
        <SyllablePlacement.WHOLE: 'whole'>
        >>> [LyricSyllable(word=Word(["Je", "sus"]), index=i).placement for i in range(2)]
        [<SyllablePlacement.BEGINNING: 'beginning'>, <SyllablePlacement.END: 'end'>]
        """
        if len(self.word) == 1:
            return SyllablePlacement.WHOLE
        if self.index == 0:
            return SyllablePlacement.BEGINNING
        if self.index == len(self.word) - 1:
            return SyllablePlacement.END
        return SyllablePlacement.MIDDLE

    def syl_str(self, hyphen: str = "-") -> str:
        """The syllable with the hyphens that connect it to its neighbours."""
        placement = self.placement
        if placement is SyllablePlacement.WHOLE:
            return self.text
        if placement is SyllablePlacement.BEGINNING:
            return f"{self.text} {hyphen}"
        if placement is SyllablePlacement.END:
            return f"{hyphen} {self.text}"
        return f"{hyphen} {self.text} {hyphen}"

    def __str__(self):
        return self.syl_str()

    def __repr__(self):
        duration = f", duration={self.duration!r}" if self.duration is not None else ""
        return f"{type(self).__name__}({self.syl_str()!r}{duration})"


@dataclass(kw_only=True, slots=True)
class LyricSection(Spanner):
    """A verse, chorus, refrain, ...: a Spanner over a line of LyricSyllables
    (STARTS_AT the first, ENDS_AT the last), carrying what is true of the
    whole text rather than of any one syllable.

    `section_name` defaults to "<type> <number>" when a type is given:

    >>> LyricSection(section_type="verse", section_number=2).section_name
    'verse 2'
    >>> LyricSection(section_type="refrain").section_name
    'refrain'
    >>> LyricSection().section_name is None
    True
    """

    section_type: str | None = None
    section_number: int | None = None
    section_name: str | None = None
    language: str | None = None  # BCP 47 language tag ("en", "la", "zh-Hant", ...).

    def __post_init__(self):
        if self.section_name is None and self.section_type is not None:
            parts = (self.section_type, self.section_number)
            self.section_name = " ".join(str(part) for part in parts if part is not None)


def parse_lyrics(
    text: str,
    hyphen: str = "-",
    primary: str | None = "'",
    secondary: str | None = ",",
) -> list[LyricSyllable]:
    """Turns typed lyrics into LyricSyllables, one per syllable, in order.

    Whitespace separates words and `hyphen` separates syllables; each word
    goes through `Word.from_string`, so the stress marks work the same way
    (`primary=None` turns them off). A token ending in the hyphen continues
    into the next token, so "Al- le- lu- ia" and a line-wrapped
    "Al-\\nle-lu-ia" both spell one word.

    >>> syllables = parse_lyrics("Al-le-'lu-ia, sing to 'Je-sus")
    >>> syllables
    [LyricSyllable('Al -'), LyricSyllable('- le -'), LyricSyllable('- lu -'), LyricSyllable('- ia,'), LyricSyllable('sing'), LyricSyllable('to'), LyricSyllable('Je -'), LyricSyllable('- sus')]
    >>> [s.text for s in syllables if s.lexical_stress is LexicalStress.PRIMARY]
    ['lu', 'Je']
    >>> syllables[0].word is syllables[3].word
    True
    >>> [str(s) for s in parse_lyrics("Al- le-\\nlu- ia")]
    ['Al -', '- le -', '- lu -', '- ia']
    >>> parse_lyrics("")
    []
    """
    words: list[str] = []
    for token in text.split():
        if words and words[-1].endswith(hyphen):
            words[-1] += token
        else:
            words.append(token)

    syllables = []
    for spelling in words:
        word = Word.from_string(spelling, hyphen, primary, secondary)
        syllables.extend(LyricSyllable(word=word, index=i) for i in range(len(word)))
    return syllables
