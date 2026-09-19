class TemporalError(Exception):
    """Base class for temporal system errors."""


class ScalingError(TemporalError):
    """Raised when a TemporalElement cannot perform the requested scaling operation.

    This covers scalars that are invalid in any system (zero, negative,
    non-rational), and scaled values that a particular TemporalSystem
    has no way to represent.

    Systems whose elements can always be re-spelled should do so rather than
    raise (WSMN's MeteredDuration, for example, resolves non-power-of-two
    scalars into dotted values, tuplets, or tied notes). Systems that cannot
    should raise this so callers can fall back to an alternate strategy,
    such as a composite element or a clock-time calculation.
    """


class TemporalCompatibilityError(TemporalError):
    """Raised when temporal elements from incompatible systems are combined.

    Callers may catch this error and implement an alternate compatibility strategy,
    such as clock-time calculations.
    """
