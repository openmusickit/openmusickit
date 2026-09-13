from __future__ import annotations
from fractions import Fraction
from typing import Tuple, Iterable

from openmusickit.values.time.duration import TemporalUnit, CompoundTemporalUnit
from openmusickit.values.time.errors import ScalingError


class TimeSignature(CompoundTemporalUnit):
    """A WSMN time signature: an ordered series of TemporalUnits
    (one for simple meters, several for additive meters such as 2+2+3/8),
    with an optional presentation (the numbers as printed).

    ```
    four_four = TimeSignature(TemporalUnit(4, MeteredDuration(1, 4)), presentation=("4", "4"))
    seven_eight = TimeSignature(
        [TemporalUnit(2, eighth), TemporalUnit(2, eighth), TemporalUnit(3, eighth)],
        presentation=("2+2+3", "8"))
    ```

    A TimeSignature compares equal to anything of the same total length,
    so 4/4 == 2/2 == 8/8.
    """

    def __init__(self, spec: TemporalUnit|Iterable[TemporalUnit]|CompoundTemporalUnit,
                 presentation: Tuple[str, str]=None):
        
        if isinstance(spec, TemporalUnit):
            spec = [spec,]
        elif isinstance(spec, CompoundTemporalUnit):
            spec = spec._units
        
        super().__init__(spec)

        self._presentation = tuple(presentation) if presentation else None

    @property
    def spec(self):
        return self._units

    @property
    def presentation(self) -> Tuple[str, str] | None:
        return self._presentation
    
    @property
    def n(self):
        if self._presentation:
            return self._presentation[0]
        return None
        
    @property
    def d(self):
        if self._presentation:
            return self._presentation[1]
        return None

    def scale(self, scalar) -> TimeSignature:
        """Scale the time signature.

        Counts are scaled when they stay whole (4/4 * 2 = 8/4; 6/8 / 2 = 3/8),
        otherwise the denominator changes (3/8 / 2 = 3/16).
        The presentation is scaled the same way when it is numeric;
        a non-numeric presentation (e.g. "C") is dropped.

        Raises:
            ScalingError: if the result is not notatable (e.g. 4/4 / 3).
        """
        scalar = Fraction(scalar)
        if scalar <= 0:
            raise ScalingError("A TimeSignature can only be scaled by a positive scalar.")

        # Scale all groups in unison, so an additive meter keeps a single denominator:
        # if any group's count would stop being whole, every group moves to the smaller base.
        new_counts = [tu.count * scalar for tu in self._units]
        leftover = 1
        for c in new_counts:
            if c.denominator > leftover:
                leftover = c.denominator
        if leftover & (leftover - 1) != 0:
            raise ScalingError(f"Cannot scale {self!r} by {scalar}: the result is not notatable.")

        try:
            new_units = [
                TemporalUnit(int(c * leftover), tu.base.scale(Fraction(1, leftover)))
                for tu, c in zip(self._units, new_counts)
            ]
        except ScalingError as e:
            raise ScalingError(f"Cannot scale {self!r} by {scalar}: {e}")

        return TimeSignature(new_units, presentation=_scale_presentation(self._presentation, scalar))

    def __repr__(self):
        if self._presentation:
            return f"TimeSignature({self._units!r}, {self._presentation})"
        else:
            return f"TimeSignature({self._units!r})"


def _scale_presentation(presentation: Tuple[str, str] | None, scalar) -> Tuple[str, str] | None:
    """Scale a numeric presentation like ("2+2+3", "8") by the same rule as TemporalUnit.scale."""
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

    # push the largest leftover denominator into the bottom number
    leftover = max(t.denominator for t in new_tops)
    if leftover & (leftover - 1) != 0:
        raise ScalingError(f"Cannot scale time signature {presentation} by {scalar}.")
    new_tops = [t * leftover for t in new_tops]
    return ("+".join(str(int(t)) for t in new_tops), str(bottom * leftover))
