from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class OmkId:
    """OMK-specific wrapper for UUID4.

    All score objects (nodes, edges, sequence items; notes, chords, events, measures, etc.)
    should have a unique OmkId that is persistent across representations of the score in storage and memory.

    This is not the same as any IDs associated with these objects by other systems,
    such as graph libraries or databases.

    OmkId is NOT used with immutable "building block" values
    (the pitch middle C, the idea of a major chord, the abstract duration of a quarter note, etc),
    only with specific instances of those appearing in a score.
    """

    value: UUID | str | None = None

    def __post_init__(self) -> None:
        if self.value is None:
            object.__setattr__(self, "value", uuid4())
        elif isinstance(self.value, str):
            parsed = UUID(self.value)
            if parsed.version != 4:
                raise ValueError(f"{self.value!r} is not a valid uuid4 string.")
            object.__setattr__(self, "value", parsed)
        elif isinstance(self.value, UUID):
            if self.value.version != 4:
                raise ValueError(f"{self.value!r} is not a valid uuid4.")
        else:
            raise TypeError(f"OmkId value must be a UUID or str, got {type(self.value).__name__}.")

    @classmethod
    def new(cls) -> OmkId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> OmkId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        """Equal to another OmkId, or to the string form of one, with the same UUID.

        String equality is deliberate: persistence layers and graph backends
        carry ids as strings. (Whether OmkId should exist at all, rather than
        plain UUID strings, is an open question -- see _plans/revisit.md.)

        >>> a = OmkId.new()
        >>> a == OmkId(str(a)), a == str(a), a == OmkId.new()
        (True, True, False)
        >>> a == 42
        False
        """
        if isinstance(other, (OmkId, str)):
            return str(self) == str(other)
        return NotImplemented
