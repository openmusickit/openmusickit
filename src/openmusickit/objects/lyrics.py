from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.errors import LyricConsistencyError
from openmusickit.objects.omk_object import OmkObject
from openmusickit.utils.id import OmkId


class LexicalStress(StrEnum):
    UNSTRESSED = auto()
    SECONDARY = auto()
    PRIMARY = auto()


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


# TODO: Lyrics need to be an event, as they occur in sequence.


@dataclass(kw_only=True)
class LyricSyllable(OmkObject):
    """A single syllable of lyric text.

    The syllable string should not include hyphens."""

    text: str
    word: str | None  # The full word. Identical to `text` in single-syllable words.
    location: int | None = (
        0  # The zero-indexed location of the syllable in the word. `0` for single-syllable words.
    )
    placement: SyllablePlacement | None = SyllablePlacement.WHOLE
    lexical_stress: LexicalStress | None = None
    language: str | None = None  # Two letter BCP 47 language code.

    def __post_init__(self):
        """Validates syllable placement/location is consistent."""
        if self.word is None:
            self.word = self.text

        if self.text not in self.word:
            raise LyricConsistencyError(
                f"Syllable should be in word. {self.text} is not in {self.word}."
            )
        if not isinstance(self.location, int) or self.location < 0:
            raise LyricConsistencyError("location must be 0 or a positive integer")
        if self.text == self.word:
            if self.location > 0:
                raise LyricConsistencyError(
                    f"Syllables representing an entire word should have location of 0, got {self.location}."
                )
            if self.placement is not SyllablePlacement.WHOLE:
                raise LyricConsistencyError(
                    f"Syllables representing an entire word should have placement of 'whole', got {self.placement}."
                )
        else:
            if self.placement is SyllablePlacement.WHOLE:
                raise LyricConsistencyError(
                    f"placement='whole', but {self.text} is not the whole word {self.word}"
                )

    def __str__(self):
        return self.syl_str()

    def syl_str(self, hyphen: str = "-") -> str:
        if self.placement in [SyllablePlacement.WHOLE, None]:
            return self.text
        if self.placement is SyllablePlacement.BEGINNING:
            return f"{self.text} {hyphen}"
        if self.placement is SyllablePlacement.MIDDLE:
            return f"{hyphen} {self.text} {hyphen}"
        if self.placement is SyllablePlacement.END:
            return f"{self.text} {hyphen}"


class LyricSequence(list):
    """A list of LyricSyllables,
    usually representing a complete verse, stanza, chorus, or other section."""

    def __init__(
        self,
        syllables: Iterable[LyricSyllable] = (),
        section_type: str | None = None,
        section_number: int | None = None,
        section_name: str | None = None,
        language: str | None = None,  # Two letter BCP 47 language code.
        id: OmkId | str | None = None,
    ) -> None:
        super().__init__(syllables)
        self.section_type = section_type
        self.section_number = section_number
        self.section_name = section_name or f"{section_type} {section_number}"
        self.__id = OmkId(id)

    @property
    def id(self) -> OmkId:
        """The stable identity of the LyricSequence, across sessions and storage."""
        return self.__id
