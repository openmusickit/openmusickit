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
    PHRASING = auto() # slurs, ties, pedaling, fermatas: marks that shape how events connect and are sustained
    NAVIGATION = auto() # segno, coda, and other signs that direct movement through the score
    TRANSPOSITION = auto() # 8va, 8vb, 15ma, and similar octave lines
    OTHER = auto()

class AttachmentMode(StrEnum):
    """The attachment mode of a Mark.
    
    SINGLE: A mark that is attached to a single note or event.
    SPAN: A mark that is attached to a span of notes or events.
    EITHER: A mark that can be attached to either a single event or a span.
    
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
    attachment_mode: AttachmentMode | None = None
    aliases: tuple[str, ...] = ()