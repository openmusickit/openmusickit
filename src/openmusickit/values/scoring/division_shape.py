"""How a notation system draws a division in a sequence."""


class DivisionShape:
    """How a notation system draws a division between one stretch of a line
    and the next.

    This is the general idea behind what WSMN calls a bar line,
    and what chant notation draws as a quarter, half, full or double bar:
    WSMN's `BarLineShape` (lines and repeat dots, in time order) is one
    implementation.
    A `DivisionEvent` places one in a score.
    Nothing here is measure-based:
    a division is wherever the author says it is,
    whatever a time signature would imply.

    Anything that is one system's drawing vocabulary
    (WSMN's thin and thick lines, for instance)
    belongs to the implementing system, not here.

    >>> from openmusickit.systems.wsmn.scoring.bar_line_shape import BarLineShape
    >>> isinstance(BarLineShape(), DivisionShape)
    True
    """

    __slots__ = ()
