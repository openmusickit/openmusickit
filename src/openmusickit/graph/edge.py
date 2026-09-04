from enum import StrEnum
from dataclasses import dataclass

from openmusickit.utils.id import OmkId

class EdgeType(StrEnum):
    NEXT = "next"
    PREV = "prev"

@dataclass
class OmkEdge:
    type: EdgeType
    _meta: dict
    _id: OmkId
    

