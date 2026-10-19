"""How a notation system draws a group of things stacked one above another."""


class StackGroupShape:
    """How a notation system marks a run of stacked things as one unit.

    This is the general idea behind what WSMN draws as a bracket or a brace
    at the left of a system:
    WSMN's `BracketShape` (the symbol, and how bar lines join across the
    group) is one implementation.
    A `StackGroup` places one over a run of a stack.

    Anything that is one system's drawing vocabulary
    (WSMN's brackets and braces, for instance)
    belongs to the implementing system, not here.

    >>> from openmusickit.systems.wsmn.scoring.bracket_shape import BracketShape
    >>> isinstance(BracketShape(), StackGroupShape)
    True
    """

    __slots__ = ()
