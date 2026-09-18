from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from .errors import LyricConsistencyError
from openmusickit.utils.id import OmkId
from openmusickit.objects.omk_object import OmkObject


class LexicalStress(Enum):
    UNSTRESSED = auto()
    SECONDARY = auto()
    PRIMARY = auto()

class SyllablePlacement(Enum):
    BEGINNING = auto()
    MIDDLE = auto()
    END = auto()
    WHOLE = auto()

    def is_beginning(self) -> bool:
        return self in (SyllablePlacement.BEGINNING, SyllablePlacement.WHOLE)
    
    def is_ending(self) -> bool:
        return self in (SyllablePlacement.END, SyllablePlacement.WHOLE)

# TODO: Lyrics need to be an event, as they occur in sequence.

@dataclass(kw_only=True)
class LyricSyllable(OmkObject):
    """A single syllable of lyric text.
    
    The syllable string should not include hyphens."""
    s: str
    word: str | None # The full word. Identical to `s` in single-syllable words.
    location: int | None = 0 # The zero-indexed location of the syllable in the word. `0` for single-syllable words.
    placement: SyllablePlacement | None = SyllablePlacement.WHOLE
    lexical_stress: LexicalStress | None = None
    language: str | None = None # Two letter BCP 47 language code.

    def __post__init__(self):
        """Validates syllable placement/location is consistent."""
        if self.word is None:
            self.word = self.s

        if self.s not in self.word:
            raise LyricConsistencyError(
                f"Syllable should be in word. {self.s} is not in {self.word}."
            )
        if self.location < 0 or type(self.location) != int:
            raise ValueError(
                f"location must be 0 or a positive integer"
            )
        if self.s == self.word:
            if self.location > 0:
                raise LyricConsistencyError(
                    f"Syllables representing an entire word should have location of 0, got {self.location}.")
            if self.placement is not SyllablePlacement.WHOLE:
                raise LyricConsistencyError(
                    f"Syllables representing an entire word should have placement of 'whole', got {self.placement}."
                )
        else:
            if self.placement is SyllablePlacement.WHOLE:
                raise LyricConsistencyError(
                    f"placement='whole', but {self.s} is not the whole word {self.word}"
                )
        


    @property
    def id(self):
        """The stable identity of the musical event, across sessions and storage."""
        return self.__id
    
    @property
    def meta(self):
        return self.__meta

    def __string__(self):
        return self.syl_str()
    
    def syl_str(self, hyphen: str = "-"):
        if self.placement in [SyllablePlacement.WHOLE, None]:
            return self.s
        if self.placement is SyllablePlacement.BEGINNING:
            return f"{self.s} {hyphen}"
        if self.placement is SyllablePlacement.MIDDLE:
            return f"{hyphen} {self.s} {hyphen}"
        if self.placement is SyllablePlacement.END:
            return f"{self.s} {hyphen}"

    
class LyricSequence(list):
    """A list of LyricSyllables,
    usually representing a complete verse, stanza, chorus, or other section."""

    def __init__(
        self,
        syllables: Iterable[LyricSyllable] = (),
        section_type: str | None = None,
        section_number: int | None = None,
        section_name: str | None = None,
        language: str | None = None, # Two letter BCP 47 language code.
        id: OmkId | str | None = None,
    ) -> None:
        super().__init__(syllables)
        self.section_type = section_type
        self.section_number = section_number
        self.section_name = section_name or f"{section_type} {section_number}"
        self.__id = OmkId(id)

    @property
    def id(self):
        """The stable identity of the LyricSequence, across sessions and storage."""
        return self.__id
    
