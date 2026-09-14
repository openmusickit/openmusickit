from dataclasses import dataclass
from enum import StrEnum, auto
from bidict import bidict

class MarkType(StrEnum):
    """The type of a Mark."""
    ARTICULATION = auto()
    DYNAMIC = auto()
    ORNAMENT = auto()
    TECHNIQUE = auto()
    FINGERING = auto()
    BOWING = auto()
    BREATH = auto()
    FICTA = auto()
    OTHER = auto()

class AttachmentMode(StrEnum):
    """The attachment mode of a Mark.
    
    SINGLE: A mark that is attached to a single note or event.
    SPAN: A mark that is attached to a span of notes or events.
    DISTRIBUTED: A mark that is attached to a span of notes or events, but
    
    This is not enforced at the OmkGraph level,
    but may be used in validation or rendering to determine how a mark should be applied,
    or whether/why a rendering may fail or produce unexpected results.
    
    """
    SINGLE = auto() # A mark that is attached to a single note or event.
    SPAN = auto() # A mark that is attached to a span of notes or events.
    EITHER = auto() # A mark that can be attached to either a single note or event, or a span of notes or events.

@dataclass(frozen=True, slots=True)
class Mark:
    name: str
    description: str | None = None
    type: MarkType | None = None
    attachment_mode: frozenset[AttachmentMode] | None = None
    aliases: tuple[str, ...] = ()