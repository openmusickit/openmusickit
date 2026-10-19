"""WSMN brackets and braces: what is drawn at the left of a group of staves."""

from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.values.scoring.stack_group_shape import StackGroupShape


class BracketSymbol(StrEnum):
    """The symbol at the left of a group of staves (MusicXML `group-symbol`)."""

    BRACKET = auto()
    BRACE = auto()
    LINE = auto()  # a plain vertical line
    SQUARE = auto()  # a bracket with square ends, usually a subgroup


class GroupBarLines(StrEnum):
    """How bar lines are drawn across a group of staves (MusicXML `group-barline`)."""

    SEPARATE = auto()  # each staff's bar lines are its own ("no")
    JOINED = auto()  # drawn through the staves and the gaps between them ("yes")
    MENSURSTRICH = auto()  # drawn in the gaps between staves only


@dataclass(frozen=True, slots=True)
class BracketShape(StackGroupShape):
    """A WSMN group of staves:
    the symbol at its left, or None for none,
    and how its bar lines are drawn.
    The ready-made shapes are in `symbols` (`bracket`, `brace`, ...).

    Examples
    --------
    >>> BracketShape(symbol=BracketSymbol.BRACE, bar_lines=GroupBarLines.JOINED)
    BracketShape(symbol=BracketSymbol.BRACE, bar_lines=GroupBarLines.JOINED)
    >>> BracketShape()
    BracketShape(symbol=None, bar_lines=GroupBarLines.SEPARATE)
    >>> BracketShape(symbol=BracketSymbol.BRACKET) == BracketShape(symbol=BracketSymbol.BRACKET)
    True
    """

    symbol: BracketSymbol | None = None
    bar_lines: GroupBarLines = GroupBarLines.SEPARATE

    def __repr__(self) -> str:
        symbol = None if self.symbol is None else f"BracketSymbol.{self.symbol.name}"
        return (
            f"{type(self).__name__}(symbol={symbol}, bar_lines=GroupBarLines.{self.bar_lines.name})"
        )
