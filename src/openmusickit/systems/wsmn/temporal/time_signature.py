from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from math import lcm

from openmusickit.errors import ScalingError
from openmusickit.values.time.duration import CompoundTemporalUnit, TemporalUnit


@dataclass(frozen=True, slots=True, eq=False)
class TimeSignature(CompoundTemporalUnit):
    """A WSMN time signature: an ordered series of TemporalUnits
    (one for simple meters, several for additive meters such as 2+2+3/8),
    with an optional presentation (the numbers as printed).

    >>> from openmusickit.systems.wsmn.temporal.symbols import quarter, eighth
    >>> four_four = TimeSignature(TemporalUnit(4, quarter), presentation=("4", "4"))
    >>> seven_eight = TimeSignature(
    ...     [TemporalUnit(2, eighth), TemporalUnit(2, eighth), TemporalUnit(3, eighth)],
    ...     presentation=("2+2+3", "8"))
    >>> seven_eight.rational_length
    Fraction(7, 8)

    A TimeSignature compares equal to anything of the same total length,
    so 4/4 == 2/2 == 8/8.

    >>> from openmusickit.systems.wsmn.temporal.symbols import two_two
    >>> four_four == two_two
    True
    """

    presentation: tuple[str, str] | None

    def __init__(
        self,
        spec: TemporalUnit | Iterable[TemporalUnit] | CompoundTemporalUnit,
        presentation: tuple[str, str] | None = None,
    ):
        if isinstance(spec, TemporalUnit):
            spec = [spec]
        super().__init__(spec)
        object.__setattr__(self, "presentation", tuple(presentation) if presentation else None)

    def scale(self, scalar) -> TimeSignature:
        """Scale the time signature.

        Counts are scaled when they stay whole (4/4 * 2 = 8/4; 6/8 / 2 = 3/8),
        otherwise the denominator changes (3/8 / 2 = 3/16).
        An odd factor (4/4 / 3) gives a tupleted denominator (4 triplet eighths).
        The presentation is scaled the same way when it is numeric and the
        result can be written as plain numbers; otherwise it is dropped.

        >>> from openmusickit.systems.wsmn.temporal.symbols import four_four, three_eight
        >>> four_four.scale(2)
        TimeSignature([TemporalUnit(8, MetricalDuration(1, 4))], ('8', '4'))
        >>> three_eight.scale(Fraction(1, 2))
        TimeSignature([TemporalUnit(3, MetricalDuration(1, 16))], ('3', '16'))
        >>> third = four_four.scale(Fraction(1, 3))
        >>> third.rational_length, third.presentation
        (Fraction(1, 3), None)

        Raises
        ------
        ScalingError
            if the scalar is not positive.
        """
        scalar = Fraction(scalar)
        if scalar <= 0:
            raise ScalingError("A TimeSignature can only be scaled by a positive scalar.")

        # Scale all groups in unison, so an additive meter keeps a single denominator:
        # if any group's count would stop being whole, every group moves to the smaller base.
        new_counts = [tu.count * scalar for tu in self.units]
        leftover = lcm(*(c.denominator for c in new_counts))

        try:
            new_units = [
                TemporalUnit(int(c * leftover), tu.base.scale(Fraction(1, leftover)))
                for tu, c in zip(self.units, new_counts, strict=False)
            ]
        except ScalingError as e:
            raise ScalingError(f"Cannot scale {self!r} by {scalar}: {e}") from e

        return TimeSignature(new_units, presentation=_scale_presentation(self.presentation, scalar))

    def __repr__(self):
        if self.presentation:
            return f"{type(self).__name__}({list(self.units)!r}, {self.presentation})"
        return f"{type(self).__name__}({list(self.units)!r})"


def _scale_presentation(presentation: tuple[str, str] | None, scalar) -> tuple[str, str] | None:
    """Scale a numeric presentation like ("2+2+3", "8") by the same rule as TemporalUnit.scale.

    >>> _scale_presentation(("2+2+3", "8"), 2), _scale_presentation(("3", "8"), Fraction(1, 2))
    (('4+4+6', '8'), ('3', '16'))
    >>> _scale_presentation(("4", "4"), Fraction(1, 3)) is None  # a tupleted denominator has no plain numbers
    True
    >>> _scale_presentation(("C", ""), 2) is None  # not numeric
    True
    """
    if presentation is None:
        return None
    try:
        tops = [int(x) for x in presentation[0].split("+")]
        bottom = int(presentation[1])
    except ValueError:
        return None

    scalar = Fraction(scalar)
    new_tops = [t * scalar for t in tops]
    if all(t.denominator == 1 for t in new_tops):
        return ("+".join(str(int(t)) for t in new_tops), str(bottom))

    # push the leftover denominator into the bottom number;
    # an odd factor means a tupleted denominator, which has no plain numeric presentation
    leftover = lcm(*(t.denominator for t in new_tops))
    if leftover & (leftover - 1) != 0:
        return None
    new_tops = [t * leftover for t in new_tops]
    return ("+".join(str(int(t)) for t in new_tops), str(bottom * leftover))
