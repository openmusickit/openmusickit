"""Helpers for the visualization tests: reading a `DotGraph` by OMK object."""

from openmusickit.objects.omk_object import OmkObject
from openmusickit.visualization.dot import DotEdge, DotGraph, DotNode


def nid(obj: OmkObject) -> str:
    return str(obj.id)


def end_id(obj: OmkObject) -> str:
    """The id of the visualization-only end marker of a spanner or sync line."""
    return f"{obj.id}-end"


def column_of(model: DotGraph, node_id: str) -> int:
    """The rank (column index) the node is in."""
    for index, column in enumerate(model.ranks):
        if node_id in column:
            return index
    raise KeyError(node_id)


def column(model: DotGraph, node_id: str) -> list[str]:
    """The ids of the node's column in row order, without the spine node."""
    return [i for i in model.ranks[column_of(model, node_id)] if not i.startswith("_spine_")]


def node(model: DotGraph, node_id: str) -> DotNode:
    for candidate in model.nodes:
        if candidate.id == node_id:
            return candidate
    raise KeyError(node_id)


def edges(model: DotGraph, source: str, target: str) -> list[DotEdge]:
    return [e for e in model.edges if e.source == source and e.target == target]


def edge(model: DotGraph, source: str, target: str) -> DotEdge:
    found = edges(model, source, target)
    assert len(found) == 1, f"{len(found)} edges from {source} to {target}"
    return found[0]
