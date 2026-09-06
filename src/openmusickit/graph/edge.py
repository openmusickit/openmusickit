from enum import StrEnum, auto
from dataclasses import dataclass

from openmusickit.utils.id import OmkId

class EdgeType(StrEnum):
    NEXT = auto()
    IMPLEMENTS = auto()
    REALIZES = auto()
    ANNOTATES = auto()
    LYRIC = auto()
    ACCOMPANIES = auto()
    HARMONIZES = auto()
    VARIATION_OF = auto()
    DERIVATIVE_OF = auto()
    SIMULTANEOUS = auto()
    CONTAINS = auto()
    REFERENCES = auto()
    USER_DEFINED = auto()

@dataclass(slots=True)
class OmkEdge:
    type: EdgeType
    _meta: dict
    _id: OmkId
    

