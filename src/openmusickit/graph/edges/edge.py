from enum import StrEnum, auto
from dataclasses import dataclass, field

from openmusickit.utils.id import OmkId

class EdgeType(StrEnum):
    NEXT = auto()
    IMPLEMENTS = auto()
    REALIZES = auto()
    ANNOTATES = auto()
    ARTICULATION = auto()
    LYRIC = auto()
    ACCOMPANIES = auto()
    HARMONIZES = auto()
    VARIATION_OF = auto()
    DERIVATIVE_OF = auto()
    SIMULTANEOUS = auto()
    CONTAINS = auto()
    REFERENCES = auto()
    USER_DEFINED = auto()
    STARTS_AT = auto()
    ENDS_AT = auto()

class EdgeOrigin(StrEnum):
    ASSERTED = auto()
    DERIVED = auto()
    INFERRED = auto()

@dataclass(slots=True)
class OmkEdge:
    type: EdgeType
    origin: EdgeOrigin = EdgeOrigin.ASSERTED
    _meta: dict = field(default_factory=dict)
    _id: OmkId = field(default_factory=OmkId.new)
    

