"""WSMN bar lines: what is drawn at a division."""

from dataclasses import dataclass
from enum import StrEnum, auto

from openmusickit.values.scoring.division_shape import DivisionShape


class BarLineComponent(StrEnum):
    """One element of a bar line."""

    THIN = auto()
    THICK = auto()
    DASHED = auto()
    DOTTED = auto()
    SHORT = auto()  # through the lower part of the staff only (MusicXML "short", LilyPond ",")
    TICK = auto()  # a small stroke at the top line (MusicXML "tick", LilyPond "'")
    DOTS = auto()  # repeat dots as the glyph draws them; visual only, control flow owns repeats


@dataclass(frozen=True, slots=True, init=False)
class BarLineShape(DivisionShape):
    r"""A WSMN bar line: its components in time order,
    the order LilyPond's `\bar` strings use (`:|.` is DOTS, THIN, THICK).

    A shape with no components is the invisible bar line
    (LilyPond `\bar ""`, MusicXML `none`).
    The ready-made shapes are in `symbols`
    (`single_bar`, `final_bar`, `end_repeat`, ...).

    Examples
    --------
    >>> BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK)
    BarLineShape(BarLineComponent.DOTS, BarLineComponent.THIN, BarLineComponent.THICK)
    >>> BarLineShape()
    BarLineShape()
    >>> BarLineShape(BarLineComponent.THIN) == BarLineShape(BarLineComponent.THIN)
    True
    >>> BarLineShape(BarLineComponent.THIN).components
    (<BarLineComponent.THIN: 'thin'>,)
    """

    components: tuple[BarLineComponent, ...]

    def __init__(self, *components: BarLineComponent) -> None:
        object.__setattr__(self, "components", components)

    def __repr__(self) -> str:
        inner = ", ".join(f"BarLineComponent.{component.name}" for component in self.components)
        return f"{type(self).__name__}({inner})"
